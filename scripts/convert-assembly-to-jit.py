#!/usr/bin/env python3
# Copyright 2021 Google LLC
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree.
"""Converts hand written assembly (.S files) to C++ files using the JIT.

Takes a single argument, an assembly file, and prints converted output to stdout.
"""

import argparse
from collections import defaultdict
import datetime
import re
import sys
from typing import List, Tuple, Mapping

SPACES = r'\s*'
COMMA = r',' + SPACES
COMMENTS = SPACES + '((//\s+.+)|)$'
WB = r'!'

REG_NO_GROUP = r'r\d+|s\d+|d\d+|q\d+|sp|lr|pc|x\d+|(?:v\d+\.(?:\d+)?(?:d|s|h|b))'
REG = r'(' + REG_NO_GROUP + ')'
IMM_NO_GROUP = r'\d+'
IMM = r'(' + IMM_NO_GROUP + ')'
REG_LANE_NO_GROUP = r'(?:' + REG_NO_GROUP + r')\[' + IMM_NO_GROUP + r'\]'
REG_OR_IMM = r'(' + REG_LANE_NO_GROUP + '|' + REG_NO_GROUP + '|' + IMM_NO_GROUP + ')'

REGLIST_CONSEC = r'\{(\w+)-(\w+)\}' + SPACES
REGLIST_INDIV = r'\{([\w.]+(?:,\s+[\w.]+)*)\}' + SPACES
REGLIST_INDIV_REPLICATE = r'\{(\w+(?:\[\])(,\s*\w+(?:\[\]))*)\}' + SPACES
REGLIST_INDEX = r'\{(' + REG_LANE_NO_GROUP + ')\}' + SPACES

APSR = 'APSR_nzcv'
FPSCR = '(FPSCR)'

MEMOP = r'\[' + SPACES + REG + '\]' + SPACES
MEMOP_MAYBE_WB = r'\[' + SPACES + REG + '\]' + f'({WB})?'
MEMOP_OFFSET = r'\[' + REG + COMMA + '(-?\d+)\]' + SPACES
MEMOP_OFFSET_MAYBE_WB = r'\[' + REG + COMMA + '(-?\d+)\]' + f'({WB})?' + SPACES

B_IMM = r'(\d+)(f|b)'

INSTR = SPACES + r'([A-Z0-9.]+)' + SPACES

# e.g. #ifndef __APPLE__
IFDEF_RE = re.compile(r'\s*#(ifndef|endif|ifdef).*')
# e.g. # Push 96 bytes
COMMENT_RE = re.compile(SPACES + r'((//|#)\s*.+)')
# e.g. 0:
LABEL = re.compile(r'(\w+):')
# e.g. NOP
INSTR_RE = re.compile(INSTR + COMMENTS)
# e.g. VPUSH {d8-d15}
INSTR_REGLIST_CONSEC_RE = re.compile(INSTR + REGLIST_CONSEC + COMMENTS)
# e.g. PUSH {r4, r5}
INSTR_REGLIST_LIST_RE = re.compile(INSTR + REGLIST_INDIV + COMMENTS)
# e.g. BX lr
INSTR_OP_RE = re.compile(INSTR + REG + COMMENTS)
# e.g. BLO 2f
INSTR_B_IMM = re.compile(INSTR + B_IMM + COMMENTS)
# e.g. TBNZ x0, 4, 5f
INSTR_B_REG_IMM_IMM = re.compile(INSTR + REG + COMMA + IMM + COMMA + B_IMM + COMMENTS)
# e.g. .p2align 3
P2ALIGN_RE = re.compile(SPACES + r'\.p2align\s+(\d+)')
# e.g. CMP r0, 2
INSTR_REG_IMM_RE = re.compile(INSTR + REG + COMMA + IMM + COMMENTS)
# e.g. LDR r0, [r12]
INSTR_REG_MEMOP_RE = re.compile(INSTR + REG + COMMA + MEMOP + COMMENTS)
# e.g. LDR q0, [x4], 16
INSTR_REG_MEMOP_IMM_RE = re.compile(INSTR + REG + COMMA + MEMOP + COMMA + IMM + COMMENTS)
# e.g. LDR r0, [sp, 112], STR x20, [sp, -80]!
INSTR_REG_MEMOP_OFFSET_RE = re.compile(INSTR + REG + COMMA + MEMOP_OFFSET_MAYBE_WB +
                                       COMMENTS)
# e.g. LDRD r6, r7, [sp]
INSTR_REG_REG_MEMOP_RE = re.compile(INSTR + REG + COMMA + REG + COMMA +
                                           MEMOP + COMMENTS)
# e.g. LDRD r6, r7, [sp, 104], STP d8, d9, [sp, -64]!
INSTR_REG_REG_MEMOP_OFFSET_RE = re.compile(INSTR + REG + COMMA + REG + COMMA +
                                           MEMOP_OFFSET_MAYBE_WB + COMMENTS)
# e.g. LDP q20, q21, [x5], 32
INSTR_REG_REG_MEMOP_IMM_RE = re.compile(INSTR + REG + COMMA + REG + COMMA +
                                           MEMOP + COMMA + IMM + COMMENTS)
# e.g. PLD [r4, 64]
INSTR_MEMOP_OFFSET_RE = re.compile(INSTR + MEMOP_OFFSET + COMMENTS)
# e.g. movlo r12, r3, vdup.32 q0, d14[0]
INSTR_REG_REG_RE = re.compile(INSTR + REG + COMMA + REG_OR_IMM + COMMENTS)
# e.g. SUBS r5, r2, 16 or SUBS r5, r2, r10 or VMLFA.F32 q8, q4, d0[0]
INSTR_REG_REG_REG_RE = re.compile(INSTR + REG + COMMA + REG + COMMA +
                                  REG_OR_IMM + COMMENTS)
# e.g. VEXT.8  q0, q0, q0, 4
INSTR_REG_REG_REG_IMM_RE = re.compile(INSTR + REG + COMMA + REG + COMMA + REG +
                                      COMMA + IMM + COMMENTS)
# e.g. VST1.32 {d16}, [r11], r0
INSTR_REGLIST_INDIV_MEMOP_REG = re.compile(INSTR + REGLIST_INDIV + COMMA +
                                           MEMOP + COMMA + REG + COMMENTS)
# e.g. VST1.32 {d16-d19}, [r11], r0
INSTR_REGLIST_CONSEC_MEMOP_REG = re.compile(INSTR + REGLIST_CONSEC + COMMA +
                                            MEMOP + COMMA + REG + COMMENTS)
# e.g. VLDM r9, {d16-d19}
INSTR_REG_REGLIST_CONSECT = re.compile(INSTR + REG + COMMA + REGLIST_CONSEC +
                                       COMMENTS)
# e.g. VLDM r9!, {d16-d19}
INSTR_REG_REGLIST_CONSECT_WB = re.compile(INSTR + REG + WB + COMMA +
                                          REGLIST_CONSEC + COMMENTS)
# e.g. VLDM r9!, {d16}
INSTR_REG_REGLIST_INDIV_WB = re.compile(INSTR + REG + WB + COMMA +
                                        REGLIST_INDIV + COMMENTS)
# e.g. VLD1.32 {d0}, [r3]{!}
INSTR_REGLIST_INDIV_MEMOP = re.compile(INSTR + REGLIST_INDIV + COMMA +
                                       MEMOP_MAYBE_WB + COMMENTS)
# e.g. LD1 {v16.16b, v17.16b, v18.16b}, [x5], 48
INSTR_REGLIST_INDIV_MEMOP_IMM = re.compile(INSTR + REGLIST_INDIV + COMMA +
                                       MEMOP + COMMA + IMM + COMMENTS)
# e.g. VST1.32 {d24-d25}, [r11]{!}
INSTR_REGLIST_CONSEC_MEMOP = re.compile(INSTR + REGLIST_CONSEC + COMMA +
                                        MEMOP_MAYBE_WB + COMMENTS)
# e.g. VLD1.32 {d0[]}, [r3]!
INSTR_REGLIST_REPLICATE_MEMOP = re.compile(INSTR + REGLIST_INDIV_REPLICATE +
                                           COMMA + MEMOP + r'(!)?' + COMMENTS)
# e.g. VST1.32 {d16[0]}, [r11]{!}
INSTR_REGLIST_INDEX_MEMOP = re.compile(INSTR + REGLIST_INDEX + COMMA +
                                       MEMOP_MAYBE_WB + COMMENTS)
# e.g. VMRS APSR_nzcv, FPSCR
INSTR_REG_FPSCR = re.compile(INSTR + f'({APSR}|{REG_NO_GROUP})' + COMMA +
                             FPSCR + COMMENTS)

# e.g. PRFM PLDL1KEEP, [x5]
INSTR_PLD_MEMOP = re.compile(INSTR + f'(PLDL1KEEP)' + COMMA + MEMOP + COMMENTS)
# e.g. PRFM PLDL1KEEP, [x5, 64]
INSTR_PLD_MEMOP_OFFSET = re.compile(INSTR + f'(PLDL1KEEP)' + COMMA + MEMOP_OFFSET + COMMENTS)

COND = r'([A-Z]+)'
# e.g. CSEL x9, x3, x9, LO
INSTR_REG_REG_REG_COND_RE = re.compile(INSTR + REG + COMMA + REG + COMMA + REG + COMMA + COND + COMMENTS)


def remove_brackets(s : str) -> str:
  return s.replace('[', '').replace(']', '')


def fix_replicate_instruction(s : str) -> str:
  return re.sub(r'_(\d+)', r'r_\1', s, 1)


def fix_instr_name(s : str) -> str:
  return s.lower().replace('.', '_', 2).replace('and', 'and_', 1)


def fix_comments(s : str) -> str:
  return s.replace('#', '//', 1)


def maybe_wb(wb : bool) -> str:
  return '++' if wb else ''


def fix_fn_name(name : str) -> str:
  if name.startswith('xnn_'):
    name = name[len('xnn_'):]
  # remove any type of activations from name
  if 'minmax' in name:
    name = name.replace('minmax_', '')
  return f'xnn_generate_{name}'


def remove_prfm_from_fn_name(name : str) -> str:
  assert('_prfm_' in name)
  return name.replace('prfm_', '')


def fix_regs(regs : str) -> str:
  # Vector registers with datatype need to be method calls.
  # e.g. v2.4s -> v2.v4s(), v2.s -> v2.s()
  def repl(m):
    if m.group(2):
      return f'{m[1]}v{m[2]}{m[3]}()'
    else:
      return f'{m[1]}{m[3]}()'
  return re.sub(r'(\w+\.)(\d+)?(\w+)', repl, regs)


def get_callee_saved() -> List[str]:
  return ['d8', 'd9', 'd10', 'd11', 'd12', 'd13', 'd14', 'd15',
          'x19', 'x20', 'x21', 'x22']


IGNORE_LINES = [r'\s*\.\w+']

AARCH32 = 'aarch32'
AARCH64 = 'aarch64'
GEMM = 'GEMM'
IGEMM = 'IGEMM'


# Hard-coded post operations.
# TODO(zhin): parametrize this with vector register usage mappings.
AARCH32_POST_OP = '''void Generator::perform_post_operations(
  size_t max_mr,
  size_t num_post_operations,
  const xnn_post_operation* post_operations)
{
  for (size_t i = 0; i < num_post_operations; i++) {
    switch (post_operations[i].op_type) {
      case xnn_post_operation_type_hardswish: {
        const auto sixth = q0;
        const auto three = q1;
        const auto six = q2;
        const auto zero = q3;
        vld3r_32({sixth.low(), three.low(), six.low()}, mem[r5]++);
        vmov(zero, 0);
        vmov(three.high(), three.low());
        vmov(six.high(), six.low());
        const QRegister accs[] = {q8, q9, q10, q11, q12, q13, q14, q15};
        const QRegister tmps[] = {q4, q5, q6, q7};
        f32_hardswish(sixth, three, six, zero, &accs[0], XNN_COUNT_OF(accs), &tmps[0], XNN_COUNT_OF(tmps));
        break;
      }
      default:
        XNN_UNREACHABLE;
    }
  }
}'''


AARCH64_POST_OP='''void Generator::perform_post_operations(
  size_t max_mr,
  size_t num_post_operations,
  const xnn_post_operation* post_operations)
{
  for (size_t i = 0; i < num_post_operations; i++) {
    switch (post_operations[i].op_type) {
      case xnn_post_operation_type_hardswish: {
        // Reuse A pointers (don't use v8-v15 as they are callee saved).
        const auto sixth = v0.v4s();
        const auto three = v1.v4s();
        const auto six = v2.v4s();
        const auto zero = v3.v4s();
        // v4, v5, v6, v7 available for temporaries.
        ld3r({sixth, three, six}, mem[x8]++);
        movi(zero, 0);
        const VRegister accs[] = {
          v20.v4s(), v21.v4s(), v22.v4s(), v23.v4s(),
          v24.v4s(), v25.v4s(), v26.v4s(), v27.v4s(),
          v28.v4s(), v29.v4s(), v30.v4s(), v31.v4s(),
        };
        const VRegister tmps[] = {v4.v4s(), v5.v4s(), v6.v4s(), v7.v4s()};
        f32_hardswish(sixth, three, six, zero, &accs[0], XNN_COUNT_OF(accs), &tmps[0], XNN_COUNT_OF(tmps));
        break;
      }
      default:
        XNN_UNREACHABLE;
    }
  }
}'''

def parse_prologue(input_file: str, lines: List[str], arch: str, minmax: bool,
                   kernel_type: str, prfm: bool,
                   mr: int) -> Tuple[List[str], Mapping[str, int]]:
  prologue = []
  # Whether we are in the auto-generated comment.
  in_autogen = False
  in_a_pointers = False
  # Whether we are in the comment section that lists C (output) registers.
  in_c_pointers = False
  # Whether we are in the comment section that lists vector register usage.
  in_vector_register_usage = False
  a_pointers = []
  c_pointers = []
  # Mapping from register type (A, B, or C), to the list of list of registers.
  vector_register_usage = defaultdict(list)
  # Mapping from vector registers to their row index (in MR).
  vector_register_map = {}

  for line in lines:
    if 'Auto-generated file' in line:
      in_autogen = True
      continue
    elif line.startswith('.syntax'):
      continue
    elif 'BEGIN_FUNCTION' in line:
      prologue.append(f'// Converted from: {input_file[20:]}')
      params = 'const jit_gemm_params* jit_gemm_params'
      prefetch = 'bool prefetch, ' if prfm else ''
      if kernel_type == GEMM:
        prologue.append(
            f'void Generator::generate({prefetch}size_t max_mr, size_t nc_mod_nr, size_t kc, {params})'
        )
        prologue.append('{')
      else:
        prologue.append(
            f'void Generator::generate({prefetch}size_t max_mr, size_t nc_mod_nr, size_t kc, size_t ks, {params})'
        )
        prologue.append('{')
      continue
    elif 'Copyright ' in line:
      in_autogen = False
      # replace year
      prologue.append(
          re.sub(r'\d{4}', str(datetime.date.today().year), line, 1).rstrip())
      continue
    elif '#include <xnnpack/assembly.h>' in line:
      prologue.append(f'#include <cassert>')
      prologue.append(f'#include <cstddef>')
      if minmax:
        prologue.append(f'#include <limits>')
      prologue.append('')
      prologue.append('#include <xnnpack.h>')
      prologue.append(f'#include <xnnpack/{arch}-assembler.h>')
      if kernel_type == GEMM:
        prologue.append('#include <xnnpack/gemm.h>')
      else:
        prologue.append('#include <xnnpack/igemm.h>')
      prologue.append('#include <xnnpack/memory.h>')
      prologue.append('#include <xnnpack/microparams.h>')
      prologue.append('#include <xnnpack/post-operation.h>')
      prologue.append('')
      prologue.append('namespace xnnpack {')
      prologue.append(f'namespace {arch} {{')
      prologue.append('namespace {')
      prologue.append('class Generator : public MacroAssembler {')
      prologue.append('  using MacroAssembler::MacroAssembler;')
      prologue.append('')
      prologue.append(' public:')
      params = 'float min, float max' if minmax else 'void* params'
      params = 'const jit_gemm_params* jit_gemm_params'
      prefetch = 'bool prefetch, ' if prfm else ''
      if kernel_type == GEMM:
        prologue.append(
            f'  void generate({prefetch}size_t max_mr, size_t nc_mod_nr, size_t kc, {params});'
        )
      else:
        prologue.append(
            f'  void generate({prefetch}size_t max_mr, size_t nc_mod_nr, size_t kc, size_t ks, {params});'
        )

      prologue.append('  void perform_post_operations(size_t max_mr, size_t num_post_operations, const xnn_post_operation* post_operations);');
      prologue.append('};')
      continue
    elif in_a_pointers:
      prologue.append(fix_comments(line.rstrip()))
      if not line.strip():
        in_a_pointers = False
        continue
      m = re.search(r'(?:#|//)\W+(\w\d+)', line)
      if not m:
        print(f'ERROR expected to find A pointers: {line}', file=sys.stderr)
        sys.exit(1)
      a_pointers.append(m.group(1))
      continue
    elif 'A pointers' in line:
      prologue.append(fix_comments(line.rstrip()))
      in_a_pointers = True
      continue
    elif in_c_pointers:
      prologue.append(fix_comments(line.rstrip()))
      if not line.strip():
        in_c_pointers = False
        continue
      m = re.search(r'(?:#|//)\W+(\w\d+)', line)
      if not m:
        print(f'ERROR expected to find C pointers: {line}', file=sys.stderr)
        sys.exit(1)
      c_pointers.append(m.group(1))
      continue
    elif 'C pointers' in line:
      prologue.append(fix_comments(line.rstrip()))
      in_c_pointers = True
      continue
    elif in_vector_register_usage:
      prologue.append(fix_comments(line.rstrip()))
      if line.strip() == '':
        in_vector_register_usage = False
        continue
      if 'clamp' in line.lower() or 'unused' in line.lower():
        continue
      # Skip b vector registers.
      if re.search(r'(?:#|//)\W+B', line):
        continue
      m = re.search(r'(?:#|//)\W+(A|C)\d?\W+(((?:v|d|q|r)\d+(?:\W*|-))+)', line)
      if not m:
        print(
            f'ERROR failed to parse vector register usage: {line}',
            file=sys.stderr)
        sys.exit(1)
      param_reg = m.group(1)
      vec_regs = m.group(2).split()
      vector_register_usage[param_reg].append(vec_regs)
      continue
    elif 'register usage' in line.lower():
      prologue.append(fix_comments(line.rstrip()))
      in_vector_register_usage = True
      continue
    elif any(re.fullmatch(p, line) for p in IGNORE_LINES):
      continue
    elif in_autogen:
      continue
    else:
      prologue.append(fix_comments(line.rstrip()))
      continue

  # check that number of registers matches mr
  if a_pointers and len(a_pointers) != int(mr):
    print(f'len(a_pointers) {len(a_pointers)} != mr {mr}', file=sys.stderr)
    sys.exit(1)
  if c_pointers and len(c_pointers) != int(mr):
    print('len(c_pointers) != mr', file=sys.stderr)
    sys.exit(1)

  for i, v in enumerate(a_pointers):
    vector_register_map[v] = i
  for i, v in enumerate(c_pointers):
    vector_register_map[v] = i

  for reg_alphabet, v in vector_register_usage.items():
    for i, _ in enumerate(v):
      for j, _ in enumerate(v[i]):
        # register maps specify v registers, but we sometimes refer to the q/s/d registers as well.
        regs = v[i][j].split('-')
        for reg in regs:
          vector_register_map[reg] = i
          vector_register_map[reg.replace('v', 'q')] = i
          vector_register_map[reg.replace('v', 's')] = i
          vector_register_map[reg.replace('v', 'd')] = i
          # TODO d registers and aarch32 should use q

  return prologue, vector_register_map


def emit_prefetch_instruction(instr : str, prfm : bool, instructions : List[str]) -> None:
  """
  Emit instructions depending on prfm.
  If prfm is True, guard instruction behind a prefetch check.
  instr should be the generated prefetch instruction (not the assembly instruction).
  """
  if prfm:
    instructions.append(f'if (prefetch) {{ {instr} }}')


def emit_clamp_instruction(instr : str, instructions : List[str]) -> None:
  """
  Guard fmax/fmin instructions behind a clamp_min/clamp_max check.
  """
  if 'fmax' in instr or 'vmax' in instr:
    instructions.append(f'if (clamp_min) {{ {instr} }}')
  elif 'fmin' in instr or 'vmin' in instr:
    instructions.append(f'if (clamp_max) {{ {instr} }}')
  else:
    instructions.append(instr)


def emit_instruction(instr: str, instructions: List[str],
                     vector_register_map: Mapping[str, int]) -> None:
  # emit a guard for instruction if it is using a particular register
  # mapping is a map from register to the mr it is used, e.g. v0 -> 0 to guard v0 behind max_mr > 0.
  # parse the dest register from this instruction
  pat = re.compile(r'(\w+)\(\{?((?:v|x|q|s|d|r)\d+)')
  m = re.search(pat, instr)
  if not m:
    instructions.append(instr)
    return

  instr_name = m.group(1)
  reg = m.group(2)

  if instr_name in ['fmin', 'fmax', 'vmin_f32', 'vmax_f32']:
    max_mr = vector_register_map[reg]
    if (max_mr == 0):
      return emit_clamp_instruction(instr, instructions)
    else:
      return emit_clamp_instruction(
          f'if (max_mr > {max_mr}) {{ {instr.rstrip()} }}', instructions)

  if instr_name == 'ld2r' or instr_name == 'vld1r_32':  # loading min/max
    instructions.append(f'if (clamp_min || clamp_max) {{ {instr} }}')
    return

  if ((instr_name == 'stp' or instr_name == 'ldp') and
      reg in get_callee_saved()
     ):  # pushing and popping from stack, no max_mr guard.
    instructions.append(instr)
    return

  cmp_m = re.search(r'cmp\((?:x|r)0, (\d+)\);', instr)
  if cmp_m:
    instructions.append(f'if (max_mr > {int(cmp_m[1])-1}) {{ {instr} }}')
    return

  if instr_name == 'push' or instr_name == 'pop':
    instructions.append(instr)
    return

  if 'mem[sp' in instr: # loading from stack is almost always a parameter load.
    instructions.append(instr)
    return

  if '// ks -= MR' in instr or '// a += MR' in instr:
    # Rewrite based on max_mr (since the actual number depends on max_mr).
    instructions.append(
        re.sub(r'(add|subs)\((\w\d+), (\w\d+), (\d+)\);',
               r'\1(\2, \3, max_mr * sizeof(void*));',
               instr))
    return

  if reg not in vector_register_map:
    instructions.append(instr)
    return

  max_mr = vector_register_map[reg]
  if (max_mr == 0):
    instructions.append(instr)
    return

  instructions.append(f'if (max_mr > {max_mr}) {{ {instr} }}')


def parse_microkernel(
    lines: List[str], prfm: bool,
    vector_register_map: Mapping[str, int]) -> Tuple[List[str], List[str]]:
  # All labels need to be declared first, collect them and output them after
  # function signature.
  labels = []
  sc = ';'
  instructions = []
  for line in lines:
    # We are now in the microkernel function body.
    # Don't keep the ifdefs.
    m = re.fullmatch(IFDEF_RE, line)
    if m:
      continue
    # But keep other comments.
    m = re.fullmatch(COMMENT_RE, line)
    if m:
      emit_instruction(m[1], instructions, vector_register_map)
      continue

    m = re.fullmatch(LABEL, line)
    if m:
      labels.append(m[1])
      instructions.append(f'bind(l{m[1]}){sc}')
      continue
    m = re.fullmatch(INSTR_RE, line)
    if m:
      emit_instruction(f'{fix_instr_name(m[1])}(){sc} {m[2]}', instructions,
                       vector_register_map)
      continue
    m = re.fullmatch(INSTR_OP_RE, line)
    if m:
      emit_instruction(f'{fix_instr_name(m[1])}({m[2]}){sc} {m[3]}',
                       instructions, vector_register_map)
      continue
    m = re.fullmatch(INSTR_REGLIST_CONSEC_MEMOP_REG, line)
    if m:
      emit_instruction(
          f'{fix_instr_name(m[1])}({{{m[2]}-{m[3]}}}, mem[{m[4]}], {m[5]}){sc} {m[6]}',
          instructions, vector_register_map)
      continue
    m = re.fullmatch(INSTR_REGLIST_INDIV_MEMOP_REG, line)
    if m:
      emit_instruction(
          f'{fix_instr_name(m[1])}({{{fix_regs(m[2])}}}, mem[{m[3]}], {m[4]}){sc} {m[5]}',
          instructions, vector_register_map)
      continue
    m = re.fullmatch(INSTR_REGLIST_CONSEC_RE, line)
    if m:
      emit_instruction(f'{fix_instr_name(m[1])}({{{m[2]}-{m[3]}}}){sc} {m[4]}',
                       instructions, vector_register_map)
      continue
    m = re.fullmatch(INSTR_REGLIST_LIST_RE, line)
    if m:
      emit_instruction(f'{fix_instr_name(m[1])}({{{m[2]}}}){sc} {m[3]}',
                       instructions, vector_register_map)
      continue
    m = re.fullmatch(INSTR_MEMOP_OFFSET_RE, line)
    if m:
      if m[1].lower() == 'pld':
        emit_prefetch_instruction(
          f'{fix_instr_name(m[1])}(mem[{m[2]}, {m[3]}]){sc} {m[4]}',
          prfm, instructions)
      else:
        emit_instruction(
            f'{fix_instr_name(m[1])}(mem[{m[2]}, {m[3]}]){sc} {m[4]}',
            instructions, vector_register_map)
      continue
    m = re.fullmatch(INSTR_REG_MEMOP_RE, line)
    if m:
      emit_instruction(
          f'{fix_instr_name(m[1])}({m[2]}, mem[{m[3]}]){sc} {m[4]}',
          instructions, vector_register_map)
      continue
    m = re.fullmatch(INSTR_REG_MEMOP_IMM_RE, line)
    if m:
      emit_instruction(
          f'{fix_instr_name(m[1])}({m[2]}, mem[{m[3]}], {m[4]}){sc} {m[5]}',
          instructions, vector_register_map)
      continue
    m = re.fullmatch(INSTR_REG_MEMOP_OFFSET_RE, line)
    if m:
      if m[5]:  # wb
        emit_instruction(
            f'{fix_instr_name(m[1])}({m[2]}, mem[{m[3]}, {m[4]}]++){sc} {m[6]}',
            instructions, vector_register_map)
      else:  # no wb
        emit_instruction(
            f'{fix_instr_name(m[1])}({m[2]}, mem[{m[3]}, {m[4]}]){sc} {m[6]}',
            instructions, vector_register_map)
      continue
    m = re.fullmatch(INSTR_REG_REG_MEMOP_RE, line)
    if m:
      emit_instruction(
          f'{fix_instr_name(m[1])}({m[2]}, {m[3]}, mem[{m[4]}]){sc} {m[5]}',
          instructions, vector_register_map)
      continue
    m = re.fullmatch(INSTR_REG_REG_MEMOP_OFFSET_RE, line)
    if m:
      if m[6]:  # wb
        emit_instruction(
            f'{fix_instr_name(m[1])}({m[2]}, {m[3]}, mem[{m[4]}, {m[5]}]++){sc} {m[7]}',
            instructions, vector_register_map)
      else:  # no wb
        emit_instruction(
            f'{fix_instr_name(m[1])}({m[2]}, {m[3]}, mem[{m[4]}, {m[5]}]){sc} {m[7]}',
            instructions, vector_register_map)
      continue
    m = re.fullmatch(INSTR_REG_REG_MEMOP_IMM_RE, line)
    if m:
      emit_instruction(
          f'{fix_instr_name(m[1])}({m[2]}, {m[3]}, mem[{m[4]}], {m[5]}){sc} {m[6]}',
          instructions, vector_register_map)
      continue
    m = re.fullmatch(INSTR_REG_IMM_RE, line)
    if m:
      emit_instruction(
          f'{fix_instr_name(m[1])}({fix_regs(m[2])}, {m[3]}){sc} {m[4]}',
          instructions, vector_register_map)
      continue
    m = re.fullmatch(INSTR_REG_REG_REG_RE, line)
    if m:
      emit_instruction(
          f'{fix_instr_name(m[1])}({fix_regs(m[2])}, {fix_regs(m[3])}, {fix_regs(m[4])}){sc} {m[5]}',
          instructions, vector_register_map)
      continue
    m = re.fullmatch(INSTR_REG_REG_REG_IMM_RE, line)
    if m:
      emit_instruction(
          f'{fix_instr_name(m[1])}({m[2]}, {m[3]}, {m[4]}, {m[5]}){sc} {m[6]}',
          instructions, vector_register_map)
      continue
    m = re.fullmatch(INSTR_REG_REG_RE, line)
    if m:
      emit_instruction(
          f'{fix_instr_name(m[1])}({fix_regs(m[2])}, {fix_regs(m[3])}){sc} {m[4]}',
          instructions, vector_register_map)
      continue
    m = re.fullmatch(INSTR_REG_REGLIST_CONSECT, line)
    if m:
      emit_instruction(
          f'{fix_instr_name(m[1])}(mem[{m[2]}], {{{m[3]}-{m[4]}}}){sc} {m[5]}',
          instructions, vector_register_map)
      continue
    m = re.fullmatch(INSTR_REG_REGLIST_CONSECT_WB, line)
    if m:
      emit_instruction(
          f'{fix_instr_name(m[1])}(mem[{m[2]}]++, {{{m[3]}-{m[4]}}}){sc} {m[5]}',
          instructions, vector_register_map)
      continue
    m = re.fullmatch(INSTR_REG_REGLIST_INDIV_WB, line)
    if m:
      emit_instruction(
          f'{fix_instr_name(m[1])}(mem[{m[2]}]++, {{{m[3]}}}){sc} {m[4]}',
          instructions, vector_register_map)
      continue
    m = re.fullmatch(INSTR_B_IMM, line)
    if m:
      emit_instruction(f'{fix_instr_name(m[1])}(l{m[2]}){sc} {m[4]}',
                       instructions, vector_register_map)
      continue
    m = re.fullmatch(INSTR_B_REG_IMM_IMM, line)
    if m:
      instructions.append(
          f'{fix_instr_name(m[1])}({m[2]}, {m[3]}, l{m[4]}){sc} {m[6]}')
      continue
    m = re.fullmatch(INSTR_REGLIST_INDIV_MEMOP, line)
    if m:
      emit_instruction(
          f'{fix_instr_name(m[1])}({{{fix_regs(m[2])}}}, mem[{m[3]}]{maybe_wb(m[4])}){sc} {m[5]}',
          instructions, vector_register_map)
      continue
    m = re.fullmatch(INSTR_REGLIST_INDIV_MEMOP_IMM, line)
    if m:
      emit_instruction(
          f'{fix_instr_name(m[1])}({{{fix_regs(m[2])}}}, mem[{m[3]}], {m[4]}){sc} {m[5]}',
          instructions, vector_register_map)
      continue
    m = re.fullmatch(INSTR_REGLIST_CONSEC_MEMOP, line)
    if m:
      emit_instruction(
          f'{fix_instr_name(m[1])}({{{m[2]}-{m[3]}}}, mem[{m[4]}]{maybe_wb(m[5])}){sc} {m[6]}',
          instructions, vector_register_map)
      continue
    m = re.fullmatch(INSTR_REGLIST_REPLICATE_MEMOP, line)
    if m:
      if m[5]:
        emit_instruction(
            f'{fix_replicate_instruction(fix_instr_name(m[1]))}({{{remove_brackets(m[2])}}}, mem[{m[4]}]++){sc} {m[6]}',
            instructions, vector_register_map)
      else:
        emit_instruction(
            f'{fix_replicate_instruction(fix_instr_name(m[1]))}({{{remove_brackets(m[2])}}}, mem[{m[4]}]){sc} {m[6]}',
            instructions, vector_register_map)
      continue
    m = re.fullmatch(INSTR_REGLIST_INDEX_MEMOP, line)
    if m:
      emit_instruction(
          f'{fix_instr_name(m[1])}({{{m[2]}}}, mem[{m[3]}]{maybe_wb(m[4])}){sc} {m[5]}',
          instructions, vector_register_map)
      continue
    m = re.fullmatch(P2ALIGN_RE, line)
    if m:
      instructions.append(f'align({1 << int(m[1])}){sc}')
      continue
    m = re.fullmatch(INSTR_REG_FPSCR, line)
    if m:
      instructions.append(f'{fix_instr_name(m[1])}({m[2]}, {m[3]}){sc} {m[4]}')
      continue
    m = re.fullmatch(INSTR_PLD_MEMOP, line)
    if m:
      emit_prefetch_instruction(
          f'{fix_instr_name(m[1])}(k{m[2]}, mem[{m[3]}]){sc} {m[4]}', prfm, instructions)
      continue
    m = re.fullmatch(INSTR_PLD_MEMOP_OFFSET, line)
    if m:
      emit_prefetch_instruction(
          f'{fix_instr_name(m[1])}(k{m[2]}, mem[{m[3]}, {m[4]}]){sc} {m[5]}', prfm, instructions)
      continue
    m = re.fullmatch(INSTR_REG_REG_REG_COND_RE, line)
    if m:
      emit_instruction(
          f'{fix_instr_name(m[1])}({m[2]}, {m[3]}, {m[4]}, k{m[5]}){sc} {m[6]}',
          instructions, vector_register_map)
      continue

    # Keep empty lines for formatting
    if line.strip() == '':
      instructions.append('')
      continue

    # Assembly directives that we don't are about.
    if line.strip().startswith('.'):
      continue

    if line.startswith('END_FUNCTION'):
      break

    # All other lines are error.
    print(f'ERROR: {line}', file=sys.stderr)
    sys.exit(1)

  return instructions, labels


def emit_instructions_with_same_check(check : str, instrs : List[str], output : List[str]) -> None:
  """
  A helper method to emit a list of instructions which share the same check.
  """
  if not instrs:
    return
  m = re.search(r'(\W*)if \(([^)]+)\) \{', instrs[0])
  indent = ''
  check = ''
  if m:
    indent = m[1]
    check = m[2]
  output.append(f'{indent}if ({check}) {{')
  for instr in instrs:
    if instr.strip().startswith('//'):  # comment line
      output.append(f'  {instr}')
      continue
    # Each instruction is of the form "if (check) { instr(); }", we only want the instr,
    # so find the opening and closing brace, and only output what's in between.
    start = instr.index('{')
    end = instr.rindex('}')
    output.append(f'  {indent}{instr[start+1:end].strip()}')
  output.append(f'{indent}}}')


def merge_consecutive_checks(instructions : List[str]) -> List[str]:
  """
  Each instruction has its own check, leading to excessive number of checks, e.g.

    if (clamp) { fmin(v0) }
    if (clamp) { fmin(v1) }
    ...
    if (clamp) { fmin(v10) }

  This walks the instructions stream, checks for consecutive checks for the same condition,
  and merge them:

    if (clamp) {
      fmin(v0);
      fmin(v1);
      ...
      fmin(v10);
  }

  This assumes that checks should be on the same line as the instruction, e.g.
  `if (clamp) { ... }`
  """
  previous_check = None
  current_check = None
  # Avoid mutating the input instructions stream, write all output to this new list.
  output = []
  # Holds the list of instructions that have the same check.
  instructions_with_same_check = []
  # cases we consider:
  # 1. Same check
  #     if (checkA) {}
  #     if (checkA) {}
  # 2. Different check
  #     if (checkA) {}
  #     if (checkB) {}
  # 3. Comment line
  #     // comment
  # 4. Everything else
  #     instruction
  for instr in instructions:
    m = re.search(r'if \(([^)]+)\) \{ .+', instr)
    if m:
      current_check = m.group(1)
      if (current_check == previous_check):
        instructions_with_same_check.append(instr)
      else:
        # Special case if the previous line is a comment.
        comment = ''
        if output and output[-1].strip().startswith('//'):
          comment = output.pop()
        elif instructions_with_same_check and instructions_with_same_check[-1].strip().startswith('//'):
          comment = instructions_with_same_check.pop()
        emit_instructions_with_same_check(previous_check, instructions_with_same_check, output)
        previous_check = current_check
        instructions_with_same_check = [instr]
        if comment:
          # Need to wrap comment with this check so that we can merge the checks correctly, this is not valid C code due
          # to the // comment, but we will remove that.
          instructions_with_same_check.insert(0, f'if ({current_check}) {{ {comment} }}')
    elif re.fullmatch(r'\W*//.+', instr) and len(
        instructions_with_same_check) != 0:  # purely comment line
      instructions_with_same_check.append(instr)
    else:
      emit_instructions_with_same_check(previous_check, instructions_with_same_check, output)
      previous_check = None
      output.append(instr)
      instructions_with_same_check = []
  return output


def insert_post_operations(instructions : List[str]):
  index = 0
  # Look for the comment marking where we store full tile, that's where we will
  # perform post operations.
  for i, l in enumerate(instructions):
    if 'Store full ' in l:
      index = i
      break
  assert(instructions[index-1].strip() == '')
  instructions.insert(
      index-1,
      "perform_post_operations(max_mr, num_post_operations, post_operations);")
  return instructions


def main(input_file : str) -> None:
  arch = None
  kernel_type = GEMM
  minmax = False
  prfm = False
  ctype = 'float'

  if 'aarch32' in input_file:
    arch = AARCH32
  elif 'aarch64' in input_file:
    arch = AARCH64
  else:
    print('ERROR: unknown architecture')
    sys.exit(1)

  if 'igemm' in input_file:
    kernel_type = IGEMM
  if 'minmax' in input_file:
    minmax = True
  if 'prfm' in input_file:
    prfm = True

  mr = 0
  nr = 0
  m = re.search(r'(\d+)x(\d+)', input_file)
  if m:
    mr = int(m[1])
    nr = int(m[2])

  # Instructions that make up the microkernel.
  instructions = []
  # Lines of code or comments before the actual function body.
  prologue = []
  # Name of the microkernel function.
  fn_name = ''

  lines = []
  with open(input_file, 'r', encoding='utf-8') as f:
    lines = f.read().splitlines()

  begin_function_index = 0
  for i, line in enumerate(lines):
    if 'BEGIN_FUNCTION' in line:
      begin_function_index = i
      break

  fn_name = lines[begin_function_index].split()[1]

  # Prologue includes the BEING_FUNCTION declaration of function name.
  prologue_lines = lines[:begin_function_index + 1]
  # Microkernel body does not include the BEGIN_FUNCION.
  microkernel_body = lines[begin_function_index + 1:]

  prologue, vector_register_map = parse_prologue(input_file, prologue_lines,
                                                 arch, minmax, kernel_type,
                                                 prfm, mr)
  instructions, labels = parse_microkernel(microkernel_body, prfm,
                                           vector_register_map)
  # TODO(zhin): iterate until fixpoint instead.
  instructions = merge_consecutive_checks(instructions)
  instructions = merge_consecutive_checks(instructions)
  instructions = insert_post_operations(instructions)

  # Actually emit the JIT codegen (to stdout).
  for p in prologue:
    print(p)

  labels_str = ', '.join(f'l{l}' for l in labels)
  print(f'  assert(max_mr <= {mr});')
  print(f'  assert(nc_mod_nr < {nr});')
  print('  assert(kc != 0);')
  print(f'  assert(kc % sizeof({ctype}) == 0);')
  if kernel_type == IGEMM:
    print('  assert(ks != 0);')
  print()
  print(f'  Label {labels_str};')
  print('  const size_t num_post_operations = jit_gemm_params->num_post_operations;')
  print('  const xnn_post_operation* post_operations = jit_gemm_params->post_operations;')
  print('  const float min = jit_gemm_params->f32_minmax.min;')
  print('  const float max = jit_gemm_params->f32_minmax.max;')
  if minmax:
    print(
        '  const bool clamp_min = min != -std::numeric_limits<float>::infinity();'
    )
    print(
        '  const bool clamp_max = max != +std::numeric_limits<float>::infinity();'
    )
    print('  assert(num_post_operations == 0 || (!clamp_min && !clamp_max));')

  indent = '  '
  for i in instructions:
    if i.strip().startswith('#'):
      print(indent + fix_comments(i))
    elif i.strip().startswith('//'):
      print(indent + i)
    elif i.strip() == '':
      print()
    else:
      print(indent + (i).rstrip())
  if arch == AARCH32:
    print(indent + 'align(16);')
  else:
    print(indent + 'align(16, AlignInstruction::kHlt);')

  print('}')
  # print post operations definition
  if arch == AARCH32:
    print()
    print(AARCH32_POST_OP)
    print()
  else:
    print()
    print(AARCH64_POST_OP)
    print()
  print('}  // namespace')
  print(f'}}  // namespace {arch}')
  print('}  // namespace xnnpack')
  print('')
  if prfm:
    print_generator_definition(kernel_type, remove_prfm_from_fn_name(fn_name), arch, minmax, prefetch='false, ')
    print()
    print_generator_definition(kernel_type, fn_name, arch, minmax, prefetch='true, ')
  else:
    print_generator_definition(kernel_type, fn_name, arch, minmax)


def print_generator_definition(kernel_type, fn_name, arch, minmax, prefetch=''):
  if kernel_type == GEMM:
    print(
        f'xnn_status_t {fix_fn_name(fn_name)}(xnn_code_buffer* code, size_t max_mr, size_t nc_mod_nr, size_t kc, const void* params) {{'
    )
  else:
    print(
        f'xnn_status_t {fix_fn_name(fn_name)}(xnn_code_buffer* code, size_t max_mr, size_t nc_mod_nr, size_t kc, size_t ks, const void* params) {{'
    )
  print(f'  using namespace xnnpack::{arch};')
  print('  Generator g(code);')
  if minmax:
    print('  assert(params != nullptr);')
  if kernel_type == GEMM:
    if minmax:
      print(f'  g.generate({prefetch}max_mr, nc_mod_nr, kc, static_cast<const jit_gemm_params*>(params));')
    else:
      print(f'  g.generate({prefetch}max_mr, nc_mod_nr, kc, nullptr);')
  else:
    if minmax:
      print(f'  g.generate({prefetch}max_mr, nc_mod_nr, kc, ks, static_cast<const jit_gemm_params*>(params));')
    else:
      print(f'  g.generate({prefetch}max_mr, nc_mod_nr, kc, ks, nullptr);')
  print('  g.finalize();')
  print('  if (g.error() != xnnpack::Error::kNoError) {')
  print('    return xnn_status_invalid_state;')
  print('  }')
  print('  return xnn_status_success;')
  print('}')


if __name__ == '__main__':
  parser = argparse.ArgumentParser(description='Convert assembly to to JIT C++, writes to stdout.')
  parser.add_argument('input_file', help='Input assembly filename')
  args = parser.parse_args()
  main(args.input_file)
