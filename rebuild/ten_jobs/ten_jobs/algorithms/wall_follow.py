"""Right-hand wall following used to explore the house and build the map.

Input is a 360-degree laser scan (index 0 = front, counter-clockwise, one value per degree).
Output is a (linear, angular) velocity command.
"""
from dataclasses import dataclass
import math


@dataclass
class WallFollowConfig:
    target_distance: float = 0.45   # keep this far from the right wall (m)
    front_clearance: float = 0.5    # turn left when an obstacle is closer than this in front (m)
    lost_wall_distance: float = 1.2  # right wall is "lost" beyond this (m)
    linear_speed: float = 0.18
    max_angular: float = 0.9
    kp: float = 2.0


def sector_min(ranges, start_deg, end_deg):
    """Smallest valid range in [start_deg, end_deg] (degrees, may wrap around 0)."""
    n = len(ranges)
    idx = range(start_deg, end_deg + 1) if start_deg <= end_deg else list(range(start_deg, n)) + list(range(0, end_deg + 1))
    vals = [ranges[i % n] for i in idx if 0.0 < ranges[i % n] < math.inf]
    return min(vals) if vals else math.inf


def wall_follow_command(ranges, cfg: WallFollowConfig = WallFollowConfig()):
    front = sector_min(ranges, 345, 15)
    right = sector_min(ranges, 255, 285)
    front_right = sector_min(ranges, 300, 330)

    # 1) blocked ahead -> rotate left in place
    if front < cfg.front_clearance:
        return 0.0, cfg.max_angular

    # 2) no wall on the right (doorway / corner) -> curve right to find it again
    if right > cfg.lost_wall_distance and front_right > cfg.lost_wall_distance:
        return cfg.linear_speed * 0.6, -cfg.max_angular * 0.6

    # 3) follow the wall with a P controller on the distance error
    error = cfg.target_distance - min(right, front_right)
    angular = max(-cfg.max_angular, min(cfg.max_angular, cfg.kp * error))
    return cfg.linear_speed, angular
