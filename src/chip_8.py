# -----------------------------------------------
# CHIP-8 Python Emulator
# By Phil Boivin - 2025
# Version 0.0.10
# -----------------------------------------------
import random
import time

class Chip8:
    def __init__(self):
        # MEMORY
        self.MEM_SIZE = 0x1000        # 4 Kb
        self.mem      = bytearray(self.MEM_SIZE)
        # STACK
        self.stack    = [0] * 16
        self.sp       = 0
        # TIMERS
        self.dt       = 0
        self.st       = 0
        # PROGRAM COUNTER & INDEX
        self.pc       = 0x200
        self.I        = 0
        # REGISTERS V0..VF
        self.regs     = { f'V{i:X}': 0 for i in range(16) }
        # DISPLAY
        self.SCREEN_W = 64
        self.SCREEN_H = 32
        self.screen   = bytearray(self.SCREEN_W * self.SCREEN_H)
        # KEYPAD
        self.keypad   = [False] * 16
        # FONT
        self.FONT_START = 0x050
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
        self.mem[self.FONT_START : self.FONT_START + len(font_data)] = font_data
        self.random = random
        self.time = time


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
    def step(self) -> bool:
        op = self.fetch()
        return self.match_op(op)


    """
    FETCH
    Fetch two bytes from memory to form a 16-bit opcode
    1. Read the byte at address regs['PC'] from memory -> opcode.
    2. Increment PC by 2 so it points to the next fetch.
    3. Return the opcode for decoding.
    """
    def fetch(self) -> int:
        high = self.mem[self.pc]
        low  = self.mem[self.pc + 1]
        opcode = (high << 8) | low
        self.pc = (self.pc + 2) & 0xFFFF
        return opcode

        
    def match_op(self, op) -> bool:
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
                    self.op_disp_clear()
                elif op == 0x00EE:
                    self.op_ret_from_subroutine()
            case 1:
                self.op_jump_to_addr(nnn)
            case 2:
                self.op_call_addr(nnn)
            case 3:
                self.op_se_vx_byte(vx,nn)
            case 4:
                self.op_sne_vx_byte(vx,nn)
            case 5:
                self.op_se_vx_vy(vx,vy)
            case 6:
                self.op_ld_vx_byte(vx, nn)
            case 7:
                self.op_add_vx_byte(vx, nn)
            case 8:
                if n4 == 0:
                    self.op_ld_vx_vy(vx,vy)
                elif n4 == 1:
                    self.op_or_vx_vy(vx,vy)
                elif n4 == 2:
                    self.op_and_vx_vy(vx,vy)
                elif n4 == 3:
                    self.op_xor_vx_vy(vx,vy)
                elif n4 == 4:
                    self.op_add_vx_vy(vx,vy)
                elif n4 == 5:
                    self.op_sub_vx_vy(vx,vy)
                elif n4 == 6:
                    self.op_shr_vx(vx)
                elif n4 == 7:
                    self.op_subn_vx_vy(vx,vy)
                elif n4 == 14:
                    self.op_shl_vx(vx)
            case 9:
                self.op_sne_vx_vy(vx,vy)
            case 10: # A
                self.op_ld_i_addr(nnn)
            case 11: # B
                self.op_jump_v0_addr(nnn)
            case 12: # C
                self.op_rnd_vx(vx,nn)
            case 13: # D
                self.op_drw_vx_vy_n(vx, vy, n4)
            case 14: # E
                if nn == 0x9E:
                    self.op_skp_vx(vx)
                elif nn == 0xA1:
                    self.op_sknp_vx(vx)
            case 15: # F
                if nn == 0x07:
                    self.op_ld_vx_dt(vx)
                elif nn == 0x0A:
                    self.op_ld_vx_k(vx)
                elif nn == 0x15:
                    self.op_ld_dt_vx(vx)
                elif nn == 0x18:
                    self.op_ld_st_vx(vx)
                elif nn == 0x1E:
                    self.op_add_i_vx(vx)
                elif nn == 0x29:
                    self.op_ld_f_vx(vx)
                elif nn == 0x33:
                    self.op_ld_b_vx(vx)
                elif nn == 0x55:
                    self.op_ld_i_vx(n2)
                elif nn == 0x65:
                    self.op_ld_vx_i(n2)
        return True  


    def load_rom(self, path):
        """
        Load .ch8 binary (ROM)
        Make sure it fits in the 4K memory above 0x200
        Copy into memory and reset PC for the first instruction
        """
        with open(path, "rb") as f:
            program = f.read()
        if len(program) > self.MEM_SIZE - 0x200:
            raise RuntimeError("ROM too large for memory")
        self.mem[0x200 : 0x200 + len(program)] = program
        self.pc = 0x200


    # -----------------------------------------------
    # Opcode Functions
    # -----------------------------------------------

    def op_disp_clear(self): 
        """
        00E0 
        Clear the display (CLS)
        """
        self.screen[:] = bytearray(len(self.screen))


    def op_ret_from_subroutine(self):
        """
        00EE
        Return from a subroutine (pop the address from the stack).
        Subtracts 1 from the stack pointer, then set the PC 
        to the address at the top of the stack. 
        """
        if self.sp == 0:
            raise RuntimeError("Stack underflow on RET")
        self.sp -= 1
        self.pc = self.stack[self.sp]  


    def op_jump_to_addr(self, nnn):
        """
        1nnn 
        Jump to address nnn.
        """
        self.pc = nnn & 0xFFF


    def op_call_addr(self, nnn):
        """
        2nnn 
        Call subroutine at nnn.
        Puts the current PC on the top of the stack,
        increments the stack pointer,
        Set PC to nnn.
        """
        if self.sp >= len(self.stack):
            raise RuntimeError("Stack overflow on CALL")
        self.stack[self.sp] = self.pc
        self.sp += 1
        self.pc = nnn & 0xFFF


    def op_se_vx_byte(self, vx, nn): 
        """
        3xnn
        SE Vx, byte
        Skip the next instruction if Vx == nn.
        """
        if self.regs[vx] == nn:
            self.pc = (self.pc + 2) & 0xFFFF
  

    def op_sne_vx_byte(self, vx, nn): 
        """
        4xnn
        SNE Vx, byte
        Skip the next instruction if Vx != nn.
        """
        if self.regs[vx] != nn:
            self.pc = (self.pc + 2) & 0xFFFF


    def op_se_vx_vy(self, vx, vy): 
        """
        5xy0
        SE Vx, Vy
        Skip next instruction if Vx == Vy
        """
        if self.regs[vx] == self.regs[vy]:
            self.pc = (self.pc + 2) & 0xFFFF
  

    def op_ld_vx_byte(self, vx, nn): 
        """
        6xnn 
        LD Vx, byte
        Set Vx = nn.
        """
        self.regs[vx] = nn & 0xFF


    def op_add_vx_byte(self, vx, nn): 
        """
        7xnn ADD Vx, byte
        Set Vx = Vx + nn (no carry flag).
        """
        self.regs[vx] = (self.regs[vx] + nn) & 0xFF


    def op_ld_vx_vy(self, vx,vy):
        """
        8xy0 - LD Vx, Vy - Set Vx = Vy. 
        Stores the value of register Vy in register Vx.
        """
        self.regs[vx] = self.regs[vy]


    def op_or_vx_vy(self, vx,vy):
        """
        8xy1 - OR Vx, Vy - Set Vx = Vx OR Vy. 
        Performs a bitwise OR on the values of Vx and Vy, 
        then stores the result in Vx.
        """
        self.regs[vx] = self.regs[vx] | self.regs[vy]


    def op_and_vx_vy(self, vx,vy):
        """
        8xy2 - AND Vx, Vy - Set Vx = Vx AND Vy. 
        Performs a bitwise AND on the values of Vx and Vy, 
        then stores the result in Vx.
        """
        self.regs[vx] = self.regs[vx] & self.regs[vy]


    def op_xor_vx_vy(self, vx,vy):
        """
        8xy3 - XOR Vx, Vy - Set Vx = Vx XOR Vy. 
        Performs a bitwise XOR on the values of Vx and Vy, 
        then stores the result in Vx.
        """
        self.regs[vx] = self.regs[vx] ^ self.regs[vy]


    def op_add_vx_vy(self, vx,vy):
        """
        8xy4 - ADD Vx, Vy - Set Vx = Vx + Vy, set VF = carry.
        The values of Vx and Vy are added together. 
        If the result is greater than 8 bits (i.e., > 255,) VF is set to 1, otherwise 0. 
        Only the lowest 8 bits of the result are kept, and stored in Vx.
        """
        result = self.regs[vx] + self.regs[vy]
        if result > 0xFF:
            self.regs['VF'] = 1
        else: 
            self.regs['VF'] = 0
        self.regs[vx] = result & 0xFF


    def op_sub_vx_vy(self, vx,vy):
        """
        8xy5 - SUB Vx, Vy - Set Vx = Vx - Vy, set VF = NOT borrow.
        If Vx > Vy, then VF is set to 1, otherwise 0.
        Then Vy is subtracted from Vx, and the result stored in Vx.
        """
        if self.regs[vx] > self.regs[vy]:
            self.regs['VF'] = 1
        else:
            self.regs['VF'] = 0
        self.regs[vx] = (self.regs[vx] - self.regs[vy]) & 0xFF


    def op_shr_vx(self, vx):
        """
        8xy6 - SHR Vx {, Vy}
        Store least-significant bit of Vx in VF, then Vx >>= 1.
        """
        self.regs['VF'] = self.regs[vx] & 0x1
        self.regs[vx] = (self.regs[vx] >> 1) & 0xFF


    def op_subn_vx_vy(self, vx,vy):
        """
        8xy7 - SUBN Vx, Vy
        Set Vx = Vy - Vx; set VF = 0 on borrow, else 1.
        """
        if self.regs[vy] >= self.regs[vx]:
            self.regs['VF'] = 1
        else:
            self.regs['VF'] = 0
        self.regs[vx] = (self.regs[vy] - self.regs[vx]) & 0xFF


    def op_shl_vx(self, vx):
        """
        8xyE - SHL Vx {, Vy}
        Store most-significant bit of Vx in VF, then Vx <<= 1.
        """
        self.regs['VF'] = (self.regs[vx] >> 7) & 1
        self.regs[vx] = (self.regs[vx] << 1) & 0xFF


    def op_sne_vx_vy(self, vx,vy):
        """
        9xy0 - SNE Vx, Vy - Skip next instruction if Vx != Vy. 
        The values of Vx and Vy are compared, and if they are not equal, 
        the program counter is increased by 2
        """
        if self.regs[vx] != self.regs[vy]:
            self.pc = (self.pc + 2) & 0xFFFF


    def op_ld_i_addr(self, nnn):
        """
        Annn - LD I, addr
        Set I to nnn.
        """
        self.I = nnn & 0xFFF


    def op_jump_v0_addr(self, nnn):
        """
        Bnnn - JP V0, addr - Jump to location nnn + V0. 
        The program counter is set to nnn + the value of V0.
        """
        result = (nnn + self.regs['V0']) & 0xFFF
        self.pc = result


    def op_rnd_vx(self, vx, nn):
        """
        Cxkk - RND Vx, byte - Set Vx = random byte AND kk. 
        Generates a random number from 0 to 255, which is then ANDed with the value kk.
        """
        rnd = self.random.getrandbits(8) # 0-255 integer
        self.regs[vx] = rnd & nn


    def op_drw_vx_vy_n(self, vx,vy,n):
        """
        Dxyn - DRW Vx, Vy, nibble
        Draw sprite at (Vx, Vy) with height N
        Width of each line is 8 bit.
        set VF = 1 on any pixel collision, else 0.
        """
        x_coord = self.regs[vx] & (self.SCREEN_W - 1)
        y_coord = self.regs[vy] & (self.SCREEN_H - 1)
        i = self.I
        vf = 0

        for r in range(n):
            sprite = self.mem[i + r]
            py = ((y_coord + r) % self.SCREEN_H) * self.SCREEN_W
            for b in range(8):
                bit = (sprite >> (7 - b)) & 1
                px = (x_coord + b) % self.SCREEN_W
                idx = py + px
                old = self.screen[idx]
                if old & bit:
                    vf = 1
                self.screen[idx] = old ^ bit

        self.regs['VF'] = vf


    def op_skp_vx(self, vx):
        """
        Ex9E - SKP Vx 
        Skip next instruction if key with the value of Vx is pressed. 
        """
        key = self.regs[vx]
        if self.keypad[key]:
            self.pc = (self.pc + 2) & 0xFFFF


    def op_sknp_vx(self, vx):
        """
        ExA1 - SKNP Vx 
        Skip next instruction if key with the value of Vx is not pressed. 
        """
        key = self.regs[vx]
        if not self.keypad[key]:
            self.pc = (self.pc + 2) & 0xFFFF


    def op_ld_vx_dt(self, vx):
        """
        Fx07 - LD Vx, DT
        Set Vx = delay timer value. 
        The value of DT is placed into Vx.
        """
        self.regs[vx] = self.dt


    def op_ld_vx_k(self, vx):
        """
        Fx0A - LD Vx, K
        Wait for a key press, store the value of the key in Vx. 
        All execution stops until a key is pressed, then the value of that key is stored in Vx.
        """
        while True:
            for idx, pressed in enumerate(self.keypad):
                if pressed:
                    self.regs[vx] = idx
                    return
            self.time.sleep(0.001) # Small sleep to control CPU usage


    def op_ld_dt_vx(self, vx):
        """
        Fx15 - LD DT, Vx 
        Set delay timer = Vx. 
        DT is set equal to the value of Vx.
        """
        self.dt = self.regs[vx] & 0xFF


    def op_ld_st_vx(self, vx):
        """
        Fx18 - LD ST, Vx 
        Set sound timer = Vx. 
        ST is set equal to the value of Vx.
        """
        self.st = self.regs[vx] & 0xFF


    def op_add_i_vx(self, vx):
        """
        Fx1E - ADD I, Vx 
        Set I = I + Vx. 
        """
        self.I = (self.I + self.regs[vx]) & 0xFFF


    def op_ld_f_vx(self, vx):
        """
        Fx29 - LD F, Vx 
        Set I = location of sprite for digit Vx. 
        """
        self.I = self.FONT_START + (self.regs[vx] * 5)


    def op_ld_b_vx(self, vx):
        """
        Fx33 - LD B, Vx Store BCD representation of Vx in memory locations I, I+1, and I+2. 
        """
        n = self.regs[vx]
        hund = (n // 100) % 10
        tens = (n //  10) % 10
        ones = n % 10
        self.mem[self.I] = hund
        self.mem[self.I + 1] = tens
        self.mem[self.I + 2] = ones


    def op_ld_i_vx(self, x):
        """
        Fx55 - LD [I], Vx Store registers V0 through Vx in memory starting at location I. 
        The interpreter copies the values of registers V0 through Vx into memory, 
        starting at the address in I
        """
        if self.I + x >= self.MEM_SIZE:
            raise RuntimeError(f"Memory overflow: trying to write through address {self.I + x:03X}, "
                f"but MEM_SIZE is {self.MEM_SIZE:03X}")
        for i in range(x+1):
            self.mem[self.I + i] = self.regs[f'V{i:X}']


    def op_ld_vx_i(self, x):
        """
        Fx65 - LD Vx, [I] Read registers V0 through Vx from memory starting at location I. 
        The interpreter reads values from memory starting at location I into registers V0 through Vx.
        """
        for i in range(x+1):
            self.regs[f"V{i:X}"] = self.mem[self.I + i]


if __name__ == "__main__":
    import sys
    chip = Chip8()
    chip.load_rom(sys.argv[1])
    while chip.step():
        pass