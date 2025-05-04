# BIT-CCTV Hardware Documentation Summary

## 1. BIT-CCTV Pan Tilt Control Commands with Pelco D Protocol

This document provides a comprehensive explanation of the Pelco D protocol implementation used for controlling BIT-CCTV pan-tilt equipment.

### Command Structure
- **Basic Format**: `0xFF add cmd1 cmd2 data1 data2 sum`
  - `0xFF` - Synchronization character
  - `add` - Device address (1-255)
  - `cmd1`, `cmd2` - Command bytes
  - `data1`, `data2` - Data bytes
  - `sum` - Checksum (sum of all bytes except 0xFF, taking lower 8 bits)

### Command Categories
1. **Basic Control Commands**
   - Up: `FF add 00 08 00 data2 sum` (data2 = speed level 0x00-0x3F)
   - Down: `FF add 00 10 00 data2 sum` (data2 = speed level 0x00-0x3F)
   - Left: `FF add 00 04 data1 00 sum` (data1 = speed level 0x00-0x3F)
   - Right: `FF add 00 02 data1 00 sum` (data1 = speed level 0x00-0x3F)
   - Stop: `FF add 00 00 00 00 sum`
   - Combined movements (e.g., Left-Up): `FF add 00 0C data1 data2 sum`

2. **Extended Commands**
   - Set Preset: `FF add 00 03 00 data2 sum`
   - Call Preset: `FF add 00 07 00 data2 sum`
   - Delete Preset: `FF add 00 05 00 data2 sum`
   - Auxiliary Switch control (On/Off): `FF add 00 09/0B 00 data2 sum`

3. **Remote Reset**
   - Reset Pan Tilt: `FF add 00 0F 00 00 sum`

4. **Position Query Commands**
   - Pan Position Query: `FF 01 00 51 00 00 52` (for address 1)
   - Tilt Position Query: `FF 01 00 53 00 00 54` (for address 1)

### Position Response Format
1. **Pan Position Response**
   - Format: `FF 01 00 59 PMSB PLSB SUM`
   - Position calculation:
     - Convert PMSB, PLSB hex to decimal
     - Calculate Pdata = PMSB*256 + PLSB
     - Angle = Pdata ÷ 100 (in degrees)

2. **Tilt Position Response**
   - Format: `FF 01 00 5B TMSB TLSB SUM`
   - Position calculation:
     - Convert TMSB, TLSB hex to decimal
     - Calculate Tdata1 = TMSB*256 + TLSB
     - If Tdata1 > 18000, then Tdata2 = 36000 - Tdata1
     - If Tdata1 < 18000, then Tdata2 = -Tdata1
     - Angle = Tdata2 ÷ 100 (in degrees)

### Absolute Position Control
1. **Pan Absolute Control**
   - Format: `FF ADD 00 4B DATA1 DATA2 SUM`
   - Position calculation: (DATA1<<8) + DATA2 = angle*100

2. **Tilt Absolute Control**
   - Format: `FF ADD 00 4D DATA1 DATA2 SUM`
   - For negative angles: (DATA1<<8) + DATA2 = |angle|*100
   - For positive angles: (DATA1<<8) + DATA2 = 36000 - angle*100

### Detailed Examples
- Multiple examples showing command execution and response interpretation
- Step-by-step calculations for converting position data to angles

## 2. BIT-CCTV Pan Tilt Control Commands 2022

This document provides a tabular reference of all Pelco D protocol commands supported by BIT-CCTV equipment.

### Command List (36 commands total)
1. **Movement Controls**
   - Pan Right: `FF add 00 02 data1 00 sum`
   - Pan Left: `FF add 00 04 data1 00 sum`
   - Up Control: `FF add 00 08 00 data2 sum`
   - Down Control: `FF add 00 10 00 data2 sum`
   - Stop: `FF add 00 00 00 00 sum`

2. **Position Queries**
   - Pan Angle Query: `FF 01 00 51 00 00 52`
   - Tilt Angle Query: `FF 01 00 53 00 00 54`

3. **Zero Point Settings**
   - Pan 0 Point: `FF 01 00 03 00 67 6B`
   - Tilt 0 Point: `FF 01 00 03 00 68 6C`

4. **Preset Management**
   - Set Preset: `FF add 00 03 00 data2 sum`
   - Call Preset: `FF add 00 07 00 data2 sum`
   - Delete Preset: `FF add 00 05 00 data2 sum`

5. **Cruise Controls**
   - Start Cruising: `FF 01 00 07 00 62 6A`
   - Cruising Dwell Time: Multiple commands sequence
   - Cruising Speed Set: Multiple commands sequence

6. **Scan Controls**
   - Set Line Scan Start: `FF 01 00 03 00 5C 60`
   - Set Line Scan End: `FF 01 00 03 00 5D 61`
   - Run Line Scan: `FF 01 00 07 00 63 6B`
   - Set Line Scan Speed: Multiple commands sequence

7. **Position Controls**
   - Pan Angle Positioning: `FF ADD 00 4B DATA1 DATA2 SUM`
   - Tilt Angle Positioning: `FF ADD 00 4D DATA1 DATA2 SUM`

8. **Guard Location Controls**
   - Enable Guard Location: `FF 01 00 03 00 5E 62`
   - Disable Guard Location: `FF 01 00 07 00 5E 66`
   - Set Guard Location Time: Multiple commands sequence

9. **Auxiliary Controls**
   - Open Aux: `FF add 00 09 00 data2 sum`
   - Shut Aux: `FF add 00 0B 00 data2 sum`

10. **Optical Controls**
    - Zoom +: `FF 01 00 20 00 00 21`
    - Zoom -: `FF 01 00 40 00 00 41`
    - Focus Far: `FF 01 00 80 00 00 81`
    - Focus Near: `FF 01 01 00 00 00 02`
    - Iris Open: `FF 01 02 00 00 00 03`
    - Iris Shut: `FF 01 04 00 00 00 05`

11. **Feedback Controls**
    - Open Real-time Angle Feedback: `FF 01 00 03 00 69 6D`
    - Shut Real-time Angle Feedback: `FF 01 00 07 00 69 71`

12. **System Controls**
    - Remote Restart: `FF 01 00 03 00 FE 02`
    - Factory Default: Multiple commands sequence

## 3. BIT-PT850 50kg Heavy Duty Pan Tilt Unit Positioner

This document provides specifications and features for the BIT-PT850 pan-tilt mount.

### Key Features
- Maximum load capacity: 50kg (110.23lb)
- Pan angle: 0-360° continuous
- Tilt angle: -45° to +45°
- Pan speed: 0.01°/s to 30°/s
- Tilt speed: 0.01°/s to 15°/s
- Preset accuracy: ±0.1°
- Self-lock with memory after power failure
- Strong wind resistance
- RS485/RS422 control via Pelco D/P
- Optional Ethernet P/T control
- Support for absolute position and position response
- Anti-corrosion surface treatment
- IP66 rated for dust and water protection

### Technical Specifications
1. **Load Specifications**
   - Max load: 50kg (110.23lb), top load
   - Load type: Indoor/outdoor, top load

2. **Movement Specifications**
   - Programmable presets: 200
   - Cruising tracks: 8
   - Scan modes: 8
   - Support for coordinate feedback (query/real-time)
   - Adaptive PTZ speed to zoom
   - Guard location support

3. **Communication**
   - Protocol: Pelco P/D
   - Baud rate: 2400/4800/9600/19200 bps
   - Interface: RS485 (Optional RS422) or Ethernet
   - Transmission: Worm gear

4. **Wiring/Interface**
   - Pan Tilt Base: 100M Ethernet with RJ45, RS485 P/T control input, 24V AC/DC Input, GND
   - Pan Tilt Top: 100M Ethernet with RJ45, RS485 P/T control input, 12V DC Output, 24V AC/DC Output, GND

5. **Power**
   - Operating voltage: AC24V±25%, 50/60Hz or DC24V±10%
   - Power consumption: ≤100W
   - Surge protection: 4000V for power lines

6. **Environmental**
   - Working temperature: -40°C to +60°C (-40°F to 140°F)
   - Working humidity: 90±5% RH
   - Storage temperature: -40°C to +70°C (-40°F to 158°F)

7. **Physical**
   - Material: Aluminum alloy
   - Weight: 23kg (50.7lb)
   - Dimensions: 224×341×403mm (8.81×12.42×15.86in)

## 4. BIT-K7203 PTZ Keyboard Controller

This document details the specifications and features of the BIT-K7203 PTZ keyboard controller.

### Key Features
- Mini keyboard with controllable speed for Pan/Tilt and Zoom
- Built-in Pelco P/D protocol
- Selectable baud rate
- Support for 4 keyboard cascade connections
- Max controllable devices: 128
- OSD menu with display of address/protocol/baud rate
- Universal 3D joystick

### Technical Specifications
1. **Communication**
   - Interfaces: RS232, RS485
   - Max transmitting distance: 1200m
   - Baud rate: 2400/4800/9600/19200 bps
   - Protocol: PELCO P/D

2. **Power**
   - Supply: DC 9V-12V ±10%
   - Current: 350mA
   - Power consumption: 4.2W
   - Standby consumption: 1W

3. **Environmental**
   - Temperature: -20°C to +50°C
   - Humidity: 0-95% (non-condensation)

4. **Physical**
   - Dimensions: 181(L) × 219(W) × 97(H) mm
   - Weight: 1.3kg

## 5. Heavy Duty Tripod 9116Y

This document provides specifications for the 9116Y heavy-duty tripod designed for pan-tilt units.

### Key Features
- Maximum load capacity: 110kg
- Aluminum alloy construction
- Height adjustment from 760mm to 1480mm
- Maximum transport length: 950mm
- Weight: 11.5kg
- Feet brackets for ground mounting
- Custom mounting plate options

## 6. Description of Pan Tilt Wiring and Control

This document explains the wiring connections and control methods for the pan-tilt hardware.

### Wiring Diagram
1. **Pan-Tilt Top Connections**
   - Pass-through Ethernet cable
   - RS485 P&T Control Input
   - Grounding
   - 24VDC Output
   - 12VDC Output

2. **Pan-Tilt Base Connections**
   - Pass-through Ethernet cable
   - RS485 P&T Control Input
   - Grounding
   - 24VDC P&T Input

### Control Methods
1. **PTZ Keyboard Controller Connection**
   - Direct RS485 connection between keyboard and pan-tilt base
   - RS485A and RS485B wiring details

2. **Software Control via Laptop**
   - RS485 to USB converter usage
   - Connection to control software on PC
   - Wiring diagram showing signal routing

## 7. K7203 Network Keyboard Manual V2.0

This comprehensive user manual details the operation and configuration of the K7203 network keyboard controller.

### Contents Overview
1. **Introduction**
   - Features and specifications
   - Connection interfaces

2. **Network Keyboard Settings**
   - Connection methods
   - Menu settings
   - IP configuration

3. **Non-Network Keyboard Connection**
   - Interface instructions
   - RS485/RS422 connections
   - Direct dome connection
   - System integration

4. **Operation Manual**
   - Power-up sequence
   - LCD interface
   - Joystick control
   - Camera selection
   - Lens control
   - Function operations (presets, patterns, scan, tour)

5. **Menu Control**
   - Parameter settings
   - Keyboard ID configuration
   - Baud rate selection
   - Joystick calibration
   - Multi-keyboard configuration
   - Camera settings (presets, scan, pattern, cruise)
   - Protocol selection

6. **Appendix**
   - Shortcut operation reference
   - RS485 bus knowledge
   - Menu navigation map

7. **Maintenance**
   - Warranty information
   - Service terms

### Key Operational Instructions
- Keyboard shortcuts for common functions
- Menu navigation paths
- Error handling procedures
- Multi-keyboard cascade configuration
- RS485 bus connection guidelines and troubleshooting
