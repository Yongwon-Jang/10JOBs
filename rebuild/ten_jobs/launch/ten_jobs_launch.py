"""Starts every robot feature at once, plus rosbridge so the Android app can talk to ROS2 over WebSocket.

    ros2 launch ten_jobs ten_jobs_launch.py model_dir:=/path/to/saved_model
"""
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.launch_description_sources import AnyLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    model_dir = LaunchConfiguration('model_dir')

    return LaunchDescription([
        DeclareLaunchArgument('model_dir', default_value='', description='TensorFlow SavedModel for object finding'),

        # App <-> ROS2 bridge (ws://<robot>:9090)
        IncludeLaunchDescription(AnyLaunchDescriptionSource(
            PathJoinSubstitution([FindPackageShare('rosbridge_server'), 'launch', 'rosbridge_websocket_launch.xml']))),

        Node(package='ten_jobs', executable='wall_follower', name='wall_follower', output='screen'),
        Node(package='ten_jobs', executable='path_planner', name='path_planner', output='screen',
             parameters=[{'robot_radius': 0.2}]),
        Node(package='ten_jobs', executable='object_finder', name='object_finder', output='screen',
             parameters=[{'model_dir': model_dir}]),
        Node(package='ten_jobs', executable='guard_mode', name='guard_mode', output='screen',
             parameters=[{'patrol_waypoints': [1.0, 1.0, 3.5, 1.0, 3.5, 4.0, 1.0, 4.0]}]),  # living room -> kitchen -> room -> entrance
        Node(package='ten_jobs', executable='device_control', name='device_control', output='screen'),
        Node(package='ten_jobs', executable='battery_monitor', name='battery_monitor', output='screen'),
    ])
