//! Experimental C5 stock conversion. No settings values are embedded.
use crate::ui::{Reading, Peaks};

#[derive(Clone, Copy)]
pub struct Calibration { vd: f32, id: f32, zero: f32, vr: f64, ir: f64 }
impl Calibration {
    pub fn decode(data: &[u8]) -> Option<Self> {
        if data.len()!=240 { return None; }
        for (start,end) in [(0,0x1b),(0x1c,0x6f),(0x70,0x9f),(0xa0,0xe9)] {
            if data[start..end].iter().fold(0xa5,|a,b|a^b)!=data[end] { return None; }
        }
        let integer=|n| i32::from_le_bytes(data[n..n+4].try_into().unwrap()) as i64;
        let float=|n| f32::from_le_bytes(data[n..n+4].try_into().unwrap());
        let vd=204800+integer(4)+integer(0x4f);
        let id=409600+integer(0x0c)+integer(0x53)-integer(8);
        let vr=10.0+float(0x10) as f64;let ir=2.0+float(0x14) as f64;
        // Conservative acceptance around the stock endpoints, not calibration.
        if !(102400..=409600).contains(&vd)||!(204800..=819200).contains(&id)
            || !vr.is_finite()||!ir.is_finite()||!(9.0..=11.0).contains(&vr)
            ||!(1.0..=3.0).contains(&ir)||integer(8).abs()>40960 { return None; }
        Some(Self { vd:vd as f32,id:id as f32,zero:integer(8) as f32,vr,ir })
    }
    pub fn convert(&self,shunt:u32,bus:u32)->Option<Reading> {
        if shunt>0xffffff||bus>0xffffff||(shunt|bus)&15!=0 { return None; }
        let q=((shunt as i32)<<8)>>8;
        let v=((((bus>>2)&0x3ffffc) as f32 as f64)*self.vr/self.vd as f64) as f32;
        let mut i=(((q as f32-self.zero) as f64)*self.ir/self.id as f64) as f32;
        if (-0.002f32..=0.001f32).contains(&i) { i=0.0; }
        // This first display is bounded to the physically compared 5 V bench.
        if !v.is_finite()||!i.is_finite()||!(0.0..=5.5).contains(&v)||i.abs()>1.1 { return None; }
        Some(Reading { mv:(v*1000.0+0.5) as u32,ma:(i*1000.0+if i<0.0 {-0.5}else{0.5}) as i32 })
    }
}

pub struct Meter {
    calibration:Option<Calibration>,reading:Option<Reading>,tick:u32,
    pub peaks:Peaks,pub error:bool,
}
impl Meter {
    pub fn fault(&mut self) { self.error=true;self.reading=None; }
    pub const fn new()->Self { Self { calibration:None,reading:None,tick:0,
        peaks:Peaks{mv:0,ma:0,mw:0},error:false } }
    pub fn configure(&mut self,bytes:&[u8])->bool {
        self.calibration=Calibration::decode(bytes);self.reading=None;
        self.error=self.calibration.is_none();!self.error
    }
    pub fn sample(&mut self,valid:bool,shunt:u32,bus:u32,tick:u32,now:u32) {
        if !valid||now.wrapping_sub(tick)>500 { self.reading=None;return; }
        if self.error { self.reading=None;return; }
        self.reading=self.calibration.and_then(|c|c.convert(shunt,bus));self.tick=tick;
        if let Some(r)=self.reading { self.peaks.update(r); } else {self.error=true;}
    }
    pub fn reading(&self,now:u32)->Option<Reading> {
        if now.wrapping_sub(self.tick)>500 {None}else{self.reading}
    }
}
