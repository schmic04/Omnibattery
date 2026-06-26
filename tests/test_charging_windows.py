"""Tests for multi-window predictive charging math.

Covers the union/overnight/merge logic that turns up to 3 charging windows into
the consumption (solar+battery) window, which is their complement.

No Home Assistant runtime: ConsumptionTracker is built via ``__new__`` and wired
to a stand-in controller, mirroring test_charge_delay.
"""
from __future__ import annotations

from types import SimpleNamespace

from custom_components.omnibattery.tracking.consumption_tracker import (
    ConsumptionTracker,
    _merge_window_hours,
)


def _win(start, end, days=None):
    return {"start_time": start, "end_time": end, "days": days or ["mon"]}


def _tracker(slots):
    t = ConsumptionTracker.__new__(ConsumptionTracker)
    t._controller = SimpleNamespace(charging_time_slots=slots)
    return t


def test_merge_single():
    assert _merge_window_hours([_win("02:00:00", "05:00:00")]) == [[2.0, 5.0]]


def test_merge_disjoint():
    slots = [_win("02:00:00", "05:00:00"), _win("12:00:00", "14:00:00")]
    assert _merge_window_hours(slots) == [[2.0, 5.0], [12.0, 14.0]]


def test_merge_overlapping():
    slots = [_win("02:00:00", "05:00:00"), _win("04:00:00", "07:00:00")]
    assert _merge_window_hours(slots) == [[2.0, 7.0]]


def test_merge_overnight_split():
    # 22:00->02:00 splits at midnight then merges into two pieces
    assert _merge_window_hours([_win("22:00:00", "02:00:00")]) == [[0.0, 2.0], [22.0, 24.0]]


def test_merge_overnight_plus_morning():
    slots = [_win("22:00:00", "06:00:00"), _win("02:00:00", "05:00:00")]
    assert _merge_window_hours(slots) == [[0.0, 6.0], [22.0, 24.0]]


def test_window_hours_per_day_union():
    # two disjoint 3h + 2h windows → 24 - 5 = 19h consumption window
    t = _tracker([_win("02:00:00", "05:00:00"), _win("12:00:00", "14:00:00")])
    assert t.get_consumption_window_hours_per_day() == 19.0


def test_window_hours_per_day_no_slots():
    assert _tracker([]).get_consumption_window_hours_per_day() == 24.0


def test_hours_in_range_subtracts_all_windows():
    # consumption hours in [0,12] excluding 02-05 and 12-14 → 12 - 3 = 9
    t = _tracker([_win("02:00:00", "05:00:00"), _win("12:00:00", "14:00:00")])
    assert t.consumption_window_hours_in_range(0.0, 12.0) == 9.0


def test_hours_in_range_no_slots_full_range():
    assert _tracker([]).consumption_window_hours_in_range(6.0, 10.0) == 4.0


if __name__ == "__main__":
    import sys

    failed = 0
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            try:
                fn()
            except AssertionError as e:
                failed += 1
                print(f"FAIL {name}: {e}")
            else:
                print(f"ok   {name}")
    sys.exit(1 if failed else 0)
