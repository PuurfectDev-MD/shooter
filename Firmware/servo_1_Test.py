import machine
import time

# Isolate just pin 33
servo = machine.PWM(machine.Pin(33), freq=50)

def set_pulse(us):
    # Calculate duty cycle for 50Hz (20,000us period)
    duty = int((us / 20000) * 1023)
    servo.duty(duty)

print("Testing Pin 33... Press Ctrl+C to stop.")

try:
    while True:
        print("Forward...")
        set_pulse(2000)
        time.sleep(2)
        
        print("Stopping...")
        set_pulse(1500)
        time.sleep(2)
        
        print("Backward...")
        set_pulse(1000)
        time.sleep(2)

except KeyboardInterrupt:
    servo.deinit()
    print("Test stopped.")