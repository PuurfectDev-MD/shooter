import time
from machine import Pin, PWM, ADC

azimuth = PWM(Pin(2, Pin.OUT), freq=50)
altitude = PWM(Pin(3, Pin.OUT), freq=50)

joystick_x = ADC(Pin(34))
joystick_y = ADC(Pin(35))

joystick_x.atten(ADC.ATTN_11DB) 
joystick_y.atten(ADC.ATTN_11DB)  


def map_value(x, in_min=0, in_max=65535, out_min=0, out_max=100):
    return int((x-in_min)/(in_max-in_min)*(out_max-out_min)+out_min)
#maps the value of the joystick to pwm values for the servo motors





