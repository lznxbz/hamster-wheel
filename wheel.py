"""Serial protocol and wheel-speed estimate for the animation."""
from collections import deque
from dataclasses import dataclass, field
import time


def parse_line(line: str):
    parts = line.strip().split(",")
    try:
        if len(parts) == 2 and parts[0] == "E":
            return ("event", int(parts[1]))
        if len(parts) == 4 and parts[0] == "R":
            return ("raw", int(parts[1]), int(parts[2]), int(parts[3]))
    except ValueError:
        pass
    return ("other", line.strip())


class LineReader:
    def __init__(self, port):
        self.port = port
        self.buffer = bytearray()

    def lines(self):
        data = self.port.read(self.port.in_waiting or 1)
        self.buffer.extend(data)
        if len(self.buffer) > 4096:
            self.buffer.clear()
        while b"\n" in self.buffer:
            line, _, remainder = self.buffer.partition(b"\n")
            self.buffer = bytearray(remainder)
            yield line.decode("ascii", errors="replace").strip()


@dataclass
class WheelSpeed:
    pulses_per_revolution: int = 1
    last_timestamp: int | None = None
    last_received: float = 0.0
    period: float = 0.0
    rpm: float = 0.0
    periods: deque = field(default_factory=lambda: deque(maxlen=8))

    def __post_init__(self):
        if self.pulses_per_revolution < 1:
            raise ValueError("pulses_per_revolution must be positive")
        self.periods = deque(maxlen=max(8, self.pulses_per_revolution * 2))

    def event(self, timestamp_us: int, now: float | None = None):
        now = time.monotonic() if now is None else now
        if self.last_timestamp is not None:
            elapsed_us = (timestamp_us - self.last_timestamp) & 0xFFFFFFFF
            if 40_000 <= elapsed_us <= 10_000_000:
                if now - self.last_received > 10:
                    self.periods.clear()
                self.periods.append(elapsed_us / 1_000_000)
                if len(self.periods) >= self.pulses_per_revolution:
                    full_turn = sum(list(self.periods)[-self.pulses_per_revolution:])
                    self.period = full_turn / self.pulses_per_revolution
                    self.rpm = 60 / full_turn
            else:
                self.periods.clear()
                self.rpm = 0.0
        self.last_timestamp = timestamp_us
        self.last_received = now

    def target_rpm(self, now: float | None = None) -> float:
        now = time.monotonic() if now is None else now
        if not self.period or now - self.last_received > max(1.2, self.period * 1.8):
            return 0.0
        return self.rpm
