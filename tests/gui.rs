use c5_standalone::{App, Frame, PIXELS, source_index};
use firmware_core::buttons::{self, Detail, Group, Page, SettingsFocus, Tab};
use firmware_core::settings::Item;

fn tap(app: &mut App, keys: u8) {
    for _ in 0..5 { app.poll(keys); }
    for _ in 0..5 { app.poll(0); }
}

#[test]
fn in_place_startup_matches_normal_constructor() {
    let mut memory = core::mem::MaybeUninit::<App>::uninit();
    unsafe { App::init_in_place(memory.as_mut_ptr()); }
    let mut inplace = unsafe { memory.assume_init() };
    let mut normal = App::new();
    let mut a = [0; PIXELS]; let mut b = [0; PIXELS];
    for key in [0, buttons::RIGHT, buttons::OK, buttons::RIGHT, buttons::BACK] {
        tap(&mut inplace, key); tap(&mut normal, key);
        inplace.render(&mut a, 1000); normal.render(&mut b, 1000);
        assert_eq!(inplace.input, normal.input);
        assert_eq!(inplace.history, normal.history);
        assert_eq!(a, b);
    }
}

#[test]
fn reaches_all_groups_and_monitor_tabs_with_real_button_sequences() {
    let mut app = App::new();
    assert_eq!(app.page_code(), 0);
    tap(&mut app, buttons::RIGHT);
    assert_eq!(app.page_code(), 5);
    tap(&mut app, buttons::RIGHT);
    assert_eq!(app.page_code(), 13);
    tap(&mut app, buttons::RIGHT);
    assert_eq!(app.page_code(), 0);
    tap(&mut app, buttons::OK);
    for expected in [1, 2, 3, 4, 0] {
        tap(&mut app, buttons::RIGHT);
        assert_eq!(app.page_code(), expected);
    }
}

#[test]
fn trigger_actions_stay_closed_and_suppression_does_not_leak_into_next_page() {
    let mut app = App::new();
    for tab in Group::Trigger.available(false) {
        app.select_page(Page::Tabs(tab));
        let before = app.blocked_actions;
        tap(&mut app, buttons::OK);
        assert_eq!(app.input.page, Page::Tabs(tab));
        assert_eq!(app.blocked_actions, before + 1);
        assert_eq!(app.input.trigger, None);
        assert!(!app.input.pd_active);
        for _ in 0..200 { app.poll(buttons::OK); }
        for _ in 0..5 { app.poll(0); }
        assert_eq!(app.input.page, Page::Tabs(tab));
    }
    app.select_page(Page::Tabs(Tab::Overview));
    tap(&mut app, buttons::RIGHT);
    assert_eq!(app.input.page, Page::Tabs(Tab::Lines));
}

#[test]
fn unsupported_settings_do_not_open_and_display_controls_change_in_ram() {
    let mut app = App::new();
    for item in [Item::EnergyMemory, Item::TimerMode, Item::Calibration] {
        app.select_page(Page::Settings(SettingsFocus::Row(item)));
        tap(&mut app, buttons::OK);
        assert_eq!(app.input.page, Page::Settings(SettingsFocus::Row(item)));
    }
    app.select_page(Page::Settings(SettingsFocus::Brightness));
    let old = app.brightness();
    tap(&mut app, buttons::RIGHT);
    assert_ne!(app.brightness(), old);
    app.select_page(Page::Settings(SettingsFocus::Rotation));
    tap(&mut app, buttons::RIGHT);
    assert!(app.flipped());
    // After the flip the physical left arrow is now the viewer's right.
    tap(&mut app, buttons::LEFT);
    assert!(!app.flipped());
    assert_eq!(App::new().brightness(), old);
    assert!(!App::new().flipped());
}

#[test]
fn every_page_renders_without_readings_in_both_orientations() {
    let mut app = App::new();
    let mut frame: Frame = [0; PIXELS];
    let mut rendered = 0;
    for group in Group::ALL {
        for tab in group.available(false) {
            app.select_page(Page::Tabs(tab));
            app.render(&mut frame, 1000);
            assert!(frame.iter().any(|p| *p != 0), "{tab:?}");
            rendered += 1;
        }
    }
    assert_eq!(rendered, 17);
    for detail in [Detail::Pd, Detail::Charger, Detail::Cable, Detail::System] {
        app.select_page(Page::Tabs(Tab::detail(detail)));
        app.render(&mut frame, 0);
    }
    app.select_page(Page::Settings(SettingsFocus::Rotation));
    tap(&mut app, buttons::RIGHT);
    for group in Group::ALL {
        for tab in group.available(false) {
            app.select_page(Page::Tabs(tab));
            app.render(&mut frame, 2000);
            assert!(app.flipped());
        }
    }
}

#[test]
fn scaling_covers_every_logical_pixel_and_flips_exactly() {
    let mut seen = [false; PIXELS];
    for y in 0..172 {
        for x in 0..320 {
            let index = source_index(x, y, false);
            assert_eq!(index, source_index(319-x, 171-y, true));
            if let Some(index) = index { assert!(index < PIXELS); seen[index] = true; }
            else { assert!(x < 7 || x >= 313); }
        }
    }
    assert!(seen.iter().all(|b| *b));
    assert_eq!(source_index(7, 0, false), Some(0));
    assert_eq!(source_index(312, 171, false), Some(PIXELS-1));
    assert_eq!(source_index(320, 0, false), None);
    assert_eq!(source_index(0, 172, false), None);
}
