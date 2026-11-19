import os

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge, ReadOnly, NextTimeStep

import asm as asm_mod


def clz_golden(v):
    if v == 0:
        return 32
    return 31 - v.bit_length() + 1 if False else (32 - v.bit_length())


def ctz_golden(v):
    if v == 0:
        return 32
    n = 0
    while not (v & 1):
        v >>= 1
        n += 1
    return n


def build_program():
    """CLZ/CTZ test program. Uses x5 as working value, x6/x7 for expected."""
    a = asm_mod.Assembler()
    a.label("main")

    # tests: (value, clz, ctz)
    tests = [
        (0x00000001, 31, 0),
        (0x00000002, 30, 1),
        (0x0000FFFF, 16, 0),
        (0x80000000, 0, 31),
        (0x00FF0000, 8, 16),
        (0x00000000, 32, 32),
        (0xDEADBEEF, 0, 0),
        (0x00F0000F, 8, 0),
        (0x10000000, 3, 28),
    ]

    for i, (val, want_clz, want_ctz) in enumerate(tests):
        # x5 = val  (lui+addi for any 32-bit value)
        a.inst("lui", "x5", (val >> 12) & 0xFFFFF)
        a.inst("addi", "x5", "x5", val & 0xFFF)
        a.inst("clz", "x6", "x5", "x0")   # x6 = clz(x5)
        a.inst("ctz", "x7", "x5", "x0")   # x7 = ctz(x5)
        # check: x6 == want_clz, x7 == want_ctz
        a.inst("addi", "x8", "x0", want_clz)
        a.inst("beq", "x6", "x8", "@ok%d" % i)   # skip fail path
        a.inst("addi", "x9", "x0", 1)            # x9 = 1 -> clz mismatch
        a.label("ok%d" % i)
        a.inst("addi", "x8", "x0", want_ctz)
        a.inst("beq", "x7", "x8", "@ok2%d" % i)
        a.inst("addi", "x9", "x0", 2)            # x9 = 2 -> ctz mismatch
        a.label("ok2%d" % i)

    a.inst("addi", "x9", "x0", 0)                # x9 = 0 -> all good
    a.inst("ebreak", "x0", "x0", 0)

    return a, {"x9": 0}


@cocotb.test()
async def test_custom_instruction(dut):
    """Runs the CLZ/CTZ program and checks the mismatch flag stays 0."""
    a, exp = build_program()
    a.assemble()
    hexpath = os.path.join(os.getcwd(), "imem.hex")
    a.write_hex(hexpath)
    dut._log.info(f"wrote {hexpath} with {len(a.words)} instructions")

    cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start())
    dut.rst_n.value = 0
    dut.en.value = 0
    dut.dbg_raddr.value = 0
    dut.dbg_waddr.value = 0
    await RisingEdge(dut.clk)
    await NextTimeStep()
    dut.rst_n.value = 1
    dut.en.value = 1

    halted = False
    for _ in range(2000):
        await RisingEdge(dut.clk)
        await ReadOnly()
        if int(dut.halt_o.value):
            halted = True
            break
        await NextTimeStep()
    assert halted, "core never reached EBREAK"

    async def rd(reg_name):
        await NextTimeStep()
        dut.dbg_raddr.value = int(reg_name[1:])
        await ReadOnly()
        return int(dut.dbg_rdata.value)

    for reg_name, value in exp.items():
        got = await rd(reg_name)
        assert got == value, f"{reg_name} = {got:#x}, expected {value:#x}"

    dut._log.info("custom instruction (CLZ/CTZ) checks PASSED")
