import pytest

from ten_jobs.algorithms.patrol import Patrol


def test_loops_through_waypoints():
    p = Patrol([(0, 0), (1, 0), (1, 1)])
    assert p.current == (0, 0)
    assert p.report_arrival() == (1, 0)
    assert p.report_arrival() == (1, 1)
    assert p.report_arrival() == (0, 0)


def test_arrival_tolerance():
    p = Patrol([(1.0, 1.0)], arrive_tolerance=0.2)
    assert p.arrived(1.1, 1.1)
    assert not p.arrived(1.5, 1.0)


def test_skips_waypoint_after_repeated_failures():
    p = Patrol([(0, 0), (5, 5), (1, 1)], max_failures=2)
    p.report_arrival()            # now at (5, 5)
    p.report_failure()            # 1st failure -> moves on
    p.report_arrival()            # (1,1) -> (0,0)
    p.report_arrival()            # (0,0) -> (5,5)
    assert p.current == (5, 5)
    assert p.report_failure() == (1, 1)   # 2nd failure
    p.report_arrival()            # (1,1) -> (0,0)
    assert p.report_arrival() == (1, 1)   # (5,5) skipped now


def test_all_unreachable_returns_none_and_empty_is_rejected():
    p = Patrol([(0, 0), (1, 1)], max_failures=1)
    p.report_failure()
    assert p.report_failure() is None
    with pytest.raises(ValueError):
        Patrol([])
