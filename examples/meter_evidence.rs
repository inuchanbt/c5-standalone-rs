//! Offline verification using private files supplied at runtime, never embedded.
use std::{fs,env,io::Write};
use c5_standalone::{meter::Calibration,App,PIXELS,source_index};
fn main(){
    let args:Vec<_>=env::args().collect();assert_eq!(args.len(),4);
    let settings=fs::read(&args[1]).unwrap();let cal=Calibration::decode(&settings[..240]).unwrap();
    let vectors=fs::read_to_string(&args[2]).unwrap();let mut count=0;let mut app=App::new();
    assert!(app.meter.configure(&settings[..240]));
    for line in vectors.lines(){
        let v:Vec<i64>=line.split_whitespace().map(|s|s.parse().unwrap()).collect();
        assert_eq!(v.len(),4);let r=cal.convert(v[0] as u32,v[1] as u32).unwrap();
        assert_eq!((r.mv,r.ma),(v[2] as u32,v[3] as i32));
        if count==0 {app.meter.sample(true,v[0] as u32,v[1] as u32,1000,1000);}
        count+=1;
    }
    assert!(count>0);let mut frame=[0;PIXELS];app.render(&mut frame,1000);
    let mut f=fs::File::create(&args[3]).unwrap();write!(f,"P6\n320 172\n255\n").unwrap();
    for y in 0..172 {for x in 0..320 {
        let p=source_index(x,y,false).map(|i|frame[i]).unwrap_or(0);
        let (r,g,b)=(((p>>11)&31) as u8,((p>>5)&63) as u8,(p&31) as u8);
        f.write_all(&[(r<<3)|(r>>2),(g<<2)|(g>>4),(b<<3)|(b>>2)]).unwrap();
    }}
    println!("Matched {count} private captured vectors; preview is a host rendering, not a device photo.");
}
