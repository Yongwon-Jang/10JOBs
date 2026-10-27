import pytest

from ten_jobs.algorithms.battery import BatteryMonitor, voltage_to_percent


def test_voltage_mapping_is_clamped():
    assert voltage_to_percent(12.6) == 100.0
    assert voltage_to_percent(11.0) == 0.0
    assert voltage_to_percent(10.0) == 0.0
    assert voltage_to_percent(11.8) == pytest.approx(50.0)


def test_smoothing_ignores_single_spike():
    m = BatteryMonitor(alpha=0.2)
    m.update(80)
    level, _ = m.update(10)  # one bad reading
    assert level > 60


def test_low_alert_once_with_hysteresis():
    m = BatteryMonitor(low_threshold=20, recover_margin=5, alpha=1.0)
    assert m.update(30)[1] is None
    assert m.update(19)[1] == 'low'
    assert m.update(18)[1] is None      # no repeated alert
    assert m.update(22)[1] is None      # still inside the margin
    assert m.update(26)[1] == 'recovered'
