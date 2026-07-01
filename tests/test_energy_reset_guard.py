"""Tests for ``is_untrusted_energy_reading`` (coordinator.py).

Regression for daily charge/discharge energy sensors occasionally reading 0
mid-day (comm noise on the Modbus/HTTP read), which HA's total_increasing
statistics treated as a legitimate meter reset - double-counting the energy
once the real value reappeared, and skewing the Home Consumption calc. Only a
drop to exactly 0 for a "daily" counter near local midnight is a real reset;
anywhere else it must be discarded like any other implausible backward jump.
"""
from __future__ import annotations

from datetime import datetime

from custom_components.omnibattery.infra import coordinator as coordinator_module
from custom_components.omnibattery.infra.coordinator import is_untrusted_energy_reading


def _set_now(monkeypatch, hour, minute):
    monkeypatch.setattr(
        coordinator_module.dt_util, "now", lambda: datetime(2026, 7, 1, hour, minute)
    )


def test_midday_zero_on_daily_counter_is_discarded(monkeypatch):
    _set_now(monkeypatch, 15, 0)
    assert is_untrusted_energy_reading("total_daily_charging_energy", 0, 1.34) is True


def test_midnight_zero_on_daily_counter_is_accepted(monkeypatch):
    _set_now(monkeypatch, 0, 2)
    assert is_untrusted_energy_reading("total_daily_charging_energy", 0, 2.41) is False


def test_midday_zero_on_lifetime_counter_is_discarded(monkeypatch):
    _set_now(monkeypatch, 15, 0)
    assert is_untrusted_energy_reading("total_charging_energy", 0, 491.0) is True


def test_partial_read_backward_jump_is_discarded(monkeypatch):
    _set_now(monkeypatch, 15, 0)
    assert is_untrusted_energy_reading("total_charging_energy", 50.0, 491.0) is True


def test_normal_increase_is_accepted(monkeypatch):
    _set_now(monkeypatch, 15, 0)
    assert is_untrusted_energy_reading("total_daily_charging_energy", 1.5, 1.34) is False


def test_first_reading_with_no_previous_is_accepted():
    assert is_untrusted_energy_reading("total_daily_charging_energy", 0, None) is False
