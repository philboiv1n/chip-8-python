"""
CHIP-8 Python Emulator
By Phil Boivin - 2025
Version 0.0.1
"""


"""
MEMORY
This sets the total addressable memory to 4 KiB.
"""
MEM_SIZE = 0x1000
mem = bytearray(MEM_SIZE)


"""
SCREEN
"""
SCREEN_X = 64
SCREEN_Y = 32


"""
FONTS - for later
0xF0, 0x90, 0x90, 0x90, 0xF0, // 0
0x20, 0x60, 0x20, 0x20, 0x70, // 1
0xF0, 0x10, 0xF0, 0x80, 0xF0, // 2
0xF0, 0x10, 0xF0, 0x10, 0xF0, // 3
0x90, 0x90, 0xF0, 0x10, 0x10, // 4
0xF0, 0x80, 0xF0, 0x10, 0xF0, // 5
0xF0, 0x80, 0xF0, 0x90, 0xF0, // 6
0xF0, 0x10, 0x20, 0x40, 0x40, // 7
0xF0, 0x90, 0xF0, 0x90, 0xF0, // 8
0xF0, 0x90, 0xF0, 0x10, 0xF0, // 9
0xF0, 0x90, 0xF0, 0x90, 0x90, // A
0xE0, 0x90, 0xE0, 0x90, 0xE0, // B
0xF0, 0x80, 0x80, 0x80, 0xF0, // C
0xE0, 0x90, 0x90, 0x90, 0xE0, // D
0xF0, 0x80, 0xF0, 0x80, 0xF0, // E
0xF0, 0x80, 0xF0, 0x80, 0x80  // F
"""



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
3 - Execute
"""
def step() -> bool:
	op = fetch()
	return match_op(op)
	

def match_op(op) -> bool:
    """
    Match opcode with the appropriate function.
    Matching top 4 bits first (16 : 0 to F) then execute the assigned function.
    
    Starting with 
    00E0 (clear screen)
    1NNN (jump)
    6XNN (set register VX)
    7XNN (add value to register VX)
    ANNN (set index register I)
    DXYN (display/draw)
    """
    
    if op == 0xFFFF: # Halt
        return False

    match op & 0xF000:
         
        case 0x0000:
            if op == 0x00E0:
                op_disp_clear()
            elif op == 0x00EE:
                op_return_from_subroutine()
                
        case 0x1000:
            op_jump_to_addr(op)
            
        case 0x2000:
            pass
        case 0x3000:
            pass
        case 0x4000:
            pass
        case 0x5000:
            pass
        case 0x6000:
            pass
        case 0x7000:
            pass
        case 0x8000:
            pass
        case 0x9000:
            pass
        case 0xA000:
            pass
        case 0xB000:
            pass
        case 0xC000:
            pass
        case 0xD000:
            pass
        case 0xE000:
            pass
        case 0xF000:
            pass
         
    return True  


"""
opcode related functions
They will be added here while developping the emulator.
"""

def op_disp_clear(): #0x00E0
	print("Clear Screen") # Coming soon!


def op_return_from_subroutine(): #0x00EE
    """
    pop the topmost value off the stack—that very same return address that CALL put there—and reload it into the PC.
	"""
    print("Return from a subroutine (pop the address from the stack).") # Coming soon!


def op_jump_to_addr(op): #0x1NNN
    """
    Jump to address NNN.
    """
    addr = op & 0x0FFF
    regs['PC'] = addr
	


"""
PROGRAM (ROM)
Load a small test program into mem
"""
program = bytes([
0x00, 0xE0,     # Clear Screen
0x12, 0x04,     # Jump to address
0xFF, 0xFF      # Halt
])

# Load program at the start address (PC)
mem[regs['PC']:regs['PC'] + len(program)] = program



"""
RUN
"""
while step():
	pass



"""
OUTPUT / DEBUG
"""
print("PC =", regs['PC'])
print("I =", regs['I'])
