from machine import Pin, PWM, ADC

PWM_FREQ = 20000

# XIAO RP2040 ADC uses GPIO 26 (D0)
SLIDER_POT = ADC(Pin(26)) 

# Motor Driver Pins mapped to D5, D6, D7, D8
ain1 = PWM(Pin(7), freq=PWM_FREQ, duty_u16=0)
ain2 = PWM(Pin(0), freq=PWM_FREQ, duty_u16=0)

bin1 = PWM(Pin(1), freq=PWM_FREQ, duty_u16=0)
bin2 = PWM(Pin(2), freq=PWM_FREQ, duty_u16=0)

motor_speed = 0

MIN_START_DUTY = 30000
MAX_DUTY = 65535
