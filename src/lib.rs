//! WITRN C5 GUI adapter. The KWS-X1 renderer and navigation remain unchanged.
#![cfg_attr(target_os = "none", no_std)]

use core::convert::Infallible;
use embedded_graphics::{pixelcolor::{Rgb565, raw::RawU16}, prelude::*};
use embedded_graphics::mono_font::{ascii::FONT_6X10, MonoTextStyle};
use embedded_graphics::text::Text;
use firmware_core::buttons::{self, Detail, Group, Input, Navigation, Page, SettingsFocus, Tab, View};
use firmware_core::power_history::History;
use firmware_core::settings::{BRIGHTNESS_PERCENT, Item, Rotation, Settings};

#[path = "../upstream/firmware/src/ui.rs"]
#[allow(dead_code, unexpected_cfgs)]
pub mod ui;
#[path = "../upstream/firmware/src/single_wire_drive/status.rs"]
#[allow(dead_code)]
pub mod single_wire_drive;
pub mod line_adc {
    pub const REFERENCE_MV: u16 = 1083; // UI-only upstream constant, never used for C5 ADC conversion.
    #[derive(Clone, Copy, Debug, Default, PartialEq, Eq)]
    pub struct LineVoltages { pub dp_mv: u16, pub dm_mv: u16, pub cc1_mv: u16, pub cc2_mv: u16 }
}
pub mod qc_drive {
    #[derive(Clone, Copy, Debug, Default, PartialEq, Eq)]
    pub enum Status {
        #[default] Off,
        Entering,
        Failed(qc_protocol::qc2::Failure),
        Active(qc_protocol::qc2::Voltage, Option<qc_protocol::detect::Outcome>),
        Stepping(u16),
        Detecting(qc_protocol::detect::Stage),
        Detected(qc_protocol::detect::Report),
        Scp(u8, crate::single_wire_drive::Status),
        Fcp(u8, crate::single_wire_drive::Status),
        Afc(u8, crate::single_wire_drive::Status),
    }
}
pub mod meter;
pub mod energy_store {
    #[derive(Clone, Copy, Debug, PartialEq, Eq)]
    pub enum Status { Ready, Occupied, SaveFailed }
}
pub mod settings_store {
    #[derive(Clone, Copy, Debug, PartialEq, Eq)]
    pub enum Status { Saved, NoSpace, WriteFailed }
}

pub const WIDTH: usize = 240;
pub const HEIGHT: usize = 135;
pub const PIXELS: usize = WIDTH * HEIGHT;
pub const LCD_WIDTH: usize = 320;
pub const LCD_HEIGHT: usize = 172;
pub const SCALED_WIDTH: usize = 306;
pub const X_MARGIN: usize = (LCD_WIDTH - SCALED_WIDTH) / 2;
pub type Frame = [u16; PIXELS];

/// Native RGB565, high byte transmitted first by the board adapter.
pub struct Canvas<'a>(pub &'a mut Frame);
impl OriginDimensions for Canvas<'_> {
    fn size(&self) -> Size { Size::new(WIDTH as u32, HEIGHT as u32) }
}
impl DrawTarget for Canvas<'_> {
    type Color = Rgb565;
    type Error = Infallible;
    fn draw_iter<I: IntoIterator<Item = Pixel<Rgb565>>>(&mut self, pixels: I) -> Result<(), Self::Error> {
        for Pixel(p, c) in pixels {
            if p.x >= 0 && p.y >= 0 && (p.x as usize) < WIDTH && (p.y as usize) < HEIGHT {
                self.0[p.y as usize * WIDTH + p.x as usize] = RawU16::from(c).into_inner();
            }
        }
        Ok(())
    }
}

/// Physical scanout coordinate -> logical pixel, including the 180-degree flip.
pub fn source_index(x: usize, y: usize, flipped: bool) -> Option<usize> {
    if x >= LCD_WIDTH || y >= LCD_HEIGHT { return None; }
    let (x,y) = if flipped { (LCD_WIDTH - 1 - x, LCD_HEIGHT - 1 - y) } else { (x,y) };
    if !(X_MARGIN..X_MARGIN + SCALED_WIDTH).contains(&x) { return None; }
    Some(y * HEIGHT / LCD_HEIGHT * WIDTH + (x - X_MARGIN) * WIDTH / SCALED_WIDTH)
}

pub struct App {
    nav: Navigation,
    pub input: Input,
    pub history: History,
    pub meter: meter::Meter,
    pub blocked_actions: u32,
    // A suppressed press stays suppressed through release; no delayed command.
    suppress_ok: bool,
    wait_release: bool,
    settings_notice: bool,
}
impl Default for App { fn default() -> Self { Self::new() } }
impl App {
    pub fn new() -> Self {
        let settings = Settings { rotation: Rotation::Normal, ..Settings::default() };
        let mut nav = Navigation::new(Page::default(), settings);
        nav.set_selectable(false);
        let (input, _) = nav.update(0);
        Self { nav, input, history: History::default(), meter: meter::Meter::new(), blocked_actions: 0, suppress_ok: false, wait_release: false, settings_notice: false }
    }

    /// Initialize the large history directly in its static destination.
    ///
    /// # Safety
    /// `target` must point to aligned writable storage for one App, exclusively
    /// owned by the foreground loop. No field may be read until this returns.
    pub unsafe fn init_in_place(target: *mut Self) {
        let settings = Settings { rotation: Rotation::Normal, ..Settings::default() };
        let mut nav = Navigation::new(Page::default(), settings);
        nav.set_selectable(false);
        let input = nav.update(0).0;
        unsafe {
            core::ptr::addr_of_mut!((*target).nav).write(nav);
            core::ptr::addr_of_mut!((*target).input).write(input);
            core::ptr::addr_of_mut!((*target).history).write(const { History::empty() });
            core::ptr::addr_of_mut!((*target).meter).write(meter::Meter::new());
            core::ptr::addr_of_mut!((*target).blocked_actions).write(0);
            core::ptr::addr_of_mut!((*target).suppress_ok).write(false);
            core::ptr::addr_of_mut!((*target).wait_release).write(false);
            core::ptr::addr_of_mut!((*target).settings_notice).write(false);
        }
    }

    /// Exactly one call per 10 ms physical sampling interval.
    pub fn poll(&mut self, physical_keys: u8) {
        if self.wait_release {
            if physical_keys == 0 { self.wait_release = false; }
            return;
        }
        let raw = if self.flipped() { buttons::swap_arrows(physical_keys) } else { physical_keys };
        let unsupported = match self.input.page {
            Page::Tabs(tab) => matches!(tab.group(), Group::Trigger) || matches!(tab, Tab::Detail { page: Detail::Cable | Detail::Charger | Detail::Pd, .. }),
            Page::Settings(SettingsFocus::Row(item)) => !matches!(item, Item::Brightness | Item::Rotation),
            _ => false,
        };
        if unsupported && raw & buttons::OK != 0 && !self.suppress_ok {
            self.blocked_actions = self.blocked_actions.saturating_add(1);
            self.settings_notice = true;
            self.suppress_ok = true;
        }
        let effective = if self.suppress_ok { raw & !buttons::OK } else { raw };
        let (mut input, command) = self.nav.update(effective);
        // No C5 PD/legacy PHY has been qualified. Every command is discarded.
        if command.is_some() { self.blocked_actions = self.blocked_actions.saturating_add(1); }
        if raw & buttons::OK == 0 { self.suppress_ok = false; }
        // C5 has no qualified orientation sensor. Skip upstream's Auto setting.
        if input.settings.rotation == Rotation::Auto {
            input.settings.rotation = Rotation::Normal;
        }
        if input.settings.rotation != self.input.settings.rotation {
            self.nav = Navigation::new(input.page, input.settings);
            self.nav.set_selectable(false);
            self.wait_release = physical_keys != 0;
        }
        if input.page != self.input.page { self.settings_notice = false; }
        self.input = input;
    }
    pub fn flipped(&self) -> bool { self.input.settings.rotation == Rotation::Flipped }
    pub fn brightness(&self) -> u8 { BRIGHTNESS_PERCENT[self.input.settings.brightness as usize] }
    pub fn page_code(&self) -> u8 {
        match self.input.page.tab() {
            Some(Tab::Overview) => 0, Some(Tab::Lines) => 1, Some(Tab::Energy) => 2,
            Some(Tab::Graph) => 3, Some(Tab::Ripple) => 4, Some(Tab::Fixed) => 5,
            Some(Tab::Pps) => 6, Some(Tab::Avs) => 7, Some(Tab::Qc2) => 8,
            Some(Tab::Qc3) => 9, Some(Tab::Scp) => 10, Some(Tab::Fcp) => 11,
            Some(Tab::Afc) => 12, Some(Tab::Detail { page: Detail::Pd, .. }) => 13,
            Some(Tab::Detail { page: Detail::Charger, .. }) => 14,
            Some(Tab::Detail { page: Detail::Cable, .. }) => 15,
            Some(Tab::Detail { page: Detail::System, .. }) => 16, None => 17,
        }
    }
    pub fn render(&mut self, frame: &mut Frame, now_ms: u32) {
        frame.fill(0);
        let mut canvas = Canvas(frame);
        let tab = self.input.page.tab().unwrap_or(Tab::Overview);
        let group = tab.group();
        let mut tabs = [Tab::Overview; buttons::MAX_TABS];
        let mut count = 0;
        for t in group.available(false) { tabs[count] = t; count += 1; }
        let current = tabs[..count].iter().position(|t| t.same(tab)).unwrap_or(0);
        let header = if matches!(self.input.page, Page::Settings(_)) { ui::Header::Settings } else {
            ui::Header::Tabs { tabs: &tabs[..count], current, group: group.position(false), level: self.input.page.level(), passthrough: false }
        };
        let input = self.input;
        let offer = ui::Offer::default();
        match input.page.view() {
            View::Overview => ui::draw_meter(&mut canvas, &header, &ui::Meter {
                reading: self.meter.reading(now_ms), peaks: self.meter.peaks, protocol: ui::Protocol::Unknown, cc: None,
                flipped: self.flipped(), alive: Rgb565::new(31, 35, 0), pulses: now_ms / 500, reset_hold: 0,
            }),
            View::Lines => ui::draw_lines(&mut canvas, &header, None),
            View::Energy => ui::draw_energy(&mut canvas, &header, Default::default(), Default::default(), energy_store::Status::Ready, 0),
            View::Graph(focus) => ui::draw_graph(&mut canvas, &header, &self.history, input.graph_trace, input.graph_window, focus, 0),
            View::Ripple => ui::draw_ripple(&mut canvas, &header, &ui::Ripple {
                reading: None, reference: None, bus: None, hold: false, timebase: input.ripple_timebase,
                scale: input.ripple_scale, focus: None, clock_hz: None,
            }),
            View::Fixed { .. } => ui::draw_fixed(&mut canvas, &header, &offer, false),
            View::Pps(_) => ui::draw_pps(&mut canvas, &header, &offer, None, None),
            View::Avs { .. } => ui::draw_avs(&mut canvas, &header, &offer, false, None),
            View::Qc2(_) | View::Probe => ui::draw_qc2(&mut canvas, &header, &ui::Qc2 {
                preview: None, request: None, mode: ui::QcMode::Plain, status: qc_drive::Status::Off, qc: Default::default(),
            }),
            View::Qc3 { .. } => ui::draw_qc3(&mut canvas, &header, &ui::Qc3 {
                target_mv: None, adjusting: false, mode: ui::QcMode::Plain, status: qc_drive::Status::Off,
                qc: Default::default(), lines: None, reading: None,
            }),
            View::Scp { .. } => ui::draw_scp(&mut canvas, &header, &ui::Scp {
                probing: false, mode: ui::QcMode::Plain, findings: None, status: None,
                selection: None, focus: None, active: false, reading: None,
            }),
            View::Fcp { .. } => ui::draw_fcp(&mut canvas, &header, &ui::Fcp {
                mode: ui::QcMode::Plain, probing: false, preview: None, adapter: None, request: None, status: None,
            }),
            View::Afc { .. } => ui::draw_afc(&mut canvas, &header, &ui::Afc {
                mode: ui::QcMode::Plain, probing: false, preview: None, adapter: None, request: None, status: None,
            }),
            View::Settings(focus) => {
                ui::draw_settings(&mut canvas, &header, input.settings, focus, settings_store::Status::Saved, 0);
            }
            View::Detail { page, top, scrolling } => {
                let sections = detail_lines(page);
                let view = ui::draw_detail(&mut canvas, &header, page, [sections], top, scrolling);
                self.nav.set_list_end(view.end);
            }
        }
        // Always-visible status replaces upstream's bottom hints in this bring-up.
        for y in 124..HEIGHT { canvas.0[y * WIDTH..(y+1) * WIDTH].fill(0); }
        let message = if self.settings_notice { "C5 DRIVER NOT READY" }
            else if matches!(input.page, Page::Settings(_)) { "DISPLAY ONLY / RAM SETTINGS" }
            else if matches!(input.page.view(), View::Energy | View::Graph(_)) { "HISTORY / ENERGY NOT READY" }
            else if self.meter.error { "METER ERROR / PD NOT READY" }
            else if self.meter.reading(now_ms).is_some() { "EXPERIMENTAL / PD NOT READY" }
            else { "METER WAIT / PD NOT READY" };
        let _ = Text::new(message, Point::new(5, 133), MonoTextStyle::new(&FONT_6X10, Rgb565::YELLOW)).draw(&mut canvas);
    }
    /// Host fixtures select pages without manufacturing readings or PD offers.
    pub fn select_page(&mut self, page: Page) {
        self.nav = Navigation::new(page, self.input.settings);
        self.nav.set_selectable(false);
        self.input = self.nav.update(0).0;
        self.suppress_ok = false;
    }
}

fn detail_lines(page: Detail) -> [[u8; 28]; 8] {
    let mut lines = [[b' '; 28]; 8];
    let source: [&[u8]; 8] = match page {
        Detail::System => [b"WITRN C5 GUI BRING-UP", b"KWS-X1 RUST UI PORT", b"LCD: 320x172 / GUI:240x135", b"KEYS: PB14 PB15 PA13 PA14", b"DISPLAY SETTINGS: RAM ONLY", b"METER: EXP 5.5V / 1.1A MAX", b"PD PHY: NOT READY", b"NO RUNTIME FLASH WRITES"],
        Detail::Pd => [b"C5 PD SESSION", b"PD PHY NOT QUALIFIED", b"NO PD REQUESTS SENT", b"", b"", b"", b"", b""],
        Detail::Charger => [b"C5 CHARGER", b"DRIVER NOT READY", b"CAPABILITIES NOT ACQUIRED", b"NO PD/QC REQUESTS SENT", b"", b"", b"", b""],
        Detail::Cable => [b"C5 CABLE", b"DRIVER NOT READY", b"E-MARKER NOT QUERIED", b"", b"", b"", b"", b""],
    };
    for (row, text) in lines.iter_mut().zip(source) { row[..text.len()].copy_from_slice(text); }
    lines
}

#[cfg(target_os = "none")]
mod ffi;
