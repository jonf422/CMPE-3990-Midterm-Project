import board
import busio
import time
import digitalio


from lcd_circuitpy.lcd import LCD
from lcd_circuitpy.i2c_pcf8574_interface import I2CPCF8574Interface
from lcd_circuitpy.lcd import CursorMode
from circuitpython_nrf24l01.rf24_lite import RF24

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
RADIO_ID = 0
ADDRESSES = (b"PGR00", b"PGR01")


#i2c pins
SCL = board.B6
SDA = board.B7

#i2c device addrs
LCD_ADDR = 0x27
KB_ADDR = 0x5f

#####################################
#       FUNCTION DEFS
######################################    

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


# ------------- Radio functions -------------------------- #
#TODO: radio send and receive
def radio_send(msg):
    nrf.listen = False                       # switch to transmit
    ok = nrf.send(msg.encode("utf-8")[:32])  # 32-byte max payload
    nrf.listen = True                        # back to receive
    print(f"send '{msg}': {'OK' if ok else 'FAILED'}")
    return ok

def radio_receive():
    if nrf.available():
        data = nrf.read()
        if data:
            try:
                return bytes(data).decode("utf-8").rstrip("\x00")
            except UnicodeError:
                return None
    return None

def recv_handle(msg):
    '''
    Stores a received message and marks the display dirty.

    Parameters:
    - msg: received message string

    SENDING: increments new message flag (doesn't interrupt typing)
    RECEIVING: message displays immediately on redraw
    '''
    global recv_msg, new_msg_flag, dirty

    recv_msg = msg
    if state == SENDING:
        new_msg_flag += 1
    dirty = True


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
    '''
    handler for enter key in SENDING

    if a message has been typed, the handler will transmit the message
    '''
    global send_msg, cursor_pos
    if send_msg:
        ok = radio_send(send_msg)
        send_msg, cursor_pos = "", 0
        lcd.set_cursor_pos(1, 0)
        lcd.print("SENT" if ok else "FAIL")
        time.sleep(.5)

def send_backspace():
    '''
    handler for backspace key in SENDING

    deletes character in message before the cursor
    '''
    global send_msg, cursor_pos
    if cursor_pos > 0:
        send_msg = send_msg[:cursor_pos-1] + send_msg[cursor_pos:]
        cursor_pos -= 1


def send_escape():
    '''
    handler for escape key in SENDING

    clears current message
    '''
    global send_msg, cursor_pos
    send_msg = ""
    cursor_pos = 0

def send_up():
    '''
    handler for up key in SENDING
    
    no current functionality
    '''
    pass

def send_down():
    '''
    handler for down key in SENDING
    
    no current functionality
    '''
    pass

def send_left():
    '''
    handler for left key in SENDING
    
    moves cursor left
    '''
    global cursor_pos
    cursor_pos = max(0, cursor_pos - 1)

def send_right():
    '''
    handler for right key in SENDING
    
    moves cursor right
    '''
    global cursor_pos
    cursor_pos = min(len(send_msg), cursor_pos + 1)

def tab(): ###### CHANGES DEVICE STATE SEND OR RECEIVE#################
    '''
    handler for tab key in SENDING or RECEIVING
    
    changes device state
    
    outbox <-> inbox
    '''
    next_state = not state
    change_state(next_state)


############ SPECIAL KEY HANDLER DICT
'''
KEY: VALUE => M5 KB Special Key: Special Key Handler Function

On index of special key, calls appropriate key handler function per device state
'''
SPECIAL = {
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

###########################################
# ------------- INITS ------------------- #
###########################################
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

#radio init
spi = busio.SPI(board.A5, MOSI=board.A7, MISO=board.A6)
csn = digitalio.DigitalInOut(board.A4)
ce = digitalio.DigitalInOut(board.B0)
nrf = RF24(spi, csn, ce)
nrf.pa_level = -12                  # low power for bench testing; raise later
nrf.open_tx_pipe(ADDRESSES[1 - RADIO_ID])     # send to the other pager
nrf.open_rx_pipe(1, ADDRESSES[RADIO_ID])      # listen on my own address
nrf.listen = True                   # default to receive mode


##########################################
# ------------- LOOP ------------------- #
##########################################
while 1:
    msg = radio_receive() #poll message receive function
    if msg is not None:
        recv_handle(msg)

    key = kb.read_key() #poll key press receive function
    if key is not None:
        dirty = True
        #check if key press was special key with function in current device state
        handlers = SPECIAL[state]
        if key in handlers: 
            handlers[key]() #call special key function

        #check if key press is keycode in ASCII range
        elif state == SENDING and 32 <= key <= 126:
            send_msg = send_msg[:cursor_pos] + chr(key) + send_msg[cursor_pos:] #add character to sending message
            cursor_pos += 1

    if dirty: #redraw screen
        redraw()
        dirty = False

    time.sleep(0.05)
