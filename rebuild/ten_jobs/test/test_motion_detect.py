import numpy as np

from ten_jobs.algorithms.motion_detect import MotionDetector


def frame(value=0):
    return np.full((48, 64, 3), value, dtype=np.uint8)


def test_no_alert_on_static_scene():
    d = MotionDetector()
    assert d.update(frame(10)) == (False, 0.0)
    alert, ratio = d.update(frame(10))
    assert not alert and ratio == 0.0


def test_alert_when_large_area_changes():
    d = MotionDetector(area_ratio=0.05)
    d.update(frame(0))
    moved = frame(0)
    moved[10:30, 10:40] = 200
    alert, ratio = d.update(moved)
    assert alert and ratio > 0.05


def test_cooldown_suppresses_repeated_alerts():
    d = MotionDetector(area_ratio=0.05, cooldown_frames=3)
    d.update(frame(0))
    assert d.update(frame(200))[0]
    assert not d.update(frame(0))[0]
