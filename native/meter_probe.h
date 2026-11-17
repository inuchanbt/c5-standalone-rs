/* SPDX-License-Identifier: GPL-2.0-or-later */
#ifndef C5_METER_PROBE_H
#define C5_METER_PROBE_H
#include <stdint.h>

/* Fixed ID and INA228 raw-register reads at the stock C4/C5 address.
 * No register-value writes, address scans, clock recovery or sensor resets.
 * The board releases a line for 1 and drives only 0. pause() must bound time.
 */
enum { C5_SCL=0, C5_SDA=1 };
enum { C5_PROBE_OK=0, C5_PROBE_UNKNOWN=1, C5_PROBE_NACK=2,
       C5_PROBE_BUSY=3, C5_PROBE_TIMEOUT=4, C5_PROBE_NOT_READY=5 };
struct c5_meter_io {
    void *context;
    void (*set)(void *, unsigned line, unsigned released);
    unsigned (*get)(void *, unsigned line);
    int (*pause)(void *);
};
struct c5_meter_result {
    uint8_t status, kind, idle_lines, valid_mask;
    uint16_t manufacturer_3e, device_3f, manufacturer_fe, device_ff;
    uint32_t elapsed_ms;
    uint16_t failed_stage, successful_reads;
};
struct c5_meter_bus { const struct c5_meter_io *io; unsigned error, stage; };

static int c5_meter_step(struct c5_meter_bus *b) {
    if (b->error==C5_PROBE_TIMEOUT) return 0;
    if (!b->io->pause(b->io->context)) { b->error=C5_PROBE_TIMEOUT; return 0; }
    return 1;
}
static void c5_meter_set(struct c5_meter_bus *b,unsigned line,unsigned released) {
    b->io->set(b->io->context,line,released);
}
static int c5_meter_high(struct c5_meter_bus *b) {
    c5_meter_set(b,C5_SCL,1);
    for (unsigned i=0;i<32;i++) {
        if (!c5_meter_step(b)) return 0;
        if (b->io->get(b->io->context,C5_SCL)) return 1;
    }
    b->error=C5_PROBE_TIMEOUT;return 0;
}
static int c5_meter_start(struct c5_meter_bus *b) {
    c5_meter_set(b,C5_SDA,1);
    if (!c5_meter_step(b)||!c5_meter_high(b)) return 0;
    c5_meter_set(b,C5_SDA,0);
    if (!c5_meter_step(b)) return 0;
    c5_meter_set(b,C5_SCL,0);return c5_meter_step(b);
}
static int c5_meter_write_byte(struct c5_meter_bus *b,unsigned value) {
    for (unsigned i=0;i<8;i++) {
        c5_meter_set(b,C5_SDA,!!(value&0x80));value<<=1;
        if (!c5_meter_step(b)||!c5_meter_high(b)) return 0;
        c5_meter_set(b,C5_SCL,0);
        if (!c5_meter_step(b)) return 0;
    }
    c5_meter_set(b,C5_SDA,1);
    if (!c5_meter_step(b)||!c5_meter_high(b)) return 0;
    unsigned nack=b->io->get(b->io->context,C5_SDA);
    c5_meter_set(b,C5_SCL,0);
    if (!c5_meter_step(b)) return 0;
    if (nack) { b->error=C5_PROBE_NACK;return 0; }
    return 1;
}
static int c5_meter_read_byte(struct c5_meter_bus *b,unsigned ack,unsigned *value) {
    unsigned result=0;c5_meter_set(b,C5_SDA,1);
    for (unsigned i=0;i<8;i++) {
        if (!c5_meter_step(b)||!c5_meter_high(b)) return 0;
        result=(result<<1)|!!b->io->get(b->io->context,C5_SDA);
        c5_meter_set(b,C5_SCL,0);
        if (!c5_meter_step(b)) return 0;
    }
    c5_meter_set(b,C5_SDA,!ack);
    if (!c5_meter_step(b)||!c5_meter_high(b)) return 0;
    c5_meter_set(b,C5_SCL,0);
    if (!c5_meter_step(b)) return 0;
    c5_meter_set(b,C5_SDA,1);*value=result;return 1;
}
static int c5_meter_stop(struct c5_meter_bus *b) {
    c5_meter_set(b,C5_SCL,0);c5_meter_set(b,C5_SDA,0);
    if (!c5_meter_step(b)||!c5_meter_high(b)) return 0;
    c5_meter_set(b,C5_SDA,1);return c5_meter_step(b);
}
static int c5_i2c_read_begin(struct c5_meter_bus *b,unsigned address,unsigned reg) {
    b->stage=(reg<<8)|1;
    if (!c5_meter_start(b)||!c5_meter_write_byte(b,address<<1)) return 0;
    b->stage=(reg<<8)|2;
    if (!c5_meter_write_byte(b,reg)) return 0;
    b->stage=(reg<<8)|3;
    return c5_meter_start(b)&&c5_meter_write_byte(b,(address<<1)|1u);
}
static int c5_meter_read_register(struct c5_meter_bus *b,unsigned reg,unsigned count,uint32_t *value) {
    unsigned result=0,byte=0;int ok=0;
    if (!c5_i2c_read_begin(b,0x40,reg)) goto done;
    b->stage=(reg<<8)|4;
    for (unsigned i=0;i<count;i++) {
        if (!c5_meter_read_byte(b,i+1<count,&byte)) goto done;
        result=(result<<8)|byte;
    }
    ok=1;
done:
    if (ok) b->stage=(reg<<8)|5;
    if (b->error!=C5_PROBE_TIMEOUT&&!c5_meter_stop(b)) ok=0;
    if (ok) *value=result;
    return ok;
}
static int c5_meter_read_id(struct c5_meter_bus *b,unsigned reg,uint16_t *value) {
    uint32_t result=0;
    if (!c5_meter_read_register(b,reg,2,&result)) return 0;
    *value=(uint16_t)result;return 1;
}
static void c5_meter_probe(const struct c5_meter_io *io,struct c5_meter_result *r) {
    *r=(struct c5_meter_result){0};
    struct c5_meter_bus b={io,0,0};
    io->set(io->context,C5_SDA,1);io->set(io->context,C5_SCL,1);
    if (!c5_meter_step(&b)) goto failed;
    r->idle_lines=(uint8_t)(!!io->get(io->context,C5_SCL)
                         | (!!io->get(io->context,C5_SDA)<<1));
    if (r->idle_lines!=3) { b.error=C5_PROBE_BUSY;goto failed; }
    if (!c5_meter_read_id(&b,0x3e,&r->manufacturer_3e)) goto failed;
    r->valid_mask|=1;r->successful_reads++;
    if (!c5_meter_read_id(&b,0x3f,&r->device_3f)) goto failed;
    r->valid_mask|=2;r->successful_reads++;
    if (r->manufacturer_3e==0x5449&&(r->device_3f>>4)==0x228) {
        r->kind=2;goto done;
    }
    if (!c5_meter_read_id(&b,0xfe,&r->manufacturer_fe)) goto failed;
    r->valid_mask|=4;r->successful_reads++;
    if (!c5_meter_read_id(&b,0xff,&r->device_ff)) goto failed;
    r->valid_mask|=8;r->successful_reads++;
    if (r->manufacturer_fe==0x5449&&(r->device_ff>>4)==0x226) r->kind=1;
    else r->status=C5_PROBE_UNKNOWN;
    goto done;
failed:
    r->status=(uint8_t)b.error;r->failed_stage=(uint16_t)b.stage;
done:
    /* On timeout, do not attempt recovery pulses or an unbounded STOP. */
    io->set(io->context,C5_SDA,1);io->set(io->context,C5_SCL,1);
}

/* Raw diagnostic snapshot only. Identification is repeated before touching
 * model-specific registers. Values are not promoted to calibrated GUI samples.
 * Do not read DIAG_ALRT (0x0b): some flags have read-to-clear behavior.
 */
struct c5_meter_raw_result {
    uint8_t status,kind,idle_lines,reserved;
    uint16_t valid_mask,config,adc_config,shunt_cal,shunt_tempco,die_temp;
    uint32_t shunt_raw,bus_raw,elapsed_ms,failed_stage,successful_reads;
};
static void c5_meter_raw_probe(const struct c5_meter_io *io,struct c5_meter_raw_result *r) {
    *r=(struct c5_meter_raw_result){0};
    struct c5_meter_result identity;c5_meter_probe(io,&identity);
    r->status=identity.status;r->kind=identity.kind;r->idle_lines=identity.idle_lines;
    r->failed_stage=identity.failed_stage;r->successful_reads=identity.successful_reads;
    if (identity.status||identity.kind!=2) {
        if (!identity.status) r->status=6; /* Identified model has no raw adapter. */
        return;
    }
    struct c5_meter_bus b={io,0,0};
    for (unsigned reg=0;reg<=6;reg++) {
        uint32_t value=0;
        if (!c5_meter_read_register(&b,reg,(reg==4||reg==5)?3:2,&value)) {
            r->status=(uint8_t)b.error;r->failed_stage=b.stage;break;
        }
        r->valid_mask|=(uint16_t)(1u<<reg);r->successful_reads++;
        switch(reg) {
        case 0:r->config=(uint16_t)value;break;
        case 1:r->adc_config=(uint16_t)value;break;
        case 2:r->shunt_cal=(uint16_t)value;break;
        case 3:r->shunt_tempco=(uint16_t)value;break;
        case 4:r->shunt_raw=value;break;
        case 5:r->bus_raw=value;break;
        case 6:r->die_temp=(uint16_t)value;break;
        }
    }
    io->set(io->context,C5_SDA,1);io->set(io->context,C5_SCL,1);
}

/* Stock storage addressing: 2 KiB at 0x50..0x57 with an 8-bit pointer.
 * The USB interface exposes fixed aligned 16-byte read blocks only. No byte
 * value is ever transmitted after the pointer; writes and init tests are absent.
 */
struct c5_storage_result {
    uint8_t status,count,idle_lines,reserved;
    uint16_t offset,failed_stage;
    uint32_t elapsed_ms;
    uint8_t data[16];
};
static void c5_storage_read_block(const struct c5_meter_io *io,unsigned block,struct c5_storage_result *r) {
    *r=(struct c5_storage_result){0};
    if(block>=128){r->status=7;return;}
    r->offset=(uint16_t)(block*16);
    struct c5_meter_bus b={io,0,0};unsigned value=0;int ok=0;
    io->set(io->context,C5_SDA,1);io->set(io->context,C5_SCL,1);
    if(!c5_meter_step(&b))goto failed;
    r->idle_lines=(uint8_t)(!!io->get(io->context,C5_SCL)| (!!io->get(io->context,C5_SDA)<<1));
    if(r->idle_lines!=3){b.error=C5_PROBE_BUSY;goto failed;}
    if(!c5_i2c_read_begin(&b,0x50u+(r->offset>>8),r->offset&255u))goto finish;
    b.stage=((r->offset&255u)<<8)|4;
    for(unsigned i=0;i<16;i++){
        if(!c5_meter_read_byte(&b,i!=15,&value))goto finish;
        r->data[i]=(uint8_t)value;r->count++;
    }
    ok=1;b.stage=((r->offset&255u)<<8)|5;
finish:
    if(b.error!=C5_PROBE_TIMEOUT&&!c5_meter_stop(&b))ok=0;
    if(ok)goto done;
failed:
    r->status=(uint8_t)b.error;r->failed_stage=(uint16_t)b.stage;
done:
    io->set(io->context,C5_SDA,1);io->set(io->context,C5_SCL,1);
}
#endif
