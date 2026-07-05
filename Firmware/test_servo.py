import time
from machine import Pin, PWM

# Initialize PWM pins for the servos at 50Hz
servo_x = PWM(Pin(29), freq=50)
servo_y = PWM(Pin(6), freq=50)

# 16-bit pulse width boundaries for typical 50Hz servos:
# ~1ms pulse (0 degrees)   -> ~3276 duty
# ~1.5ms pulse (90 degrees) -> ~4915 duty
# ~2ms pulse (180 degrees)  -> ~6553 duty
MIN_DUTY = 2500
MAX_DUTY = 7000
MID_DUTY = 4915

print("Centering servos...")
servo_x.duty_u16(MID_DUTY)
servo_y.duty_u16(MID_DUTY)
time.sleep(1.5)

print("Starting sweep test. Press Ctrl+C in the terminal to stop.")

try:
    while True:
        # Sweep from MIN to MAX
        print("Moving to MIN position...")
        servo_x.duty_u16(MIN_DUTY)
        servo_y.duty_u16(MIN_DUTY)
        time.sleep(1.0)
        
        # Sweep to Center
        print("Moving to CENTER position...")
        servo_x.duty_u16(MID_DUTY)
        servo_y.duty_u16(MID_DUTY)
        time.sleep(1.0)
        
        # Sweep to MAX
        print("Moving to MAX position...")
        servo_x.duty_u16(MAX_DUTY)
        servo_y.duty_u16(MAX_DUTY)
        time.sleep(1.0)

except KeyboardInterrupt:
    print("\nTest stopped. Centering servos before exiting...")
    servo_x.duty_u16(MID_DUTY)
    servo_y.duty_u16(MID_DUTY)
    time.sleep(0.5)
    # Deinitialize PWM to safely release the pins
    servo_x.deinit()
    servo_y.deinit()
    print("Servos disconnected safely.")