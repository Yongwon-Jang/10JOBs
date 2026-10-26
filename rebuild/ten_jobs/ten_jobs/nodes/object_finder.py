"""Finds the object the user asked for in the robot camera image.

The simulator's semantic camera mode could not be switched from external code,
so detection runs on the normal RGB camera with a TensorFlow detection model.

Sub:  /image_raw (Image), /find_object (String, e.g. "wallet")
Pub:  /found_object (String, JSON: label, score, bbox)
Param: model_dir (TensorFlow SavedModel), labels (comma separated, index = class id - 1)
"""
import json

import numpy as np
import rclpy
from cv_bridge import CvBridge
from rclpy.node import Node
from sensor_msgs.msg import Image
from std_msgs.msg import String


class ObjectFinder(Node):
    def __init__(self):
        super().__init__('object_finder')
        self.declare_parameter('model_dir', '')
        self.declare_parameter('labels', 'wallet,key,remote,phone,cup')
        self.declare_parameter('min_score', 0.6)
        self.labels = self.get_parameter('labels').value.split(',')
        self.min_score = self.get_parameter('min_score').value

        self.detect = self.load_model(self.get_parameter('model_dir').value)
        self.bridge = CvBridge()
        self.target = None

        self.found_pub = self.create_publisher(String, '/found_object', 10)
        self.create_subscription(String, '/find_object', self.on_request, 10)
        self.create_subscription(Image, '/image_raw', self.on_image, 1)

    def load_model(self, model_dir):
        if not model_dir:
            self.get_logger().warn('model_dir not set: object finding disabled')
            return None
        import tensorflow as tf  # imported lazily so other nodes start without TensorFlow
        model = tf.saved_model.load(model_dir)
        self.get_logger().info(f'model loaded from {model_dir}')

        def detect(rgb: np.ndarray):
            out = model(tf.convert_to_tensor(rgb[np.newaxis, ...], dtype=tf.uint8))
            return (out['detection_boxes'][0].numpy(),
                    out['detection_classes'][0].numpy().astype(int),
                    out['detection_scores'][0].numpy())
        return detect

    def on_request(self, msg: String):
        self.target = msg.data.strip() or None
        self.get_logger().info(f'searching for: {self.target}')

    def on_image(self, img: Image):
        if not self.target or self.detect is None:
            return
        rgb = self.bridge.imgmsg_to_cv2(img, desired_encoding='rgb8')
        boxes, classes, scores = self.detect(rgb)
        for box, cls, score in zip(boxes, classes, scores):
            label = self.labels[cls - 1] if 0 < cls <= len(self.labels) else str(cls)
            if label == self.target and score >= self.min_score:
                self.found_pub.publish(String(data=json.dumps({
                    'label': label, 'score': round(float(score), 3), 'bbox': [round(float(v), 3) for v in box],
                })))
                self.get_logger().info(f'found {label} ({score:.2f})')
                self.target = None
                break


def main():
    rclpy.init()
    node = ObjectFinder()
    try:
        rclpy.spin(node)
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
