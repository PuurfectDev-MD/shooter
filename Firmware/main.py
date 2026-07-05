import time
from machine import Pin, PWM
from control import map_value, x_axis, y_axis, joystick_x, joystick_y, filtered_x, filtered_y, get_filtered_reading, MIN_DUTY, MAX_DUTY
import uasyncio as asyncio

# async def read_joystick():
#     global x_duty, y_duty, prev_x_duty, prev_y_duty
#     while True:
#         x_value = joystick_x.read_u16()
#         y_value = joystick_y.read_u16()
#         
#         print(x_value)
#         print(y_value)
#         
#         prev_x_duty = x_duty
#         prev_y_duty = y_duty
# 
#         
#         x_duty = map_value(x_value)
#         y_duty = map_value(y_value)
#         
#         print(f"X duty: {x_duty} | Y duty: {y_duty}")
# 
#         await asyncio.sleep_ms(20)
# 
async def main_loop():
    global x_duty, y_duty, filtered_x, filtered_y
    while True:
        filtered_x = get_filtered_reading(joystick_x, filtered_x)
        filtered_y = get_filtered_reading(joystick_y, filtered_y)
        
        
        duty_x = map_value(filtered_x, 0,65535, MIN_DUTY, MAX_DUTY)
        duty_y = map_value(filtered_y, 0, 65535, MIN_DUTY, MAX_DUTY)
        
        x_axis.duty(duty_x)
        y_axis.duty(duty_y)
            
        await asyncio.sleep_ms(20)

async def main():
    print("Initializing servos to idle/stop position...")
    await asyncio.sleep_ms(100)

    x_axis.duty(77)  
    y_axis.duty(77) 
    await asyncio.sleep_ms(500) 
    
    print("Starting background loops...")
    await asyncio.gather( main_loop())
    
asyncio.run(main())