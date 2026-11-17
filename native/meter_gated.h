/* SPDX-License-Identifier: GPL-2.0-or-later */
#ifndef C5_METER_GATED_H
#define C5_METER_GATED_H
#include "meter_sampler.h"

/* Experimental raw acquisition. A cache requires an observed CNVRF 0 -> 1
 * before its data reads. This does not make the two data words atomic, supply
 * an ADC timestamp, qualify analog accuracy or enable GUI measurements.
 * Each step performs at most one read; DIAG reads can clear status flags.
 */
struct c5_gated_sampler {
    struct c5_sampler s;
    uint32_t gate_begin,clear_tick,ready_tick,sample_clear_tick,sample_ready_tick;
    uint32_t diag_reads,clear_events,ready_events;
    uint16_t last_diag,gate_ms,max_gate_ms;
};
static inline unsigned c5_sampling_active(const struct c5_sampler *s){
    return s->state==C5_SAMPLE_IDENTIFY||s->state==C5_SAMPLE_RUNNING;
}
static inline void c5_gated_start(struct c5_gated_sampler *g,uint32_t now){
    if(c5_sampling_active(&g->s)){g->s.heartbeat=now;return;}
    *g=(struct c5_gated_sampler){0};c5_sampler_start(&g->s,now);
}
static inline void c5_gated_fail(struct c5_sampler *s,unsigned error){
    s->error=error;s->state=C5_SAMPLE_FAULT;
}
static inline void c5_gated_step(struct c5_gated_sampler *g,uint32_t now,unsigned presenting,
                                c5_sample_read read,void *context){
    struct c5_sampler *s=&g->s;
    if(!c5_sampling_active(s))return;
    if((uint32_t)(now-s->heartbeat)>2000){s->state=C5_SAMPLE_OFF;return;}
    if(presenting||(int32_t)(now-s->next_tick)<0)return;
    if(s->phase>9){c5_gated_fail(s,10);return;}
    if((s->phase==4&&(uint32_t)(now-g->gate_begin)>500)||
       (s->phase==5&&(uint32_t)(now-g->clear_tick)>500)||
       (s->phase>=6&&(uint32_t)(now-g->ready_tick)>150)||
       (s->phase>=3&&(uint32_t)(now-s->cycle_begin)>1200)){
        c5_gated_fail(s,11);return;
    }
    static const uint8_t regs[]={0x3e,0x3f,0,1,0x0b,0x0b,4,5,0,1};
    if(s->phase==2)s->cycle_begin=now;
    if(s->phase==6)s->pair_begin=now;
    unsigned reg=regs[s->phase];uint32_t value=0,elapsed=0;
    unsigned error=read(context,reg,(reg==4||reg==5)?3:2,&value,&elapsed);
    uint32_t end=now+elapsed;
    if(elapsed>s->max_transaction_ms)s->max_transaction_ms=(uint16_t)(elapsed>65535?65535:elapsed);
    s->next_tick=end+5;
    if(error){c5_gated_fail(s,error);return;}
    if(elapsed>12){c5_gated_fail(s,9);return;}
    if((s->phase==4&&(uint32_t)(end-g->gate_begin)>500)||
       (s->phase==5&&(uint32_t)(end-g->clear_tick)>500)||
       (s->phase>=6&&(uint32_t)(end-g->ready_tick)>150)||
       (s->phase>=3&&(uint32_t)(end-s->cycle_begin)>1200)){
        c5_gated_fail(s,11);return;
    }
    switch(s->phase){
    case 0:if(value!=0x5449)s->error=6;break;
    case 1:if((value>>4)!=0x228)s->error=6;else s->state=C5_SAMPLE_RUNNING;break;
    case 2:s->pending_config=(uint16_t)value;if(value!=0)s->error=7;break;
    case 3:
        s->pending_adc=(uint16_t)value;if(value!=0xfb68)s->error=7;
        g->gate_begin=end;break;
    case 4:case 5:
        g->last_diag=(uint16_t)value;g->diag_reads++;
        /* Only the owner's observed MEMSTAT=1, ALATCH=0, no other flags. */
        if((value&~2u)!=1u){s->error=12;break;}
        s->next_tick=end;
        if(s->phase==4){
            if(value&2)return;
            g->clear_tick=end;g->clear_events++;
        }else{
            if(!(value&2))return;
            g->ready_tick=end;g->ready_events++;
            uint32_t span=end-g->gate_begin;
            if(span>g->max_gate_ms)g->max_gate_ms=(uint16_t)span;
        }
        break;
    case 6:s->pending_shunt=value;if(value&15)s->error=8;break;
    case 7:
        s->pending_bus=value;s->pair_ms=(uint16_t)(end-s->pair_begin);
        if(value&15||(uint32_t)(end-s->pair_begin)>75)s->error=9;
        if(s->pair_ms>s->max_pair_ms)s->max_pair_ms=s->pair_ms;
        break;
    case 8:if(value!=s->pending_config)s->error=8;break;
    case 9:
        if(value!=s->pending_adc)s->error=8;
        if(!s->error){
            s->config=s->pending_config;s->adc=s->pending_adc;
            s->shunt=s->pending_shunt;s->bus=s->pending_bus;s->sample_tick=end;
            g->sample_clear_tick=g->clear_tick;g->sample_ready_tick=g->ready_tick;
            g->gate_ms=(uint16_t)(g->ready_tick-g->gate_begin);
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
