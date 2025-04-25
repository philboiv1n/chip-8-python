# -----------------------------------------------
# CHIP-8 Python Emulator
# By Phil Boivin - 2025
# Version 0.0.5
# -----------------------------------------------
import time
import curses


"""
MEMORY
This sets the total addressable memory (RAM) to 4 KiB.
Stack is a list of 16 possible 16-bit return addresses.
The stack pointer (sp) point to the next available free slot.
Sound and Delay timers are declared here.
"""
MEM_SIZE = 0x1000
mem = bytearray(MEM_SIZE)
stack = [0] * 16
sp = 0
sound_timer = 0
delay_timer = 0


"""
SCREEN : Creating a bytearray of 2KB (1 byte per pixel) for simplicity.
Another option was to create a bit-array of 256 bytes (8 pixels / byte)
"""
SCREEN_W = 64 # Width, col
SCREEN_H = 32 # Height, row
SCREEN_C = "█" # Character when pixel on (1)
SCREEN_E = " " # Empty when pixel off (0)
screen = bytearray(SCREEN_W * SCREEN_H)


"""
FONT
Store in mem 050-09F (by popular convention) 
"""
FONT_START = 0x050
font_data = bytes([
    0xF0, 0x90, 0x90, 0x90, 0xF0,  # 0
    0x20, 0x60, 0x20, 0x20, 0x70,  # 1
    0xF0, 0x10, 0xF0, 0x80, 0xF0,  # 2
    0xF0, 0x10, 0xF0, 0x10, 0xF0,  # 3
    0x90, 0x90, 0xF0, 0x10, 0x10,  # 4
    0xF0, 0x80, 0xF0, 0x10, 0xF0,  # 5
    0xF0, 0x80, 0xF0, 0x90, 0xF0,  # 6
    0xF0, 0x10, 0x20, 0x40, 0x40,  # 7
    0xF0, 0x90, 0xF0, 0x90, 0xF0,  # 8
    0xF0, 0x90, 0xF0, 0x10, 0xF0,  # 9
    0xF0, 0x90, 0xF0, 0x90, 0x90,  # A
    0xE0, 0x90, 0xE0, 0x90, 0xE0,  # B
    0xF0, 0x80, 0x80, 0x80, 0xF0,  # C
    0xE0, 0x90, 0x90, 0x90, 0xE0,  # D
    0xF0, 0x80, 0xF0, 0x80, 0xF0,  # E
    0xF0, 0x80, 0xF0, 0x80, 0x80,  # F
])
mem[FONT_START : FONT_START + len(font_data)] = font_data


"""
REGISTERS
V0 to VF : 16 x 8-bit registers (value from 0x00 to 0xFF.)
Register VF is used as a flag to hold information about the result of operations.
PC : Program counter (16-bit) : 0x200-0xFFF
I : Index register (16-bit)
"""
regs = { f'V{i:X}': 0 for i in range(16) }
regs['PC'] = 0x200
regs['I'] = 0


# -----------------------------------------------
# Main functions
# -----------------------------------------------

"""
FETCH
Fetch two bytes from memory to form a 16-bit opcode
1. Read the byte at address regs['PC'] from memory -> opcode.
2. Increment PC by 2 so it points to the next fetch.
3. Return the opcode for decoding.
"""
def fetch():
	high = mem[regs['PC']]
	low  = mem[regs['PC'] + 1]
	opcode = (high << 8) | low
	regs['PC'] = (regs['PC'] + 2) & 0xFFFF
	return opcode


"""
STEP
Fetch, Decode & Execute Loop
1 - Fetch the opcode
2 - Match the opcode to a function
3 - Execute
"""
def step() -> bool:
	op = fetch()
	return match_op(op)
	
    
def match_op(op) -> bool:
    """
    Match opcode with the appropriate function.
    Matching top 4 bits first (0 to F) then execute the assigned function.
    """
    
    # Halt
    if op == 0xFFFF:
        return False

    # extract each nibble
    n1 = (op & 0xF000) >> 12
    n2 = (op & 0x0F00) >> 8
    n3 = (op & 0x00F0) >> 4   
    n4 =  op & 0x000F
    nnn = op & 0x0FFF # last 3
    nn = op & 0x00FF  # last 2

    match n1:
        case 0:
            if op == 0x00E0:
                op_disp_clear()
        case 1:
            op_jump_to_addr(nnn)
        case 6:
            op_ld_vx_byte(n2, nn)
        case 7:
            op_add_vx_byte(n2, nn)
        case 10:
            op_ld_i_addr(nnn)
        case 13:
            op_drw_vx_vy_n(n2, n3, n4)
    return True  


def load_rom(path):
    """
    Load .ch8 binary (ROM)
    Make sure it fits in the 4K memory above 0x200
    Copy into memory and reset PC for the first instruction
    """
    with open(path, "rb") as f:
        program = f.read()
    if len(program) > MEM_SIZE - 0x200:
        raise RuntimeError("ROM too large for memory")
    mem[0x200 : 0x200 + len(program)] = program
    regs['PC'] = 0x200


# -----------------------------------------------
# opcode related functions
# -----------------------------------------------

def op_disp_clear(): 
    """
    00E0 Clear the display (CLS)
    """
    screen[:] = bytearray(len(screen))


def op_jump_to_addr(nnn):
    """
    1NNN Jump to address NNN.
    """
    regs['PC'] = nnn & 0xFFF


def op_ld_vx_byte(x, nn): 
    """
    6XNN LD Vx, byte
    Set Vx = NN.
    """
    reg = f"V{x:X}"
    regs[reg] = nn & 0xFF


def op_add_vx_byte(x, nn): 
    """
    7XNN ADD Vx, byte
    Set Vx = Vx + NN (no carry flag).
    """
    reg = f"V{x:X}"
    regs[reg] = (regs[reg] + nn) & 0xFF


def op_ld_i_addr(nnn):
    """
    ANNN - LD I, addr
    Set I = NNN.
    """
    regs['I'] = nnn


def op_drw_vx_vy_n(x,y,n):
    """
    DXYN - DRW Vx, Vy, nibble
    Draw sprite at (Vx, Vy) with height N
    Width of each line is 8 bit.
    set VF = 1 on any pixel collision, else 0.
    """
    x_coord = regs[f"V{x:X}"] & (SCREEN_W - 1)
    y_coord = regs[f"V{y:X}"] & (SCREEN_H - 1)
    i = regs['I']
    vf = 0

    for r in range(n):
        sprite = mem[i + r]
        py = ((y_coord + r) % SCREEN_H) * SCREEN_W
        for b in range(8):
            bit = (sprite >> (7 - b)) & 1
            px = (x_coord + b) % SCREEN_W
            idx = py + px
            old = screen[idx]
            if old & bit:
                vf = 1
            screen[idx] = old ^ bit

    regs['VF'] = vf


# -----------------------------------------------
# PROGRAM
# Load program into memory at 0x200
# -----------------------------------------------

if __name__ == "__main__":

    # ---------------
    # LOAD ROM
    # ---------------
    # load_rom("programs/IBM Logo.ch8")
    load_rom("programs/1-chip8-logo.ch8")
    # load_rom("programs/test01.ch8")



    def main(stdscr):
        curses.curs_set(0)       # hide cursor
        stdscr.nodelay(True)     # make getch() non-blocking
        while True:
            step()
            # get terminal size and clip to screen buffer
            height, width = stdscr.getmaxyx()
            rows_to_draw = min(SCREEN_H, height)
            cols_to_draw = min(SCREEN_W, width)
            stdscr.erase()
            for y in range(rows_to_draw):
                row_str = ''.join(
                    SCREEN_C if screen[y * SCREEN_W + x] else SCREEN_E
                    for x in range(cols_to_draw)
                )
                try:
                    stdscr.addnstr(y, 0, row_str, cols_to_draw)
                except curses.error:
                    pass
            stdscr.refresh()
            time.sleep(1/60)
    curses.wrapper(main)
        