"""Tiny in-process stand-ins for rclpy and the ROS message packages.

They let the node classes run under plain pytest (no ROS2 install): publishers record
what they publish, subscriptions and timers can be fired by hand. Only the parts of the
API that the nodes in this package use are implemented.

When a real ROS2 environment is available, `install()` does nothing and the real
packages are used instead.
"""
import sys
import types
from dataclasses import dataclass, field


# ---------------------------------------------------------------- messages
@dataclass
class _Data:
    data: object = None


@dataclass
class Vector3:
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0


@dataclass
class Twist:
    linear: Vector3 = field(default_factory=Vector3)
    angular: Vector3 = field(default_factory=Vector3)


@dataclass
class Quaternion:
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0
    w: float = 1.0


@dataclass
class Pose:
    position: Vector3 = field(default_factory=Vector3)
    orientation: Quaternion = field(default_factory=Quaternion)


@dataclass
class Header:
    frame_id: str = ''


@dataclass
class PoseStamped:
    header: Header = field(default_factory=Header)
    pose: Pose = field(default_factory=Pose)


@dataclass
class _PoseWrap:
    pose: Pose = field(default_factory=Pose)


@dataclass
class Odometry:
    pose: _PoseWrap = field(default_factory=_PoseWrap)


@dataclass
class Path:
    header: Header = field(default_factory=Header)
    poses: list = field(default_factory=list)


@dataclass
class MapMetaData:
    resolution: float = 0.1
    width: int = 0
    height: int = 0
    origin: Pose = field(default_factory=Pose)


@dataclass
class OccupancyGrid:
    info: MapMetaData = field(default_factory=MapMetaData)
    data: list = field(default_factory=list)


@dataclass
class LaserScan:
    ranges: list = field(default_factory=list)


@dataclass
class Image:
    array: object = None  # the fake CvBridge returns this as-is


@dataclass
class BatteryState:
    percentage: float = float('nan')
    voltage: float = 0.0


# ---------------------------------------------------------------- rclpy
class _Logger:
    def __init__(self):
        self.lines = []

    def _log(self, level, msg):
        self.lines.append((level, msg))

    def info(self, msg):
        self._log('info', msg)

    def warn(self, msg):
        self._log('warn', msg)

    def error(self, msg):
        self._log('error', msg)


class _Publisher:
    def __init__(self, topic):
        self.topic = topic
        self.sent = []

    def publish(self, msg):
        self.sent.append(msg)


class _Param:
    def __init__(self, value):
        self.value = value


class _Timer:
    def __init__(self, period, callback):
        self.period = period
        self.callback = callback
        self.cancelled = False

    def cancel(self):
        self.cancelled = True


class Node:
    """Records publishers/subscriptions so tests can drive the node."""
    param_overrides = {}

    def __init__(self, name):
        self.name = name
        self.publishers = {}
        self.subscriptions = {}
        self.timers = []
        self._params = {}
        self._logger = _Logger()

    def declare_parameter(self, name, default):
        self._params[name] = Node.param_overrides.get(name, default)

    def get_parameter(self, name):
        return _Param(self._params[name])

    def create_publisher(self, _type, topic, _qos):
        self.publishers[topic] = _Publisher(topic)
        return self.publishers[topic]

    def create_subscription(self, _type, topic, callback, _qos):
        self.subscriptions[topic] = callback

    def create_timer(self, period, callback, **_):
        t = _Timer(period, callback)
        self.timers.append(t)
        return t

    def destroy_timer(self, timer):
        timer.cancel()
        if timer in self.timers:
            self.timers.remove(timer)

    def get_logger(self):
        return self._logger

    def destroy_node(self):
        pass

    # --- test helpers ---------------------------------------------------------
    def receive(self, topic, msg):
        self.subscriptions[topic](msg)

    def sent(self, topic):
        return self.publishers[topic].sent

    def tick(self):
        for t in list(self.timers):
            if not t.cancelled:
                t.callback()


class QoSProfile:
    def __init__(self, **kwargs):
        self.kwargs = kwargs


class DurabilityPolicy:
    TRANSIENT_LOCAL = 'transient_local'
    VOLATILE = 'volatile'


class CvBridge:
    def imgmsg_to_cv2(self, img, desired_encoding=None):
        return img.array


def _module(name, **attrs):
    mod = types.ModuleType(name)
    mod.__dict__.update(attrs)
    sys.modules[name] = mod
    return mod


def install():
    try:
        import rclpy  # noqa: F401  real ROS2 is available
        return False
    except ImportError:
        pass
    rclpy = _module('rclpy', init=lambda *a, **k: None, shutdown=lambda *a, **k: None, spin=lambda n: None)
    rclpy.node = _module('rclpy.node', Node=Node)
    rclpy.qos = _module('rclpy.qos', QoSProfile=QoSProfile, DurabilityPolicy=DurabilityPolicy)
    _module('std_msgs')
    _module('std_msgs.msg', String=type('String', (_Data,), {}), Bool=type('Bool', (_Data,), {}),
            Float32=type('Float32', (_Data,), {}))
    _module('geometry_msgs')
    _module('geometry_msgs.msg', Twist=Twist, PoseStamped=PoseStamped)
    _module('sensor_msgs')
    _module('sensor_msgs.msg', LaserScan=LaserScan, Image=Image, BatteryState=BatteryState)
    _module('nav_msgs')
    _module('nav_msgs.msg', OccupancyGrid=OccupancyGrid, Odometry=Odometry, Path=Path)
    _module('cv_bridge', CvBridge=CvBridge)
    return True
