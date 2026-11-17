/* SPDX-License-Identifier: GPL-2.0-or-later */
#ifndef C5_METER_FRESH_H
#define C5_METER_FRESH_H
#include "meter_probe.h"

/* Explicit diagnostic of INA228 completion flags. Reading DIAG_ALRT may clear
 * latched flags; it is deliberately separate from ordinary raw snapshots.
 * No configuration/calibration/register-value writes are implemented.
 */
struct c5_fresh_result {
    uint8_t status,kind,idle_lines,count;
    uint16_t config,adc,manufacturer,device,diag[8];
    uint32_t elapsed_ms,failed_stage;
};
static void c5_meter_fresh_probe(const struct c5_meter_io *io,struct c5_fresh_result *r){
    *r=(struct c5_fresh_result){0};
    struct c5_meter_result id;c5_meter_probe(io,&id);
    r->status=id.status;r->kind=id.kind;r->idle_lines=id.idle_lines;
    r->manufacturer=id.manufacturer_3e;r->device=id.device_3f;r->failed_stage=id.failed_stage;
    if(r->status)return;
    if(id.kind!=2){r->status=6;return;}
    struct c5_meter_bus bus={io,0,0};uint32_t value=0;
    if(!c5_meter_read_register(&bus,0,2,&value))goto failed;
    r->config=(uint16_t)value;
    if(!c5_meter_read_register(&bus,1,2,&value))goto failed;
    r->adc=(uint16_t)value;
    if(r->config!=0||r->adc!=0xfb68){r->status=6;goto done;}
    for(unsigned i=0;i<8;i++){
        if(!c5_meter_read_register(&bus,0x0b,2,&value))goto failed;
        r->diag[i]=(uint16_t)value;r->count++;
    }
    r->failed_stage=0;goto done;
failed:
    r->status=(uint8_t)(bus.error?bus.error:C5_PROBE_UNKNOWN);r->failed_stage=bus.stage;
done:
    io->set(io->context,C5_SDA,1);io->set(io->context,C5_SCL,1);
}
#endif
