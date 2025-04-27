import importlib.util
import os
import pytest

# Dynamically load the chip-8 module from chip-8.py
spec = importlib.util.spec_from_file_location(
    "chip8",
    os.path.join(os.path.dirname(__file__), "chip_8.py")
)
chip8 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(chip8)

def setup_function(function):
    """
    Reset the emulator state before each test.
    """
    # Clear memory
    chip8.mem[:] = bytearray(chip8.MEM_SIZE)
    # Clear display
    chip8.screen[:] = bytearray(chip8.SCREEN_W * chip8.SCREEN_H)
    # Reset registers
    for key in list(chip8.regs.keys()):
        if key.startswith('V'):
            chip8.regs[key] = 0
    chip8.regs['I'] = 0
    chip8.regs['PC'] = 0x200

def test_clear_display():
    # Fill display with non-zero values, then clear
    chip8.screen[:] = bytearray([1] * len(chip8.screen))
    chip8.op_disp_clear()
    assert all(pixel == 0 for pixel in chip8.screen), "Display was not cleared properly"

def test_ld_vx_byte():
    # Test loading different register values
    chip8.op_ld_vx_byte(5, 0xAB)
    assert chip8.regs['V5'] == 0xAB
    chip8.op_ld_vx_byte(0xF, 0x01)
    assert chip8.regs['VF'] == 0x01

def test_add_vx_byte_without_wrap():
    # Test add without wrap-around
    chip8.regs['V2'] = 0x10
    chip8.op_add_vx_byte(2, 0x20)
    assert chip8.regs['V2'] == 0x30

def test_add_vx_byte_with_wrap():
    # Test add with wrap-around over 0xFF
    chip8.regs['V2'] = 0xF0
    chip8.op_add_vx_byte(2, 0x20)
    assert chip8.regs['V2'] == (0xF0 + 0x20) & 0xFF

def test_jump_to_addr():
    # Test jump sets PC correctly (masking to 12 bits)
    chip8.op_jump_to_addr(0x345)
    assert chip8.regs['PC'] == 0x345 & 0xFFF
    chip8.op_jump_to_addr(0x1234)
    assert chip8.regs['PC'] == 0x234  # high nibble masked off

def test_step_sequence():
    # Test step() executes a small program: LD V0,1 then HALT
    # Program: 0x60 0x01, 0xFF 0xFF
    addr = chip8.regs['PC']
    chip8.mem[addr:addr+4] = bytes([0x60, 0x01, 0xFF, 0xFF])
    # First step: should load V0 and continue
    cont = chip8.step()
    assert cont is True
    assert chip8.regs['V0'] == 0x01
    # Second step: should halt and return False
    cont = chip8.step()
    assert cont is False


def test_ld_i_addr():
    # Test loading address into I register
    chip8.op_ld_i_addr(0x200)
    assert chip8.regs['I'] == 0x200
    # Test loading a different address
    chip8.op_ld_i_addr(0xABC)
    assert chip8.regs['I'] == 0xABC


def test_draw_sprite_no_collision():
    chip8.regs['I'] = 0x300
    chip8.mem[0x300] = 0b10000001
    chip8.regs['V0'] = 2
    chip8.regs['V1'] = 3
    chip8.op_drw_vx_vy_n(0, 1, 1)
    assert chip8.regs['VF'] == 0
    idx1 = 3 * chip8.SCREEN_W + 2
    idx2 = 3 * chip8.SCREEN_W + 9
    assert chip8.screen[idx1] == 1
    assert chip8.screen[idx2] == 1


def test_draw_sprite_with_collision():
    chip8.regs['I'] = 0x310
    chip8.mem[0x310] = 0b11110000
    chip8.regs['V2'] = 5
    chip8.regs['V3'] = 5
    chip8.op_drw_vx_vy_n(2, 3, 1)
    assert chip8.regs['VF'] == 0
    chip8.op_drw_vx_vy_n(2, 3, 1)
    assert chip8.regs['VF'] == 1
    idx = 5 * chip8.SCREEN_W + 5
    assert chip8.screen[idx] == 0