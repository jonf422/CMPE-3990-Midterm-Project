import board
import busio
import time

from lcd_circuitpy.lcd import LCD
from lcd_circuitpy.i2c_pcf8574_interface import I2CPCF8574Interface
from lcd_circuitpy.lcd import CursorMode

import m5_micro_keyboard as m5

#state machine
SENDING, RECEIVING = 0,1

#Global Vars
state = SENDING
send_msg = ""
cursor_pos = 0
recv_msg = ""
new_msg_flag = 0
status = ""
dirty = True
lcd_cols = 16

### FOR TESTINGG ##################
last_recv_time = time.monotonic()
test_index = 0
###############################

#i2c pins
SCL = board.B6
SDA = board.B7

#i2c device addrs
LCD_ADDR = 0x27
KB_ADDR = 0x5f

# ------------ State Machine Functions ------------------- #
def set_status():
    '''
    Sets status message based on device state [SENDING, RECEIVING]

    SENDING: Displays new message flag
    RECEIVING: Displays instructions to exit to SENDING
    '''
    global status
    if state == SENDING:
        status = f"INBOX: {new_msg_flag}"
    else:
        status = "TAB TO EXIT"


def change_state(next_state):
    '''
    Changes device state and marks display dirty

    Parameters:
    - next_state: state to enter

    SENDING: clears new message flag, reenables cursor
    RECIEVING: hides cursor
    '''
    global state, new_msg_flag, dirty

    state = next_state
    lcd.set_cursor_pos(0,0)

    if state == SENDING:
        new_msg_flag = 0
        lcd.set_cursor_mode(CursorMode.LINE)
    else: #state == RECEIVING
        lcd.set_cursor_mode(CursorMode.HIDE) 
    dirty = True

#############################################################
# ------------- Radio functions -------------------------- #
#TODO: radio send and receive
def radio_send(msg):
    print(f"Sent: {msg}")

def radio_receive():
    global recv_msg, new_msg_flag, last_recv_time, dirty, test_index
    if time.monotonic() - last_recv_time > 30: #send test msg every 30s
        recv_msg = f"test{test_index}"
        test_index += 1

        if state == SENDING: #enable msg flag
            new_msg_flag = 1
        last_recv_time = time.monotonic()
        dirty = True
################################################################


# ------------- LCD functions -------------------------- #
def redraw():
    '''
    Redraws LCD display, updating send/receive and status message and reprinting

    SENDING: displays current send_msg, sets cursor to last cursor_pos
    RECIEVING: displays most recent recv_message or blank if none.    
    '''
    set_status()
    lcd.clear()

    if state == SENDING:
        lcd.print(send_msg[:lcd_cols])

    else:
        lcd.print(recv_msg[:lcd_cols])

    lcd.set_cursor_pos(1, lcd_cols - len(status))
    lcd.print(status)

    if state == SENDING:
        lcd.set_cursor_pos(0, min(cursor_pos, lcd_cols - 1))


# ------------ Special key handler functions -------------- #
#######  SENDING
def send_enter():
    global send_msg, cursor_pos
    if send_msg:
        #TODO: radio.send()
        radio_send(send_msg)
        send_msg, cursor_pos = "", 0
        lcd.set_cursor_pos(1, 0)
        lcd.print("SENT")
        time.sleep(.5)
    else:
        change_state(RECEIVING)

def send_backspace():
    global send_msg, cursor_pos
    if cursor_pos > 0:
        send_msg = send_msg[:cursor_pos-1] + send_msg[cursor_pos:]
        cursor_pos -= 1


def send_escape():
    global send_msg, cursor_pos
    send_msg = ""
    cursor_pos = 0

def send_up():
    pass

def send_down():
    pass

def send_left():
    global cursor_pos
    cursor_pos = max(0, cursor_pos - 1)

def send_right():
    global cursor_pos
    cursor_pos = min(len(send_msg), cursor_pos + 1)

def tab():
    next_state = not state
    change_state(next_state)


############ SPECIAL KEY HANDLER
SPECIAL = { #special key handler dict
    SENDING: {
        m5.Keyboard.ENTER: send_enter,
        m5.Keyboard.BACKSPACE: send_backspace,
        m5.Keyboard.TAB: tab,
        m5.Keyboard.ESC: send_escape,
        m5.Keyboard.UP: send_up,
        m5.Keyboard.DOWN: send_down,
        m5.Keyboard.LEFT: send_left,
        m5.Keyboard.RIGHT: send_right
    },

    RECEIVING: {
        m5.Keyboard.TAB: tab
    }
}


# ------------- INIT ------------------- #
i2c = busio.I2C(scl=SCL, sda=SDA) #init I2C bus
while not i2c.try_lock(): pass

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
lcd = LCD(I2CPCF8574Interface(i2c, LCD_ADDR), num_rows=2, num_cols=lcd_cols) #init lcd using libraries
lcd.set_cursor_mode(CursorMode.LINE) #set cursor mode
lcd.clear()

# ------------- LOOP ------------------- #
while 1:
    radio_receive()
    key = kb.read_key()
    if key is not None:
        handlers = SPECIAL[state]
        if key in handlers:
            handlers[key]()
        elif state == SENDING and 32 <= key <= 126:  # Printable ASCII range
            send_msg = send_msg[:cursor_pos] + chr(key) + send_msg[cursor_pos:]
            cursor_pos += 1
        dirty = True

    if dirty: #redraw screen
        redraw()
        dirty = False

    time.sleep(0.05)
