/* SPDX-License-Identifier: GPL-2.0-or-later */
#ifndef C5_METER_SETTINGS_H
#define C5_METER_SETTINGS_H
#include <stdint.h>
/* Two complete passes over the 240-byte settings prefix, one block per step.
 * Comparison/checksum failure never repairs storage or starts sampling. */
struct c5_settings_load { uint8_t bytes[240];unsigned step,state,error; };
typedef unsigned (*c5_settings_reader)(void *,unsigned,uint8_t *);
typedef unsigned (*c5_settings_accept)(const uint8_t *);
static inline void c5_settings_step(struct c5_settings_load *s,c5_settings_reader read,
                                    void *context,c5_settings_accept accept){
    if(s->state)return;
    uint8_t block[16];unsigned index=s->step%15;
    unsigned error=read(context,index,block);
    if(error){s->error=error;s->state=2;return;}
    for(unsigned i=0;i<16;i++){
        if(s->step<15)s->bytes[index*16+i]=block[i];
        else if(s->bytes[index*16+i]!=block[i]){s->error=20;s->state=2;return;}
    }
    if(++s->step==30){
        s->state=accept(s->bytes)?1:2;
        if(s->state==2)s->error=21;
    }
}
#endif
