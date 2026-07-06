#should run at startup
import time
from machine import Pin, PWM
from control import map_value, x_axis, y_axis, joystick_x, joystick_y, filtered_x, filtered_y, get_filtered_reading, MIN_DUTY, MAX_DUTY, joy_switch,slider_servo
import uasyncio as asyncio
import motor
import setup
from setup import SLIDER_POT
import sys
import select



MAX_SPEED = 100  
current_duty_x = 4915  
current_duty_y = 4915

poll = select.poll()
poll.register(sys.stdin, select.POLLIN)


async def read_serial():
    while True:
        events = poll.poll(0)  
        if events:
            line = sys.stdin.readline().strip()
            if line == "F":
                print("FIRE command received from serial")
                motor.set_motor_a()
                await asyncio.sleep(0.1)
                motor.stop_slider_motor()
        await asyncio.sleep_ms(20)

async def read_switch():
    while True:
        value = joy_switch.value()
        if value == 0:
            print("Rotating the servo to drop")
            motor.set_motor_a()
            await asyncio.sleep(0.1)
            motor.stop_slider_motor()
    
            while joy_switch.value() == 0:
                await asyncio.sleep_ms(50) 
                
            print("Button released. Ready for next drop.")
            
        await asyncio.sleep_ms(200)

async def main_loop():
    global filtered_x, filtered_y, current_duty_x, current_duty_y
    while True:
        # 1. Read joystick inputs
        filtered_x = get_filtered_reading(joystick_x, filtered_x)
        filtered_y = get_filtered_reading(joystick_y, filtered_y)
        
        # 2. Get target positions from joystick
        target_duty_x = map_value(filtered_x, 0, 65535, MIN_DUTY, MAX_DUTY)
        target_duty_y = map_value(filtered_y, 0, 65535, MIN_DUTY, MAX_DUTY)
        
        # 3. Smoothly step X-axis toward target position
        diff_x = target_duty_x - current_duty_x
        if abs(diff_x) > MAX_SPEED:
            if diff_x > 0:
                current_duty_x += MAX_SPEED
            else:
                current_duty_x -= MAX_SPEED
        else:
            current_duty_x = target_duty_x

        # 4. Smoothly step Y-axis toward target position
        diff_y = target_duty_y - current_duty_y
        if abs(diff_y) > MAX_SPEED:
            if diff_y > 0:
                current_duty_y += MAX_SPEED
            else:
                current_duty_y -= MAX_SPEED
        else:
            current_duty_y = target_duty_y
        
        # 5. Write smoothed values to the servos
        x_axis.duty_u16(current_duty_x)
        y_axis.duty_u16(current_duty_y)
      
        # Yield execution back to the asyncio event loop for 20ms
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

    x_axis.duty_u16(4915)  
    y_axis.duty_u16(30000)
    slider_servo.duty_u16(4915)
    await asyncio.sleep_ms(400) 
    
    print("Starting background loops...")
    await asyncio.gather(main_loop(), read_pot_value(), read_switch(), read_serial())

asyncio.run(main())


