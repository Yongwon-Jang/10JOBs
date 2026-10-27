"""Guard (security) mode: patrols the house while nobody is home and alerts the app on motion.

Sub:  /image_raw (Image), /guard_mode (Bool, on/off from the app), /goal_result (String from path_planner)
Pub:  /guard_alert (String, JSON: time, changed_ratio, waypoint), /goal_pose (PoseStamped, next patrol point)
Param: patrol_waypoints (flat list [x1, y1, x2, y2, ...] in map frame; empty = watch in place)
"""
import json
import time

import rclpy
from cv_bridge import CvBridge
from geometry_msgs.msg import PoseStamped
from rclpy.node import Node
from sensor_msgs.msg import Image
from std_msgs.msg import Bool, String

from ten_jobs.algorithms.motion_detect import MotionDetector
from ten_jobs.algorithms.patrol import Patrol


class GuardMode(Node):
    def __init__(self):
        super().__init__('guard_mode')
        self.declare_parameter('area_ratio', 0.02)
        self.declare_parameter('patrol_waypoints', [0.0])
        flat = [float(v) for v in self.get_parameter('patrol_waypoints').value]
        self.waypoints = list(zip(flat[0::2], flat[1::2]))

        self.detector = MotionDetector(area_ratio=self.get_parameter('area_ratio').value)
        self.bridge = CvBridge()
        self.enabled = False
        self.patrol = None
        self.moving = False
        self.resume_timer = None
        self.next_point = None

        self.alert_pub = self.create_publisher(String, '/guard_alert', 10)
        self.goal_pub = self.create_publisher(PoseStamped, '/goal_pose', 10)
        self.create_subscription(Bool, '/guard_mode', self.on_toggle, 10)
        self.create_subscription(Image, '/image_raw', self.on_image, 1)
        self.create_subscription(String, '/goal_result', self.on_goal_result, 10)

    def on_toggle(self, msg: Bool):
        self.enabled = msg.data
        self.detector = MotionDetector(area_ratio=self.detector.area_ratio)  # reset baseline frame
        self.get_logger().info(f'guard mode {"ON" if self.enabled else "OFF"}')
        if self.enabled and self.waypoints:
            self.patrol = Patrol(self.waypoints)
            self.send_goal(self.patrol.current)
        else:
            self.patrol = None

    # --- patrol ---------------------------------------------------------------
    def send_goal(self, point):
        if point is None:
            self.get_logger().error('every patrol point is unreachable; watching in place')
            self.patrol = None
            return
        goal = PoseStamped()
        goal.header.frame_id = 'map'
        goal.pose.position.x, goal.pose.position.y = point
        goal.pose.orientation.w = 1.0
        self.goal_pub.publish(goal)
        self.moving = True
        self.get_logger().info(f'patrol -> {point}')

    def on_goal_result(self, msg: String):
        if not (self.enabled and self.patrol):
            return
        self.moving = False
        # pause briefly at each point so the camera can compare still frames
        nxt = self.patrol.report_arrival() if msg.data == 'reached' else self.patrol.report_failure()
        self.detector = MotionDetector(area_ratio=self.detector.area_ratio)
        self.next_point = nxt
        if self.resume_timer is None:
            self.resume_timer = self.create_timer(3.0, self._resume)

    def _resume(self):
        self.destroy_timer(self.resume_timer)  # one-shot
        self.resume_timer = None
        if self.enabled and self.patrol:
            self.send_goal(self.next_point)

    # --- motion detection -------------------------------------------------------
    def on_image(self, img: Image):
        # only compare frames while standing still; a moving camera changes every pixel
        if not self.enabled or self.moving:
            return
        frame = self.bridge.imgmsg_to_cv2(img, desired_encoding='bgr8')
        alert, ratio = self.detector.update(frame)
        if alert:
            where = self.patrol.current if self.patrol else None
            self.alert_pub.publish(String(data=json.dumps({
                'time': time.time(), 'changed_ratio': round(ratio, 3), 'waypoint': where,
            })))
            self.get_logger().warn(f'motion detected ({ratio:.1%} of frame changed) at {where}')


def main():
    rclpy.init()
    node = GuardMode()
    try:
        rclpy.spin(node)
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
