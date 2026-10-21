# CMPE 3990 Pager

## Description
A two-way text pager built on an STM32F411 "Black Pill" running CircuitPython. Messages are typed on an M5Stack CardKB keyboard, shown on a 16x2 I2C LCD, and sent between two pagers over nRF24L01 2.4 GHz radios.

## Features
- Type and edit messages with cursor movement, backspace, and clear
- Send messages wirelessly to a second pager
- Inbox counter for messages received while typing
- Two-mode state machine: Sending and Receiving