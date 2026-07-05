import time
from machine import Pin, PWM
from control import map_value, x_axis, y_axis, joystick_x, joystick_y, filtered_x, filtered_y, get_filtered_reading, MIN_DUTY, MAX_DUTY
import uasyncio as asyncio
import motor
import setup
from setup import SLIDER_POT

async def main_loop():
    global x_duty, y_duty, filtered_x, filtered_y
    while True:
        filtered_x = get_filtered_reading(joystick_x, filtered_x)
        filtered_y = get_filtered_reading(joystick_y, filtered_y)
        
        duty_x = map_value(filtered_x, 0, 65535, MIN_DUTY, MAX_DUTY)
        duty_y = map_value(filtered_y, 0, 65535, MIN_DUTY, MAX_DUTY)
        
        x_axis.duty_u16(duty_x)
        y_axis.duty_u16(duty_y)
        
        print(f"x_duty= {duty_x}")
        print(f"y_duty = {duty_y}")
        await asyncio.sleep_ms(20)
        
async def read_pot_value():
    import setup
    while True:
        raw_value = SLIDER_POT.read_u16()
        speed_value = raw_value // 6553
        
        if speed_value != setup.motor_speed:
            print("Value changed")
            setup.motor_speed = speed_value
            print("Motor speed is now", setup.motor_speed)
            motor.set_both_speed(setup.motor_speed)
        await asyncio.sleep_ms(200)

async def main():
    print("Initializing servos to idle/stop position...")

    # Fixed: Replaced ESP32 8-bit .duty(77) with RP2040 16-bit center value (~4915)
    x_axis.duty_u16(4915)  
    y_axis.duty_u16(4915) 
    await asyncio.sleep_ms(400) 
    
    print("Starting background loops...")
    await asyncio.gather(main_loop(), read_pot_value())

asyncio.run(main())