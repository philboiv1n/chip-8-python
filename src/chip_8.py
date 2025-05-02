# -----------------------------------------------
# CHIP-8 Python Emulator
# By Phil Boivin - 2025
# Version 0.0.9
# -----------------------------------------------
import random

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
STEP
Fetch, Decode & Execute Loop
1 - Fetch the opcode
2 - Match the opcode to a function
3 - Execute
"""
def step() -> bool:
    op = fetch()
    return match_op(op)


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

    # create vx & vy
    vx = f"V{n2:X}"
    vy = f"V{n3:X}"

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
            op_se_vx_byte(vx,nn)
        case 4:
            op_sne_vx_byte(vx,nn)
        case 5:
            op_se_vx_vy(vx,vy)
        case 6:
            op_ld_vx_byte(vx, nn)
        case 7:
            op_add_vx_byte(vx, nn)
        case 8:
            if n4 == 0:
                op_ld_vx_vy(vx,vy)
            elif n4 == 1:
                op_or_vx_vy(vx,vy)
            elif n4 == 2:
                op_and_vx_vy(vx,vy)
            elif n4 == 3:
                op_xor_vx_vy(vx,vy)
            elif n4 == 4:
                op_add_vx_vy(vx,vy)
            elif n4 == 5:
                op_sub_vx_vy(vx,vy)
            elif n4 == 6:
                op_shr_vx(vx)
            elif n4 == 7:
                op_subn_vx_vy(vx,vy)
            elif n4 == 14:
                op_shl_vx(vx)
        case 9:
            op_sne_vx_vy(vx,vy)
        case 10: # A
            op_ld_i_addr(nnn)
        case 11: # B
            op_jump_v0_addr(nnn)
        case 12: # C
            op_rnd_vx(vx,nn)
        case 13: # D
            op_drw_vx_vy_n(vx, vy, n4)
        case 14: # E
            if nn == 0x9E:
                op_skp_vx(vx)
            elif nn == 0xA1:
                op_sknp_vx(vx)
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
# Opcode Functions
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


def op_se_vx_byte(vx, nn): 
    """
    3xnn
    SE Vx, byte
    Skip the next instruction if Vx == nn.
    """
    if regs[vx] == nn:
        regs['PC'] = (regs['PC'] + 2) & 0xFFFF
  

def op_sne_vx_byte(vx, nn): 
    """
    4xnn
    SNE Vx, byte
    Skip the next instruction if Vx != nn.
    """
    if regs[vx] != nn:
        regs['PC'] = (regs['PC'] + 2) & 0xFFFF


def op_se_vx_vy(vx, vy): 
    """
    5xy0
    SE Vx, Vy
    Skip next instruction if Vx == Vy
    """
    if regs[vx] == regs[vy]:
        regs['PC'] = (regs['PC'] + 2) & 0xFFFF
  

def op_ld_vx_byte(vx, nn): 
    """
    6xnn 
    LD Vx, byte
    Set Vx = nn.
    """
    regs[vx] = nn & 0xFF


def op_add_vx_byte(vx, nn): 
    """
    7xnn ADD Vx, byte
    Set Vx = Vx + nn (no carry flag).
    """
    regs[vx] = (regs[vx] + nn) & 0xFF


def op_ld_vx_vy(vx,vy):
    """
    8xy0 - LD Vx, Vy - Set Vx = Vy. 
    Stores the value of register Vy in register Vx.
    """
    regs[vx] = regs[vy]


def op_or_vx_vy(vx,vy):
    """
    8xy1 - OR Vx, Vy - Set Vx = Vx OR Vy. 
    Performs a bitwise OR on the values of Vx and Vy, 
    then stores the result in Vx.
    """
    regs[vx] = regs[vx] | regs[vy]


def op_and_vx_vy(vx,vy):
    """
    8xy2 - AND Vx, Vy - Set Vx = Vx AND Vy. 
    Performs a bitwise AND on the values of Vx and Vy, 
    then stores the result in Vx.
    """
    regs[vx] = regs[vx] & regs[vy]


def op_xor_vx_vy(vx,vy):
    """
    8xy3 - XOR Vx, Vy - Set Vx = Vx XOR Vy. 
    Performs a bitwise XOR on the values of Vx and Vy, 
    then stores the result in Vx.
    """
    regs[vx] = regs[vx] ^ regs[vy]


def op_add_vx_vy(vx,vy):
    """
    8xy4 - ADD Vx, Vy - Set Vx = Vx + Vy, set VF = carry.
    The values of Vx and Vy are added together. 
    If the result is greater than 8 bits (i.e., > 255,) VF is set to 1, otherwise 0. 
    Only the lowest 8 bits of the result are kept, and stored in Vx.
    """
    result = regs[vx] + regs[vy]
    if result > 0xFF:
        regs['VF'] = 1
    else: 
        regs['VF'] = 0
    regs[vx] = result & 0xFF


def op_sub_vx_vy(vx,vy):
    """
    8xy5 - SUB Vx, Vy - Set Vx = Vx - Vy, set VF = NOT borrow.
    If Vx > Vy, then VF is set to 1, otherwise 0.
    Then Vy is subtracted from Vx, and the result stored in Vx.
    """
    if regs[vx] > regs[vy]:
        regs['VF'] = 1
    else:
        regs['VF'] = 0
    regs[vx] = (regs[vx] - regs[vy]) & 0xFF


def op_shr_vx(vx):
    """
    8xy6 - SHR Vx {, Vy}
    Store least-significant bit of Vx in VF, then Vx >>= 1.
    """
    regs['VF'] = regs[vx] & 0x1
    regs[vx] = (regs[vx] >> 1) & 0xFF


def op_subn_vx_vy(vx,vy):
    """
    8xy7 - SUBN Vx, Vy
    Set Vx = Vy - Vx; set VF = 0 on borrow, else 1.
    """
    if regs[vy] >= regs[vx]:
        regs['VF'] = 1
    else:
        regs['VF'] = 0
    regs[vx] = (regs[vy] - regs[vx]) & 0xFF


def op_shl_vx(vx):
    """
    8xyE - SHL Vx {, Vy}
    Store most-significant bit of Vx in VF, then Vx <<= 1.
    """
    regs['VF'] = (regs[vx] >> 7) & 1
    regs[vx] = (regs[vx] << 1) & 0xFF


def op_sne_vx_vy(vx,vy):
    """
    9xy0 - SNE Vx, Vy - Skip next instruction if Vx != Vy. 
    The values of Vx and Vy are compared, and if they are not equal, 
    the program counter is increased by 2
    """
    if regs[vx] != regs[vy]:
        regs['PC'] = (regs['PC'] + 2) & 0xFFFF


def op_ld_i_addr(nnn):
    """
    Annn - LD I, addr
    Set I to nnn.
    """
    regs['I'] = nnn


def op_jump_v0_addr(nnn):
    """
    Bnnn - JP V0, addr - Jump to location nnn + V0. 
    The program counter is set to nnn + the value of V0.
    """
    result = (nnn + regs['V0']) & 0xFFF
    regs['PC'] = result


def op_rnd_vx(vx,nn):
    """
    Cxkk - RND Vx, byte - Set Vx = random byte AND kk. 
    Generates a random number from 0 to 255, which is then ANDed with the value kk.
    """
    rnd = random.getrandbits(8) # 0-255 integer
    regs[vx] = rnd & nn


def op_drw_vx_vy_n(vx,vy,n):
    """
    Dxyn - DRW Vx, Vy, nibble
    Draw sprite at (Vx, Vy) with height N
    Width of each line is 8 bit.
    set VF = 1 on any pixel collision, else 0.
    """
    x_coord = regs[vx] & (SCREEN_W - 1)
    y_coord = regs[vy] & (SCREEN_H - 1)
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


def op_skp_vx(vx):
    """
    Ex9E - SKP Vx 
    Skip next instruction if key with the value of Vx is pressed. 
    """
    key = regs[vx]
    if keypad[key]:
        regs['PC'] = (regs['PC'] + 2) & 0xFFFF


def op_sknp_vx(vx):
    """
    ExA1 - SKNP Vx 
    Skip next instruction if key with the value of Vx is not pressed. 
    """
    key = regs[vx]
    if not keypad[key]:
        regs['PC'] = (regs['PC'] + 2) & 0xFFFF