"""Plans the shortest path on the built map and drives the robot along it.

Sub:  /map (OccupancyGrid), /odom (Odometry), /goal_pose (PoseStamped from the app)
Pub:  /global_path (Path), /cmd_vel (Twist), /goal_result (String: reached | failed)
"""
import math

import numpy as np
import rclpy
from geometry_msgs.msg import PoseStamped, Twist
from nav_msgs.msg import OccupancyGrid, Odometry, Path
from rclpy.node import Node
from std_msgs.msg import String

from ten_jobs.algorithms.grid_path import astar, inflate, simplify


def yaw_from_quaternion(q):
    return math.atan2(2 * (q.w * q.z + q.x * q.y), 1 - 2 * (q.y * q.y + q.z * q.z))


class PathPlanner(Node):
    def __init__(self):
        super().__init__('path_planner')
        self.declare_parameter('robot_radius', 0.2)
        self.declare_parameter('goal_tolerance', 0.15)
        self.robot_radius = self.get_parameter('robot_radius').value
        self.goal_tolerance = self.get_parameter('goal_tolerance').value

        self.map = None
        self.blocked = None
        self.pose = None  # (x, y, yaw)
        self.waypoints = []

        self.path_pub = self.create_publisher(Path, '/global_path', 10)
        self.cmd_pub = self.create_publisher(Twist, '/cmd_vel', 10)
        self.result_pub = self.create_publisher(String, '/goal_result', 10)
        self.create_subscription(OccupancyGrid, '/map', self.on_map, 1)
        self.create_subscription(Odometry, '/odom', self.on_odom, 10)
        self.create_subscription(PoseStamped, '/goal_pose', self.on_goal, 10)
        self.create_timer(0.1, self.follow)

    # --- map / pose -------------------------------------------------------
    def on_map(self, msg: OccupancyGrid):
        self.map = msg
        grid = np.array(msg.data, dtype=np.int16).reshape(msg.info.height, msg.info.width)
        self.blocked = inflate(grid, int(math.ceil(self.robot_radius / msg.info.resolution)))

    def on_odom(self, msg: Odometry):
        p = msg.pose.pose
        self.pose = (p.position.x, p.position.y, yaw_from_quaternion(p.orientation))

    def world_to_cell(self, x, y):
        info = self.map.info
        return (int((y - info.origin.position.y) / info.resolution),
                int((x - info.origin.position.x) / info.resolution))

    def cell_to_world(self, cell):
        info = self.map.info
        return (info.origin.position.x + (cell[1] + 0.5) * info.resolution,
                info.origin.position.y + (cell[0] + 0.5) * info.resolution)

    # --- planning -----------------------------------------------------------
    def on_goal(self, goal: PoseStamped):
        if self.blocked is None or self.pose is None:
            self.get_logger().warn('map or odometry not ready yet')
            self.result_pub.publish(String(data='failed'))
            return
        start = self.world_to_cell(*self.pose[:2])
        target = self.world_to_cell(goal.pose.position.x, goal.pose.position.y)
        cells = astar(self.blocked, start, target)
        if not cells:
            self.get_logger().warn(f'no path from {start} to {target}')
            self.result_pub.publish(String(data='failed'))
            return

        self.waypoints = [self.cell_to_world(c) for c in simplify(cells)][1:]
        path = Path()
        path.header.frame_id = 'map'
        for c in cells:
            ps = PoseStamped()
            ps.pose.position.x, ps.pose.position.y = self.cell_to_world(c)
            path.poses.append(ps)
        self.path_pub.publish(path)
        self.get_logger().info(f'path planned: {len(cells)} cells, {len(self.waypoints)} waypoints')

    # --- pure pursuit style follower -----------------------------------------
    def follow(self):
        if not self.waypoints or self.pose is None:
            return
        x, y, yaw = self.pose
        tx, ty = self.waypoints[0]
        dist = math.hypot(tx - x, ty - y)
        if dist < self.goal_tolerance:
            self.waypoints.pop(0)
            if not self.waypoints:
                self.cmd_pub.publish(Twist())
                self.result_pub.publish(String(data='reached'))
                self.get_logger().info('goal reached')
            return

        heading_error = math.atan2(ty - y, tx - x) - yaw
        heading_error = math.atan2(math.sin(heading_error), math.cos(heading_error))
        cmd = Twist()
        cmd.angular.z = max(-1.0, min(1.0, 1.5 * heading_error))
        cmd.linear.x = 0.0 if abs(heading_error) > 0.6 else min(0.22, 0.5 * dist)
        self.cmd_pub.publish(cmd)


def main():
    rclpy.init()
    node = PathPlanner()
    try:
        rclpy.spin(node)
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
