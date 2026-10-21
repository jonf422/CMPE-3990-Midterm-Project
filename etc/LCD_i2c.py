# Requires CircuitPython_LCD-main library

import board
import busio

from lcd.lcd import LCD
from lcd.i2c_pcf8574_interface import I2CPCF8574Interface
from lcd.lcd import CursorMode

print("initialising i2c and looking for address")
i2c = busio.I2C(scl=board.B6, sda=board.B7)
i2c.try_lock()
address = i2c.scan()[0]
print(f"found address of i2c '{address}'")

i2c.unlock()
lcd = LCD(I2CPCF8574Interface(i2c, address), num_rows=2, num_cols=16)
print("debug: lcd initialised")

lcd.clear()
print("debug: clearing screen")

message = "Hello World!"
lcd.print(message)
print(f"debug: lcd printed '{message}'")
