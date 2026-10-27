"""Publishes a smoothed battery percentage for the app and warns when it runs low.

The simulator does not report a battery, so when /battery_state never arrives the
node keeps publishing "unknown" instead of a misleading 0 %.

Sub:  /battery_state (sensor_msgs/BatteryState)
Pub:  /battery_percent (Float32, -1 = unknown), /battery_alert (String: low | recovered)
"""
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import BatteryState
from std_msgs.msg import Float32, String

from ten_jobs.algorithms.battery import BatteryMonitor, voltage_to_percent


class BatteryMonitorNode(Node):
    def __init__(self):
        super().__init__('battery_monitor')
        self.declare_parameter('low_threshold', 20.0)
        self.monitor = BatteryMonitor(low_threshold=self.get_parameter('low_threshold').value)
        self.received = False

        self.percent_pub = self.create_publisher(Float32, '/battery_percent', 10)
        self.alert_pub = self.create_publisher(String, '/battery_alert', 10)
        self.create_subscription(BatteryState, '/battery_state', self.on_battery, 10)
        self.create_timer(5.0, self.publish_unknown)

    def on_battery(self, msg: BatteryState):
        self.received = True
        # prefer the driver's percentage (0~1); fall back to voltage
        raw = msg.percentage * 100.0 if 0.0 <= msg.percentage <= 1.0 else voltage_to_percent(msg.voltage)
        level, event = self.monitor.update(raw)
        self.percent_pub.publish(Float32(data=float(level)))
        if event:
            self.alert_pub.publish(String(data=event))
            self.get_logger().warn(f'battery {event}: {level}%')

    def publish_unknown(self):
        if not self.received:
            self.percent_pub.publish(Float32(data=-1.0))


def main():
    rclpy.init()
    node = BatteryMonitorNode()
    try:
        rclpy.spin(node)
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
