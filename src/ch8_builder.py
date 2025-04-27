# -----------------------------------------------
# CHIP-8 .ch8 builder
# Simple utility to build a .ch8 binary file
# using the provided program code.
# By Phil Boivin - 2025
# Version 0.0.1
# -----------------------------------------------

OUTPUT_CH8 = "programs/test.ch8"

program = bytes([

   0xA2, 0x06,    # LD Point I to sprite
   0xD0, 0x11,    # DRW
   0x12, 0x04,    # JP - Loop here
   0x80           # Sprite data    

])

# Create the file
with open(OUTPUT_CH8, "wb") as out:
    out.write(program)