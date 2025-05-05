# -----------------------------------------------
# CHIP-8 Python Emulator
# By Phil Boivin - 2025
# Version 0.1.1
# -----------------------------------------------
import random
import time

class NeedKey(Exception):
    def __init__(self, vx_idx): # Store the index
        self.vx_idx = vx_idx

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
        self.regs = bytearray(16) # Use bytearray for V0-VF registers
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


        # --- QUIRK FLAGS ---
        self.quirk_display_wait = True # Set True to enable Display Wait quirk
        self.quirk_clipping = True     # Set True to enable Clipping quirk
        self.quirk_shifting = False    # Set True to enable Shifting quirk (Vx only)
        self.quirk_load_store = True # Common I increment quirk for Fx55/Fx65 (already implemented)
        
        # Internal state for display wait quirk
        self._waiting_for_draw_sync = False


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
                    self.op_disp_clear()
                    return True
                elif op == 0x00EE:
                    self.op_ret_from_subroutine()
                    return True
                else:
                    # 0NNN: SYS addr, ignored in modern interpreters
                    return True
            case 1:
                self.op_jump_to_addr(nnn)
                return True
            case 2:
                self.op_call_addr(nnn)
                return True
            case 3:
                self.op_se_vx_byte(n2,nn)
                return True
            case 4:
                self.op_sne_vx_byte(n2,nn)
                return True
            case 5:
                self.op_se_vx_vy(n2,n3)
                return True
            case 6:
                self.op_ld_vx_byte(n2, nn)
                return True
            case 7:
                self.op_add_vx_byte(n2, nn)
                return True
            case 8:
                if n4 == 0:
                    self.op_ld_vx_vy(n2,n3)
                    return True
                elif n4 == 1:
                    self.op_or_vx_vy(n2,n3)
                    return True
                elif n4 == 2:
                    self.op_and_vx_vy(n2,n3)
                    return True
                elif n4 == 3:
                    self.op_xor_vx_vy(n2,n3)
                    return True
                elif n4 == 4:
                    self.op_add_vx_vy(n2,n3)
                    return True
                elif n4 == 5:
                    self.op_sub_vx_vy(n2,n3)
                    return True
                elif n4 == 6:
                    self.op_shr_vx(n2)
                    return True
                elif n4 == 7:
                    self.op_subn_vx_vy(n2,n3)
                    return True
                elif n4 == 14:
                    self.op_shl_vx(n2)
                    return True
                else:
                    return True
            case 9:
                self.op_sne_vx_vy(n2,n3)
                return True
            case 10: # A
                self.op_ld_i_addr(nnn)
                return True
            case 11: # B
                self.op_jump_v0_addr(nnn)
                return True
            case 12: # C
                self.op_rnd_vx(n2,nn)
                return True
            case 13: # D
                self.op_drw_vx_vy_n(n2,n3,n4)
                return True
            case 14: # E
                if nn == 0x9E:
                    self.op_skp_vx(n2)
                    return True
                elif nn == 0xA1:
                    self.op_sknp_vx(n2)
                    return True
                else:
                    return True
            case 15: # F
                if nn == 0x07:
                    self.op_ld_vx_dt(n2)
                    return True
                elif nn == 0x0A:
                    self.op_ld_vx_k(n2)
                    return True
                elif nn == 0x15:
                    self.op_ld_dt_vx(n2)
                    return True
                elif nn == 0x18:
                    self.op_ld_st_vx(n2)
                    return True
                elif nn == 0x1E:
                    self.op_add_i_vx(n2)
                    return True
                elif nn == 0x29:
                    self.op_ld_f_vx(n2)
                    return True
                elif nn == 0x33:
                    self.op_ld_b_vx(n2)
                    return True
                elif nn == 0x55:
                    self.op_ld_i_vx(n2)
                    return True
                elif nn == 0x65:
                    self.op_ld_vx_i(n2)
                    return True
                else:
                    return True
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


    def update_timers(self):
        """
        Decrement Delay Timer (DT) and Sound Timer (ST) if they are > 0.
        This method should be called at a rate of 60Hz by the main loop.
        """
        if self.dt > 0:
            self.dt -= 1
        if self.st > 0:
            self.st -= 1

    @property
    def is_sound_on(self) -> bool:
        """Returns True if the sound timer is active (greater than zero)."""
        return self.st > 0


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


    def op_se_vx_byte(self, vx_idx, nn): 
        """
        3xnn
        SE Vx, byte
        Skip the next instruction if Vx == nn.
        """
        if self.regs[vx_idx] == nn:
            self.pc = (self.pc + 2) & 0xFFFF
  

    def op_sne_vx_byte(self, vx_idx, nn): 
        """
        4xnn
        SNE Vx, byte
        Skip the next instruction if Vx != nn.
        """
        if self.regs[vx_idx] != nn:
            self.pc = (self.pc + 2) & 0xFFFF


    def op_se_vx_vy(self, vx_idx, vy_idx): 
        """
        5xy0
        SE Vx, Vy
        Skip next instruction if Vx == Vy
        """
        if self.regs[vx_idx] == self.regs[vy_idx]:
            self.pc = (self.pc + 2) & 0xFFFF
  

    def op_ld_vx_byte(self, vx_idx, nn): 
        """
        6xnn 
        LD Vx, byte
        Set Vx = nn.
        """
        self.regs[vx_idx] = nn & 0xFF


    def op_add_vx_byte(self, vx_idx, nn): 
        """
        7xnn ADD Vx, byte
        Set Vx = Vx + nn (no carry flag).
        """
        self.regs[vx_idx] = (self.regs[vx_idx] + nn) & 0xFF


    def op_ld_vx_vy(self, vx_idx,vy_idx):
        """
        8xy0 - LD Vx, Vy - Set Vx = Vy. 
        Stores the value of register Vy in register Vx.
        """
        self.regs[vx_idx] = self.regs[vy_idx]


    def op_or_vx_vy(self, vx_idx,vy_idx):
        """
        8xy1 - OR Vx, Vy - Set Vx = Vx OR Vy. 
        Performs a bitwise OR on the values of Vx and Vy, 
        then stores the result in Vx.
        """
        self.regs[vx_idx] = self.regs[vx_idx] | self.regs[vy_idx]
        self.regs[0xF] = 0
        

    def op_and_vx_vy(self, vx_idx,vy_idx):
        """
        8xy2 - AND Vx, Vy - Set Vx = Vx AND Vy. 
        Performs a bitwise AND on the values of Vx and Vy, 
        then stores the result in Vx.
        """
        self.regs[vx_idx] = self.regs[vx_idx] & self.regs[vy_idx]
        self.regs[0xF] = 0


    def op_xor_vx_vy(self, vx_idx,vy_idx):
        """
        8xy3 - XOR Vx, Vy - Set Vx = Vx XOR Vy. 
        Performs a bitwise XOR on the values of Vx and Vy, 
        then stores the result in Vx.
        """
        self.regs[vx_idx] = self.regs[vx_idx] ^ self.regs[vy_idx]
        self.regs[0xF] = 0


    def op_add_vx_vy(self, vx_idx,vy_idx):
        """
        8xy4 - ADD Vx, Vy - Set Vx = Vx + Vy, set VF = carry.
        The values of Vx and Vy are added together. 
        If the result is greater than 8 bits (i.e., > 255,) VF is set to 1, otherwise 0. 
        Only the lowest 8 bits of the result are kept, and stored in Vx.
        """
        vx_val = self.regs[vx_idx]
        vy_val = self.regs[vy_idx]
        total  = vx_val + vy_val
        self.regs[vx_idx] = total & 0xFF
        self.regs[0xF] = 1 if total > 0xFF else 0


    def op_sub_vx_vy(self, vx_idx, vy_idx):
        """
        8xy5 - SUB Vx, Vy - Set Vx = Vx - Vy, set VF = NOT borrow.
        If Vx > Vy, then VF is set to 1, otherwise 0 (tests expect VF=0 on equal).
        Then Vy is subtracted from Vx, and the result stored in Vx.
        """
        vx_val = self.regs[vx_idx]
        vy_val = self.regs[vy_idx]
        flag_value = 1 if vx_val > vy_val else 0
        result = (vx_val - vy_val) & 0xFF
        self.regs[vx_idx] = result
        self.regs[0xF] = flag_value


    def op_shr_vx(self, vx_idx):
        """
        8xy6 - SHR Vx {, Vy}
        Store least-significant bit of Vx in VF, then Vx >>= 1.
        """
        val = self.regs[vx_idx]
        lsb = val & 0x1
        self.regs[vx_idx] = (val >> 1) & 0xFF
        self.regs[0xF] = lsb


    def op_subn_vx_vy(self, vx_idx, vy_idx):
        """
        8xy7 - SUBN Vx, Vy
        Set Vx = Vy - Vx; set VF = 0 on borrow, else 1.
        """
        vx_val = self.regs[vx_idx]
        vy_val = self.regs[vy_idx]
        flag_value = 1 if vy_val >= vx_val else 0
        result = (vy_val - vx_val) & 0xFF
        self.regs[vx_idx] = result
        self.regs[0xF] = flag_value


    def op_shl_vx(self, vx_idx):
        """
        8xyE - SHL Vx {, Vy}
        Store most-significant bit of Vx in VF, then Vx <<= 1.
        """
        val = self.regs[vx_idx]
        msb = (val >> 7) & 0x1
        self.regs[vx_idx] = (val << 1) & 0xFF
        self.regs[0xF] = msb


    def op_sne_vx_vy(self, vx_idx,vy_idx):
        """
        9xy0 - SNE Vx, Vy - Skip next instruction if Vx != Vy. 
        The values of Vx and Vy are compared, and if they are not equal, 
        the program counter is increased by 2
        """
        if self.regs[vx_idx] != self.regs[vy_idx]:
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
        result = (nnn + self.regs[0]) & 0xFFF
        self.pc = result


    def op_rnd_vx(self, vx_idx, nn):
        """
        Cxkk - RND Vx, byte - Set Vx = random byte AND kk. 
        Generates a random number from 0 to 255, which is then ANDed with the value kk.
        """
        rnd = self.random.getrandbits(8) # 0-255 integer
        self.regs[vx_idx] = rnd & nn


    def op_drw_vx_vy_n(self, vx_idx, vy_idx, n):
        """
        Dxyn - DRW Vx, Vy, nibble
        Draw sprite at (Vx, Vy) with height N. Width 8 bits.
        Base coordinates (Vx, Vy) are wrapped first.
        Subsequent pixels are wrapped OR clipped based on self.quirk_clipping.
        Sets VF = 1 on pixel collision, else 0.
        Optionally sets wait flag based on self.quirk_display_wait.
        """
        # This applies regardless of the clipping quirk for individual pixels.
        base_x = self.regs[vx_idx] % self.SCREEN_W
        base_y = self.regs[vy_idx] % self.SCREEN_H

        i = self.I
        self.regs[0xF] = 0 # Reset VF (collision flag)

        for r in range(n):
            sprite_byte = self.mem[i + r]
            # Calculate potential Y relative to the (already wrapped) base_y
            pixel_row_y = base_y + r

            # --- Clipping/Wrapping Logic for INDIVIDUAL PIXELS (Y) ---
            if self.quirk_clipping:
                # Check if the calculated pixel_row_y is off-screen
                if pixel_row_y < 0 or pixel_row_y >= self.SCREEN_H:
                    continue # Skip this entire row if the pixel Y is clipped
                final_y = pixel_row_y # Use the valid pixel Y
            else:
                # Wrap the calculated pixel_row_y
                final_y = pixel_row_y % self.SCREEN_H
            # --- End Clipping/Wrapping Logic (Y) ---

            for b in range(8):
                # Only process if sprite bit is 1
                if (sprite_byte >> (7 - b)) & 1:
                    # Calculate potential X relative to the (already wrapped) base_x
                    pixel_col_x = base_x + b

                    # --- Clipping/Wrapping Logic for INDIVIDUAL PIXELS (X) ---
                    if self.quirk_clipping:
                        # Check if the calculated pixel_col_x is off-screen
                        if pixel_col_x < 0 or pixel_col_x >= self.SCREEN_W:
                            continue # Skip this specific pixel if its X is clipped
                        final_x = pixel_col_x # Use the valid pixel X
                    else:
                        # Wrap the calculated pixel_col_x
                        final_x = pixel_col_x % self.SCREEN_W
                    # --- End Clipping/Wrapping Logic (X) ---

                    # Calculate screen buffer index using final wrapped/clipped coordinates
                    idx = final_y * self.SCREEN_W + final_x

                    # Final bounds check (good practice, less critical now)
                    if 0 <= idx < len(self.screen):
                        # Check for collision BEFORE drawing
                        if self.screen[idx] == 1:
                            self.regs[0xF] = 1 # Set collision flag
                        # Draw the pixel (XOR)
                        self.screen[idx] ^= 1
                    # else: pixel fell outside bounds after clipping/wrapping (unlikely now)

        # --- Display Wait Quirk Logic ---
        if self.quirk_display_wait:
            self._waiting_for_draw_sync = True

    def op_skp_vx(self, vx_idx):
        """
        Ex9E - SKP Vx 
        Skip next instruction if key with the value of Vx is pressed. 
        """
        key = self.regs[vx_idx]
        if self.keypad[key]:
            self.pc = (self.pc + 2) & 0xFFFF


    def op_sknp_vx(self, vx_idx):
        """
        ExA1 - SKNP Vx 
        Skip next instruction if key with the value of Vx is not pressed. 
        """
        key = self.regs[vx_idx]
        if not self.keypad[key]:
            self.pc = (self.pc + 2) & 0xFFFF


    def op_ld_vx_dt(self, vx_idx):
        """
        Fx07 - LD Vx, DT
        Set Vx = delay timer value. 
        The value of DT is placed into Vx.
        """
        self.regs[vx_idx] = self.dt


    def op_ld_vx_k(self, vx_idx):
        """
        Fx0A - LD Vx, K
        Wait for a key press, store the value of the key in Vx. 
        All execution stops until a key is pressed, then the value of that key is stored in Vx.
        """
        # Check for any key already pressed; if so, store it and return
        for idx, pressed in enumerate(self.keypad):
            if pressed:
                self.regs[vx_idx] = idx
                return
        # No key pressed: block until next key event
        raise NeedKey(vx_idx)


    def op_ld_dt_vx(self, vx_idx):
        """
        Fx15 - LD DT, Vx 
        Set delay timer = Vx. 
        DT is set equal to the value of Vx.
        """
        self.dt = self.regs[vx_idx] & 0xFF


    def op_ld_st_vx(self, vx_idx):
        """
        Fx18 - LD ST, Vx 
        Set sound timer = Vx. 
        ST is set equal to the value of Vx.
        """
        self.st = self.regs[vx_idx] & 0xFF


    def op_add_i_vx(self, vx_idx):
        """
        Fx1E - ADD I, Vx 
        Set I = I + Vx. 
        """
        self.I = (self.I + self.regs[vx_idx]) & 0xFFF


    def op_ld_f_vx(self, vx_idx):
        """
        Fx29 - LD F, Vx 
        Set I = location of sprite for digit Vx. 
        """
        self.I = self.FONT_START + (self.regs[vx_idx] * 5)


    def op_ld_b_vx(self, vx_idx):
        """
        Fx33 - LD B, Vx Store BCD representation of Vx in memory locations I, I+1, and I+2. 
        """
        n = self.regs[vx_idx]
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
            self.mem[self.I + i] = self.regs[i]
        self.I = (self.I + x + 1) & 0xFFF


    def op_ld_vx_i(self, x):
        """
        Fx65 - LD Vx, [I] Read registers V0 through Vx from memory starting at location I. 
        The interpreter reads values from memory starting at location I into registers V0 through Vx.
        """
        for i in range(x+1):
            self.regs[i] = self.mem[self.I + i]
        self.I = (self.I + x + 1) & 0xFFF


if __name__ == "__main__":
    import sys
    chip = Chip8()
    chip.load_rom(sys.argv[1])
    while chip.step():
        pass