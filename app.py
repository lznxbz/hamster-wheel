"""First-person forward scenery driven by a hamster wheel."""
import argparse
import math
import time

from wheel import LineReader, WheelSpeed, parse_line

W, H = 960, 540
HORIZON = 205
SPEED_STEPS = (0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 4.0, 8.0, 12.0, 16.0, 20.0)


def speed_buttons(size):
    """Control positions in display pixels, independent of canvas scaling."""
    w, _ = size
    return (w - 154, 18, 62, 54), (w - 82, 18, 62, 54)


def change_speed(scale, direction):
    index = min(range(len(SPEED_STEPS)), key=lambda i: abs(SPEED_STEPS[i] - scale))
    return SPEED_STEPS[max(0, min(len(SPEED_STEPS) - 1, index + direction))]


def draw_speed_controls(pg, screen, scale, font):
    minus, plus = speed_buttons(screen.get_size())
    for rect, symbol in ((minus, "−"), (plus, "+")):
        pg.draw.rect(screen, (238, 246, 233), rect, border_radius=12)
        pg.draw.rect(screen, (57, 105, 70), rect, width=3, border_radius=12)
        label = font.render(symbol, True, (38, 83, 53))
        screen.blit(label, label.get_rect(center=pg.Rect(rect).center))
    label = font.render(f"Speed x{scale:g}", True, (32, 66, 49))
    background = label.get_rect(topright=(screen.get_width() - 20, 80)).inflate(20, 12)
    pg.draw.rect(screen, (238, 246, 233), background, border_radius=9)
    screen.blit(label, label.get_rect(center=background.center))


def project(distance_m, side, drift=0.0):
    """Place a roadside object: distant at the horizon, near at the bottom."""
    near = max(0.0, min(1.0, 1 - distance_m / 24.0))
    depth = near ** 1.7
    y = int(HORIZON + depth * (H - HORIZON + 55))
    x = int(W / 2 + side * (58 + depth * 320) + drift * depth * 40)
    scale = .14 + depth * 1.25
    return x, y, scale


def draw_scene(pg, screen, travel_m, rpm, speed_mps, status, font=None):
    canvas = pg.Surface((W, H))
    canvas.fill((150, 213, 230))
    pg.draw.circle(canvas, (247, 230, 168), (755, 89), 41)
    pg.draw.ellipse(canvas, (122, 183, 153), (-90, 165, 560, 115))
    pg.draw.ellipse(canvas, (111, 175, 147), (430, 160, 600, 125))
    pg.draw.rect(canvas, (119, 190, 121), (0, HORIZON, W, H - HORIZON))
    # A straight path that widens toward the viewer establishes first person.
    pg.draw.polygon(canvas, (206, 179, 132),
                    [(464, HORIZON), (496, HORIZON), (790, H), (170, H)])
    pg.draw.lines(canvas, (226, 204, 163), False,
                  [(464, HORIZON), (170, H)], 3)
    pg.draw.lines(canvas, (226, 204, 163), False,
                  [(496, HORIZON), (790, H)], 3)

    # Ground marks move down and outward as the wheel turns.
    for index in range(50):
        distance = (index * .72 - travel_m) % 28
        if distance > 24:
            continue
        for side in (-1, 1):
            x, y, scale = project(distance, side, ((index * 7) % 5 - 2) * .24)
            if 0 <= y < H + 20:
                length = max(2, int(7 * scale))
                pg.draw.line(canvas, (82, 146, 87), (x, y),
                             (x + side * length, y - max(2, length // 2)),
                             max(1, int(2 * scale)))

    # Draw far trees first, so near trees overlap them naturally.
    trees = []
    for index in range(14):
        distance = (index * 9 - travel_m) % 126
        if distance <= 24:
            for side in (-1, 1):
                trees.append((distance, side, index))
    for distance, side, index in sorted(trees, reverse=True):
        x, y, scale = project(distance, side, ((index * 3) % 5 - 2) * .35)
        if x < -120 or x > W + 120 or y > H + 65:
            continue
        trunk_w = max(3, int(23 * scale))
        trunk_h = max(10, int(175 * scale))
        crown = max(9, int(160 * scale))
        pg.draw.rect(canvas, (107, 105, 76),
                     (x - trunk_w // 2, y - trunk_h, trunk_w, trunk_h))
        pg.draw.circle(canvas, (62, 141, 86),
                       (x, y - trunk_h - crown // 3), crown)
        pg.draw.circle(canvas, (78, 160, 97),
                       (x - crown // 3, y - trunk_h - crown // 5),
                       max(3, crown * 2 // 3))

    if font is not None:
        label = font.render(f"{rpm:.0f} RPM   {speed_mps:.2f} m/s   {status}",
                            True, (32, 66, 62))
        canvas.blit(label, (18, 16))
    screen.blit(pg.transform.smoothscale(canvas, screen.get_size()), (0, 0))


def main():
    parser = argparse.ArgumentParser(description="仓鼠视角前进动画")
    parser.add_argument("--port", help="Arduino 串口，例如 /dev/cu.usbmodem2101")
    parser.add_argument("--display", type=int, default=1, help="外接屏编号，默认 1")
    parser.add_argument("--windowed", action="store_true", help="窗口模式，适合初次测试")
    parser.add_argument("--demo", action="store_true", help="无硬件演示；上下键调速度")
    parser.add_argument("--debug-hud", action="store_true", help="显示人用测速信息")
    parser.add_argument("--pulses-per-rev", type=int, default=2, help="每转遮光次数，默认 2")
    parser.add_argument("--diameter-cm", type=float, default=12.0, help="跑轮直径厘米，默认 12")
    parser.add_argument("--speed-scale", type=float, default=2.0, choices=SPEED_STEPS,
                        help="画面速度倍率，默认 2；运行中可用 +/− 键或画面按钮调整")
    parser.add_argument("--list-ports", action="store_true")
    parser.add_argument("--list-displays", action="store_true")
    args = parser.parse_args()
    if args.pulses_per_rev < 1 or args.diameter_cm <= 0:
        parser.error("遮光次数和跑轮直径必须大于 0")
    if args.list_ports:
        from serial.tools import list_ports
        for port in list_ports.comports():
            print(port.device, port.description)
        return
    import pygame as pg
    pg.init()
    if not pg.display.get_init():
        parser.error("无法初始化显示器；请在 Mac 图形桌面中运行")
    sizes = pg.display.get_desktop_sizes()
    if args.list_displays:
        for i, size in enumerate(sizes):
            print(f"{i}: {size[0]} × {size[1]}")
        pg.quit()
        return
    if not args.demo and not args.port:
        parser.error("实际运行需 --port；没有 Arduino 时可用 --demo")
    if args.display < 0 or args.display >= len(sizes):
        parser.error(f"屏幕编号应在 0 到 {len(sizes)-1} 之间；用 --list-displays 查看")
    port = None
    if not args.demo:
        import serial
        port = serial.Serial(args.port, 115200, timeout=0)
        time.sleep(2.5)  # Opening Uno USB serial commonly resets the board.
        port.reset_input_buffer()
        reader = LineReader(port)
    else:
        reader = None
    size = (min(960, sizes[args.display][0]), min(540, sizes[args.display][1])) if args.windowed else sizes[args.display]
    screen = pg.display.set_mode(size, 0 if args.windowed else pg.FULLSCREEN, display=args.display)
    pg.display.set_caption("Hamster View")
    font = pg.font.SysFont(None, 28) if args.debug_hud else None
    control_font = pg.font.SysFont(None, 32)
    clock = pg.time.Clock()
    wheel = WheelSpeed(pulses_per_revolution=args.pulses_per_rev)
    demo_rpm = 0.0
    shown_rpm = 0.0
    travel_m = 0.0
    speed_scale = args.speed_scale
    controls_until = 0.0
    status = "DEMO" if args.demo else "Waiting for sensor"
    try:
        running = True
        while running:
            dt = min(clock.tick(60) / 1000, .1)
            for event in pg.event.get():
                if event.type == pg.QUIT or (event.type == pg.KEYDOWN and event.key == pg.K_ESCAPE):
                    running = False
                elif event.type == pg.KEYDOWN:
                    if event.key in (pg.K_EQUALS, pg.K_PLUS, pg.K_KP_PLUS, pg.K_RIGHT):
                        speed_scale = change_speed(speed_scale, 1)
                        controls_until = time.monotonic() + 4
                    elif event.key in (pg.K_MINUS, pg.K_KP_MINUS, pg.K_LEFT):
                        speed_scale = change_speed(speed_scale, -1)
                        controls_until = time.monotonic() + 4
                elif event.type == pg.MOUSEMOTION:
                    controls_until = time.monotonic() + 4
                elif event.type == pg.MOUSEBUTTONDOWN and event.button == 1:
                    minus, plus = (pg.Rect(rect) for rect in speed_buttons(screen.get_size()))
                    if minus.collidepoint(event.pos):
                        speed_scale = change_speed(speed_scale, -1)
                        controls_until = time.monotonic() + 4
                    elif plus.collidepoint(event.pos):
                        speed_scale = change_speed(speed_scale, 1)
                        controls_until = time.monotonic() + 4
            if args.demo:
                keys = pg.key.get_pressed()
                demo_rpm = max(0, min(240, demo_rpm + (keys[pg.K_UP] - keys[pg.K_DOWN]) * 100 * dt))
                target = demo_rpm
            else:
                for line in reader.lines():
                    message = parse_line(line)
                    if message[0] == "event":
                        wheel.event(message[1])
                    elif message[0] == "raw":
                        status = f"sensor {message[1]}  baseline {message[2]}"
                target = wheel.target_rpm()
            shown_rpm += (target - shown_rpm) * min(1, dt * 4)
            speed_mps = shown_rpm / 60 * math.pi * args.diameter_cm / 100
            travel_m += speed_mps * speed_scale * dt
            draw_scene(pg, screen, travel_m, shown_rpm, speed_mps, status, font)
            if time.monotonic() < controls_until:
                draw_speed_controls(pg, screen, speed_scale, control_font)
            pg.display.flip()
    except KeyboardInterrupt:
        pass
    finally:
        if port is not None:
            port.close()
        pg.quit()


if __name__ == "__main__":
    main()
