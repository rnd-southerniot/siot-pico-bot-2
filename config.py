"""
siot-pico-bot: Hardware Configuration
Central pin definitions and constants for the Robo Pico platform.

Hardware:
  - Cytron Robo Pico (MX1515H motor driver)
  - Raspberry Pi Pico W
  - TT Metal Gear Motor w/ Hall Encoder (×2)
  - MPU6050 IMU (GY-521)
  - Cytron Aluminum 2WD TT Chassis
"""

# ──────────────────────────────────────────────
# Motor Driver (MX1515H on Robo Pico)
# ──────────────────────────────────────────────
MOTOR_LEFT_A  = 8    # GP8  — M1A (forward)
MOTOR_LEFT_B  = 9    # GP9  — M1B (backward)
MOTOR_RIGHT_A = 10   # GP10 — M2A (forward)
MOTOR_RIGHT_B = 11   # GP11 — M2B (backward)
MOTOR_PWM_FREQ = 1000  # Hz (MX1515H supports up to 20kHz)

# ──────────────────────────────────────────────
# Hall Encoders (TT Motor, PH2.0-6PIN)
#   Wiring: V→3V3, G→GND, H1→Ch_A, H2→Ch_B
# ──────────────────────────────────────────────
ENC_LEFT_A  = 6    # GP6  — Left Hall H1 (Channel A)
ENC_LEFT_B  = 7    # GP7  — Left Hall H2 (Channel B)
ENC_RIGHT_A = 26   # GP26 — Right Hall H1 (Channel A)
ENC_RIGHT_B = 27   # GP27 — Right Hall H2 (Channel B)

# ──────────────────────────────────────────────
# Encoder Constants
# ──────────────────────────────────────────────
ENCODER_MAG_PULSES = 6       # Magnetic ring pulses per motor rev
GEAR_RATIO         = 42      # 1:42 gearbox
TICKS_PER_REV      = ENCODER_MAG_PULSES * GEAR_RATIO  # 252 (single-phase)
TICKS_PER_REV_QUAD = TICKS_PER_REV * 4                # 1008 (quadrature 4×)

# ──────────────────────────────────────────────
# Wheel / Chassis Geometry
# ──────────────────────────────────────────────
WHEEL_DIAMETER_MM    = 65.0
WHEEL_CIRCUMFERENCE  = 3.14159265 * WHEEL_DIAMETER_MM  # ~204.2 mm
MM_PER_TICK          = WHEEL_CIRCUMFERENCE / TICKS_PER_REV  # ~0.81 mm
TRACK_WIDTH_MM       = 150.0   # Distance between wheel centers (measure yours)

# ──────────────────────────────────────────────
# IMU — MPU6050 via I2C
# ──────────────────────────────────────────────
I2C_ID    = 0
I2C_SDA   = 0     # GP0 — Grove 1 SDA (I2C0)
I2C_SCL   = 1     # GP1 — Grove 1 SCL (I2C0)
I2C_FREQ  = 400000

MPU6050_ADDR    = 0x68
MPU6050_WHO_AM_I = 0x75
MPU6050_PWR_MGMT = 0x6B
MPU6050_ACCEL_X  = 0x3B   # 14 bytes: accel(6) + temp(2) + gyro(6)
MPU6050_GYRO_Z_H = 0x47   # 2 bytes: gyro Z high + low

# Sensitivity at default ranges
ACCEL_SCALE = 16384.0   # LSB/g  (±2g range)
GYRO_SCALE  = 131.0     # LSB/(°/s) (±250°/s range)

# ──────────────────────────────────────────────
# Onboard Peripherals (Robo Pico)
# ──────────────────────────────────────────────
NEOPIXEL_PIN   = 18   # GP18 — 2× WS2812 RGB LEDs
NEOPIXEL_COUNT = 2
BUZZER_PIN     = 22   # GP22 — Piezo buzzer (check mute switch!)
BUTTON_A_PIN   = 20   # GP20 — Programmable button A
BUTTON_B_PIN   = 21   # GP21 — Programmable button B

# ──────────────────────────────────────────────
# Servo Ports
# ──────────────────────────────────────────────
SERVO_PINS = [12, 13, 14, 15]  # GP12–GP15

# ──────────────────────────────────────────────
# WiFi (Gate 8)
# ──────────────────────────────────────────────
WIFI_AP_SSID     = "RoboPico-Lab"
WIFI_AP_PASSWORD = "robopico1"
WIFI_AP_IP       = "192.168.4.1"
HTTP_PORT        = 80

# ──────────────────────────────────────────────
# Motor Safety (K-8 classroom safety cap)
# ──────────────────────────────────────────────
# K-8 safety: maximum motor speed as a percentage (0–100).
# Applied inside MotorHAL.drive() — cannot be bypassed by higher layers.
# 70% reduces collision energy while keeping movement engaging.
# Adjust per school environment if needed.
MOTOR_MAX_SPEED_PCT = 70

# ──────────────────────────────────────────────
# PID Defaults (Gate 6) — tune for your motors
# ──────────────────────────────────────────────
PID_KP = 0.8
PID_KI = 0.3
PID_KD = 0.05
PID_LOOP_HZ = 20
PID_TARGET_RPM = 60

# ──────────────────────────────────────────────
# Autonomous Mission Defaults (Gate 9)
# ──────────────────────────────────────────────
MISSION_SIDE_MM     = 500    # 50 cm square
MISSION_TURN_DEG    = 90
MISSION_DRIVE_SPEED = 40     # % PWM
MISSION_TURN_SPEED  = 30     # % PWM
MISSION_TURN_TOL    = 3.0    # degrees
