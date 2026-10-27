import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(__file__))
import fake_ros  # noqa: E402

FAKE = fake_ros.install()


@pytest.fixture
def params():
    """Override ROS parameters for the node created in a test."""
    if not FAKE:
        pytest.skip('node tests use the fake rclpy; run them without ROS2 sourced')
    fake_ros.Node.param_overrides = {}
    yield fake_ros.Node.param_overrides
    fake_ros.Node.param_overrides = {}
