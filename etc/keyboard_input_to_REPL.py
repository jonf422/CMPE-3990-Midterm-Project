#Found this online
# https://scruss.com/blog/2021/06/02/cardkb-mini-keyboard-with-micropython/
import time
import board
import busio


#SDA = board.B6
#SCL = board.B7


i2c = busio.I2C(board.SCL, board.SDA)
 
while not i2c.try_lock():
    pass
 
cardkb = i2c.scan()[0]  # should return 95
if cardkb != 95:
    print("!!! Check I2C config: " + str(i2c))
    print("!!! CardKB not found. I2C device", cardkb,
          "found instead.")
    exit(1)
 
ESC = chr(27)
NUL = '\x00'
CR = "\r"
LF = "\n"
c = ''
b = bytearray(1)
 
# can't really clear screen, so this will do
for i in range(12):
    print()
print("*** APPALLING TYPEWRITER ***")
print("** Type stuff, Esc to end **")
for i in range(8):
    print()
 
while (c != ESC):
    # returns NUL char if no character read
    i2c.readfrom_into(cardkb, b)
    c = b.decode()
    if c == CR:
        # convert CR return key to LF
        c = LF
    if c != NUL or c != ESC:
        print(c, end='')
    time.sleep(0.005)
 
# be nice, clean up
i2c.unlock()
