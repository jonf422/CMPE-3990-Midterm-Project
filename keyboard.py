import board 
import busio

PIN_SCL = board.B6
PIN_SDA = board.B7

class Keyboard:
    KB_ADDR = 0x5f

    def __init__(self, i2c, addr=KB_ADDR):
        self._i2c = i2c
        self._addr = addr
        self._buf = bytearray(1)

        while not self._i2c.try_lock():
            pass
        try:
            found = self._i2c.scan()
        finally:
            self._i2c.unlock()

        if self._addr not in found:
            raise RuntimeError(f"CARD KB not found at {self._addr}. Bus has {found}")

    def read_key(self):
        while not self._i2c.try_lock():
            pass
        try:
            self._i2c.readfrom_into(self._addr, self._buf)
        finally:
            self._i2c.unlock()

        if self._buf[0] != 0:
            return self._buf[0]

'''
# ----------- INIT ------------------ #
i2c = busio.I2C(PIN_SCL, PIN_SDA)
kb = Keyboard(i2c)

# ------------ LOOP ----------------- #
while 1:
    key = kb.read_key()
    if key != None:
        print("Key pressed (hex): ", hex(key))
        print("Key pressed (char): ", chr(key))
'''