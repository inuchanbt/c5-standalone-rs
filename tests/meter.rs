use c5_standalone::{meter::{Calibration,Meter},ui::Reading,App,PIXELS};
fn settings()->[u8;240] { let mut b=[0;240];checks(&mut b);b }
fn checks(b:&mut [u8;240]) {
    for (a,z) in [(0,0x1b),(0x1c,0x6f),(0x70,0x9f),(0xa0,0xe9)] {
        b[z]=b[a..z].iter().fold(0xa5,|a,v|a^v);
    }
}
#[test] fn conversion_preserves_current_direction_power_and_rounding() {
    let c=Calibration::decode(&settings()).unwrap();
    let positive=c.convert(204800,409600).unwrap();
    let negative=c.convert(((-204800i32) as u32)&0xffffff,409600).unwrap();
    assert_eq!(positive,Reading{mv:5000,ma:1000});
    assert_eq!(negative,Reading{mv:5000,ma:-1000});assert_eq!(negative.mw(),5000);
    assert_eq!(c.convert(16,16),Some(Reading{mv:0,ma:0}));
}
#[test] fn every_checksum_nonfinite_and_bad_span_rejects_settings() {
    for n in [0,0x1c,0x70,0xa0] {let mut b=settings();b[n]^=1;assert!(Calibration::decode(&b).is_none());}
    for val in [f32::NAN,f32::INFINITY,30.0] {let mut b=settings();b[16..20].copy_from_slice(&val.to_le_bytes());checks(&mut b);assert!(Calibration::decode(&b).is_none());}
    let mut b=settings();b[4..8].copy_from_slice(&i32::MAX.to_le_bytes());checks(&mut b);assert!(Calibration::decode(&b).is_none());
    assert!(Calibration::decode(&[0;239]).is_none());
}
#[test] fn old_failed_and_outside_envelope_samples_never_display_or_change_max() {
    let mut m=Meter::new();assert!(m.configure(&settings()));
    m.sample(true,204800,409600,u32::MAX-10,u32::MAX-10);
    assert_eq!(m.reading(20).unwrap().ma,1000);assert!(m.reading(501).is_none());
    m.sample(false,0,0,30,30);assert!(m.reading(30).is_none());assert_eq!(m.peaks.mw,5000);
    m.sample(true,409600,409600,40,40);assert!(m.error);assert!(m.reading(40).is_none());
    m.sample(true,204800,409600,50,50);assert!(m.reading(50).is_none());assert_eq!(m.peaks.mw,5000);
}
#[test] fn invalid_raw_words_and_voltage_are_rejected() {
    let c=Calibration::decode(&settings()).unwrap();
    assert!(c.convert(1,409600).is_none());assert!(c.convert(0x1000000,0).is_none());
    assert!(c.convert(0,500000).is_none());
}
#[test] fn actual_renderer_changes_with_live_sample_and_expires() {
    let mut app=App::new();let mut before=[0;PIXELS];let mut live=[0;PIXELS];let mut stale=[0;PIXELS];
    app.render(&mut before,100);assert!(app.meter.configure(&settings()));
    app.meter.sample(true,204800,409600,100,100);app.render(&mut live,100);
    assert_ne!(before,live);app.render(&mut stale,601);assert_ne!(stale,live);
    assert!(app.meter.reading(601).is_none());assert_eq!(app.meter.peaks.mw,5000);
}
