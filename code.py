import board
import busio
import time

from lcd.lcd import LCD
from lcd.i2c_pcf8574_interface import I2CPCF8574Interface
from lcd.lcd import CursorMode

import m5_micro_keyboard as m5

SCL = board.B6
SDA = board.B7

LCD_ADDR = 0x27
KB_ADDR = 0x5f

msg = ""
cursor_pos = 0

# ------------- LCD functions -------------------------- #
def redraw():
    lcd.clear()
    lcd.print(msg[:16])
    lcd.set_cursor_pos(0, min(cursor_pos, 15))

# ------------ Special key handler functions -------------- #
def on_enter():
    global msg, cursor_pos
    #radio.send()
    print(f"sent: {msg}")
    msg, cursor_pos = "", 0
    lcd.set_cursor_pos(1, 0)
    lcd.print("SENT")
    time.sleep(.5)
def on_backspace():
    global msg
    msg = msg[0:-1]
def on_tab():
    pass
def on_escape():
    global msg
    msg = ""
def on_up():
    pass
def on_down():
    pass
def on_left():
    global cursor_pos
    cursor_pos -= 1
def on_right():
    global cursor_pos
    cursor_pos += 1

SPECIAL = { #special key handler dict
    m5.Keyboard.ENTER: on_enter,
    m5.Keyboard.BACKSPACE: on_backspace,
    m5.Keyboard.TAB: on_tab,
    m5.Keyboard.ESC: on_escape,
    m5.Keyboard.UP: on_up,
    m5.Keyboard.DOWN: on_down,
    m5.Keyboard.LEFT: on_left,
    m5.Keyboard.RIGHT: on_right
}

# ------------- INIT ------------------- #
i2c = busio.I2C(scl=SCL, sda=SDA) #init I2C bus
i2c.try_lock()

#check address list is valid
try:
    address = i2c.scan()
    if KB_ADDR not in address:
        print(f"keyboard not found at address {hex(KB_ADDR)}")
        print(f"found address of i2c '{[hex(addr) for addr in address]}'")
        raise Exception("keyboard not found")
    if LCD_ADDR not in address:
        print(f"lcd not found at address {hex(LCD_ADDR)}")
        print(f"found address of i2c '{[hex(addr) for addr in address]}'")
        raise Exception("lcd not found")
finally:
    i2c.unlock()

kb = m5.Keyboard(i2c) #init keyboard from class
lcd = LCD(I2CPCF8574Interface(i2c, LCD_ADDR), num_rows=2, num_cols=16) #init lcd using libraries
lcd.set_cursor_mode(CursorMode.LINE | CursorMode.BLINK) #set cursor mode
lcd.clear()

# ------------- LOOP ------------------- #
while 1:
    key = kb.read_key()
    if key is not None:
        if key in SPECIAL:
            SPECIAL[key]()
        elif 32 <= key <= 126:  # Printable ASCII range
            msg = msg[:cursor_pos] + chr(key) + msg[cursor_pos:]
            cursor_pos += 1
        redraw()
    time.sleep(0.05)
