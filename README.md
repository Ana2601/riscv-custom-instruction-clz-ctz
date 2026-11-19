# Custom instruction (CLZ/CTZ) on the RV32I core

[![CI](https://github.com/Ana2601/riscv-custom-instruction-clz-ctz/actions/workflows/ci.yml/badge.svg)](https://github.com/Ana2601/riscv-custom-instruction-clz-ctz/actions/workflows/ci.yml)

Extends the [rv32i-single-cycle-core](https://github.com/Ana2601/rv32i-single-cycle-core) RV32I core with a **custom instruction** using
RISC-V's reserved **CUSTOM-0** opcode space (0x0B), demonstrating the
standard path for adding application-specific ISA extensions.

## The custom instruction

| mnemonic | encoding                          | semantics           |
|----------|-----------------------------------|---------------------|
| `clz rd, rs1, 0` | `funct7=0x00 funct3=0 opcode=0x0B` | `rd = count_leading_zeros(rs1)`  |
| `ctz rd, rs1, 0` | `funct7=0x01 funct3=0 opcode=0x0B` | `rd = count_trailing_zeros(rs1)` |

RISC-V reserves the `CUSTOM-0`..`CUSTOM-3` opcodes (0x0B, 0x2B, 0x5B, 0x7B)
precisely so extensions like this don't collide with the base ISA. CLZ/CTZ
are the classic "worth a hardware instruction" operations (used in
allocators, hashtables, soft-float normalization) - they are in the B
extension for exactly this reason.

## How it was added

1. **Decode**: `is_clz` / `is_ctz` combinational signals in `rv32i_core.sv`
   match `opcode==0x0B, funct3==0, funct7=={0,1}`.
2. **Datapath**: two small always_comb loops scan the operand bit-by-bit.
   (A real implementation would use a tree/priority encoder; this keeps the
   RTL readable for the demo.)
3. **Writeback**: `wb_data` muxes the CLZ/CTZ result when the custom opcode
   is active; `wb_we` already excludes only stores/branches/ebreak.
4. **Assembler**: `clz`/`ctz` added to `tb/asm.py` (R-type, funct7 field).

No change to any base instruction encoding - the extension is fully
backward-compatible with RV32I.

## Verification

`tb/test_custom_instr.py` assembles a 92-instruction program that runs 9
CLZ/CTZ vectors covering edge cases (0x0, 0x1, 0x80000000, 0xDEADBEEF,
leading/trailing bit positions), checks both results against branch-based
golden compares, and uses a mismatch flag register (`x9`) that must stay 0.

```
** TESTS=1 PASS=1 FAIL=0 SKIP=0
custom instruction (CLZ/CTZ) checks PASSED
```

## Layout

```
src/rv32i_core.sv        core with CLZ/CTZ extension (fork of rv32i-single-cycle-core)
tb/asm.py                assembler with clz/ctz support
tb/test_custom_instr.py  9-vector CLZ/CTZ test (cocotb + Verilator)
run_sim.sh / Makefile    one-command flow
```

## Run

```bash
./run_sim.sh
```


## Next (FPGA host)

- Re-express the accelerator as a **CV-X-IF** coprocessor (vendor-neutral
  tightly-coupled-accelerator interface) and verify on M1.
- Take the CV-X-IF platform to build on **CVA6 / Alveo U250** (official
  X-interface platform) for a real-hardware demonstration.

## Setup

- [OSS CAD Suite](https://github.com/YosysHQ/oss-cad-suite-build) (Icarus Verilog, Verilator, Yosys)
- Python packages: `pip install -r requirements.txt`

```bash
./run_sim.sh
```

The same commands run in CI on every push (`.github/workflows/ci.yml`).
