import time
from machine import Pin, PWM, ADC

# Initialize PWM pins
azimuth = PWM(Pin(33, Pin.OUT), freq=50)
altitude = PWM(Pin(32, Pin.OUT), freq=50)

# Initialize ADC pins for joystick
joystick_x = ADC(Pin(27))
joystick_y = ADC(Pin(26))

joystick_x.atten(ADC.ATTN_11DB) 
joystick_y.atten(ADC.ATTN_11DB)  

def map_value(x, in_min=0, in_max=65535, out_min=40, out_max=115):
    """
    Maps ADC (0-65535) to standard Servo Duty values (approx 40 to 115).
    77 is roughly the center point (1.5ms pulse) where continuous servos stop.
    """
    return int((x - in_min) / (in_max - in_min) * (out_max - out_min) + out_min)