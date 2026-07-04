import time
from machine import Pin, PWM
from control import map_value, azimuth, altitude, joystick_x, joystick_y
import uasyncio as asyncio



x_duty = 0
y_duty = 0

prev_x_duty= 0
prev_y_duty = 0

async def read_joystick():
    global x_duty, y_duty, prev_x_duty, prev_y_duty
    while True:
        # Read the joystick values from ADC pins (replace with actual ADC reading code)
        x_value = joystick_x.read_u16()
        y_value = joystick_y.read_u16()
        
        print(f"x-value = {x_value}")
        print(f"y-value = {y_value}")
        
        prev_x_duty = x_duty
        prev_y_duty  =y_duty

        x_duty = map_value(x_value,out_max = 360)
        y_duty = map_value(y_value, out_max = 120)
        
        print(f"X duty: {x_duty}")
        print(f"Y duty: {y_duty}")

        await asyncio.sleep_ms(20)


async def main_loop():
    global x_duty, y_duty
    while True:
        if prev_x_duty != x_duty or prev_y_duty != y_duty:
            azimuth.duty(x_duty)
            altitude.duty(y_duty)
        
        await asyncio.sleep_ms(20)


async def main():
    print("Initializing servos to startup position...")
    await asyncio.sleep_ms(100)
    azimuth.duty(75)  # Center position (~1.5ms pulse)
    altitude.duty(75) 
    await asyncio.sleep_ms(500) # Give them time to physically move there
    
    print("Starting background loops...")
    await asyncio.gather(read_joystick(), main_loop())
    
asyncio.run(main())