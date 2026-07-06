import time
from machine import Pin, PWM, ADC

x_axis = PWM(Pin(29), freq=50)
y_axis = PWM(Pin(4), freq=50)

slider_servo = PWM(Pin(3), freq=50)

joystick_x = ADC(Pin(27))
joystick_y = ADC(Pin(28))
joy_switch = Pin(6, Pin.IN, Pin.PULL_UP)

CENTER_VAL = 32768
DEADZONE = 2000
SMOOTHING = 0.2

MIN_DUTY = 2500
MAX_DUTY = 7000

filtered_x = CENTER_VAL
filtered_y = CENTER_VAL

def get_filtered_reading(adc_pin, current_filtered):
    # This reads 0-65535 natively on RP2040
    raw = adc_pin.read_u16() 
    if abs(raw - CENTER_VAL) < DEADZONE:
        target = CENTER_VAL
    else:
        target = raw
    updated_val = current_filtered + SMOOTHING * (target - current_filtered)
    return updated_val

def map_value(x, in_min, in_max, out_min, out_max):
    return int((x - in_min) * (out_max - out_min) / (in_max - in_min) + out_min)


