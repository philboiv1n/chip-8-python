# -----------------------------------------------
# CHIP-8 Python Emulator - Tests
# By Phil Boivin - 2025
# Version 0.1.1
# -----------------------------------------------
import importlib.util
import os
import pytest

# Dynamically load the chip8 module from chip_8.py
spec = importlib.util.spec_from_file_location(
    "chip8",
    os.path.join(os.path.dirname(__file__), "chip_8.py")
)
chip8 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(chip8)

@pytest.fixture
def chip():
    return chip8.Chip8()

def test_disp_clear_clears_screen(chip):
    chip.screen[:] = bytearray([1] * len(chip.screen))
    chip.op_disp_clear()
    assert all(pixel == 0 for pixel in chip.screen)

def test_jump_to_addr_masks_address(chip):
    chip.op_jump_to_addr(0x1234)
    assert chip.pc == 0x1234 & 0xFFF

def test_call_addr_pushes_and_jumps(chip):
    initial_pc = chip.pc
    chip.op_call_addr(0x300)
    assert chip.sp == 1
    assert chip.stack[0] == initial_pc
    assert chip.pc == 0x300

def test_ret_from_subroutine_pops_pc(chip):
    chip.stack[0] = 0x250
    chip.sp = 1
    chip.op_ret_from_subroutine()
    assert chip.sp == 0
    assert chip.pc == 0x250

def test_se_vx_byte_skips_when_equal(chip):
    chip.regs[0x1] = 0xAA
    chip.pc = 0x200
    chip.op_se_vx_byte(0x1, 0xAA)
    assert chip.pc == 0x202

def test_se_vx_byte_no_skip_when_not_equal(chip):
    chip.regs[0x1] = 0xAB
    chip.pc = 0x200
    chip.op_se_vx_byte(0x1, 0xAA)
    assert chip.pc == 0x200

def test_sne_vx_byte_skips_when_not_equal(chip):
    chip.regs[0x2] = 0x01
    chip.pc = 0x200
    chip.op_sne_vx_byte(0x2, 0x02)
    assert chip.pc == 0x202

def test_sne_vx_byte_no_skip_when_equal(chip):
    chip.regs[0x2] = 0x02
    chip.pc = 0x200
    chip.op_sne_vx_byte(0x2, 0x02)
    assert chip.pc == 0x200

def test_se_vx_vy_skips_when_equal(chip):
    chip.regs[0x3] = 0x05
    chip.regs[0x4] = 0x05
    chip.pc = 0x200
    chip.op_se_vx_vy(0x3, 0x4)
    assert chip.pc == 0x202

def test_se_vx_vy_no_skip_when_not_equal(chip):
    chip.regs[0x3] = 0x05
    chip.regs[0x4] = 0x06
    chip.pc = 0x200
    chip.op_se_vx_vy(0x3, 0x4)
    assert chip.pc == 0x200

def test_ld_vx_byte_sets_register(chip):
    chip.op_ld_vx_byte(0x5, 0xAB)
    assert chip.regs[0x5] == 0xAB

def test_add_vx_byte_wraps(chip):
    chip.regs[0x5] = 0xF0
    chip.op_add_vx_byte(0x5, 0x20)
    assert chip.regs[0x5] == (0xF0 + 0x20) & 0xFF

def test_ld_vx_vy_copies_register(chip):
    chip.regs[0x6] = 0x3C
    chip.op_ld_vx_vy(0x7, 0x6)
    assert chip.regs[0x7] == 0x3C

def test_or_and_xor_and_vx_vy_logical_ops(chip):
    chip.regs[0x8] = 0x0F
    chip.regs[0x9] = 0xF0
    # OR
    chip.op_or_vx_vy(0x8, 0x9)
    assert chip.regs[0x8] == (0x0F | 0xF0)
    # AND
    chip.regs[0x8] = 0x0F
    chip.op_and_vx_vy(0x8, 0x9)
    assert chip.regs[0x8] == (0x0F & 0xF0)
    # XOR
    chip.regs[0x8] = 0x0F
    chip.op_xor_vx_vy(0x8, 0x9)
    assert chip.regs[0x8] == (0x0F ^ 0xF0)

def test_add_vx_vy_sets_carry_flag(chip):
    chip.regs[0xA] = 0xFF
    chip.regs[0xB] = 0x01
    chip.regs[0xF] = 0
    chip.op_add_vx_vy(0xA, 0xB)
    assert chip.regs[0xF] == 1
    assert chip.regs[0xA] == 0x00

def test_add_vx_vy_no_carry_flag(chip):
    chip.regs[0xA] = 0x01
    chip.regs[0xB] = 0x01
    chip.regs[0xF] = 1
    chip.op_add_vx_vy(0xA, 0xB)
    assert chip.regs[0xF] == 0

def test_ld_i_addr_sets_index_register(chip):
    chip.op_ld_i_addr(0x123)
    assert chip.I == 0x123

def test_drw_vx_vy_n_draw_and_collision(chip):
    # prepare two-line sprite
    chip.I = 0x300
    chip.mem[0x300] = 0b11000000
    chip.mem[0x301] = 0b00110000
    chip.regs[0x0] = 0
    chip.regs[0x1] = 0
    # first draw: no collision
    chip.op_drw_vx_vy_n(0x0, 0x1, 2)
    assert chip.regs[0xF] == 0
    # some pixels should be set
    assert chip.screen[0] == 1
    assert chip.screen[1] == 1
    # Second draw at same position: pixels should toggle off
    chip.op_drw_vx_vy_n(0x0, 0x1, 2)
    assert chip.screen[0] == 0
    assert chip.screen[1] == 0

def test_sub_vx_vy_no_borrow(chip):
    # When Vx > Vy, VF should be 1 and Vx = Vx - Vy.
    chip.regs[0x2] = 0x20
    chip.regs[0x3] = 0x10
    chip.regs[0xF] = 0  # clear flag
    chip.op_sub_vx_vy(0x2, 0x3)
    assert chip.regs[0x2] == 0x10
    assert chip.regs[0xF] == 1

def test_sub_vx_vy_with_borrow(chip):
    # When Vx < Vy, VF should be 0 and result wraps around.
    chip.regs[0x4] = 0x05
    chip.regs[0x5] = 0x10
    chip.regs[0xF] = 1  # set flag to non-zero
    chip.op_sub_vx_vy(0x4, 0x5)
    assert chip.regs[0x4] == (0x05 - 0x10) & 0xFF
    assert chip.regs[0xF] == 0

def test_sub_vx_vy_equal(chip):
    # When Vx == Vy, VF should be 0 and Vx becomes 0.
    chip.regs[0x6] = 0xAB
    chip.regs[0x7] = 0xAB
    chip.regs[0xF] = 1
    chip.op_sub_vx_vy(0x6, 0x7)
    assert chip.regs[0x6] == 0x00
    assert chip.regs[0xF] == 0


def test_shr_vx_with_lsb_one(chip):
    # When Vx is odd, VF should be set to 1 and Vx should shift right by 1
    chip.regs[0x2] = 0x05  # binary 00000101, LSB = 1
    chip.regs[0xF] = 0      # clear flag
    chip.op_shr_vx(0x2)
    assert chip.regs[0xF] == 1
    assert chip.regs[0x2] == 0x02  # 5 >> 1 = 2

def test_shr_vx_with_lsb_zero(chip):
    # When Vx is even, VF should be set to 0 and Vx should shift right by 1
    chip.regs[0x3] = 0x08  # binary 00001000, LSB = 0
    chip.regs[0xF] = 1      # set flag to non-zero
    chip.op_shr_vx(0x3)
    assert chip.regs[0xF] == 0
    assert chip.regs[0x3] == 0x04  # 8 >> 1 = 4

def test_shr_vx_zero_result(chip):
    # Shifting a 1 results in zero and VF should capture the 1 bits
    chip.regs[0x4] = 0x01  # binary 00000001, LSB = 1
    chip.regs[0xF] = 0
    chip.op_shr_vx(0x4)
    assert chip.regs[0xF] == 1
    assert chip.regs[0x4] == 0x00  # 1 >> 1 = 0

# SUBN Vx, Vy tests
def test_subn_vx_vy_no_borrow(chip):
    # When Vy >= Vx, VF should be 1 and Vx = Vy - Vx
    chip.regs[0x2] = 0x10
    chip.regs[0x3] = 0x20
    chip.regs[0xF] = 0
    chip.op_subn_vx_vy(0x2, 0x3)
    assert chip.regs[0x2] == 0x10  # 0x20 - 0x10
    assert chip.regs[0xF] == 1

def test_subn_vx_vy_with_borrow(chip):
    # When Vy < Vx, VF should be 0 and result wraps around
    chip.regs[0x4] = 0x10
    chip.regs[0x5] = 0x05
    chip.regs[0xF] = 1
    chip.op_subn_vx_vy(0x4, 0x5)
    assert chip.regs[0x4] == (0x05 - 0x10) & 0xFF
    assert chip.regs[0xF] == 0

def test_subn_vx_vy_equal(chip):
    # When Vy == Vx, VF should be 1 and Vx becomes 0
    chip.regs[0x6] = 0xAB
    chip.regs[0x7] = 0xAB
    chip.regs[0xF] = 0
    chip.op_subn_vx_vy(0x6, 0x7)
    assert chip.regs[0x6] == 0x00
    assert chip.regs[0xF] == 1

def test_shl_vx_msb_one(chip):
    # When Vx’s MSB is 1, VF should be set to 1 and Vx should shift left (with wrap).
    chip.regs[0x8] = 0x80  # binary 10000000, MSB = 1
    chip.regs[0xF] = 0      # clear flag
    chip.op_shl_vx(0x8)
    assert chip.regs[0xF] == 1
    # 0x80 << 1 = 0x100, masked to 8 bits gives 0x00
    assert chip.regs[0x8] == 0x00

def test_shl_vx_msb_zero(chip):
    # When Vx’s MSB is 0, VF should be set to 0 and Vx should shift left.
    chip.regs[0x9] = 0x40  # binary 01000000, MSB = 0
    chip.regs[0xF] = 1      # set flag to non-zero
    chip.op_shl_vx(0x9)
    assert chip.regs[0xF] == 0
    # 0x40 << 1 = 0x80
    assert chip.regs[0x9] == 0x80

def test_shl_vx_wraps(chip):
    # Shifting 0xFF (11111111) left yields 0xFE after wrap, VF captures the old MSB.
    chip.regs[0xA] = 0xFF  # MSB = 1
    chip.regs[0xF] = 0
    chip.op_shl_vx(0xA)
    assert chip.regs[0xF] == 1
    # 0xFF << 1 = 0x1FE masked to 0xFF gives 0xFE
    assert chip.regs[0xA] == 0xFE

def test_sne_vx_vy_skips_when_not_equal(chip):
    # When Vx != Vy, PC should advance by 2 (skip next instruction)
    chip.regs[0x2] = 0x05
    chip.regs[0x3] = 0x06
    chip.pc = 0x200
    chip.op_sne_vx_vy(0x2, 0x3)
    assert chip.pc == 0x202

def test_sne_vx_vy_no_skip_when_equal(chip):
    # When Vx == Vy, PC should not change
    chip.regs[0x4] = 0x07
    chip.regs[0x5] = 0x07
    chip.pc = 0x200
    chip.op_sne_vx_vy(0x4, 0x5)
    assert chip.pc == 0x200

def test_jump_v0_addr_basic(chip):
    # When V0 is 0x10 and nnn is 0x200, PC should become 0x210 (masked to 12 bits)
    chip.regs[0x0] = 0x10
    chip.pc = 0x000
    chip.op_jump_v0_addr(0x200)
    assert chip.pc == (0x200 + 0x10) & 0xFFF

def test_jump_v0_addr_wraps(chip):
    # When V0 + nnn exceeds 0xFFF, it should wrap modulo 0x1000
    chip.regs[0x0] = 0x1
    chip.pc = 0x000
    chip.op_jump_v0_addr(0xFFF)
    assert chip.pc == (0xFFF + 0x1) & 0xFFF  # 0x1000 wraps to 0x000

def test_rnd_vx_masks_random(chip, monkeypatch):
    # Monkeypatch random.getrandbits to return a known byte
    monkeypatch.setattr(chip.random, 'getrandbits', lambda bits: 0b10101111)
    chip.regs[0x2] = 0x00
    chip.op_rnd_vx(0x2, 0x0F)
    expected = 0b10101111 & 0x0F
    assert chip.regs[0x2] == expected

def test_skp_vx_skips_when_key_pressed(chip):
    # When the keypad at Vx is True, PC should advance by 2
    chip.regs[0x2] = 0x03   # test with key index 3
    chip.pc = 0x200
    chip.keypad[3] = True
    chip.op_skp_vx(0x2)
    assert chip.pc == 0x202

def test_skp_vx_no_skip_when_key_not_pressed(chip):
    # When the keypad at Vx is False, PC should not change
    chip.regs[0x4] = 0x05   # test with key index 5
    chip.pc = 0x200
    chip.keypad[5] = False
    chip.op_skp_vx(0x4)
    assert chip.pc == 0x200

def test_sknp_vx_skips_when_key_not_pressed(chip):
    # ExA1: Skip when the keypad at Vx is not pressed
    chip.regs[0x2] = 0x03   # key index 3
    chip.pc = 0x200
    chip.keypad[3] = False
    chip.op_sknp_vx(0x2)
    assert chip.pc == 0x202

def test_sknp_vx_no_skip_when_key_pressed(chip):
    # ExA1: Do not skip when the keypad at Vx is pressed
    chip.regs[0x4] = 0x05   # key index 5
    chip.pc = 0x200
    chip.keypad[5] = True
    chip.op_sknp_vx(0x4)
    assert chip.pc == 0x200

def test_ld_vx_dt_sets_from_delay_timer(chip):
    # FX07: Vx should be set to the current delay timer value
    chip.dt = 0x3C
    chip.regs[0x5] = 0x00
    chip.op_ld_vx_dt(0x5)
    assert chip.regs[0x5] == 0x3C

def test_ld_vx_k_waits_for_key(chip, monkeypatch):
    # FX0A: Vx should receive the index of the first pressed key
    # Prevent actual sleeping to speed up the test
    monkeypatch.setattr(chip.time, 'sleep', lambda x: None)
    chip.keypad[7] = True
    chip.regs[0x2] = 0x00
    chip.op_ld_vx_k(0x2)
    assert chip.regs[0x2] == 7

def test_ld_dt_vx_sets_delay_timer(chip):
    # FX15: delay timer should be set to the value in Vx
    chip.regs[0x3] = 0x7D
    chip.dt = 0x00
    chip.op_ld_dt_vx(0x3)
    assert chip.dt == 0x7D

def test_ld_st_vx_sets_sound_timer(chip):
    # FX18: sound timer should be set to the value in Vx
    chip.regs[0x4] = 0xA5
    chip.st = 0x00
    chip.op_ld_st_vx(0x4)
    assert chip.st == 0xA5

def test_add_i_vx_basic(chip):
    # FX1E: I should increase by Vx without wrapping when within 12-bit range
    chip.I = 0x100
    chip.regs[0x2] = 0x20
    chip.op_add_i_vx(0x2)
    assert chip.I == 0x120

def test_add_i_vx_wraps_12bit(chip):
    # FX1E: I should wrap around modulo 0x1000 when I + Vx == 0x1000
    chip.I = 0xFFF
    chip.regs[0x3] = 0x1
    chip.op_add_i_vx(0x3)
    assert chip.I == (0xFFF + 0x1) & 0xFFF  # 0x1000 wraps to 0x000

def test_ld_f_vx_zero(chip):
    # FX29: I should point to FONT_START when Vx is 0
    chip.regs[0x0] = 0x0
    chip.I = 0x000
    chip.op_ld_f_vx(0x0)
    assert chip.I == chip.FONT_START + (0x0 * 5)

def test_ld_f_vx_middle_digit(chip):
    # FX29: I should point 5 bytes in when Vx is 5
    chip.regs[0x5] = 0x5
    chip.I = 0x000
    chip.op_ld_f_vx(0x5)
    assert chip.I == chip.FONT_START + (0x5 * 5)

def test_ld_f_vx_max_digit(chip):
    # FX29: I should point to the last font sprite when Vx is F (15)
    chip.regs[0xF] = 0xF
    chip.I = 0x000
    chip.op_ld_f_vx(0xF)
    assert chip.I == chip.FONT_START + (0xF * 5)

def test_ld_b_vx_stores_bcd(chip):
    # Test Fx33: BCD conversion of Vx into memory at I, I+1, I+2
    chip.I = 0x300
    chip.regs[0x2] = 254  # 254 -> digits 2, 5, 4
    chip.op_ld_b_vx(0x2)
    assert chip.mem[0x300] == 2
    assert chip.mem[0x301] == 5
    assert chip.mem[0x302] == 4

def test_ld_i_vx_stores_registers_in_memory(chip):
    # Test Fx55: store V0 through Vx into memory starting at I
    chip.I = 0x400
    chip.regs[0x0], chip.regs[0x1], chip.regs[0x2], chip.regs[0x3] = 1, 2, 3, 4
    chip.op_ld_i_vx(3)
    assert chip.mem[0x400] == 1
    assert chip.mem[0x401] == 2
    assert chip.mem[0x402] == 3
    assert chip.mem[0x403] == 4

def test_ld_i_vx_overflow_raises(chip):
    # Overflow if I + x >= MEM_SIZE
    chip.I = chip.MEM_SIZE - 2
    with pytest.raises(RuntimeError):
        chip.op_ld_i_vx(chip.MEM_SIZE)

def test_ld_vx_i_loads_memory_into_registers(chip):
    # Test Fx65: load V0 through Vx from memory starting at I
    chip.I = 0x500
    chip.mem[0x500] = 9
    chip.mem[0x501] = 8
    chip.mem[0x502] = 7
    chip.op_ld_vx_i(2)
    assert chip.regs[0x0] == 9
    assert chip.regs[0x1] == 8
    assert chip.regs[0x2] == 7