// Auto-generated file. Do not edit!
//   Template: src/f16-dwconv2d-chw/5x5p2-neonfp16arith.c.in
//   Generator: tools/xngen
//
// Copyright 2020 Google LLC
//
// This source code is licensed under the BSD-style license found in the
// LICENSE file in the root directory of this source tree.

#include <assert.h>

#include <arm_neon.h>

#include <xnnpack/dwconv.h>
#include <xnnpack/math.h>


void xnn_f16_dwconv2d_chw_ukernel_5x5p2__neonfp16arith_2x8_acc3(
    size_t input_height,
    size_t input_width,
    const void* input,
    const void* weights,
    const void* zero,
    void* output,
    uint32_t padding_top,
    const union xnn_f16_chw_params params[restrict XNN_MIN_ELEMENTS(1)]) XNN_OOB_READS
{
  assert(input_height != 0);
  assert(input_width != 0);
  assert(input_width % sizeof(__fp16) == 0);
  assert(padding_top == 2);

  const uint16x8_t vmask = vld1q_u16(params->neonfp16arith.maskx8);
  const float16x8_t vmax = vld1q_dup_f16(&params->neonfp16arith.max);
  const float16x8_t vmin = vld1q_dup_f16(&params->neonfp16arith.min);

  const __fp16* w0 = (const __fp16*)weights;
  const float16x8_t vw01234567 = vld1q_f16(w0);
  const float16x8_t vw89ABCDEF = vld1q_f16(w0 + 8);
  const float16x8_t vwGHIJKLMN = vld1q_f16(w0 + 16);
  const float16x4_t vwOP = vreinterpret_f16_u32(vld1_dup_u32((const void*)(w0 + 24)));

  const size_t input_decrement = round_up_po2(input_width, 8 * sizeof(__fp16));

  const __fp16* i0 = zero;
  const __fp16* i1 = zero;
  const __fp16* i2 = input;
  const __fp16* i3 = (const __fp16*) ((uintptr_t) i2 + input_width);
  const __fp16* i4 = (const __fp16*) ((uintptr_t) i3 + input_width);
  const __fp16* i5 = (const __fp16*) ((uintptr_t) i4 + input_width);

  __fp16* o0 = output;
  __fp16* o1 = (__fp16*) ((uintptr_t) o0 + input_width);

  size_t output_height = input_height;
  do {
    if XNN_UNPREDICTABLE(output_height < 2) {
      i3 = zero;
      o1 = o0;
    }
    if XNN_UNPREDICTABLE(output_height < 3) {
      i4 = zero;
    }
    if XNN_UNPREDICTABLE(output_height < 4) {
      i5 = zero;
    }

    float16x8_t vi0x0123 = vmovq_n_f16(0);
    float16x8_t vi1x0123 = vmovq_n_f16(0);
    float16x8_t vi2x0123 = vmovq_n_f16(0);
    float16x8_t vi3x0123 = vmovq_n_f16(0);
    float16x8_t vi4x0123 = vmovq_n_f16(0);
    float16x8_t vi5x0123 = vmovq_n_f16(0);

    float16x8_t vi0x4567 = vld1q_f16(i0); i0 += 8;
    float16x8_t vi1x4567 = vld1q_f16(i1); i1 += 8;
    float16x8_t vi2x4567 = vld1q_f16(i2); i2 += 8;
    float16x8_t vi3x4567 = vld1q_f16(i3); i3 += 8;
    float16x8_t vi4x4567 = vld1q_f16(i4); i4 += 8;
    float16x8_t vi5x4567 = vld1q_f16(i5); i5 += 8;

    size_t w = input_width;
    for (; w > 16 * sizeof(__fp16); w -= 8 * sizeof(__fp16)) {
      float16x8_t vo0p0 = vdupq_laneq_f16(vw01234567, 0);
      float16x8_t vo1p0 = vdupq_laneq_f16(vw01234567, 0);

      const float16x8_t vi0x89AB = vld1q_f16(i0); i0 += 8;
      const float16x8_t vi1x89AB = vld1q_f16(i1); i1 += 8;
      const float16x8_t vi2x89AB = vld1q_f16(i2); i2 += 8;
      const float16x8_t vi3x89AB = vld1q_f16(i3); i3 += 8;
      const float16x8_t vi4x89AB = vld1q_f16(i4); i4 += 8;
      const float16x8_t vi5x89AB = vld1q_f16(i5); i5 += 8;

      // Center column
      float16x8_t vo0p1 = vmulq_laneq_f16(vi0x4567, vw01234567, 3);
      float16x8_t vo1p1 = vmulq_laneq_f16(vi1x4567, vw01234567, 3);

      float16x8_t vo0p2 = vmulq_laneq_f16(vi1x4567, vw89ABCDEF, 0);
      float16x8_t vo1p2 = vmulq_laneq_f16(vi2x4567, vw89ABCDEF, 0);

      vo0p1 = vfmaq_laneq_f16(vo0p1, vi2x4567, vw89ABCDEF, 5);
      vo1p1 = vfmaq_laneq_f16(vo1p1, vi3x4567, vw89ABCDEF, 5);

      vo0p2 = vfmaq_laneq_f16(vo0p2, vi3x4567, vwGHIJKLMN, 2);
      vo1p2 = vfmaq_laneq_f16(vo1p2, vi4x4567, vwGHIJKLMN, 2);

      vo0p0 = vfmaq_laneq_f16(vo0p0, vi4x4567, vwGHIJKLMN, 7);
      vo1p0 = vfmaq_laneq_f16(vo1p0, vi5x4567, vwGHIJKLMN, 7);

      // Left by 1 column
      const float16x8_t vi0x3456 = vextq_f16(vi0x0123, vi0x4567, 7);
      const float16x8_t vi1x3456 = vextq_f16(vi1x0123, vi1x4567, 7);
      const float16x8_t vi2x3456 = vextq_f16(vi2x0123, vi2x4567, 7);
      const float16x8_t vi3x3456 = vextq_f16(vi3x0123, vi3x4567, 7);
      const float16x8_t vi4x3456 = vextq_f16(vi4x0123, vi4x4567, 7);
      const float16x8_t vi5x3456 = vextq_f16(vi5x0123, vi5x4567, 7);

      vo0p1 = vfmaq_laneq_f16(vo0p1, vi0x3456, vw01234567, 2);
      vo1p1 = vfmaq_laneq_f16(vo1p1, vi1x3456, vw01234567, 2);

      vo0p2 = vfmaq_laneq_f16(vo0p2, vi1x3456, vw01234567, 7);
      vo1p2 = vfmaq_laneq_f16(vo1p2, vi2x3456, vw01234567, 7);

      vo0p0 = vfmaq_laneq_f16(vo0p0, vi2x3456, vw89ABCDEF, 4);
      vo1p0 = vfmaq_laneq_f16(vo1p0, vi3x3456, vw89ABCDEF, 4);

      vo0p1 = vfmaq_laneq_f16(vo0p1, vi3x3456, vwGHIJKLMN, 1);
      vo1p1 = vfmaq_laneq_f16(vo1p1, vi4x3456, vwGHIJKLMN, 1);

      vo0p2 = vfmaq_laneq_f16(vo0p2, vi4x3456, vwGHIJKLMN, 6);
      vo1p2 = vfmaq_laneq_f16(vo1p2, vi5x3456, vwGHIJKLMN, 6);

      // Left by 2 column
      const float16x8_t vi0x2345 = vextq_f16(vi0x0123, vi0x4567, 6);
      vi0x0123 = vi0x4567;
      const float16x8_t vi1x2345 = vextq_f16(vi1x0123, vi1x4567, 6);
      vi1x0123 = vi1x4567;
      const float16x8_t vi2x2345 = vextq_f16(vi2x0123, vi2x4567, 6);
      vi2x0123 = vi2x4567;
      const float16x8_t vi3x2345 = vextq_f16(vi3x0123, vi3x4567, 6);
      vi3x0123 = vi3x4567;
      const float16x8_t vi4x2345 = vextq_f16(vi4x0123, vi4x4567, 6);
      vi4x0123 = vi4x4567;
      const float16x8_t vi5x2345 = vextq_f16(vi5x0123, vi5x4567, 6);
      vi5x0123 = vi5x4567;

      vo0p0 = vfmaq_laneq_f16(vo0p0, vi0x2345, vw01234567, 1);
      vo1p0 = vfmaq_laneq_f16(vo1p0, vi1x2345, vw01234567, 1);

      vo0p1 = vfmaq_laneq_f16(vo0p1, vi1x2345, vw01234567, 6);
      vo1p1 = vfmaq_laneq_f16(vo1p1, vi2x2345, vw01234567, 6);

      vo0p2 = vfmaq_laneq_f16(vo0p2, vi2x2345, vw89ABCDEF, 3);
      vo1p2 = vfmaq_laneq_f16(vo1p2, vi3x2345, vw89ABCDEF, 3);

      vo0p0 = vfmaq_laneq_f16(vo0p0, vi3x2345, vwGHIJKLMN, 0);
      vo1p0 = vfmaq_laneq_f16(vo1p0, vi4x2345, vwGHIJKLMN, 0);

      vo0p1 = vfmaq_laneq_f16(vo0p1, vi4x2345, vwGHIJKLMN, 5);
      vo1p1 = vfmaq_laneq_f16(vo1p1, vi5x2345, vwGHIJKLMN, 5);

      // Right by 1 column
      const float16x8_t vi0x5678 = vextq_f16(vi0x4567, vi0x89AB, 1);
      const float16x8_t vi1x5678 = vextq_f16(vi1x4567, vi1x89AB, 1);
      const float16x8_t vi2x5678 = vextq_f16(vi2x4567, vi2x89AB, 1);
      const float16x8_t vi3x5678 = vextq_f16(vi3x4567, vi3x89AB, 1);
      const float16x8_t vi4x5678 = vextq_f16(vi4x4567, vi4x89AB, 1);
      const float16x8_t vi5x5678 = vextq_f16(vi5x4567, vi5x89AB, 1);

      vo0p2 = vfmaq_laneq_f16(vo0p2, vi0x5678, vw01234567, 4);
      vo1p2 = vfmaq_laneq_f16(vo1p2, vi1x5678, vw01234567, 4);

      vo0p0 = vfmaq_laneq_f16(vo0p0, vi1x5678, vw89ABCDEF, 1);
      vo1p0 = vfmaq_laneq_f16(vo1p0, vi2x5678, vw89ABCDEF, 1);

      vo0p1 = vfmaq_laneq_f16(vo0p1, vi2x5678, vw89ABCDEF, 6);
      vo1p1 = vfmaq_laneq_f16(vo1p1, vi3x5678, vw89ABCDEF, 6);

      vo0p2 = vfmaq_laneq_f16(vo0p2, vi3x5678, vwGHIJKLMN, 3);
      vo1p2 = vfmaq_laneq_f16(vo1p2, vi4x5678, vwGHIJKLMN, 3);

      vo0p0 = vfmaq_lane_f16(vo0p0, vi4x5678, vwOP, 0);
      vo1p0 = vfmaq_lane_f16(vo1p0, vi5x5678, vwOP, 0);

      // Right by 2 column
      const float16x8_t vi0x6789 = vextq_f16(vi0x4567, vi0x89AB, 2);
      vi0x4567 = vi0x89AB;
      const float16x8_t vi1x6789 = vextq_f16(vi1x4567, vi1x89AB, 2);
      vi1x4567 = vi1x89AB;
      const float16x8_t vi2x6789 = vextq_f16(vi2x4567, vi2x89AB, 2);
      vi2x4567 = vi2x89AB;
      const float16x8_t vi3x6789 = vextq_f16(vi3x4567, vi3x89AB, 2);
      vi3x4567 = vi3x89AB;
      const float16x8_t vi4x6789 = vextq_f16(vi4x4567, vi4x89AB, 2);
      vi4x4567 = vi4x89AB;
      const float16x8_t vi5x6789 = vextq_f16(vi5x4567, vi5x89AB, 2);
      vi5x4567 = vi5x89AB;

      vo0p1 = vfmaq_laneq_f16(vo0p1, vi0x6789, vw01234567, 5);
      vo1p1 = vfmaq_laneq_f16(vo1p1, vi1x6789, vw01234567, 5);

      vo0p2 = vfmaq_laneq_f16(vo0p2, vi1x6789, vw89ABCDEF, 2);
      vo1p2 = vfmaq_laneq_f16(vo1p2, vi2x6789, vw89ABCDEF, 2);

      vo0p0 = vfmaq_laneq_f16(vo0p0, vi2x6789, vw89ABCDEF, 7);
      vo1p0 = vfmaq_laneq_f16(vo1p0, vi3x6789, vw89ABCDEF, 7);

      vo0p1 = vfmaq_laneq_f16(vo0p1, vi3x6789, vwGHIJKLMN, 4);
      vo1p1 = vfmaq_laneq_f16(vo1p1, vi4x6789, vwGHIJKLMN, 4);

      vo0p2 = vfmaq_lane_f16(vo0p2, vi4x6789, vwOP, 1);
      vo1p2 = vfmaq_lane_f16(vo1p2, vi5x6789, vwOP, 1);

      vo0p0 = vaddq_f16(vo0p0, vo0p1);
      vo1p0 = vaddq_f16(vo1p0, vo1p1);
      vo0p0 = vaddq_f16(vo0p0, vo0p2);
      vo1p0 = vaddq_f16(vo1p0, vo1p2);

      float16x8_t vo0 = vmaxq_f16(vo0p0, vmin);
      float16x8_t vo1 = vmaxq_f16(vo1p0, vmin);

      vo0 = vminq_f16(vo0, vmax);
      vo1 = vminq_f16(vo1, vmax);

      vst1q_f16(o1, vo1); o1 += 8;
      vst1q_f16(o0, vo0); o0 += 8;
    }

    // Always process the last block of 5..16 pixels.
    assert(w <= 16 * sizeof(__fp16));
    if XNN_LIKELY(w > 8 * sizeof(__fp16)) {
      float16x8_t vo0p0 = vdupq_laneq_f16(vw01234567, 0);
      float16x8_t vo1p0 = vdupq_laneq_f16(vw01234567, 0);

      float16x8_t vi0x89AB = vld1q_f16(i0); i0 += 8;
      float16x8_t vi1x89AB = vld1q_f16(i1); i1 += 8;
      float16x8_t vi2x89AB = vld1q_f16(i2); i2 += 8;
      float16x8_t vi3x89AB = vld1q_f16(i3); i3 += 8;
      float16x8_t vi4x89AB = vld1q_f16(i4); i4 += 8;
      float16x8_t vi5x89AB = vld1q_f16(i5); i5 += 8;

      vi0x89AB = vreinterpretq_f16_u16(vandq_u16(vmask, vreinterpretq_u16_f16(vi0x89AB)));
      vi1x89AB = vreinterpretq_f16_u16(vandq_u16(vmask, vreinterpretq_u16_f16(vi1x89AB)));
      vi2x89AB = vreinterpretq_f16_u16(vandq_u16(vmask, vreinterpretq_u16_f16(vi2x89AB)));
      vi3x89AB = vreinterpretq_f16_u16(vandq_u16(vmask, vreinterpretq_u16_f16(vi3x89AB)));
      vi4x89AB = vreinterpretq_f16_u16(vandq_u16(vmask, vreinterpretq_u16_f16(vi4x89AB)));
      vi5x89AB = vreinterpretq_f16_u16(vandq_u16(vmask, vreinterpretq_u16_f16(vi5x89AB)));

      // Center column
      float16x8_t vo0p1 = vmulq_laneq_f16(vi0x4567, vw01234567, 3);
      float16x8_t vo1p1 = vmulq_laneq_f16(vi1x4567, vw01234567, 3);

      float16x8_t vo0p2 = vmulq_laneq_f16(vi1x4567, vw89ABCDEF, 0);
      float16x8_t vo1p2 = vmulq_laneq_f16(vi2x4567, vw89ABCDEF, 0);

      vo0p1 = vfmaq_laneq_f16(vo0p1, vi2x4567, vw89ABCDEF, 5);
      vo1p1 = vfmaq_laneq_f16(vo1p1, vi3x4567, vw89ABCDEF, 5);

      vo0p2 = vfmaq_laneq_f16(vo0p2, vi3x4567, vwGHIJKLMN, 2);
      vo1p2 = vfmaq_laneq_f16(vo1p2, vi4x4567, vwGHIJKLMN, 2);

      vo0p0 = vfmaq_laneq_f16(vo0p0, vi4x4567, vwGHIJKLMN, 7);
      vo1p0 = vfmaq_laneq_f16(vo1p0, vi5x4567, vwGHIJKLMN, 7);

      // Left by 1 column
      const float16x8_t vi0x3456 = vextq_f16(vi0x0123, vi0x4567, 7);
      const float16x8_t vi1x3456 = vextq_f16(vi1x0123, vi1x4567, 7);
      const float16x8_t vi2x3456 = vextq_f16(vi2x0123, vi2x4567, 7);
      const float16x8_t vi3x3456 = vextq_f16(vi3x0123, vi3x4567, 7);
      const float16x8_t vi4x3456 = vextq_f16(vi4x0123, vi4x4567, 7);
      const float16x8_t vi5x3456 = vextq_f16(vi5x0123, vi5x4567, 7);

      vo0p1 = vfmaq_laneq_f16(vo0p1, vi0x3456, vw01234567, 2);
      vo1p1 = vfmaq_laneq_f16(vo1p1, vi1x3456, vw01234567, 2);

      vo0p2 = vfmaq_laneq_f16(vo0p2, vi1x3456, vw01234567, 7);
      vo1p2 = vfmaq_laneq_f16(vo1p2, vi2x3456, vw01234567, 7);

      vo0p0 = vfmaq_laneq_f16(vo0p0, vi2x3456, vw89ABCDEF, 4);
      vo1p0 = vfmaq_laneq_f16(vo1p0, vi3x3456, vw89ABCDEF, 4);

      vo0p1 = vfmaq_laneq_f16(vo0p1, vi3x3456, vwGHIJKLMN, 1);
      vo1p1 = vfmaq_laneq_f16(vo1p1, vi4x3456, vwGHIJKLMN, 1);

      vo0p2 = vfmaq_laneq_f16(vo0p2, vi4x3456, vwGHIJKLMN, 6);
      vo1p2 = vfmaq_laneq_f16(vo1p2, vi5x3456, vwGHIJKLMN, 6);

      // Left by 2 column
      const float16x8_t vi0x2345 = vextq_f16(vi0x0123, vi0x4567, 6);
      vi0x0123 = vi0x4567;
      const float16x8_t vi1x2345 = vextq_f16(vi1x0123, vi1x4567, 6);
      vi1x0123 = vi1x4567;
      const float16x8_t vi2x2345 = vextq_f16(vi2x0123, vi2x4567, 6);
      vi2x0123 = vi2x4567;
      const float16x8_t vi3x2345 = vextq_f16(vi3x0123, vi3x4567, 6);
      vi3x0123 = vi3x4567;
      const float16x8_t vi4x2345 = vextq_f16(vi4x0123, vi4x4567, 6);
      vi4x0123 = vi4x4567;
      const float16x8_t vi5x2345 = vextq_f16(vi5x0123, vi5x4567, 6);
      vi5x0123 = vi5x4567;

      vo0p0 = vfmaq_laneq_f16(vo0p0, vi0x2345, vw01234567, 1);
      vo1p0 = vfmaq_laneq_f16(vo1p0, vi1x2345, vw01234567, 1);

      vo0p1 = vfmaq_laneq_f16(vo0p1, vi1x2345, vw01234567, 6);
      vo1p1 = vfmaq_laneq_f16(vo1p1, vi2x2345, vw01234567, 6);

      vo0p2 = vfmaq_laneq_f16(vo0p2, vi2x2345, vw89ABCDEF, 3);
      vo1p2 = vfmaq_laneq_f16(vo1p2, vi3x2345, vw89ABCDEF, 3);

      vo0p0 = vfmaq_laneq_f16(vo0p0, vi3x2345, vwGHIJKLMN, 0);
      vo1p0 = vfmaq_laneq_f16(vo1p0, vi4x2345, vwGHIJKLMN, 0);

      vo0p1 = vfmaq_laneq_f16(vo0p1, vi4x2345, vwGHIJKLMN, 5);
      vo1p1 = vfmaq_laneq_f16(vo1p1, vi5x2345, vwGHIJKLMN, 5);

      // Right by 1 column
      const float16x8_t vi0x5678 = vextq_f16(vi0x4567, vi0x89AB, 1);
      const float16x8_t vi1x5678 = vextq_f16(vi1x4567, vi1x89AB, 1);
      const float16x8_t vi2x5678 = vextq_f16(vi2x4567, vi2x89AB, 1);
      const float16x8_t vi3x5678 = vextq_f16(vi3x4567, vi3x89AB, 1);
      const float16x8_t vi4x5678 = vextq_f16(vi4x4567, vi4x89AB, 1);
      const float16x8_t vi5x5678 = vextq_f16(vi5x4567, vi5x89AB, 1);

      vo0p2 = vfmaq_laneq_f16(vo0p2, vi0x5678, vw01234567, 4);
      vo1p2 = vfmaq_laneq_f16(vo1p2, vi1x5678, vw01234567, 4);

      vo0p0 = vfmaq_laneq_f16(vo0p0, vi1x5678, vw89ABCDEF, 1);
      vo1p0 = vfmaq_laneq_f16(vo1p0, vi2x5678, vw89ABCDEF, 1);

      vo0p1 = vfmaq_laneq_f16(vo0p1, vi2x5678, vw89ABCDEF, 6);
      vo1p1 = vfmaq_laneq_f16(vo1p1, vi3x5678, vw89ABCDEF, 6);

      vo0p2 = vfmaq_laneq_f16(vo0p2, vi3x5678, vwGHIJKLMN, 3);
      vo1p2 = vfmaq_laneq_f16(vo1p2, vi4x5678, vwGHIJKLMN, 3);

      vo0p0 = vfmaq_lane_f16(vo0p0, vi4x5678, vwOP, 0);
      vo1p0 = vfmaq_lane_f16(vo1p0, vi5x5678, vwOP, 0);

      // Right by 2 column
      const float16x8_t vi0x6789 = vextq_f16(vi0x4567, vi0x89AB, 2);
      vi0x4567 = vi0x89AB;
      const float16x8_t vi1x6789 = vextq_f16(vi1x4567, vi1x89AB, 2);
      vi1x4567 = vi1x89AB;
      const float16x8_t vi2x6789 = vextq_f16(vi2x4567, vi2x89AB, 2);
      vi2x4567 = vi2x89AB;
      const float16x8_t vi3x6789 = vextq_f16(vi3x4567, vi3x89AB, 2);
      vi3x4567 = vi3x89AB;
      const float16x8_t vi4x6789 = vextq_f16(vi4x4567, vi4x89AB, 2);
      vi4x4567 = vi4x89AB;
      const float16x8_t vi5x6789 = vextq_f16(vi5x4567, vi5x89AB, 2);
      vi5x4567 = vi5x89AB;

      vo0p1 = vfmaq_laneq_f16(vo0p1, vi0x6789, vw01234567, 5);
      vo1p1 = vfmaq_laneq_f16(vo1p1, vi1x6789, vw01234567, 5);

      vo0p2 = vfmaq_laneq_f16(vo0p2, vi1x6789, vw89ABCDEF, 2);
      vo1p2 = vfmaq_laneq_f16(vo1p2, vi2x6789, vw89ABCDEF, 2);

      vo0p0 = vfmaq_laneq_f16(vo0p0, vi2x6789, vw89ABCDEF, 7);
      vo1p0 = vfmaq_laneq_f16(vo1p0, vi3x6789, vw89ABCDEF, 7);

      vo0p1 = vfmaq_laneq_f16(vo0p1, vi3x6789, vwGHIJKLMN, 4);
      vo1p1 = vfmaq_laneq_f16(vo1p1, vi4x6789, vwGHIJKLMN, 4);

      vo0p2 = vfmaq_lane_f16(vo0p2, vi4x6789, vwOP, 1);
      vo1p2 = vfmaq_lane_f16(vo1p2, vi5x6789, vwOP, 1);

      vo0p0 = vaddq_f16(vo0p0, vo0p1);
      vo1p0 = vaddq_f16(vo1p0, vo1p1);
      vo0p0 = vaddq_f16(vo0p0, vo0p2);
      vo1p0 = vaddq_f16(vo1p0, vo1p2);

      float16x8_t vo0 = vmaxq_f16(vo0p0, vmin);
      float16x8_t vo1 = vmaxq_f16(vo1p0, vmin);

      vo0 = vminq_f16(vo0, vmax);
      vo1 = vminq_f16(vo1, vmax);

      vst1q_f16(o1, vo1); o1 += 8;
      vst1q_f16(o0, vo0); o0 += 8;

      w -= 8 * sizeof(__fp16);
    }

    assert(w >= 1 * sizeof(__fp16));
    assert(w <= 8 * sizeof(__fp16));
    {
      float16x8_t vo0p0 = vdupq_laneq_f16(vw01234567, 0);
      float16x8_t vo1p0 = vdupq_laneq_f16(vw01234567, 0);

      vi0x4567 = vreinterpretq_f16_u16(vandq_u16(vmask, vreinterpretq_u16_f16(vi0x4567)));
      vi1x4567 = vreinterpretq_f16_u16(vandq_u16(vmask, vreinterpretq_u16_f16(vi1x4567)));
      vi2x4567 = vreinterpretq_f16_u16(vandq_u16(vmask, vreinterpretq_u16_f16(vi2x4567)));
      vi3x4567 = vreinterpretq_f16_u16(vandq_u16(vmask, vreinterpretq_u16_f16(vi3x4567)));
      vi4x4567 = vreinterpretq_f16_u16(vandq_u16(vmask, vreinterpretq_u16_f16(vi4x4567)));
      vi5x4567 = vreinterpretq_f16_u16(vandq_u16(vmask, vreinterpretq_u16_f16(vi5x4567)));

      // Center column
      float16x8_t vo0p1 = vmulq_laneq_f16(vi0x4567, vw01234567, 3);
      float16x8_t vo1p1 = vmulq_laneq_f16(vi1x4567, vw01234567, 3);

      float16x8_t vo0p2 = vmulq_laneq_f16(vi1x4567, vw89ABCDEF, 0);
      float16x8_t vo1p2 = vmulq_laneq_f16(vi2x4567, vw89ABCDEF, 0);

      vo0p1 = vfmaq_laneq_f16(vo0p1, vi2x4567, vw89ABCDEF, 5);
      vo1p1 = vfmaq_laneq_f16(vo1p1, vi3x4567, vw89ABCDEF, 5);

      vo0p2 = vfmaq_laneq_f16(vo0p2, vi3x4567, vwGHIJKLMN, 2);
      vo1p2 = vfmaq_laneq_f16(vo1p2, vi4x4567, vwGHIJKLMN, 2);

      vo0p0 = vfmaq_laneq_f16(vo0p0, vi4x4567, vwGHIJKLMN, 7);
      vo1p0 = vfmaq_laneq_f16(vo1p0, vi5x4567, vwGHIJKLMN, 7);

      // Left by 1 column
      const float16x8_t vi0x3456 = vextq_f16(vi0x0123, vi0x4567, 7);
      const float16x8_t vi1x3456 = vextq_f16(vi1x0123, vi1x4567, 7);
      const float16x8_t vi2x3456 = vextq_f16(vi2x0123, vi2x4567, 7);
      const float16x8_t vi3x3456 = vextq_f16(vi3x0123, vi3x4567, 7);
      const float16x8_t vi4x3456 = vextq_f16(vi4x0123, vi4x4567, 7);
      const float16x8_t vi5x3456 = vextq_f16(vi5x0123, vi5x4567, 7);

      vo0p1 = vfmaq_laneq_f16(vo0p1, vi0x3456, vw01234567, 2);
      vo1p1 = vfmaq_laneq_f16(vo1p1, vi1x3456, vw01234567, 2);

      vo0p2 = vfmaq_laneq_f16(vo0p2, vi1x3456, vw01234567, 7);
      vo1p2 = vfmaq_laneq_f16(vo1p2, vi2x3456, vw01234567, 7);

      vo0p0 = vfmaq_laneq_f16(vo0p0, vi2x3456, vw89ABCDEF, 4);
      vo1p0 = vfmaq_laneq_f16(vo1p0, vi3x3456, vw89ABCDEF, 4);

      vo0p1 = vfmaq_laneq_f16(vo0p1, vi3x3456, vwGHIJKLMN, 1);
      vo1p1 = vfmaq_laneq_f16(vo1p1, vi4x3456, vwGHIJKLMN, 1);

      vo0p2 = vfmaq_laneq_f16(vo0p2, vi4x3456, vwGHIJKLMN, 6);
      vo1p2 = vfmaq_laneq_f16(vo1p2, vi5x3456, vwGHIJKLMN, 6);

      // Left by 2 column
      const float16x8_t vi0x2345 = vextq_f16(vi0x0123, vi0x4567, 6);
      const float16x8_t vi1x2345 = vextq_f16(vi1x0123, vi1x4567, 6);
      const float16x8_t vi2x2345 = vextq_f16(vi2x0123, vi2x4567, 6);
      const float16x8_t vi3x2345 = vextq_f16(vi3x0123, vi3x4567, 6);
      const float16x8_t vi4x2345 = vextq_f16(vi4x0123, vi4x4567, 6);
      const float16x8_t vi5x2345 = vextq_f16(vi5x0123, vi5x4567, 6);

      vo0p0 = vfmaq_laneq_f16(vo0p0, vi0x2345, vw01234567, 1);
      vo1p0 = vfmaq_laneq_f16(vo1p0, vi1x2345, vw01234567, 1);

      vo0p1 = vfmaq_laneq_f16(vo0p1, vi1x2345, vw01234567, 6);
      vo1p1 = vfmaq_laneq_f16(vo1p1, vi2x2345, vw01234567, 6);

      vo0p2 = vfmaq_laneq_f16(vo0p2, vi2x2345, vw89ABCDEF, 3);
      vo1p2 = vfmaq_laneq_f16(vo1p2, vi3x2345, vw89ABCDEF, 3);

      vo0p0 = vfmaq_laneq_f16(vo0p0, vi3x2345, vwGHIJKLMN, 0);
      vo1p0 = vfmaq_laneq_f16(vo1p0, vi4x2345, vwGHIJKLMN, 0);

      vo0p1 = vfmaq_laneq_f16(vo0p1, vi4x2345, vwGHIJKLMN, 5);
      vo1p1 = vfmaq_laneq_f16(vo1p1, vi5x2345, vwGHIJKLMN, 5);

      // Right by 1 column
      const float16x8_t vzero = vmovq_n_f16(0);
      const float16x8_t vi0x5678 = vextq_f16(vi0x4567, vzero, 1);
      const float16x8_t vi1x5678 = vextq_f16(vi1x4567, vzero, 1);
      const float16x8_t vi2x5678 = vextq_f16(vi2x4567, vzero, 1);
      const float16x8_t vi3x5678 = vextq_f16(vi3x4567, vzero, 1);
      const float16x8_t vi4x5678 = vextq_f16(vi4x4567, vzero, 1);
      const float16x8_t vi5x5678 = vextq_f16(vi5x4567, vzero, 1);

      vo0p2 = vfmaq_laneq_f16(vo0p2, vi0x5678, vw01234567, 4);
      vo1p2 = vfmaq_laneq_f16(vo1p2, vi1x5678, vw01234567, 4);

      vo0p0 = vfmaq_laneq_f16(vo0p0, vi1x5678, vw89ABCDEF, 1);
      vo1p0 = vfmaq_laneq_f16(vo1p0, vi2x5678, vw89ABCDEF, 1);

      vo0p1 = vfmaq_laneq_f16(vo0p1, vi2x5678, vw89ABCDEF, 6);
      vo1p1 = vfmaq_laneq_f16(vo1p1, vi3x5678, vw89ABCDEF, 6);

      vo0p2 = vfmaq_laneq_f16(vo0p2, vi3x5678, vwGHIJKLMN, 3);
      vo1p2 = vfmaq_laneq_f16(vo1p2, vi4x5678, vwGHIJKLMN, 3);

      vo0p0 = vfmaq_lane_f16(vo0p0, vi4x5678, vwOP, 0);
      vo1p0 = vfmaq_lane_f16(vo1p0, vi5x5678, vwOP, 0);

      // Right by 2 column
      const float16x8_t vi0x6789 = vextq_f16(vi0x5678, vzero, 1);
      const float16x8_t vi1x6789 = vextq_f16(vi1x5678, vzero, 1);
      const float16x8_t vi2x6789 = vextq_f16(vi2x5678, vzero, 1);
      const float16x8_t vi3x6789 = vextq_f16(vi3x5678, vzero, 1);
      const float16x8_t vi4x6789 = vextq_f16(vi4x5678, vzero, 1);
      const float16x8_t vi5x6789 = vextq_f16(vi5x5678, vzero, 1);

      vo0p1 = vfmaq_laneq_f16(vo0p1, vi0x6789, vw01234567, 5);
      vo1p1 = vfmaq_laneq_f16(vo1p1, vi1x6789, vw01234567, 5);

      vo0p2 = vfmaq_laneq_f16(vo0p2, vi1x6789, vw89ABCDEF, 2);
      vo1p2 = vfmaq_laneq_f16(vo1p2, vi2x6789, vw89ABCDEF, 2);

      vo0p0 = vfmaq_laneq_f16(vo0p0, vi2x6789, vw89ABCDEF, 7);
      vo1p0 = vfmaq_laneq_f16(vo1p0, vi3x6789, vw89ABCDEF, 7);

      vo0p1 = vfmaq_laneq_f16(vo0p1, vi3x6789, vwGHIJKLMN, 4);
      vo1p1 = vfmaq_laneq_f16(vo1p1, vi4x6789, vwGHIJKLMN, 4);

      vo0p2 = vfmaq_lane_f16(vo0p2, vi4x6789, vwOP, 1);
      vo1p2 = vfmaq_lane_f16(vo1p2, vi5x6789, vwOP, 1);

      vo0p0 = vaddq_f16(vo0p0, vo0p1);
      vo1p0 = vaddq_f16(vo1p0, vo1p1);
      vo0p0 = vaddq_f16(vo0p0, vo0p2);
      vo1p0 = vaddq_f16(vo1p0, vo1p2);

      float16x8_t vo0 = vmaxq_f16(vo0p0, vmin);
      float16x8_t vo1 = vmaxq_f16(vo1p0, vmin);

      vo0 = vminq_f16(vo0, vmax);
      vo1 = vminq_f16(vo1, vmax);

      if XNN_LIKELY(w == 8 * sizeof(__fp16)) {
        vst1q_f16(o1, vo1); o1 += 8;
        vst1q_f16(o0, vo0); o0 += 8;
      } else {
        float16x4_t vo1_lo = vget_low_f16(vo1);
        float16x4_t vo0_lo = vget_low_f16(vo0);

        if (w & (4 * sizeof(__fp16))) {
         vst1_f16(o1, vo1_lo); o1 += 4;
         vst1_f16(o0, vo0_lo); o0 += 4;

          vo1_lo = vget_high_f16(vo1);
          vo0_lo = vget_high_f16(vo0);
        }
        if (w & (2 * sizeof(__fp16))) {
          vst1_lane_u32((void*) o1, vreinterpret_u32_f16(vo1_lo), 0); o1 += 2;
          vst1_lane_u32((void*) o0, vreinterpret_u32_f16(vo0_lo), 0); o0 += 2;

          vo0_lo = vext_f16(vo0_lo, vo0_lo, 2);
          vo1_lo = vext_f16(vo1_lo, vo1_lo, 2);
        }
        if (w & (1 * sizeof(__fp16))) {
          vst1_lane_f16(o1, vo1_lo, 0); o1 += 1;
          vst1_lane_f16(o0, vo0_lo, 0); o0 += 1;
        }
      }
    }

    i0 = (const __fp16*) ((uintptr_t) i2 - input_decrement);
    i1 = (const __fp16*) ((uintptr_t) i3 - input_decrement);
    i2 = (const __fp16*) ((uintptr_t) i1 + input_width);
    i3 = (const __fp16*) ((uintptr_t) i2 + input_width);
    i4 = (const __fp16*) ((uintptr_t) i3 + input_width);
    i5 = (const __fp16*) ((uintptr_t) i4 + input_width);

    o0 = o1;
    o1 = (__fp16*) ((uintptr_t) o0 + input_width);

    output_height = doz(output_height, 2);
  } while (output_height != 0);
}
