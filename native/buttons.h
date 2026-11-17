/* SPDX-License-Identifier: GPL-2.0-or-later */
#ifndef C5_BUTTONS_H
#define C5_BUTTONS_H

/* Owner-reported physical order: Back / Left(-) / OK / Right(+).
 * Active-low pins in that order: PB14 / PB15 / PA13 / PA14.
 * Upstream key bits: Left=1, Right=2, OK=4, Back=8.
 * Rotation is handled later by the Rust adapter, never here.
 */
static inline unsigned c5_keys_from_gpio(unsigned gpioa, unsigned gpiob) {
    return ((!(gpiob & (1u << 15))) << 0)
         | ((!(gpioa & (1u << 14))) << 1)
         | ((!(gpioa & (1u << 13))) << 2)
         | ((!(gpiob & (1u << 14))) << 3);
}

#endif
