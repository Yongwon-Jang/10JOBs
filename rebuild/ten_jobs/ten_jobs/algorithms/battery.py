"""Battery level smoothing and low-battery decisions.

Raw voltage readings jump around while the robot accelerates, so the percentage
shown in the app is smoothed, and low-battery alerts use hysteresis so the app
is not spammed when the level hovers around the threshold.
"""
from dataclasses import dataclass


def voltage_to_percent(voltage: float, empty: float = 11.0, full: float = 12.6) -> float:
    """Linear map of a 3S LiPo pack voltage to 0~100 %."""
    if full <= empty:
        raise ValueError('full must be greater than empty')
    pct = (voltage - empty) / (full - empty) * 100.0
    return max(0.0, min(100.0, pct))


@dataclass
class BatteryMonitor:
    low_threshold: float = 20.0    # alert below this %
    recover_margin: float = 5.0    # clear the alert only above threshold + margin
    alpha: float = 0.2             # exponential moving average weight
    level: float | None = None
    low: bool = False

    def update(self, percent: float):
        """Returns (smoothed_percent, event) where event is 'low', 'recovered' or None."""
        self.level = percent if self.level is None else self.alpha * percent + (1 - self.alpha) * self.level
        event = None
        if not self.low and self.level < self.low_threshold:
            self.low, event = True, 'low'
        elif self.low and self.level > self.low_threshold + self.recover_margin:
            self.low, event = False, 'recovered'
        return round(self.level, 1), event
