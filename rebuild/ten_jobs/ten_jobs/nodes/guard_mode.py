"""Guard (security) mode: watches the camera while nobody is home and alerts the app on motion.

Sub:  /image_raw (Image), /guard_mode (Bool, on/off from the app)
Pub:  /guard_alert (String, JSON: time, changed_ratio)
"""
import json
import time

import rclpy
from cv_bridge import CvBridge
from rclpy.node import Node
from sensor_msgs.msg import Image
from std_msgs.msg import Bool, String

from ten_jobs.algorithms.motion_detect import MotionDetector


class GuardMode(Node):
    def __init__(self):
        super().__init__('guard_mode')
        self.declare_parameter('area_ratio', 0.02)
        self.detector = MotionDetector(area_ratio=self.get_parameter('area_ratio').value)
        self.bridge = CvBridge()
        self.enabled = False

        self.alert_pub = self.create_publisher(String, '/guard_alert', 10)
        self.create_subscription(Bool, '/guard_mode', self.on_toggle, 10)
        self.create_subscription(Image, '/image_raw', self.on_image, 1)

    def on_toggle(self, msg: Bool):
        self.enabled = msg.data
        self.detector = MotionDetector(area_ratio=self.detector.area_ratio)  # reset baseline frame
        self.get_logger().info(f'guard mode {"ON" if self.enabled else "OFF"}')

    def on_image(self, img: Image):
        if not self.enabled:
            return
        frame = self.bridge.imgmsg_to_cv2(img, desired_encoding='bgr8')
        alert, ratio = self.detector.update(frame)
        if alert:
            self.alert_pub.publish(String(data=json.dumps({'time': time.time(), 'changed_ratio': round(ratio, 3)})))
            self.get_logger().warn(f'motion detected ({ratio:.1%} of frame changed)')


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
