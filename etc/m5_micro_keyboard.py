import busio

class Keyboard:
    KB_ADDR = 0x5f

    ENTER = 0x0D
    BACKSPACE = 0x08
    TAB = 0x09
    ESC = 0x1B
    LEFT = 0xB4
    UP = 0xB5
    DOWN = 0xB6
    RIGHT = 0xB7

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
        return self._buf[0] or None
