"""Node-level tests: feed messages into each ROS2 node and check what it publishes.

Runs on the fake rclpy in fake_ros.py, so no ROS2 installation is needed.
"""
import json
import math

import numpy as np

from fake_ros import BatteryState, Image, LaserScan, OccupancyGrid, Odometry, PoseStamped


def String(data):
    from std_msgs.msg import String as S
    return S(data=data)


def Bool(data):
    from std_msgs.msg import Bool as B
    return B(data=data)


# ---------------------------------------------------------------- wall follower
def test_wall_follower_moves_only_while_exploring(params):
    from ten_jobs.nodes.wall_follower import WallFollower
    node = WallFollower()
    scan = LaserScan(ranges=[math.inf] * 360)

    node.receive('/scan', scan)
    assert node.sent('/cmd_vel') == []

    node.receive('/explore', Bool(True))
    node.receive('/scan', scan)
    assert node.sent('/cmd_vel')[-1].linear.x > 0

    node.receive('/explore', Bool(False))
    stop = node.sent('/cmd_vel')[-1]
    assert stop.linear.x == 0 and stop.angular.z == 0


# ---------------------------------------------------------------- path planner
def make_map(w=40, h=40, res=0.1, wall_col=None):
    grid = np.zeros((h, w), dtype=int)
    if wall_col is not None:
        grid[0:h - 5, wall_col] = 100
    m = OccupancyGrid()
    m.info.resolution, m.info.width, m.info.height = res, w, h
    m.data = grid.flatten().tolist()
    return m


def odom(x, y):
    o = Odometry()
    o.pose.pose.position.x, o.pose.pose.position.y = x, y
    return o


def goal(x, y):
    g = PoseStamped()
    g.pose.position.x, g.pose.position.y = x, y
    return g


def test_path_planner_plans_around_wall_and_reports_arrival(params):
    from ten_jobs.nodes.path_planner import PathPlanner
    node = PathPlanner()
    node.receive('/map', make_map(wall_col=20))
    node.receive('/odom', odom(0.5, 0.5))
    node.receive('/goal_pose', goal(3.5, 0.5))

    path = node.sent('/global_path')[-1]
    xs = [p.pose.position.x for p in path.poses]
    ys = [p.pose.position.y for p in path.poses]
    assert xs[0] < 1.0 and xs[-1] > 3.0
    assert max(ys) > 3.4, 'path must go around the wall through the gap at the top'

    # teleport the robot onto each waypoint and tick the controller
    for _ in range(50):
        if not node.waypoints:
            break
        node.receive('/odom', odom(*node.waypoints[0]))
        node.tick()
    assert node.sent('/goal_result')[-1].data == 'reached'


def test_path_planner_reports_unreachable_goal(params):
    from ten_jobs.nodes.path_planner import PathPlanner
    node = PathPlanner()
    m = make_map()
    grid = np.array(m.data).reshape(40, 40)
    grid[:, 20] = 100  # full wall, no gap
    m.data = grid.flatten().tolist()
    node.receive('/map', m)
    node.receive('/odom', odom(0.5, 0.5))
    node.receive('/goal_pose', goal(3.5, 0.5))
    assert node.sent('/goal_result')[-1].data == 'failed'


# ---------------------------------------------------------------- device control
def test_device_control_applies_commands_and_rejects_bad_ones(params):
    from ten_jobs.nodes.device_control import DeviceControl
    node = DeviceControl()
    node.receive('/device_command', String(json.dumps({'device': 'aircon', 'action': 'set', 'value': 23})))
    states = {d['device']: d for d in json.loads(node.sent('/device_states')[-1].data)}
    assert states['aircon'] == {'device': 'aircon', 'kind': 'thermostat', 'on': True, 'value': 23}

    node.receive('/device_command', String('not json'))
    node.receive('/device_command', String(json.dumps({'device': 'tv', 'action': 'fly'})))
    assert len(node.sent('/device_error')) == 2


# ---------------------------------------------------------------- battery
def test_battery_unknown_until_data_then_low_alert(params):
    from ten_jobs.nodes.battery_monitor import BatteryMonitorNode
    params['low_threshold'] = 20.0
    node = BatteryMonitorNode()
    node.tick()
    assert node.sent('/battery_percent')[-1].data == -1.0

    node.monitor.alpha = 1.0  # no smoothing, to make the test readable
    node.receive('/battery_state', BatteryState(percentage=0.5))
    node.receive('/battery_state', BatteryState(percentage=0.1))
    assert node.sent('/battery_percent')[-1].data == 10.0
    assert [m.data for m in node.sent('/battery_alert')] == ['low']


def test_battery_falls_back_to_voltage(params):
    from ten_jobs.nodes.battery_monitor import BatteryMonitorNode
    node = BatteryMonitorNode()
    node.receive('/battery_state', BatteryState(voltage=12.6))
    assert node.sent('/battery_percent')[-1].data == 100.0


# ---------------------------------------------------------------- guard mode
def frame(v):
    return Image(array=np.full((48, 64, 3), v, dtype=np.uint8))


def test_guard_patrols_and_alerts_only_while_standing_still(params):
    from ten_jobs.nodes.guard_mode import GuardMode
    params['patrol_waypoints'] = [1.0, 1.0, 3.0, 1.0]
    node = GuardMode()

    node.receive('/guard_mode', Bool(True))
    first = node.sent('/goal_pose')[-1].pose.position
    assert (first.x, first.y) == (1.0, 1.0)

    # moving: camera changes are ignored
    node.receive('/image_raw', frame(0))
    node.receive('/image_raw', frame(200))
    assert node.sent('/guard_alert') == []

    # arrived -> pause -> next waypoint after the resume timer fires
    node.receive('/goal_result', String('reached'))
    node.receive('/image_raw', frame(0))
    node.receive('/image_raw', frame(200))
    alert = json.loads(node.sent('/guard_alert')[-1].data)
    assert alert['changed_ratio'] > 0.5

    node.tick()
    nxt = node.sent('/goal_pose')[-1].pose.position
    assert (nxt.x, nxt.y) == (3.0, 1.0)
    assert node.resume_timer is None  # one-shot timer cleaned up


def test_guard_without_waypoints_watches_in_place(params):
    from ten_jobs.nodes.guard_mode import GuardMode
    node = GuardMode()
    node.receive('/guard_mode', Bool(True))
    assert node.sent('/goal_pose') == []
    node.receive('/image_raw', frame(0))
    node.receive('/image_raw', frame(255))
    assert len(node.sent('/guard_alert')) == 1


# ---------------------------------------------------------------- object finder
def test_object_finder_reports_requested_object(params):
    from ten_jobs.nodes.object_finder import ObjectFinder
    node = ObjectFinder()
    # inject a fake detector instead of a TensorFlow model
    node.detect = lambda rgb: (np.array([[0.1, 0.2, 0.5, 0.6], [0, 0, 1, 1]]), np.array([2, 1]), np.array([0.9, 0.95]))
    node.receive('/image_raw', frame(0))
    assert node.sent('/found_object') == []  # nothing requested yet

    node.receive('/find_object', String('key'))
    node.receive('/image_raw', frame(0))
    found = json.loads(node.sent('/found_object')[-1].data)
    assert found['label'] == 'key' and found['score'] == 0.9
    assert node.target is None  # search stops after finding it
