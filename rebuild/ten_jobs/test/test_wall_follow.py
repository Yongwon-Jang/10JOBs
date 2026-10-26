import math

from ten_jobs.algorithms.wall_follow import WallFollowConfig, wall_follow_command

CFG = WallFollowConfig()


def scan(default=math.inf, **sectors):
    """Build a 360 scan. sectors: name=(start_deg, end_deg, distance)."""
    r = [default] * 360
    for start, end, d in sectors.values():
        for i in range(start, end + 1):
            r[i % 360] = d
    return r


def test_turns_left_when_blocked_in_front():
    lin, ang = wall_follow_command(scan(front=(350, 370, 0.3)), CFG)
    assert lin == 0.0 and ang > 0


def test_searches_right_when_wall_is_lost():
    lin, ang = wall_follow_command(scan(), CFG)
    assert lin > 0 and ang < 0


def test_steers_away_when_too_close_to_right_wall():
    lin, ang = wall_follow_command(scan(right=(250, 335, 0.2)), CFG)
    assert lin > 0 and ang > 0


def test_steers_toward_wall_when_too_far():
    lin, ang = wall_follow_command(scan(right=(250, 335, 0.8)), CFG)
    assert lin > 0 and ang < 0


def test_ignores_invalid_zero_ranges():
    r = scan(right=(250, 335, CFG.target_distance))
    r[0] = 0.0  # invalid reading in front
    lin, _ = wall_follow_command(r, CFG)
    assert lin > 0
