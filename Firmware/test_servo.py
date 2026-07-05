import machine
import time

# Set up PWM on pins 32 and 33
# Standard servo frequency is 50Hz (20ms period)
servo1 = machine.PWM(machine.Pin(32), freq=50)
servo2 = machine.PWM(machine.Pin(33), freq=50)

def set_servo_pulse(servo, us):

    duty = int((us / 20000) * 1023)
    servo.duty(duty)

print("Starting servo test... Press Ctrl+C to stop.")

try:
    while True:
        # 1. Rotate Full Speed Forward
        print("Rotating forward...")
        set_servo_pulse(servo1, 2000) # Max speed forward
        set_servo_pulse(servo2, 2000)
        time.sleep(3)                 # Run for 3 seconds

        # 2. Stop the servos
        print("Stopping...")
        set_servo_pulse(servo1, 1500) # Neutral/Stop pulse
        set_servo_pulse(servo2, 1500)
        time.sleep(2)                 # Stay stopped for 2 seconds

        # 3. Rotate Full Speed Backward
        print("Rotating backward...")
        set_servo_pulse(servo1, 1000) # Max speed backward
        set_servo_pulse(servo2, 1000)
        time.sleep(3)                 # Run for 3 seconds

        # 4. Stop the servos again
        print("Stopping...")
        set_servo_pulse(servo1, 1500)
        set_servo_pulse(servo2, 1500)
        time.sleep(2)

except KeyboardInterrupt:
    # Clean up and turn off PWM on exit
    print("\nStopping PWM...")
    servo1.deinit()
    servo2.deinit()
    print("Test finished.")