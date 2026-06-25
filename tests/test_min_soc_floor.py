"""Tests for the guaranteed-minimum-SOC floor in ``_should_activate_grid_charging`` (#417).

A solar-positive day computes zero (negative) deficit, so the predictive
charger would charge nothing overnight and the battery hits the hardware floor
in the morning before solar ramps up. The floor forces a charge sized to reach
the configured SOC regardless of the daily balance.

The method only touches a handful of attributes, so it is exercised unbound on
a stub controller (no Home Assistant runtime needed).
"""
from __future__ import annotations

import asyncio
from types import SimpleNamespace

from custom_components.omnibattery import ChargeDischargeController


class _Coord:
    def __init__(self, soc, capacity_kwh, min_soc=12, max_soc=95):
        self.min_soc = min_soc
        self.max_soc = max_soc
        self.data = {"battery_soc": soc, "battery_total_energy": capacity_kwh}


def _consumption(value):
    async def _f():
        return value
    return _f


def _ctrl(coords, floor, *, solar="50.0", consumption=2.0):
    # solar far exceeds consumption → natural deficit is negative (no charge).
    return SimpleNamespace(
        predictive_charging_enabled=True,
        coordinators=list(coords),
        _predictive_safety_margin_kwh=0.0,
        _predictive_grid_charge_margin_pct=0.0,
        _predictive_min_soc_floor=floor,
        _daily_consumption_history=[],
        solar_forecast_sensor="sensor.solar",
        hass=SimpleNamespace(states=SimpleNamespace(get=lambda _e: SimpleNamespace(state=solar))),
        _consumption_tracker=SimpleNamespace(get_dynamic_base_consumption=_consumption(consumption)),
    )


def _run(ctrl):
    return asyncio.run(ChargeDischargeController._should_activate_grid_charging(ctrl))


def test_floor_forces_charge_on_solar_positive_day():
    # 10 kWh battery at 15%, floor 30% → needs (30-15)% * 10 = 1.5 kWh.
    result = _run(_ctrl([_Coord(15.0, 10.0)], floor=30.0))
    assert result["should_charge"] is True
    assert abs(result["energy_deficit_kwh"] - 1.5) < 0.05
    assert "Guaranteed minimum" in result["reason"]


def test_floor_disabled_does_not_charge():
    # Same balanced day, floor off → no charge.
    result = _run(_ctrl([_Coord(15.0, 10.0)], floor=0.0))
    assert result["should_charge"] is False


def test_soc_above_floor_no_effect():
    # SOC already above the floor → floor contributes nothing.
    result = _run(_ctrl([_Coord(40.0, 10.0)], floor=30.0))
    assert result["should_charge"] is False


if __name__ == "__main__":
    test_floor_forces_charge_on_solar_positive_day()
    test_floor_disabled_does_not_charge()
    test_soc_above_floor_no_effect()
    print("ok")
