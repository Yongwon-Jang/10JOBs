"""Explores the house by following the right-hand wall while the map is being built.

Sub:  /scan (LaserScan), /explore (Bool, start/stop from the app)
Pub:  /cmd_vel (Twist)
"""
import rclpy
from geometry_msgs.msg import Twist
from rclpy.node import Node
from sensor_msgs.msg import LaserScan
from std_msgs.msg import Bool

from ten_jobs.algorithms.wall_follow import WallFollowConfig, wall_follow_command


class WallFollower(Node):
    def __init__(self):
        super().__init__('wall_follower')
        self.declare_parameter('target_distance', 0.45)
        self.cfg = WallFollowConfig(target_distance=self.get_parameter('target_distance').value)
        self.enabled = False

        self.cmd_pub = self.create_publisher(Twist, '/cmd_vel', 10)
        self.create_subscription(LaserScan, '/scan', self.on_scan, 10)
        self.create_subscription(Bool, '/explore', self.on_toggle, 10)

    def on_toggle(self, msg: Bool):
        self.enabled = msg.data
        self.get_logger().info(f'exploration {"started" if self.enabled else "stopped"}')
        if not self.enabled:
            self.cmd_pub.publish(Twist())

    def on_scan(self, scan: LaserScan):
        if not self.enabled:
            return
        linear, angular = wall_follow_command(list(scan.ranges), self.cfg)
        cmd = Twist()
        cmd.linear.x = linear
        cmd.angular.z = angular
        self.cmd_pub.publish(cmd)


def main():
    rclpy.init()
    node = WallFollower()
    try:
        rclpy.spin(node)
    finally:
        node.cmd_pub.publish(Twist())
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
