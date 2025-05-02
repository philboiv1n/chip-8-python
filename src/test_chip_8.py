# -----------------------------------------------
# CHIP-8 Python Emulator - Tests
# By Phil Boivin - 2025
# Version 0.0.9
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

@pytest.fixture(autouse=True)
def reset_chip8_state():
    # Clear memory and screen
    chip8.mem[:] = bytearray(chip8.MEM_SIZE)
    chip8.screen[:] = bytearray(chip8.SCREEN_W * chip8.SCREEN_H)
    # Reset general registers
    for key in list(chip8.regs.keys()):
        chip8.regs[key] = 0
    chip8.regs['PC'] = 0x200
    chip8.regs['I'] = 0
    # Reset stack pointer and stack
    chip8.sp = 0
    chip8.stack[:] = [0] * len(chip8.stack)

def test_disp_clear_clears_screen():
    chip8.screen[:] = bytearray([1] * len(chip8.screen))
    chip8.op_disp_clear()
    assert all(pixel == 0 for pixel in chip8.screen)

def test_jump_to_addr_masks_address():
    chip8.op_jump_to_addr(0x1234)
    assert chip8.regs['PC'] == 0x1234 & 0xFFF

def test_call_addr_pushes_and_jumps():
    initial_pc = chip8.regs['PC']
    chip8.op_call_addr(0x300)
    assert chip8.sp == 1
    assert chip8.stack[0] == initial_pc
    assert chip8.regs['PC'] == 0x300

def test_ret_from_subroutine_pops_pc():
    chip8.stack[0] = 0x250
    chip8.sp = 1
    chip8.op_ret_from_subroutine()
    assert chip8.sp == 0
    assert chip8.regs['PC'] == 0x250

def test_se_vx_byte_skips_when_equal():
    chip8.regs['V1'] = 0xAA
    chip8.regs['PC'] = 0x200
    chip8.op_se_vx_byte('V1', 0xAA)
    assert chip8.regs['PC'] == 0x202

def test_se_vx_byte_no_skip_when_not_equal():
    chip8.regs['V1'] = 0xAB
    chip8.regs['PC'] = 0x200
    chip8.op_se_vx_byte('V1', 0xAA)
    assert chip8.regs['PC'] == 0x200

def test_sne_vx_byte_skips_when_not_equal():
    chip8.regs['V2'] = 0x01
    chip8.regs['PC'] = 0x200
    chip8.op_sne_vx_byte('V2', 0x02)
    assert chip8.regs['PC'] == 0x202

def test_sne_vx_byte_no_skip_when_equal():
    chip8.regs['V2'] = 0x02
    chip8.regs['PC'] = 0x200
    chip8.op_sne_vx_byte('V2', 0x02)
    assert chip8.regs['PC'] == 0x200

def test_se_vx_vy_skips_when_equal():
    chip8.regs['V3'] = 0x05
    chip8.regs['V4'] = 0x05
    chip8.regs['PC'] = 0x200
    chip8.op_se_vx_vy('V3', 'V4')
    assert chip8.regs['PC'] == 0x202

def test_se_vx_vy_no_skip_when_not_equal():
    chip8.regs['V3'] = 0x05
    chip8.regs['V4'] = 0x06
    chip8.regs['PC'] = 0x200
    chip8.op_se_vx_vy('V3', 'V4')
    assert chip8.regs['PC'] == 0x200

def test_ld_vx_byte_sets_register():
    chip8.op_ld_vx_byte('V5', 0xAB)
    assert chip8.regs['V5'] == 0xAB

def test_add_vx_byte_wraps():
    chip8.regs['V5'] = 0xF0
    chip8.op_add_vx_byte('V5', 0x20)
    assert chip8.regs['V5'] == (0xF0 + 0x20) & 0xFF

def test_ld_vx_vy_copies_register():
    chip8.regs['V6'] = 0x3C
    chip8.op_ld_vx_vy('V7', 'V6')
    assert chip8.regs['V7'] == 0x3C

def test_or_and_xor_and_vx_vy_logical_ops():
    chip8.regs['V8'] = 0x0F
    chip8.regs['V9'] = 0xF0
    # OR
    chip8.op_or_vx_vy('V8', 'V9')
    assert chip8.regs['V8'] == (0x0F | 0xF0)
    # AND
    chip8.regs['V8'] = 0x0F
    chip8.op_and_vx_vy('V8', 'V9')
    assert chip8.regs['V8'] == (0x0F & 0xF0)
    # XOR
    chip8.regs['V8'] = 0x0F
    chip8.op_xor_vx_vy('V8', 'V9')
    assert chip8.regs['V8'] == (0x0F ^ 0xF0)

def test_add_vx_vy_sets_carry_flag():
    chip8.regs['VA'] = 0xFF
    chip8.regs['VB'] = 0x01
    chip8.regs['VF'] = 0
    chip8.op_add_vx_vy('VA', 'VB')
    assert chip8.regs['VF'] == 1
    assert chip8.regs['VA'] == 0x00

def test_add_vx_vy_no_carry_flag():
    chip8.regs['VA'] = 0x01
    chip8.regs['VB'] = 0x01
    chip8.regs['VF'] = 1
    chip8.op_add_vx_vy('VA', 'VB')
    assert chip8.regs['VF'] == 0

def test_ld_i_addr_sets_index_register():
    chip8.op_ld_i_addr(0x123)
    assert chip8.regs['I'] == 0x123

def test_drw_vx_vy_n_draw_and_collision():
    # prepare two-line sprite
    chip8.regs['I'] = 0x300
    chip8.mem[0x300] = 0b11000000
    chip8.mem[0x301] = 0b00110000
    chip8.regs['V0'] = 0
    chip8.regs['V1'] = 0
    # first draw: no collision
    chip8.op_drw_vx_vy_n('V0', 'V1', 2)
    assert chip8.regs['VF'] == 0
    # some pixels should be set
    assert chip8.screen[0] == 1
    assert chip8.screen[1] == 1
    # Second draw at same position: pixels should toggle off
    chip8.op_drw_vx_vy_n('V0', 'V1', 2)
    assert chip8.screen[0] == 0
    assert chip8.screen[1] == 0

def test_sub_vx_vy_no_borrow():
    # When Vx > Vy, VF should be 1 and Vx = Vx - Vy.
    chip8.regs['V2'] = 0x20
    chip8.regs['V3'] = 0x10
    chip8.regs['VF'] = 0  # clear flag
    chip8.op_sub_vx_vy('V2', 'V3')
    assert chip8.regs['V2'] == 0x10
    assert chip8.regs['VF'] == 1

def test_sub_vx_vy_with_borrow():
    # When Vx < Vy, VF should be 0 and result wraps around.
    chip8.regs['V4'] = 0x05
    chip8.regs['V5'] = 0x10
    chip8.regs['VF'] = 1  # set flag to non-zero
    chip8.op_sub_vx_vy('V4', 'V5')
    assert chip8.regs['V4'] == (0x05 - 0x10) & 0xFF
    assert chip8.regs['VF'] == 0

def test_sub_vx_vy_equal():
    # When Vx == Vy, VF should be 0 and Vx becomes 0.
    chip8.regs['V6'] = 0xAB
    chip8.regs['V7'] = 0xAB
    chip8.regs['VF'] = 1
    chip8.op_sub_vx_vy('V6', 'V7')
    assert chip8.regs['V6'] == 0x00
    assert chip8.regs['VF'] == 0


def test_shr_vx_with_lsb_one():
    # When Vx is odd, VF should be set to 1 and Vx should shift right by 1
    chip8.regs['V2'] = 0x05  # binary 00000101, LSB = 1
    chip8.regs['VF'] = 0      # clear flag
    chip8.op_shr_vx('V2')
    assert chip8.regs['VF'] == 1
    assert chip8.regs['V2'] == 0x02  # 5 >> 1 = 2

def test_shr_vx_with_lsb_zero():
    # When Vx is even, VF should be set to 0 and Vx should shift right by 1
    chip8.regs['V3'] = 0x08  # binary 00001000, LSB = 0
    chip8.regs['VF'] = 1      # set flag to non-zero
    chip8.op_shr_vx('V3')
    assert chip8.regs['VF'] == 0
    assert chip8.regs['V3'] == 0x04  # 8 >> 1 = 4

def test_shr_vx_zero_result():
    # Shifting a 1 results in zero and VF should capture the 1 bits
    chip8.regs['V4'] = 0x01  # binary 00000001, LSB = 1
    chip8.regs['VF'] = 0
    chip8.op_shr_vx('V4')
    assert chip8.regs['VF'] == 1
    assert chip8.regs['V4'] == 0x00  # 1 >> 1 = 0

# SUBN Vx, Vy tests
def test_subn_vx_vy_no_borrow():
    # When Vy >= Vx, VF should be 1 and Vx = Vy - Vx
    chip8.regs['V2'] = 0x10
    chip8.regs['V3'] = 0x20
    chip8.regs['VF'] = 0
    chip8.op_subn_vx_vy('V2', 'V3')
    assert chip8.regs['V2'] == 0x10  # 0x20 - 0x10
    assert chip8.regs['VF'] == 1

def test_subn_vx_vy_with_borrow():
    # When Vy < Vx, VF should be 0 and result wraps around
    chip8.regs['V4'] = 0x10
    chip8.regs['V5'] = 0x05
    chip8.regs['VF'] = 1
    chip8.op_subn_vx_vy('V4', 'V5')
    assert chip8.regs['V4'] == (0x05 - 0x10) & 0xFF
    assert chip8.regs['VF'] == 0

def test_subn_vx_vy_equal():
    # When Vy == Vx, VF should be 1 and Vx becomes 0
    chip8.regs['V6'] = 0xAB
    chip8.regs['V7'] = 0xAB
    chip8.regs['VF'] = 0
    chip8.op_subn_vx_vy('V6', 'V7')
    assert chip8.regs['V6'] == 0x00
    assert chip8.regs['VF'] == 1

def test_shl_vx_msb_one():
    # When Vx’s MSB is 1, VF should be set to 1 and Vx should shift left (with wrap).
    chip8.regs['V8'] = 0x80  # binary 10000000, MSB = 1
    chip8.regs['VF'] = 0      # clear flag
    chip8.op_shl_vx('V8')
    assert chip8.regs['VF'] == 1
    # 0x80 << 1 = 0x100, masked to 8 bits gives 0x00
    assert chip8.regs['V8'] == 0x00

def test_shl_vx_msb_zero():
    # When Vx’s MSB is 0, VF should be set to 0 and Vx should shift left.
    chip8.regs['V9'] = 0x40  # binary 01000000, MSB = 0
    chip8.regs['VF'] = 1      # set flag to non-zero
    chip8.op_shl_vx('V9')
    assert chip8.regs['VF'] == 0
    # 0x40 << 1 = 0x80
    assert chip8.regs['V9'] == 0x80

def test_shl_vx_wraps():
    # Shifting 0xFF (11111111) left yields 0xFE after wrap, VF captures the old MSB.
    chip8.regs['VA'] = 0xFF  # MSB = 1
    chip8.regs['VF'] = 0
    chip8.op_shl_vx('VA')
    assert chip8.regs['VF'] == 1
    # 0xFF << 1 = 0x1FE masked to 0xFF gives 0xFE
    assert chip8.regs['VA'] == 0xFE

def test_sne_vx_vy_skips_when_not_equal():
    # When Vx != Vy, PC should advance by 2 (skip next instruction)
    chip8.regs['V2'] = 0x05
    chip8.regs['V3'] = 0x06
    chip8.regs['PC'] = 0x200
    chip8.op_sne_vx_vy('V2', 'V3')
    assert chip8.regs['PC'] == 0x202

def test_sne_vx_vy_no_skip_when_equal():
    # When Vx == Vy, PC should not change
    chip8.regs['V4'] = 0x07
    chip8.regs['V5'] = 0x07
    chip8.regs['PC'] = 0x200
    chip8.op_sne_vx_vy('V4', 'V5')
    assert chip8.regs['PC'] == 0x200

def test_jump_v0_addr_basic():
    # When V0 is 0x10 and nnn is 0x200, PC should become 0x210 (masked to 12 bits)
    chip8.regs['V0'] = 0x10
    chip8.regs['PC'] = 0x000
    chip8.op_jump_v0_addr(0x200)
    assert chip8.regs['PC'] == (0x200 + 0x10) & 0xFFF

def test_jump_v0_addr_wraps():
    # When V0 + nnn exceeds 0xFFF, it should wrap modulo 0x1000
    chip8.regs['V0'] = 0xF00
    chip8.regs['PC'] = 0x000
    chip8.op_jump_v0_addr(0xA00)
    assert chip8.regs['PC'] == (0xA00 + 0xF00) & 0xFFF

def test_rnd_vx_masks_random(monkeypatch):
    # Monkeypatch random.getrandbits to return a known byte
    monkeypatch.setattr(chip8.random, 'getrandbits', lambda bits: 0b10101111)
    chip8.regs['V2'] = 0x00
    chip8.op_rnd_vx('V2', 0x0F)
    expected = 0b10101111 & 0x0F
    assert chip8.regs['V2'] == expected

def test_skp_vx_skips_when_key_pressed():
    # When the keypad at Vx is True, PC should advance by 2
    chip8.regs['V2'] = 0x03   # test with key index 3
    chip8.regs['PC'] = 0x200
    chip8.keypad[3] = True
    chip8.op_skp_vx('V2')
    assert chip8.regs['PC'] == 0x202

def test_skp_vx_no_skip_when_key_not_pressed():
    # When the keypad at Vx is False, PC should not change
    chip8.regs['V4'] = 0x05   # test with key index 5
    chip8.regs['PC'] = 0x200
    chip8.keypad[5] = False
    chip8.op_skp_vx('V4')
    assert chip8.regs['PC'] == 0x200

def test_sknp_vx_skips_when_key_not_pressed():
    # ExA1: Skip when the keypad at Vx is not pressed
    chip8.regs['V2'] = 0x03   # key index 3
    chip8.regs['PC'] = 0x200
    chip8.keypad[3] = False
    chip8.op_sknp_vx('V2')
    assert chip8.regs['PC'] == 0x202

def test_sknp_vx_no_skip_when_key_pressed():
    # ExA1: Do not skip when the keypad at Vx is pressed
    chip8.regs['V4'] = 0x05   # key index 5
    chip8.regs['PC'] = 0x200
    chip8.keypad[5] = True
    chip8.op_sknp_vx('V4')
    assert chip8.regs['PC'] == 0x200