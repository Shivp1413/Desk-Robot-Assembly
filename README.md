# ESP32-S3 OLED Face Animation & Servo Sequence Controller

A small interactive project using an **ESP32-S3**, an **SSD1306 OLED display**, and a **continuous rotation servo**.



<div align="center">

<table>
<tr>
<td align="center">
<img width="180" alt="servo" src="https://github.com/user-attachments/assets/9d367be8-0ce0-4d2c-acf7-f6d161c78587" />
Servo
</td>

<td align="center">
<img width="180"alt="oled" src="https://github.com/user-attachments/assets/81e17031-9a93-474a-8745-2771dc6871a0" />
OLED Display
</td>

<td align="center">
<img width="180" alt="esp32s3" src="https://github.com/user-attachments/assets/2391cfb4-a9ea-4b15-964a-acab5b97b2d5" />
ESP32-S3
</td>
</tr>
</table>

</div>


The ESP32 receives text commands through the Serial Monitor. These commands control:

- Animated OLED facial expressions
- Servo rotation direction and timing
- Complete action sequences

The system uses a non-blocking design, allowing the OLED animation to continue while servo movements and commands are executed.

---

# Features

## OLED Face Animation

The project uses a 128x64 SSD1306 OLED display over I2C.

### Happy Face

Features:

- Animated smiling face
- Blinking eyes
- Rising balloons
- Decorative stars

### Sad Face

Features:

- Sad expression
- Falling tears
- Eyebrows
- Animated face

The selected face continues animating after the sequence finishes.

---

# Servo Control

The servo is controlled using ESP32 LEDC PWM.

The project supports:

- Continuous rotation servo control
- Right rotation
- Left rotation
- Automatic stopping after movement

PWM settings:

```cpp
#define SERVO_FREQ 50
#define SERVO_RES_BITS 14
````

---

# Hardware Requirements

## Components

* ESP32-S3 development board
* SSD1306 128x64 OLED display
* Continuous rotation servo
* Jumper wires
* External 5V servo power supply (recommended)

---

# Wiring

## OLED Display (I2C)

| OLED Pin | ESP32-S3 Pin |
| -------- | ------------ |
| VCC      | 3.3V         |
| GND      | GND          |
| SDA      | GPIO 6       |
| SCL      | GPIO 5       |

---

## Servo

| Servo Wire | Connection              |
| ---------- | ----------------------- |
| Signal     | GPIO 9                  |
| VCC        | External 5V recommended |
| GND        | ESP32 GND               |

**Important:** The servo ground and ESP32 ground must be connected together.

---

# Required Arduino Libraries

Install these libraries using Arduino IDE Library Manager:

* Adafruit GFX Library
* Adafruit SSD1306 Library

Installation:

```
Arduino IDE
→ Tools
→ Manage Libraries
→ Search library name
→ Install
```

---

# Pin Configuration

Default pins:

```cpp
#define OLED_SDA 6
#define OLED_SCL 5
#define SERVO_PIN 9
```

OLED configuration:

```cpp
#define SCREEN_WIDTH 128
#define SCREEN_HEIGHT 64
#define OLED_ADDRESS 0x3C
```

---

# Upload Instructions

1. Connect ESP32-S3 to your computer.
2. Open Arduino IDE.
3. Select your ESP32-S3 board.
4. Select the correct COM port.
5. Upload the sketch.
6. Open Serial Monitor.

Serial Monitor settings:

```
Baud Rate: 115200
Line Ending: Newline
```

---

# Serial Command System

Commands follow this format:

```
COMMAND + VALUE
```

Example:

```
H5 R800 S3 L500 H2
```

This executes:

1. Happy face for 5 seconds
2. Servo rotates right for 800ms
3. Sad face for 3 seconds
4. Servo rotates left for 500ms
5. Happy face for 2 seconds

---

# Available Commands

## Happy Face

Format:

```
H<seconds>
```

Example:

```
H5
```

Shows the happy face animation for 5 seconds.

---

## Sad Face

Format:

```
S<seconds>
```

Example:

```
S3
```

Shows the sad face animation for 3 seconds.

---

## Servo Right

Format:

```
R<milliseconds>
```

Example:

```
R800
```

Rotates the servo right for 800 milliseconds.

---

## Servo Left

Format:

```
L<milliseconds>
```

Example:

```
L500
```

Rotates the servo left for 500 milliseconds.

---

## Stop / Cancel

Commands:

```
X
```

or:

```
STOP
```

Stops:

* Current sequence
* Servo movement

The OLED animation continues running.

---

# Command Separator

Commands can be separated using:

* Spaces
* Tabs
* Commas

Examples:

```
H5 R800 S3
```

or:

```
H5,R800,S3
```

Lowercase commands are also accepted:

```
h5 r800
```

is the same as:

```
H5 R800
```

---

# Sequence System

The project uses a non-blocking state machine.

It does not use `delay()` during operation.

The sequence system works like this:

```
Receive command
        |
        v
Parse action
        |
        v
Start action
        |
        v
Wait using millis()
        |
        v
Run next action
```

Advantages:

* OLED animation remains smooth
* Serial input stays responsive
* Multiple actions can run automatically

---

# Servo Calibration

Default servo values:

```cpp
#define STOP_US 1500
#define RIGHT_US 1556
#define LEFT_US 1444
```

## Adjust Stop Position

If the servo moves while stopped:

Change:

```cpp
#define STOP_US
```

Example:

```cpp
#define STOP_US 1495
```

---

## Adjust Speed / Direction

Modify:

```cpp
#define RIGHT_US
#define LEFT_US
```

depending on your servo.



---

# License

This project is provided for educational and hobby use.

Feel free to modify and improve it for your own projects.

```
```
