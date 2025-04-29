# -----------------------------------------------
# CHIP-8 Python Emulator
# By Phil Boivin - 2025
# Version 0.0.7
# -----------------------------------------------


"""
MEMORY
This sets the total addressable memory (RAM) to 4 KiB.
Stack is a list of 16 possible 16-bit return addresses.
The stack pointer (sp) point to the next available free slot.
Sound (st) and Delay (dt) timers are declared here.
"""
MEM_SIZE = 0x1000
mem = bytearray(MEM_SIZE)
stack = [0] * 16
sp = 0  # Stack pointer
st = 0  # Sound Timer
dt = 0  # Delay Timer



"""
SCREEN : Creating a bytearray of 2KB (1 byte per pixel) for simplicity.
Another option was to create a bit-array of 256 bytes (8 pixels / byte)
"""
SCREEN_W = 64 # Width, col
SCREEN_H = 32 # Height, row
screen = bytearray(SCREEN_W * SCREEN_H)



"""
KEYPAD
Keypad state for 16 keys (False=up, True=down)
"""
keypad = [False] * 16



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
            elif op == 0x00EE:
                op_ret_from_subroutine()
        case 1:
            op_jump_to_addr(nnn)
        case 2:
            op_call_addr(nnn)
        case 3:
            op_se_vx_byte(n2,nn)
        case 4:
            op_sne_vx_byte(n2,nn)
        case 5:
            op_se_vx_vy(n2,n3)
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
    00E0 
    Clear the display (CLS)
    """
    screen[:] = bytearray(len(screen))


def op_ret_from_subroutine():
    """
    00EE
    Return from a subroutine (pop the address from the stack).
    Subtracts 1 from the stack pointer, then set the PC 
    to the address at the top of the stack. 
    """
    global sp
    if sp == 0:
        raise RuntimeError("Stack underflow on RET")
    sp -= 1
    regs['PC'] = stack[sp]  


def op_jump_to_addr(nnn):
    """
    1nnn 
    Jump to address nnn.
    """
    regs['PC'] = nnn & 0xFFF


def op_call_addr(nnn):
    """
    2nnn 
    Call subroutine at nnn.
    Puts the current PC on the top of the stack,
    increments the stack pointer,
    Set PC to nnn.
    """
    global sp
    if sp >= len(stack):
        raise RuntimeError("Stack overflow on CALL")
    stack[sp] = regs['PC']
    sp += 1
    regs['PC'] = nnn & 0xFFF


def op_se_vx_byte(x, nn): 
    """
    3xnn
    SE Vx, byte
    Skip the next instruction if Vx == nn.
    """
    reg = f"V{x:X}"
    if regs[reg] == nn:
        regs['PC'] = (regs['PC'] + 2) & 0xFFFF
  

def op_sne_vx_byte(x, nn): 
    """
    4xnn
    SNE Vx, byte
    Skip the next instruction if Vx != nn.
    """
    reg = f"V{x:X}"
    if regs[reg] != nn:
        regs['PC'] = (regs['PC'] + 2) & 0xFFFF


def op_se_vx_vy(x, y): 
    """
    5xy0
    SE Vx, Vy
    Skip next instruction if Vx == Vy
    """
    vx = f"V{x:X}"
    vy = f"V{y:X}"
    if regs[vx] == regs[vy]:
        regs['PC'] = (regs['PC'] + 2) & 0xFFFF
  

def op_ld_vx_byte(x, nn): 
    """
    6xnn 
    LD Vx, byte
    Set Vx = nn.
    """
    reg = f"V{x:X}"
    regs[reg] = nn & 0xFF


def op_add_vx_byte(x, nn): 
    """
    7xnn ADD Vx, byte
    Set Vx = Vx + nn (no carry flag).
    """
    reg = f"V{x:X}"
    regs[reg] = (regs[reg] + nn) & 0xFF


def op_ld_i_addr(nnn):
    """
    Annn - LD I, addr
    Set I to nnn.
    """
    regs['I'] = nnn


def op_drw_vx_vy_n(x,y,n):
    """
    Dxyn - DRW Vx, Vy, nibble
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