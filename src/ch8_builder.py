# -----------------------------------------------
# CHIP-8 .ch8 builder
# Simple utility to build a .ch8 binary file
# using the provided program code.
# By Phil Boivin - 2025
# Version 0.0.1
# -----------------------------------------------

OUTPUT_CH8 = "programs/test01.ch8"

program = bytes([

    0x00, 0xE0,     # CLS
    
    # Display 0
    0xA0, 0x50,     # Set I to 0x050
    0x6A, 0x03,     # Set VA (x)
    0x6B, 0xA6,     # Set VB (y)
    0xDA, 0xB5,     # DRW

    # Display 1
    0xA0, 0x55,     # Set I to 0x050
    0x6A, 0x08,     # Set VA (x)
    0xDA, 0xB5,     # DRW

    # Display 2
    0xA0, 0x5A,     # Set I to 0x050
    0x6A, 0x0E,     # Set VA (x)
    0xDA, 0xB5,     # DRW

    0xFF, 0xFF,     # HALT

])

# Create the file
with open(OUTPUT_CH8, "wb") as out:
    out.write(program)