// pinouts
// LCD =======================
// VCC = 5V
// GND = GND
// SDA = A5
// SCL = A4
// KEYBOARD ==================
// VCC = 5V
// GND = GND
// SDA = A5
// SCL = A4
// PUT KEYBOARD AND LCD ON SAME BUS 
// FR =====================
// VCC = 3V
// GND = GND
// CE = 8
// CSN = 10 
// MOSI = 11
// MISO = 12
// SCK = 13
// IRQ = NOT USED
// GONNA NEED A 9V BATTERY, PULLS TO MUCH WITH JUST USB CONNECTION



// ALL LIBS NEEDED
#include <Arduino.h>
#include <SPI.h>
#include <Wire.h>
#include <RH_NRF24.h>
#include <LiquidCrystal_I2C.h>

// ---------------- Config ---------------- //
constexpr uint8_t LCD_ADDR = 0x27;
constexpr uint8_t KB_ADDR  = 0x5F;
constexpr uint8_t LCD_COLS = 16;
constexpr uint8_t LCD_ROWS = 2;
constexpr uint8_t MAX_MSG  = RH_NRF24_MAX_MESSAGE_LEN;  // 28 bytes

// CardKB special key codes
constexpr uint8_t KEY_BACKSPACE = 0x08;
constexpr uint8_t KEY_TAB       = 0x09;
constexpr uint8_t KEY_ENTER     = 0x0D;
constexpr uint8_t KEY_ESC       = 0x1B;
constexpr uint8_t KEY_LEFT      = 0xB4;
constexpr uint8_t KEY_UP        = 0xB5;
constexpr uint8_t KEY_DOWN      = 0xB6;
constexpr uint8_t KEY_RIGHT     = 0xB7;

// ---------------- Hardware ---------------- //
RH_NRF24 nrf24(8, 10);                       // CE = 8, CSN = 10
LiquidCrystal_I2C lcd(LCD_ADDR, LCD_COLS, LCD_ROWS);

// ---------------- State ---------------- //
enum State { SENDING, RECEIVING };

State state = SENDING;
String sendMsg = "";
String recvMsg = "";
String status  = "";
uint8_t cursorPos = 0;
bool newMsgFlag = false;
bool dirty = true;

// ---------------- Helpers ---------------- //
bool devicePresent(uint8_t addr) {
  Wire.beginTransmission(addr);
  return Wire.endTransmission() == 0;
}

void halt(const char *msg) {
  Serial.println(msg);
  lcd.clear();
  lcd.setCursor(0, 0);
  lcd.print(msg);
  while (true) delay(1000);
}

// Returns 0 if no key pressed
uint8_t readKey() {
  Wire.requestFrom(KB_ADDR, (uint8_t)1);
  if (Wire.available()) return Wire.read();
  return 0;
}

// ---------------- State machine ---------------- //
void setStatus() {
  if (state == SENDING) {
    status = "INBOX: " + String(newMsgFlag ? 1 : 0);
  } else {
    status = "TAB TO EXIT";
  }
}

void changeState(State next) {
  state = next;
  lcd.setCursor(0, 0);

  if (state == SENDING) {
    newMsgFlag = false;
    lcd.cursor();
  } else {
    lcd.noCursor();
  }
  dirty = true;
}

// ---------------- Radio ---------------- //
// Returns true if the packet was sent
bool radioSend(const String &msg) {
  Serial.print("Sent: ");
  Serial.println(msg);

  if (!nrf24.send((const uint8_t *)msg.c_str(), msg.length())) {
    return false;
  }
  nrf24.waitPacketSent();
  return true;
}

void radioReceive() {
  if (!nrf24.available()) return;

  uint8_t buf[MAX_MSG + 1];
  uint8_t len = MAX_MSG;

  if (nrf24.recv(buf, &len)) {
    buf[len] = '\0';
    recvMsg = String((char *)buf);

    Serial.print("Received: ");
    Serial.println(recvMsg);

    if (state == SENDING) newMsgFlag = true;
    dirty = true;
  } else {
    Serial.println("Receive failed");
  }
}

// ---------------- LCD ---------------- //
void redraw() {
  setStatus();
  lcd.clear();

  lcd.setCursor(0, 0);
  if (state == SENDING) lcd.print(sendMsg.substring(0, LCD_COLS));
  else                  lcd.print(recvMsg.substring(0, LCD_COLS));

  lcd.setCursor(LCD_COLS - status.length(), 1);
  lcd.print(status);

  if (state == SENDING) {
    uint8_t col = (cursorPos < LCD_COLS - 1) ? cursorPos : LCD_COLS - 1;
    lcd.setCursor(col, 0);
  }
}

// ---------------- Key handlers ---------------- //
void tabKey() {
  changeState(state == SENDING ? RECEIVING : SENDING);
}

void sendEnter() {
  if (sendMsg.length() > 0) {
    bool ok = radioSend(sendMsg);
    sendMsg = "";
    cursorPos = 0;
    lcd.setCursor(0, 1);
    lcd.print(ok ? "SENT     " : "SEND FAIL");
    delay(500);
  } else {
    changeState(RECEIVING);
  }
}

void sendBackspace() {
  if (cursorPos > 0) {
    sendMsg.remove(cursorPos - 1, 1);
    cursorPos--;
  }
}

void sendEscape() {
  sendMsg = "";
  cursorPos = 0;
}

void sendLeft()  { if (cursorPos > 0) cursorPos--; }
void sendRight() { if (cursorPos < sendMsg.length()) cursorPos++; }

// Returns true if the key was a special key handled in the current state
bool handleSpecial(uint8_t key) {
  if (state == SENDING) {
    switch (key) {
      case KEY_ENTER:     sendEnter();     return true;
      case KEY_BACKSPACE: sendBackspace(); return true;
      case KEY_TAB:       tabKey();        return true;
      case KEY_ESC:       sendEscape();    return true;
      case KEY_UP:                         return true;  // unused
      case KEY_DOWN:                       return true;  // unused
      case KEY_LEFT:      sendLeft();      return true;
      case KEY_RIGHT:     sendRight();     return true;
    }
  } else {  // RECEIVING
    if (key == KEY_TAB) { tabKey(); return true; }
  }
  return false;
}

// ---------------- Setup / Loop ---------------- //
void setup() {
  Serial.begin(9600);
  Wire.begin();

  lcd.init();
  lcd.backlight();
  lcd.setCursor(0, 0);
  lcd.print("Loading...");

  if (!devicePresent(KB_ADDR))  halt("KB not found");
  if (!devicePresent(LCD_ADDR)) halt("LCD not found");

  if (!nrf24.init()) halt("Radio init fail");
  if (!nrf24.setChannel(2)) Serial.println("setChannel failed");
  if (!nrf24.setRF(RH_NRF24::DataRate2Mbps, RH_NRF24::TransmitPower0dBm)) {
    Serial.println("setRF failed");
  }

  Serial.println("System Ready.");
  lcd.clear();
  lcd.cursor();
}

void loop() {
  radioReceive();

  uint8_t key = readKey();
  if (key != 0) {
    dirty = true;

    if (!handleSpecial(key)) {
      if (state == SENDING && key >= 32 && key <= 126 && sendMsg.length() < MAX_MSG) {
        sendMsg = sendMsg.substring(0, cursorPos) + (char)key + sendMsg.substring(cursorPos);
        cursorPos++;
      }
    }
  }

  if (dirty) {
    redraw();
    dirty = false;
  }

  delay(50);
}