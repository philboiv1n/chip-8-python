# -----------------------------------------------
# CHIP-8 Python Emulator
# By Phil Boivin - 2025
# Version 0.0.2
# -----------------------------------------------


"""
MEMORY : This sets the total addressable memory to 4 KiB.
"""
MEM_SIZE = 0x1000
mem = bytearray(MEM_SIZE)


"""
SCREEN : Creating a bytearray of 2KB (1 byte per pixel) for simplicity.
Another option was to create a bit-array of 256 bytes (8 pixels / byte)
"""
SCREEN_X = 64
SCREEN_Y = 32
SCREEN_C = "●" # Character
SCREEN_E = "·" # Empty
screen = bytearray(SCREEN_X * SCREEN_Y)


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
Decode & Execute Loop
1 - Fetch the opcode
2 - Match the opcode to a function
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


def print_screen():
    """
    Print the screen buffer
    """
    for y in range(SCREEN_Y):
        row = screen[y * SCREEN_X:(y + 1) * SCREEN_X]
        print(''.join(SCREEN_C if pixel else SCREEN_E for pixel in row))


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
    ANNN – LD I, addr
    Set I = NNN.
    """
    regs['I'] = nnn


def op_drw_vx_vy_n(x,y,n):
    """
    DXYN – DRW Vx, Vy, nibble
    Draw sprite at (Vx, Vy) with height N
    Width of each line is 8 bit.
    set VF = 1 on any pixel collision, else 0.
    """
    x_coord = regs[f"V{x:X}"] & (SCREEN_X - 1)
    y_coord = regs[f"V{y:X}"] & (SCREEN_Y - 1)
    i = regs['I']
    vf = 0

    for r in range(n):
        sprite = mem[i + r]
        py = ((y_coord + r) % SCREEN_Y) * SCREEN_X
        for b in range(8):
            bit = (sprite >> (7 - b)) & 1
            px = (x_coord + b) % SCREEN_X
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

    # 0 sprite
    mem[0x300] = 0xF0
    mem[0x301] = 0x90
    mem[0x302] = 0x90
    mem[0x303] = 0x90
    mem[0x304] = 0xF0

    # Test program
    program = bytes([
        0x00, 0xE0,     # CLS
        
        # Display 0
        0xA3, 0x00,     # Set I to 0x300
        0x6A, 0x03,     # Set VA (x)
        0x6B, 0x03,     # Set VB (y)
        0xDA, 0xBA,     # DRW

        # Display another 0 overlapping
        0x6A, 0x05,     # Set VA (x)
        0x6B, 0x05,     # Set VB (y)
        0xDA, 0xBA,     # DRW

        0xFF, 0xFF,     # HALT
    ])

    # Load program at the start address (PC)
    mem[regs['PC']:regs['PC'] + len(program)] = program

    # RUN
    while step():
        pass


    # OUTPUT / DEBUG
    print_screen()
    print("PC =", regs['PC'])
    print("I =", regs['I'])
    print("VA =", regs['VA'])
    print("VB =", regs['VB'])

