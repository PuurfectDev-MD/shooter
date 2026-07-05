from setup import ain1, ain2, bin1, bin2
def set_motor_a(speed):
    if speed > 0:
        ain1.duty_u16(speed)
        ain2.duty_u16(0)
    elif speed < 0:
        ain1.duty_u16(0)
        ain2.duty_u16(abs(speed))
    else:
        ain1.duty_u16(0)
        ain2.duty_u16(0)

def set_motor_b(speed):
    if speed > 0:
        bin1.duty_u16(speed)
        bin2.duty_u16(0)
    elif speed < 0:
        bin1.duty_u16(0)
        bin2.duty_u16(abs(speed))
    else:
        bin1.duty_u16(0)
        bin2.duty_u16(0)
        
        
def stop_all():
    set_motor_a(0)
    set_motor_b(0)
    

def set_both_speed(speed): #for shooting
    from setup import MIN_START_DUTY, MAX_DUTY
    if speed < 1 or speed>10:
        bin1.duty_u16(0)
        bin2.duty_u16(0)
        ain1.duty_u16(0)
        ain2.duty_u16(0)
    else:
        value = int(MIN_START_DUTY + ((MAX_DUTY - MIN_START_DUTY) / 9) * (speed - 1))
        print("the value for motor pwm is ", value)
        bin1.duty_u16(value)
        bin2.duty_u16(0)
        ain1.duty_u16(value)
        ain2.duty_u16(0)
        



