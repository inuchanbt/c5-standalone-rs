use core::{cell::UnsafeCell, mem::MaybeUninit};
use crate::{App, Frame, PIXELS};

// These globals have one owner: the foreground loop. USB ISR never calls Rust.
struct Shared<T>(UnsafeCell<T>);
unsafe impl<T> Sync for Shared<T> {}
static APP: Shared<MaybeUninit<App>> = Shared(UnsafeCell::new(MaybeUninit::uninit()));
static FRAME: Shared<Frame> = Shared(UnsafeCell::new([0; PIXELS]));

#[unsafe(no_mangle)]
pub extern "C" fn c5_gui_init() { unsafe { App::init_in_place((*APP.0.get()).as_mut_ptr()); } }
#[unsafe(no_mangle)]
pub extern "C" fn c5_gui_poll(keys: u32) { unsafe { (*APP.0.get()).assume_init_mut().poll(keys as u8); } }
#[unsafe(no_mangle)]
pub extern "C" fn c5_gui_render(now: u32) { unsafe { (*APP.0.get()).assume_init_mut().render(&mut *FRAME.0.get(), now); } }
#[unsafe(no_mangle)]
pub extern "C" fn c5_gui_frame() -> *const u16 { FRAME.0.get().cast::<u16>() }
#[unsafe(no_mangle)]
pub extern "C" fn c5_gui_flags() -> u32 { unsafe {
    let app = (*APP.0.get()).assume_init_ref();
    (app.flipped() as u32) | ((app.brightness() as u32) << 8) | ((app.page_code() as u32) << 16)
} }
#[unsafe(no_mangle)]
pub extern "C" fn c5_gui_blocked() -> u32 { unsafe { (*APP.0.get()).assume_init_ref().blocked_actions } }
#[panic_handler]
fn panic(_: &core::panic::PanicInfo) -> ! { unsafe { unsafe extern "C" { fn c5_panic() -> !; } c5_panic() } }

#[unsafe(no_mangle)]
pub unsafe extern "C" fn c5_gui_meter_calibration(data:*const u8)->u32 { unsafe {
    (*APP.0.get()).assume_init_mut().meter.configure(core::slice::from_raw_parts(data,240)) as u32
} }
#[unsafe(no_mangle)]
pub extern "C" fn c5_gui_meter_sample(valid:u32,shunt:u32,bus:u32,tick:u32,now:u32) { unsafe {
    if valid==2 {(*APP.0.get()).assume_init_mut().meter.fault();return;}
    (*APP.0.get()).assume_init_mut().meter.sample(valid!=0,shunt,bus,tick,now);
} }
#[unsafe(no_mangle)]
pub extern "C" fn c5_gui_meter_value(field:u32,now:u32)->u32 { unsafe {
    let meter=&(*APP.0.get()).assume_init_ref().meter;
    let reading=meter.reading(now);
    match field { 0=>reading.is_some() as u32,1=>reading.map_or(0,|r|r.mv),
        2=>reading.map_or(0,|r|r.ma as u32),_=>meter.error as u32 }
} }
