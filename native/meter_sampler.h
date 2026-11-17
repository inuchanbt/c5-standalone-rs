/* SPDX-License-Identifier: GPL-2.0-or-later */
#ifndef C5_METER_SAMPLER_H
#define C5_METER_SAMPLER_H
#include <stdint.h>

/* Shadow acquisition only: no physical units, GUI updates or sensor writes.
 * One bounded register transaction per step, exclusively outside LCD scanout.
 * Cache timestamps are host-interface acquisition times, not ADC timestamps.
 */
enum { C5_SAMPLE_OFF=0,C5_SAMPLE_IDENTIFY=1,C5_SAMPLE_RUNNING=2,C5_SAMPLE_FAULT=3 };
struct c5_sampler {
    uint32_t state,phase,error,next_tick,heartbeat,cycle_begin,pair_begin;
    uint32_t sequence,sample_tick,shunt,bus,pending_shunt,pending_bus;
    uint16_t config,adc,pending_config,pending_adc;
    uint16_t max_transaction_ms,max_pair_ms,pair_ms,cycle_ms;
};
typedef unsigned (*c5_sample_read)(void *,unsigned,unsigned,uint32_t *,uint32_t *);

static inline void c5_sampler_start(struct c5_sampler *s,uint32_t now){
    if(s->state==C5_SAMPLE_IDENTIFY||s->state==C5_SAMPLE_RUNNING){s->heartbeat=now;return;}
    *s=(struct c5_sampler){0};s->state=C5_SAMPLE_IDENTIFY;s->next_tick=now;s->heartbeat=now;
}
static inline unsigned c5_sampler_current(const struct c5_sampler *s,uint32_t now){
    return s->sequence&&s->state==C5_SAMPLE_RUNNING&&(uint32_t)(now-s->sample_tick)<=500;
}
static inline void c5_sampler_step(struct c5_sampler *s,uint32_t now,unsigned presenting,
                                  c5_sample_read read,void *context){
    if(s->state!=C5_SAMPLE_IDENTIFY&&s->state!=C5_SAMPLE_RUNNING)return;
    if((uint32_t)(now-s->heartbeat)>2000){s->state=C5_SAMPLE_OFF;return;}
    if(presenting||(int32_t)(now-s->next_tick)<0)return;
    static const uint8_t regs[]={0x3e,0x3f,0,1,4,5,0,1};
    if(s->phase>7){s->error=10;s->state=C5_SAMPLE_FAULT;return;}
    if(s->phase==2)s->cycle_begin=now;
    if(s->phase==4)s->pair_begin=now;
    unsigned reg=regs[s->phase];uint32_t value=0,elapsed=0;
    unsigned error=read(context,reg,(reg==4||reg==5)?3:2,&value,&elapsed);
    uint32_t end=now+elapsed;
    if(elapsed>s->max_transaction_ms)s->max_transaction_ms=(uint16_t)(elapsed>65535?65535:elapsed);
    s->next_tick=end+10;
    if(error){s->error=error;s->state=C5_SAMPLE_FAULT;return;}
    if(elapsed>12){s->error=9;s->state=C5_SAMPLE_FAULT;return;}
    switch(s->phase){
    case 0:if(value!=0x5449)s->error=6;break;
    case 1:if((value>>4)!=0x228)s->error=6;else s->state=C5_SAMPLE_RUNNING;break;
    case 2:s->pending_config=(uint16_t)value;if(value!=0)s->error=7;break;
    case 3:s->pending_adc=(uint16_t)value;if(value!=0xfb68)s->error=7;break;
    case 4:s->pending_shunt=value;if(value&15)s->error=8;break;
    case 5:
        s->pending_bus=value;s->pair_ms=(uint16_t)(end-s->pair_begin);
        if(value&15||(uint32_t)(end-s->pair_begin)>75)s->error=9;
        if(s->pair_ms>s->max_pair_ms)s->max_pair_ms=s->pair_ms;
        break;
    case 6:if(value!=s->pending_config)s->error=8;break;
    case 7:
        if(value!=s->pending_adc)s->error=8;
        if((uint32_t)(end-s->cycle_begin)>160)s->error=9;
        if(!s->error){
            s->config=s->pending_config;s->adc=s->pending_adc;
            s->shunt=s->pending_shunt;s->bus=s->pending_bus;s->sample_tick=end;
            if(!++s->sequence)s->sequence=1;
            s->cycle_ms=(uint16_t)(end-s->cycle_begin);
            s->phase=2;s->next_tick=end+200;return;
        }
        break;
    }
    if(s->error){s->state=C5_SAMPLE_FAULT;return;}
    s->phase++;
}
#endif
