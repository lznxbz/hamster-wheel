import unittest

from wheel import WheelSpeed, parse_line


class WheelTests(unittest.TestCase):
    def test_protocol(self):
        self.assertEqual(parse_line("R,531,490,0"), ("raw", 531, 490, 0))
        self.assertEqual(parse_line("E,4294967200"), ("event", 4294967200))

    def test_speed_stop_and_wrap(self):
        wheel = WheelSpeed()
        wheel.event(4294967200, now=1)
        wheel.event(199904, now=1.2)  # 200000 us after 32-bit wrap
        self.assertAlmostEqual(wheel.target_rpm(now=1.3), 300)
        self.assertEqual(wheel.target_rpm(now=2.5), 0)

    def test_reject_duplicate(self):
        wheel = WheelSpeed()
        wheel.event(1000000, now=1)
        wheel.event(1020000, now=1.02)
        self.assertEqual(wheel.target_rpm(now=1.1), 0)

    def test_two_markers(self):
        wheel = WheelSpeed(pulses_per_revolution=2)
        wheel.event(1_000_000, now=1)
        wheel.event(1_100_000, now=1.1)
        self.assertEqual(wheel.target_rpm(now=1.15), 0)
        wheel.event(1_500_000, now=1.5)
        self.assertEqual(wheel.target_rpm(now=1.55), 120)


if __name__ == "__main__":
    unittest.main()
