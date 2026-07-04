import time
from machine import Pin, PWM
from control import map_value, azmuth, altitude, joystick_x, joystick_y
import uasyncio as asyncio



x_duty = 0
y_duty = 0

async def read_joystick():
    global x_duty, y_duty
    while True:
        # Read the joystick values from ADC pins (replace with actual ADC reading code)
        x_value = joystick_x.read_u16()
        y_value = joystick_y.read_u16()

        x_duty = map_value(x_value,out_max = 360)
        y_duty = map_value(y_value, out_max = 120)

        await asyncio.sleep_ms(20)


async def main_loop():
    global x_duty, y_duty
    while True:
        azimuth.duty(x_duty)
        altitude.duty(y_duty)
        await asyncio.sleep_ms(20)




async def main():
    await asyncio.gather(read_joystick(), main_loop())

uasyncio.run(main())