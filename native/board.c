/* SPDX-License-Identifier: GPL-2.0-or-later
 * WITRN C5 board adapter, based on the physically tested C5 DOOM bring-up.
 * Boot private ABI: owner's 2024-08-06 image only. No PD/ADC/flash drivers.
 */
#include <stdint.h>
#include <stddef.h>
#include "buttons.h"
#include "meter_probe.h"
#include "diagnostic_queue.h"
#include "meter_sampler.h"
#include "meter_fresh.h"
#include "meter_gated.h"
#include "meter_settings.h"
#define REG(a) (*(volatile uint32_t *)(a))
#define BYTE(a) (*(volatile uint8_t *)(a))
#define CALL0(a) ((uint32_t (*)(void))((a)|1u))
#define CALL1(a) ((void (*)(uint32_t))((a)|1u))
#define CALL2(a) ((void (*)(uint32_t,uint32_t))((a)|1u))
#define CALL3(a) ((void (*)(uint32_t,uint32_t,uint32_t))((a)|1u))
#define TICKS REG(0x2000013c)
extern uint32_t _sdata[],_edata[],_sidata[],_sbss[],_ebss[];
extern void c5_gui_init(void),c5_gui_poll(uint32_t),c5_gui_render(uint32_t);
extern uint32_t c5_gui_flags(void),c5_gui_blocked(void);
extern const uint16_t *c5_gui_frame(void);
extern unsigned c5_gui_meter_calibration(const uint8_t *);
extern void c5_gui_meter_sample(unsigned,unsigned,unsigned,unsigned,unsigned);
extern unsigned c5_gui_meter_value(unsigned,unsigned);
static uint32_t frames,clock_hz,last_poll,max_poll_gap,present_ms;
static unsigned usb_ready,gui_ready,keys,state,error;
static unsigned presenting_lcd;
static struct c5_diagnostic_queue diagnostic_queue;
static struct c5_sampler sampler;
static struct c5_gated_sampler gated;
static struct c5_settings_load meter_settings;
static unsigned display_enabled,display_started;
static uint32_t settings_next;
static uint32_t display_sequence,display_tick;
static void display_step(void);
static void service(void);
static void meter_status(uint8_t *out,unsigned raw);
static void storage_status(uint8_t *out,unsigned block);
static void diagnostic_reply(unsigned command,const uint8_t *prefix);
static void sampler_reply(unsigned command,const uint8_t *prefix);
static unsigned sampler_read(void *,unsigned,unsigned,uint32_t *,uint32_t *);
static void fresh_status(uint8_t *out);
static void gated_reply(unsigned command,const uint8_t *prefix);
static unsigned gated_read(void *,unsigned,unsigned,uint32_t *,uint32_t *);

// Rust and compiler-builtins may reference these freestanding memory helpers.
void *memcpy(void *dst,const void *src,size_t n){uint8_t*d=dst;const uint8_t*s=src;while(n--)*d++=*s++;return dst;}
void *memset(void *dst,int v,size_t n){uint8_t*d=dst;while(n--)*d++=(uint8_t)v;return dst;}
void *memmove(void *dst,const void *src,size_t n){uint8_t*d=dst;const uint8_t*s=src;if(d<s)for(size_t i=0;i<n;i++)d[i]=s[i];else while(n){n--;d[n]=s[n];}return dst;}
int memcmp(const void *a,const void *b,size_t n){const uint8_t*x=a,*y=b;while(n--){int d=*x++-*y++;if(d)return d;}return 0;}
int bcmp(const void *a,const void *b,size_t n){return memcmp(a,b,n);}

void systick_handler(void){TICKS++;}
static unsigned raw_keys(void){unsigned a=REG(0x40010808),b=REG(0x40010c08);return c5_keys_from_gpio(a,b);}
static unsigned guard_free(void){const volatile uint32_t*p=_ebss;while((uintptr_t)p<0x20015000u&&*p==0xa55aa55au)p++;return (unsigned)((uintptr_t)p-(uintptr_t)_ebss);}
static void put32(uint8_t*p,uint32_t v){for(unsigned i=0;i<4;i++)p[i]=(uint8_t)(v>>(i*8));}
static void service(void){
    uint32_t now=TICKS,gap=now-last_poll;
    if(gui_ready&&gap>=10){last_poll=now;if(gap>max_poll_gap)max_poll_gap=gap;keys=raw_keys();c5_gui_poll(keys);}
    if(!usb_ready)return;
    uint8_t prefix[16];unsigned pending=c5_diagnostic_take(&diagnostic_queue,presenting_lcd,prefix);
    if(pending){diagnostic_reply(pending,prefix);return;}
    volatile uint8_t*rx=(volatile uint8_t*)0x200001e4;
    if(!rx[8]||!((unsigned(*)(unsigned))0x08002ba9)(1))return;
    uint8_t req[64];
    __asm volatile("cpsid i":::"memory");for(unsigned i=0;i<64;i++)req[i]=rx[i];rx[8]=0;__asm volatile("cpsie i":::"memory");
    CALL0(0x0800289c)();
    // Never call the bootloader DFU dispatcher; only bounded app commands follow.
    if(req[9]!=16||req[10]!='C'||req[11]!='5'||req[13]!='1')return;
    if(req[8]==0xa8&&req[12]=='V'){
        uint8_t out[52];for(unsigned i=0;i<16;i++)out[i]=req[10+i];
        uint32_t words[]={meter_settings.state,meter_settings.error,display_enabled,
            c5_gui_meter_value(0,now),c5_gui_meter_value(1,now),c5_gui_meter_value(2,now),
            display_sequence,display_sequence?now-display_tick:0xffffffffu,c5_gui_meter_value(3,now)};
        for(unsigned i=0;i<9;i++)put32(out+16+i*4,words[i]);
        ((void(*)(unsigned,const void*,unsigned))0x08002ec1)(0xa9,out,52);return;
    }
    if(req[12]=='S'&&(req[8]==0x98||req[8]==0x9a||req[8]==0x9c)){
        sampler_reply(req[8],req+10);return;
    }
    if(req[12]=='N'&&(req[8]==0xa0||req[8]==0xa2||req[8]==0xa4||req[8]==0xa6)){
        gated_reply(req[8],req+10);return;
    }
    if((req[8]==0x9e&&req[12]=='F')||(req[8]==0x96&&req[12]=='E')||(req[8]==0x92&&req[12]=='M')||(req[8]==0x94&&req[12]=='R')){
        if(c5_diagnostic_defer(&diagnostic_queue,presenting_lcd,req[8],req+10))return;
        diagnostic_reply(req[8],req+10);
        return;
    }
    if(req[8]!=0x90||req[12]!='G')return;
    uint8_t out[52];for(unsigned i=0;i<16;i++)out[i]=req[10+i];
    out[16]=(uint8_t)state;out[17]=(uint8_t)keys;out[18]=(uint8_t)error;out[19]=0;
    put32(out+20,now);put32(out+24,frames);put32(out+28,present_ms);
    put32(out+32,clock_hz);put32(out+36,guard_free());put32(out+40,gui_ready?c5_gui_flags():0);
    put32(out+44,max_poll_gap);put32(out+48,gui_ready?c5_gui_blocked():0);
    ((void(*)(unsigned,const void*,unsigned))0x08002ec1)(0x91,out,52);
}
static void diagnostic_reply(unsigned command,const uint8_t *prefix){
    uint8_t out[52];for(unsigned i=0;i<16;i++)out[i]=prefix[i];
    if(command==0x9e){
        fresh_status(out+16);
        ((void(*)(unsigned,const void*,unsigned))0x08002ec1)(0x9f,out,52);
    }else if(command==0x96){
        unsigned block=0;for(unsigned i=0;i<4;i++)block|=(unsigned)prefix[4+i]<<(8*i);
        storage_status(out+16,block);
        ((void(*)(unsigned,const void*,unsigned))0x08002ec1)(0x97,out,44);
    }else{
        unsigned raw=command==0x94;meter_status(out+16,raw);
        ((void(*)(unsigned,const void*,unsigned))0x08002ec1)(raw?0x95:0x93,out,raw?52:36);
    }
}
/* Stock V8.5 uses PB8 clock/PB9 data for address 0x40. Read only the ID or
 * fixed raw registers on explicit host requests; leave configuration untouched.
 * Release=weak pull-up input; low=output with latch zero. Never drive high.
 */
struct meter_context { uint32_t started;unsigned loops,deadline_ms; };
static void meter_line(void *context,unsigned line,unsigned released){
    (void)context;unsigned pin=8+line,shift=line*4;
    if(released){
        REG(0x40010c04)=(REG(0x40010c04)&~(15u<<shift))|(8u<<shift);
        REG(0x40010c10)=1u<<pin;
    }else{
        REG(0x40010c14)=1u<<pin;
        REG(0x40010c04)=(REG(0x40010c04)&~(15u<<shift))|(2u<<shift);
    }
}
static unsigned meter_get(void *context,unsigned line){
    (void)context;return !!(REG(0x40010c08)&(1u<<(8+line)));
}
static int meter_pause_divisor(void *context,unsigned divisor){
    struct meter_context *c=context;
    if((uint32_t)(TICKS-c->started)>=c->deadline_ms||++c->loops>c->deadline_ms*200u)return 0;
    for(volatile unsigned i=0;i<clock_hz/(1000000u*divisor);i++)__asm volatile("nop");
    return 1;
}
static int meter_pause(void *context){return meter_pause_divisor(context,1);}
/* Experimental sensor-only reader. Half the spin count, same released-line
 * waveform and deadlines. Actual I2C timing still needs physical qualification;
 * ordinary diagnostics and external storage retain their tested delay.
 */
static int gated_pause(void *context){return meter_pause_divisor(context,2);}
static void fresh_status(uint8_t *out){
    struct c5_fresh_result r={0};
    if(!gui_ready)r.status=C5_PROBE_NOT_READY;
    else if(!meter_settings.state||c5_sampling_active(&sampler)||c5_sampling_active(&gated.s))r.status=C5_PROBE_BUSY;
    else{
        struct meter_context context={TICKS,0,60};
        const struct c5_meter_io io={&context,meter_line,meter_get,meter_pause};
        c5_meter_fresh_probe(&io,&r);r.elapsed_ms=TICKS-context.started;
    }
    out[0]=r.status;out[1]=r.kind;out[2]=r.idle_lines;out[3]=r.count;
    uint16_t words[]={r.config,r.adc,r.manufacturer,r.device};
    for(unsigned i=0;i<4;i++){out[4+i*2]=(uint8_t)words[i];out[5+i*2]=(uint8_t)(words[i]>>8);}
    for(unsigned i=0;i<8;i++){out[12+i*2]=(uint8_t)r.diag[i];out[13+i*2]=(uint8_t)(r.diag[i]>>8);}
    put32(out+28,r.elapsed_ms);put32(out+32,r.failed_stage);
}
static unsigned sample_read(unsigned reg,unsigned count,uint32_t *value,uint32_t *elapsed,int (*pause)(void *)){
    struct meter_context context={TICKS,0,12};
    const struct c5_meter_io io={&context,meter_line,meter_get,pause};
    struct c5_meter_bus bus={&io,0,0};unsigned error=0;
    meter_line(&context,C5_SDA,1);meter_line(&context,C5_SCL,1);
    if(!c5_meter_step(&bus))error=bus.error;
    else if(!meter_get(&context,C5_SCL)||!meter_get(&context,C5_SDA))error=C5_PROBE_BUSY;
    else if(!c5_meter_read_register(&bus,reg,count,value))error=bus.error?bus.error:C5_PROBE_UNKNOWN;
    meter_line(&context,C5_SDA,1);meter_line(&context,C5_SCL,1);
    *elapsed=TICKS-context.started;return error;
}
static unsigned sampler_read(void *unused,unsigned reg,unsigned count,uint32_t *value,uint32_t *elapsed){
    (void)unused;return sample_read(reg,count,value,elapsed,meter_pause);
}
static unsigned gated_read(void *unused,unsigned reg,unsigned count,uint32_t *value,uint32_t *elapsed){
    (void)unused;return sample_read(reg,count,value,elapsed,gated_pause);
}
static void sampler_reply(unsigned command,const uint8_t *prefix){
    uint32_t now=TICKS;
    if(command==0x98){
        if(!meter_settings.state||c5_sampling_active(&gated.s)){sampler.state=C5_SAMPLE_FAULT;sampler.error=C5_PROBE_BUSY;}
        else if(gui_ready)c5_sampler_start(&sampler,now);
        else{sampler.state=C5_SAMPLE_FAULT;sampler.error=C5_PROBE_NOT_READY;}
    }
    if(command==0x9a&&(sampler.state==C5_SAMPLE_IDENTIFY||sampler.state==C5_SAMPLE_RUNNING))sampler.heartbeat=now;
    if(command==0x9c)sampler.state=C5_SAMPLE_OFF;
    uint8_t out[52];for(unsigned i=0;i<16;i++)out[i]=prefix[i];
    out[16]=(uint8_t)sampler.state;out[17]=(uint8_t)sampler.phase;out[18]=(uint8_t)sampler.error;
    out[19]=(uint8_t)((sampler.sequence?1:0)|(c5_sampler_current(&sampler,now)?2:0)|4);
    uint32_t words[]={sampler.sequence,sampler.sample_tick,sampler.sequence?now-sampler.sample_tick:0xffffffffu,sampler.shunt,sampler.bus};
    for(unsigned i=0;i<5;i++)put32(out+20+i*4,words[i]);
    uint16_t shorts[]={sampler.config,sampler.adc,sampler.max_transaction_ms,sampler.max_pair_ms,sampler.pair_ms,sampler.cycle_ms};
    for(unsigned i=0;i<6;i++){out[40+i*2]=(uint8_t)shorts[i];out[41+i*2]=(uint8_t)(shorts[i]>>8);}
    ((void(*)(unsigned,const void*,unsigned))0x08002ec1)(command+1,out,52);
}
static void gated_reply(unsigned command,const uint8_t *prefix){
    uint32_t now=TICKS;struct c5_sampler *s=&gated.s;
    if(command==0xa0){
        if(!meter_settings.state||c5_sampling_active(&sampler))c5_gated_fail(s,C5_PROBE_BUSY);
        else if(gui_ready)c5_gated_start(&gated,now);
        else c5_gated_fail(s,C5_PROBE_NOT_READY);
    }
    if((command==0xa2||command==0xa6)&&c5_sampling_active(s))s->heartbeat=now;
    if(command==0xa4){s->state=C5_SAMPLE_OFF;display_enabled=0;display_started=1;}
    uint8_t out[52];for(unsigned i=0;i<16;i++)out[i]=prefix[i];
    if(command==0xa6){
        uint32_t words[]={s->sequence,gated.sample_clear_tick,gated.sample_ready_tick,
            gated.diag_reads,gated.clear_events,gated.ready_events,gated.max_gate_ms,s->cycle_ms,gated.last_diag};
        for(unsigned i=0;i<9;i++)put32(out+16+i*4,words[i]);
    }else{
        out[16]=(uint8_t)s->state;out[17]=(uint8_t)s->phase;out[18]=(uint8_t)s->error;
        out[19]=(uint8_t)((s->sequence?5:0)|(c5_sampler_current(s,now)?2:0)|8);
        uint32_t words[]={s->sequence,s->sample_tick,s->sequence?now-s->sample_tick:0xffffffffu,s->shunt,s->bus};
        for(unsigned i=0;i<5;i++)put32(out+20+i*4,words[i]);
        uint16_t shorts[]={s->config,s->adc,s->max_transaction_ms,s->pair_ms,gated.gate_ms,s->cycle_ms};
        for(unsigned i=0;i<6;i++){out[40+i*2]=(uint8_t)shorts[i];out[41+i*2]=(uint8_t)(shorts[i]>>8);}
    }
    ((void(*)(unsigned,const void*,unsigned))0x08002ec1)(command+1,out,52);
}
static void meter_status(uint8_t *out,unsigned raw){
    struct meter_context context={TICKS,0,raw?50u:25u};
    const struct c5_meter_io io={&context,meter_line,meter_get,meter_pause};
    if(raw){
        struct c5_meter_raw_result r={0};
        if(!gui_ready)r.status=C5_PROBE_NOT_READY;
        else if(!meter_settings.state||c5_sampling_active(&gated.s))r.status=C5_PROBE_BUSY;
        else{c5_meter_raw_probe(&io,&r);r.elapsed_ms=TICKS-context.started;}
        out[0]=r.status;out[1]=r.kind;out[2]=r.idle_lines;out[3]=0;
        uint16_t words[]={r.valid_mask,r.config,r.adc_config,r.shunt_cal,r.shunt_tempco,r.die_temp};
        for(unsigned i=0;i<6;i++){out[4+i*2]=(uint8_t)words[i];out[5+i*2]=(uint8_t)(words[i]>>8);}
        put32(out+16,r.shunt_raw);put32(out+20,r.bus_raw);put32(out+24,r.elapsed_ms);
        put32(out+28,r.failed_stage);put32(out+32,r.successful_reads);return;
    }
    struct c5_meter_result r={0};
    if(!gui_ready)r.status=C5_PROBE_NOT_READY;
    else if(!meter_settings.state||c5_sampling_active(&gated.s))r.status=C5_PROBE_BUSY;
    else{
        c5_meter_probe(&io,&r);r.elapsed_ms=TICKS-context.started;
    }
    out[0]=r.status;out[1]=r.kind;out[2]=r.idle_lines;out[3]=r.valid_mask;
    uint16_t words[]={r.manufacturer_3e,r.device_3f,r.manufacturer_fe,r.device_ff};
    for(unsigned i=0;i<4;i++){out[4+i*2]=(uint8_t)words[i];out[5+i*2]=(uint8_t)(words[i]>>8);}
    put32(out+12,r.elapsed_ms);
    out[16]=(uint8_t)r.failed_stage;out[17]=(uint8_t)(r.failed_stage>>8);
    out[18]=(uint8_t)r.successful_reads;out[19]=(uint8_t)(r.successful_reads>>8);
}
static void storage_status(uint8_t *out,unsigned block){
    struct c5_storage_result r={0};
    if(!gui_ready){r.status=C5_PROBE_NOT_READY;if(block<128)r.offset=(uint16_t)(block*16);}
    else if(!meter_settings.state||c5_sampling_active(&gated.s))r.status=C5_PROBE_BUSY;
    else{
        struct meter_context context={TICKS,0,50};
        const struct c5_meter_io io={&context,meter_line,meter_get,meter_pause};
        c5_storage_read_block(&io,block,&r);r.elapsed_ms=TICKS-context.started;
    }
    out[0]=r.status;out[1]=r.count;out[2]=r.idle_lines;out[3]=0;
    out[4]=(uint8_t)r.offset;out[5]=(uint8_t)(r.offset>>8);
    out[6]=(uint8_t)r.failed_stage;out[7]=(uint8_t)(r.failed_stage>>8);
    put32(out+8,r.elapsed_ms);for(unsigned i=0;i<16;i++)out[12+i]=r.data[i];
}
static unsigned display_storage_read(void *unused,unsigned block,uint8_t *data){
    (void)unused;struct c5_storage_result r={0};
    struct meter_context context={TICKS,0,50};
    const struct c5_meter_io io={&context,meter_line,meter_get,meter_pause};
    c5_storage_read_block(&io,block,&r);
    if(r.status||r.count!=16)return r.status?r.status:22;
    for(unsigned i=0;i<16;i++)data[i]=r.data[i];return 0;
}
static void display_step(void){
    if(presenting_lcd||!gui_ready)return;
    if(!meter_settings.state){
        if((int32_t)(TICKS-settings_next)<0)return;
        c5_settings_step(&meter_settings,display_storage_read,0,c5_gui_meter_calibration);
        settings_next=TICKS+10;return;
    }
    if(meter_settings.state==1&&!display_started){
        display_started=1;display_enabled=1;c5_gated_start(&gated,TICKS);
    }
    if(display_enabled&&c5_sampling_active(&gated.s))gated.s.heartbeat=TICKS;
    unsigned valid=meter_settings.state==2||gated.s.state==C5_SAMPLE_FAULT?2:
        (meter_settings.state==1&&c5_sampler_current(&gated.s,TICKS));
    c5_gui_meter_sample(valid,gated.s.shunt,gated.s.bus,gated.s.sample_tick,TICKS);
    if(valid==1){display_sequence=gated.s.sequence;display_tick=gated.s.sample_tick;}
    if(c5_gui_meter_value(3,TICKS)){
        display_enabled=0;c5_gated_fail(&gated.s,23);
    }
}
void c5_panic(void) __attribute__((noreturn));
void c5_panic(void){state=3;error=2;gui_ready=0;for(;;)service();}
void fault_handler(void) __attribute__((naked));
void fault_handler(void){__asm volatile("cpsid i\n1: b 1b");}

#define SPI_STATUS (*(volatile uint16_t *)0x40003c08)
#define SPI_DATA (*(volatile uint16_t *)0x40003c0c)
static int present(void){
    presenting_lcd=1;
    const uint16_t*frame=c5_gui_frame();unsigned flip=c5_gui_flags()&1u;
    CALL3(0x08001d70)(0x2a,0,319);CALL3(0x08001d70)(0x2b,34,205);CALL1(0x08001d4c)(0x2c);
    REG(0x40010c10)=0x10;REG(0x40010814)=0x8000;
    uint32_t start=TICKS;
    for(unsigned y=0;y<172;y++){
        unsigned sy=(flip?171-y:y)*135/172;
        for(unsigned x=0;x<320;x++){
            unsigned sx=flip?319-x:x;uint16_t color=0;
            if(sx>=7&&sx<313)color=frame[sy*240+(sx-7)*240/306];
            while(!(SPI_STATUS&2u))if((uint32_t)(TICKS-start)>250)goto fail;
            SPI_DATA=color;
        }
        service();
    }
    while(SPI_STATUS&128u)if((uint32_t)(TICKS-start)>250)goto fail;
    REG(0x40010810)=0x8000;present_ms=TICKS-start;frames++;presenting_lcd=0;return 1;
fail:REG(0x40010810)=0x8000;presenting_lcd=0;return 0;
}
void reset_handler(void){
    __asm volatile("cpsid i");REG(0xe000e010)=0;
    for(unsigned i=0;i<8;i++){REG(0xe000e180+i*4)=0xffffffffu;REG(0xe000e280+i*4)=0xffffffffu;}
    REG(0xe000ed04)=(1u<<25)|(1u<<27);REG(0xe000ed08)=0x08004000;REG(0xe000ed88)|=0xfu<<20;
    __asm volatile("dsb\nisb");
    uint32_t*p=_sdata;const uint32_t*q=_sidata;while(p<_edata)*p++=*q++;
    p=_sbss;while(p<_ebss)*p++=0;
    for(p=_ebss;(uintptr_t)p<0x20015000u;p++)*p=0xa55aa55au;
    uint32_t hash=2166136261u;for(unsigned i=0;i<0x3800;i++)hash=(hash^BYTE(0x08000000+i))*16777619u;
    if(hash!=0x966c2a7fu)fault_handler();
    REG(0x20000100)=CALL0(0x08002b14)();clock_hz=REG(0x20000108);
    if(clock_hz<8000000||clock_hz>240000000)fault_handler();
    TICKS=0;REG(0xe000e014)=clock_hz/1000-1;REG(0xe000e018)=0;REG(0xe000e010)=7;
    __asm volatile("movs r0,#0\nmsr basepri,r0\ncpsie i":::"r0","memory");
    CALL1(0x08001bcc)(120);CALL1(0x08001d4c)(0x36);CALL1(0x08001db0)(0x6000);CALL1(0x08001e34)(60);
    struct{uint16_t pins;uint8_t speed,mode;}cfg={0xc000,2,0x48};
    ((void(*)(uint32_t,const void*))0x08000f7d)(0x40010c00,&cfg);cfg.pins=0x6000;
    ((void(*)(uint32_t,const void*))0x08000f7d)(0x40010800,&cfg);
    BYTE(0x200001ec)=0;BYTE(0x2000022c)=0;CALL0(0x08002a38)();usb_ready=1;state=1;
    c5_gui_init();gui_ready=1;last_poll=TICKS;state=2;
    unsigned brightness=0;uint32_t last_frame=TICKS-100;
    for(;;){
        service();
        display_step();
        if(gui_ready)c5_sampler_step(&sampler,TICKS,presenting_lcd,sampler_read,0);
        if(gui_ready)c5_gated_step(&gated,TICKS,presenting_lcd,gated_read,0);
        if((uint32_t)(TICKS-last_frame)>=100){
            last_frame=TICKS;c5_gui_render(TICKS);
            unsigned desired=(c5_gui_flags()>>8)&255u;
            if(desired!=brightness){CALL1(0x08001e34)(desired);brightness=desired;}
            if(!present()){state=3;error=1;gui_ready=0;for(;;)service();}
            if(guard_free()<1024){state=3;error=3;gui_ready=0;for(;;)service();}
        }
        __asm volatile("wfi");
    }
}
