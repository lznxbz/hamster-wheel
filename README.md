# 仓鼠跑轮第一人称互动动画

Arduino Uno 检测跑轮遮光事件，MacBook 根据转速让外接显示器呈现向前移动的 2D 路径与景物。当前轮径约 **12 cm**，两个遮光片在轮缘上等距安装，每转一圈应检测到 **2 次**遮光。画面默认没有仓鼠角色或测速文字，视角是朝前看的仓鼠视角。

## 硬件

- 光敏模块：`S → A0`、`+ → 5V`、`− → GND`。
- LED 模块：`GND → GND`、`VCC → 5V`、`IN → D9`。已通过这套接线实测：遮光时 A0 读数升高。
- LED 和光敏模块固定在轮子外侧，光线穿过轮缘的遮光片路径。两个遮光片、导线及模块必须固定牢靠，仓鼠不能碰到或啃咬，任何部件都不能摩擦轮子。

Arduino 程序**上电后自动追踪无遮挡读数**。传感器静止时被遮光片挡住也可以启动；轮子转动露出光路后，程序会更新基线并检测下一次遮光。Mac 程序不需要校准文件。若更换传感器、接线或光源，使“遮光时读数升高”这一方向反转，需要修改检测逻辑。

## 环境

安装 [Arduino CLI](https://arduino.github.io/arduino-cli/latest/installation/) 与 Uno AVR 平台。Python 使用 Conda 环境 `hamster-wheel`，包含 `pygame-ce` 和 `pyserial`。在项目根目录执行：

```bash
conda env create -f environment.yml
conda activate hamster-wheel
```


## 编译与上传 Uno

从项目根目录运行：

```bash
arduino-cli core install arduino:avr
arduino-cli compile --fqbn arduino:avr:uno arduino/wheel_sensor
arduino-cli board list
arduino-cli upload -p /dev/cu.usbmodem2101 --fqbn arduino:avr:uno arduino/wheel_sensor
```

Apple Silicon Mac 若无法执行 Arduino AVR 工具链，请安装兼容的本机 AVR 工具链后再编译上传。

`/dev/cu.usbmodem2101` 是本次检测到的 Uno 串口，重新插拔后可能变化，以 `board list` 为准。关闭 Arduino IDE 的串口监视器，避免占用端口。草图入口是 `arduino/wheel_sensor/wheel_sensor.ino`，实现位于同目录的 `.cpp` 文件。

## 启动动画

在本项目文件夹并激活 Conda 环境后，先测试窗口模式，再启动外接屏：

```bash
python app.py --list-ports
python app.py --list-displays
python app.py --demo --display 0 --windowed
python app.py --port /dev/cu.usbmodem2101 --display 1
```

本次检测到 MacBook 屏幕为 `0`，外接显示器为 `1`。演示模式使用上下方向键改变模拟转速，`Esc` 退出。路面和树木随跑轮速度向观察者移动；停轮后逐渐停止。近处树木位于屏幕两侧，高度接近整个画面。画面前进速度默认是跑轮计算速度的 **2 倍**。按 `+` / `−` 键（或右 / 左方向键）可调整画面速度，移动鼠标后可点击画面右上角的 `+` / `−` 按钮；控件 4 秒后自动隐藏。倍率可选 0.5、1、1.5、2、2.5、3、4、8、12、16、20；最高为之前 4 倍上限的 **5 倍**。也可在启动时使用 `--speed-scale 12` 设定初值。倍率仅影响画面，不影响 RPM 计算。需要给人检查读数时加 `--debug-hud`，默认动物观看的画面不显示测速文字。

默认参数是每圈 2 次遮光、轮径 12 cm；若硬件变化，使用 `--pulses-per-rev` 和 `--diameter-cm` 调整。转速按完整一圈的两个脉冲间隔计算，程序需收到至少 3 次连续遮光事件后才会显示有效 RPM。

## 验证结果与待观察项

本机已编译并上传自动追踪版 Uno 程序、通过 Python 转速测试、在外接屏启动新版实时动画。Uno 重启后未发送任何校准命令：静止时无误计，手转整整一圈记录到 2 次事件，结束后恢复无遮挡状态。高速运行时是否仍保持每圈 2 次尚需观察。光敏电阻在高速通过短遮光片时可能漏计；若出现这种情况，先检查遮光持续时间及两侧对准情况。
