/* SPDX-License-Identifier: GPL-2.0-or-later */
#ifndef C5_DIAGNOSTIC_QUEUE_H
#define C5_DIAGNOSTIC_QUEUE_H
#include <stdint.h>

/* One foreground-only job. GPIO/I2C work must never run inside LCD scanout.
 * A second client cannot overwrite an outstanding request's nonce/prefix.
 */
struct c5_diagnostic_queue { unsigned command;uint8_t prefix[16]; };
static inline int c5_diagnostic_defer(struct c5_diagnostic_queue *q,unsigned presenting,
                                     unsigned command,const uint8_t *prefix) {
    if(!presenting)return 0;
    if(!q->command){
        for(unsigned i=0;i<16;i++)q->prefix[i]=prefix[i];
        q->command=command;
    }
    return 1;
}
static inline unsigned c5_diagnostic_take(struct c5_diagnostic_queue *q,unsigned presenting,
                                         uint8_t *prefix) {
    if(presenting||!q->command)return 0;
    unsigned command=q->command;q->command=0;
    for(unsigned i=0;i<16;i++)prefix[i]=q->prefix[i];
    return command;
}
#endif
