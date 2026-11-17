use std::{fs, io::Write, path::Path};
use c5_standalone::{App, Frame, PIXELS, source_index};
use firmware_core::buttons::{Group, Page, SettingsFocus};

fn save(root: &Path, name: &str, app: &mut App, frame: &mut Frame) {
    app.render(frame, 1000);
    let mut f = fs::File::create(root.join(format!("{name}.ppm"))).unwrap();
    write!(f, "P6\n320 172\n255\n").unwrap();
    for y in 0..172 { for x in 0..320 {
        let p = source_index(x, y, app.flipped()).map(|i| frame[i]).unwrap_or(0);
        let r = ((p >> 11) & 31) as u8;
        let g = ((p >> 5) & 63) as u8;
        let b = (p & 31) as u8;
        f.write_all(&[(r << 3) | (r >> 2), (g << 2) | (g >> 4), (b << 3) | (b >> 2)]).unwrap();
    } }
}
fn main() {
    let root = Path::new("build/previews"); fs::create_dir_all(root).unwrap();
    let mut app = App::new(); let mut frame = [0; PIXELS]; let mut index=0;
    for group in Group::ALL { for tab in group.available(false) {
        app.select_page(Page::Tabs(tab)); save(root, &format!("{index:02}"), &mut app, &mut frame); index+=1;
    } }
    app.select_page(Page::Settings(SettingsFocus::Brightness)); save(root, "17-settings", &mut app, &mut frame);
    println!("Saved {index} pages and settings, using the unchanged upstream renderer.");
}
