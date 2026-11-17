"""Read-only dual DFU readback and bounded installation audit for this build."""
import argparse
import datetime as dt
import hashlib
import json
from pathlib import Path
import subprocess
import sys
from package import audit, BOOT_SHA256

ROOT=Path(__file__).resolve().parents[1]
BASELINE=Path('D:/doom_on_km003c/local/c5-research/c5_stage4/captures/usb-flash-20261116-182819/flash-pass1.bin')

def verified_source_root(build):
    frozen=build/'source-snapshot'
    source=frozen if frozen.is_dir() else ROOT
    for name,digest in json.loads((build/'source-hashes.json').read_text(encoding='utf8')).items():
        if hashlib.sha256((source/name).read_bytes()).hexdigest()!=digest:
            raise ValueError('Recorded build source changed: '+str(source/name))
    return source

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--dfu',action='store_true',help='The user has placed the C5 in DFU')
    p.add_argument('--baseline',type=Path,default=BASELINE)
    p.add_argument('--build-dir',type=Path,default=ROOT/'build/gui-v0.1.9-meter-display')
    a=p.parse_args()
    if not a.dfu:p.error('--dfu is required; enter DFU with OK held')
    build=a.build_dir.resolve();manifest=json.loads((build/'manifest.json').read_text(encoding='utf8'))
    package=build/manifest['package'];data=package.read_bytes();baseline=a.baseline.read_bytes()
    if hashlib.sha256(data).hexdigest()!=manifest['package_sha256']:raise ValueError('Package differs from the build manifest')
    if hashlib.sha256(baseline).hexdigest()!='fc128f7dccd16a163fbd8836b775befeda72719063a8a62edd1637fa2fc38cef':raise ValueError('Baseline mismatch')
    if hashlib.sha256(baseline[:0x3800]).hexdigest()!=BOOT_SHA256:raise ValueError('Bootloader mismatch')
    source=verified_source_root(build)
    out=build/'captures'/('dfu-'+dt.datetime.now().strftime('%Y%m%d-%H%M%S'))
    out.mkdir(parents=True,exist_ok=False);proof=out/'probe.json';dump=out/'dual-read'
    subprocess.run([sys.executable,'-X','utf8',str(source/'tools/dfu/c5_probe.py'),'--dfu','--read-info','--output',str(proof)],check=True)
    subprocess.run([sys.executable,'-X','utf8',str(source/'tools/dfu/c5_backup.py'),'--dfu','--probe-json',str(proof),'--output-dir',str(dump)],check=True)
    first=(dump/'flash-pass1.bin').read_bytes();second=(dump/'flash-pass2.bin').read_bytes()
    if first!=second:raise ValueError('Two readbacks differ')
    result=audit(first,data,baseline)
    result['actual_sha256']=hashlib.sha256(first).hexdigest()
    result['verified_source_root']=str(source)
    (out/'audit.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf8')
    print(json.dumps(result,indent=2));print('Evidence:',out)
    return 0 if result['passed'] else 3

if __name__=='__main__':raise SystemExit(main())
