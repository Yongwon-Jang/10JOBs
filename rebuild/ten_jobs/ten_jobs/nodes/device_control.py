"""Controls smart home devices from the app and reports their state.

Sub:  /device_command (String, JSON e.g. {"device": "aircon", "action": "set", "value": 24})
Pub:  /device_states (String, JSON list of every device, latched-style republish every 2 s)
      /device_error  (String, reason a command was rejected)
"""
import json

import rclpy
from rclpy.node import Node
from rclpy.qos import DurabilityPolicy, QoSProfile
from std_msgs.msg import String

from ten_jobs.algorithms.devices import DeviceError, DeviceHub


class DeviceControl(Node):
    def __init__(self):
        super().__init__('device_control')
        self.hub = DeviceHub()
        # transient local: an app that connects later still receives the last state
        latched = QoSProfile(depth=1, durability=DurabilityPolicy.TRANSIENT_LOCAL)
        self.state_pub = self.create_publisher(String, '/device_states', latched)
        self.error_pub = self.create_publisher(String, '/device_error', 10)
        self.create_subscription(String, '/device_command', self.on_command, 10)
        self.create_timer(2.0, self.publish_state)
        self.publish_state()

    def on_command(self, msg: String):
        try:
            command = json.loads(msg.data)
            device = self.hub.apply(command)
            self.get_logger().info(f'{command} -> {device.to_dict()}')
        except (json.JSONDecodeError, DeviceError) as e:
            self.error_pub.publish(String(data=str(e)))
            self.get_logger().warn(f'rejected command {msg.data!r}: {e}')
            return
        self.publish_state()

    def publish_state(self):
        self.state_pub.publish(String(data=json.dumps(self.hub.snapshot(), ensure_ascii=False)))


def main():
    rclpy.init()
    node = DeviceControl()
    try:
        rclpy.spin(node)
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
