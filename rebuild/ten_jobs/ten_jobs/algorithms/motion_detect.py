"""Frame-difference motion detection for guard (security) mode."""
from dataclasses import dataclass, field

import numpy as np


@dataclass
class MotionDetector:
    pixel_threshold: int = 30      # per-pixel gray difference counted as change
    area_ratio: float = 0.02       # alert when this share of the frame changed
    cooldown_frames: int = 30      # do not alert again for N frames
    _prev: np.ndarray = field(default=None, repr=False)
    _cooldown: int = 0

    @staticmethod
    def to_gray(frame: np.ndarray) -> np.ndarray:
        if frame.ndim == 3:
            frame = frame[..., :3].astype(np.float32) @ np.array([0.114, 0.587, 0.299], dtype=np.float32)  # BGR
        return frame.astype(np.int16)

    def update(self, frame: np.ndarray):
        """Feed one frame. Returns (alert: bool, changed_ratio: float)."""
        gray = self.to_gray(frame)
        if self._prev is None or self._prev.shape != gray.shape:
            self._prev = gray
            return False, 0.0

        changed = np.abs(gray - self._prev) > self.pixel_threshold
        ratio = float(changed.mean())
        self._prev = gray

        if self._cooldown > 0:
            self._cooldown -= 1
            return False, ratio
        if ratio >= self.area_ratio:
            self._cooldown = self.cooldown_frames
            return True, ratio
        return False, ratio
