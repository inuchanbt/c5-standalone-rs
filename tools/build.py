"""Build and audit the GUI-only C5 candidate offline. Never opens USB."""
from pathlib import Path
import argparse
import hashlib
import json
import os
import shutil
import struct
import subprocess
import sys
from package import encode, decode, BOOT_SHA256, APP_START, ERASE_END
from stack_audit import estimate

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RESEARCH = Path('D:/doom_on_km003c/local/c5-research')
DEFAULT_RUST = Path('D:/doom_on_km003c/tools/rustup/toolchains/stable-x86_64-pc-windows-gnu/bin')
DEFAULT_LLVM = Path('D:/doom_on_km003c/tools/llvm-mingw-20261020-ucrt-x86_64/bin')
DEFAULT_CACHE = ROOT / '.cache/cargo'

def sha(data): return hashlib.sha256(data).hexdigest()

def run(args, env=None):
    p = subprocess.run([str(a) for a in args], cwd=ROOT, env=env, text=True, encoding='utf8', errors='replace', stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    if p.returncode:
        print(p.stdout)
        raise RuntimeError(f'Command failed ({p.returncode}): {args[0]}')
    return p.stdout

def environment(rust, llvm, cache):
    env = os.environ.copy()
    env['CARGO_HOME'] = str(cache)
    env['RUSTC'] = str(rust / 'rustc.exe')
    env['RUSTDOC'] = str(rust / 'rustdoc.exe')
    env['PATH'] = str(llvm) + os.pathsep + str(rust) + os.pathsep + env.get('PATH', '')
    env['CARGO_TARGET_X86_64_PC_WINDOWS_GNU_LINKER'] = str(llvm / 'clang.exe')
    env['CARGO_TARGET_X86_64_PC_WINDOWS_GNU_RUSTFLAGS'] = '-C link-self-contained=yes -L native=' + str(rust.parent / 'lib/rustlib/x86_64-pc-windows-gnu/lib/self-contained')
    # Cargo omits target rustflags for host build scripts during a cross build.
    env['LIBRARY_PATH'] = str(rust.parent / 'lib/rustlib/x86_64-pc-windows-gnu/lib/self-contained') + os.pathsep + env.get('LIBRARY_PATH', '')
    return env

def verify_upstream():
    tree = json.loads((ROOT / 'upstream-tree.json').read_text(encoding='utf8'))
    patches = json.loads((ROOT / 'upstream-patches.json').read_text(encoding='utf8'))
    for item in tree['tree']:
        p = ROOT / 'upstream' / item['path']
        data = p.read_bytes()
        if p.suffix not in ('.png', '.webp'):
            data = data.replace(b'\r\n', b'\n')
        blob = hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest()
        if item['path'] in patches:
            patch = patches[item['path']]
            if patch['original_git_blob'] != item['sha'] or sha(data) != patch['patched_sha256']:
                raise ValueError(f'C5 upstream patch changed: {p}')
        elif blob != item['sha']: raise ValueError(f'Upstream input changed: {p}')
    return tree['sha']

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--rust-bin', type=Path, default=DEFAULT_RUST)
    p.add_argument('--llvm-bin', type=Path, default=DEFAULT_LLVM)
    p.add_argument('--cargo-home', type=Path, default=DEFAULT_CACHE)
    p.add_argument('--research', type=Path, default=DEFAULT_RESEARCH)
    p.add_argument('--output-dir', type=Path, default=ROOT / 'build/gui-v0.1.9-meter-display')
    p.add_argument('--host', action='store_true', help='Run host tests and generate previews')
    a = p.parse_args()
    revision = verify_upstream()
    env = environment(a.rust_bin, a.llvm_bin, a.cargo_home)
    cargo = a.rust_bin / 'cargo.exe'
    if a.host:
        print(run([cargo, 'test', '--offline', '--locked', '--tests'], env))
        print(run([cargo, 'run', '--offline', '--locked', '--release', '--example', 'preview'], env))
        return
    # A captured boot image is a build input, never redistributed.
    baseline = a.research / 'c5_stage4/captures/usb-flash-20261116-182819'
    flash = (baseline / 'flash-pass1.bin').read_bytes()
    if flash != (baseline / 'flash-pass2.bin').read_bytes() or sha(flash) != 'fc128f7dccd16a163fbd8836b775befeda72719063a8a62edd1637fa2fc38cef':
        raise ValueError('Verified owner baseline mismatch')
    if sha(flash[:0x3800]) != BOOT_SHA256: raise ValueError('Unsupported bootloader')
    print(run([cargo, 'build', '--offline', '--locked', '--release', '--target', 'thumbv7em-none-eabihf'], env))
    out = a.output_dir.resolve()
    out.mkdir(parents=True, exist_ok=True)
    vec = ['.syntax unified', '.thumb', '.section .vectors,"a",%progbits', '.word 0x20017000', '.word reset_handler']
    vec += ['.word ' + ('systick_handler' if i == 15 else '0x080029ed' if i == 36 else 'fault_handler') for i in range(2, 256)]
    (out / 'vectors.S').write_text('\n'.join(vec) + '\n', encoding='ascii')
    flags = ['--target=thumbv7em-none-eabihf', '-mcpu=cortex-m4', '-mthumb', '-mfpu=fpv4-sp-d16', '-mfloat-abi=hard', '-Oz', '-ffreestanding', '-fno-builtin', '-ffunction-sections', '-fdata-sections', '-fno-unwind-tables', '-fno-asynchronous-unwind-tables']
    clang = a.llvm_bin / 'clang.exe'
    run([clang, *flags, '-Wall', '-Wextra', '-Werror', '-fstack-usage', '-fstack-size-section', '-c', ROOT / 'native/board.c', '-o', out / 'board.o'], env)
    archive = ROOT / 'target/thumbv7em-none-eabihf/release/libc5_standalone.a'
    elf = out / 'c5-gui-v0.1.9-meter-display.elf'
    run([clang, *flags, '-nostdlib', '-fuse-ld=lld', '-Wl,--gc-sections', '-Wl,--build-id=none', '-Wl,-T,' + str(ROOT / 'native/memory.ld'), '-Wl,-Map,' + str(out / 'c5-gui-v0.1.9-meter-display.map'), out / 'vectors.S', out / 'board.o', archive, '-o', elf], env)
    unresolved = run([a.llvm_bin / 'llvm-nm.exe', '--undefined-only', elf], env).strip()
    if unresolved: raise ValueError('Unresolved symbols: ' + unresolved)
    disasm = run([a.llvm_bin / 'llvm-objdump.exe', '-d', '--mcpu=cortex-m4', elf], env)
    (out / 'c5-gui-v0.1.9-meter-display.disasm.txt').write_text(disasm, encoding='utf8')
    stack_sizes = estimate(disasm)
    (out / 'stack-estimates.json').write_text(json.dumps(dict(sorted(stack_sizes.items(),key=lambda p:p[1],reverse=True)),indent=2)+'\n',encoding='utf8')
    if not stack_sizes or max(stack_sizes.values()) > 4096:
        raise ValueError(f'A function stack estimate exceeds 4 KiB; inspect {out / "stack-estimates.json"}')
    raw_path = out / 'c5-gui-v0.1.9-meter-display.raw.bin'
    run([a.llvm_bin / 'llvm-objcopy.exe', '-O', 'binary', elf, raw_path], env)
    raw = raw_path.read_bytes()
    package = encode(raw)
    package_path = out / 'C5-standalone-GUI-v0.1.9-meter-display.c4ser'
    package_path.write_bytes(package)
    sizes = run([a.llvm_bin / 'llvm-size.exe', '-A', elf], env)
    print(sizes)
    sections = {}
    for line in sizes.splitlines():
        fields = line.split()
        if len(fields) == 3 and fields[0].startswith('.') and fields[1].isdigit(): sections[fields[0]] = int(fields[1])
    symbols = run([a.llvm_bin / 'llvm-nm.exe', '--defined-only', elf], env)
    bss_end = next(int(line.split()[0], 16) for line in symbols.splitlines() if line.endswith(' _ebss'))
    manifest = dict(schema='c5-standalone-gui-v0.1.9-meter-display', upstream_revision=revision,
        hardware_tested=False, measurement_driver_ready=False, pd_driver_ready=False,
        package=package_path.name, package_bytes=len(package), package_sha256=sha(package), raw_image_bytes=len(raw),
        boot_sha256=BOOT_SHA256, app_start=hex(APP_START), erase_end_exclusive=hex(ERASE_END),
        initial_sp=hex(struct.unpack_from('<I', raw)[0]), reset_vector=hex(struct.unpack_from('<I', raw, 4)[0]),
        sections=sections, bss_end=hex(bss_end), guard_bytes=0x20015000-bss_end, reserved_stack_bytes=8192,
        framebuffer_bytes=64800, physical_button_order=['Back', 'Left(-)', 'OK', 'Right(+)'],
        button_pins={'Back':'PB14', 'Left':'PB15', 'OK':'PA13', 'Right':'PA14'},
        largest_static_frame_estimate=max(stack_sizes.values()),
        stack_estimated_functions=len(stack_sizes), runtime_flash_programming=False, boot_private_abi=True,
        meter_id_probe=True, meter_id_probe_hardware_tested=False, meter_id_probe_on_startup=False,
        meter_raw_probe=True, meter_raw_probe_hardware_tested=False,
        meter_raw_registers=['0x00','0x01','0x02','0x03','0x04','0x05','0x06'],
        external_storage_read=True, external_storage_read_hardware_tested=False,
        external_storage_value_writes=False, external_storage_range_bytes=2048,
        external_storage_fixed_block_bytes=16,
        i2c_diagnostics_deferred_outside_lcd=True,
        shadow_sampler=True, shadow_sampler_hardware_tested=False,
        shadow_sampler_on_startup=False, shadow_sampler_host_lease_ms=2000,
        shadow_sampler_gui_updates=False, shadow_sampler_reads_diag_alert=False,
        explicit_ready_flag_probe=True, ready_flag_probe_hardware_tested=False,
        ready_flag_probe_diag_reads=8, ready_flag_probe_read_to_clear_side_effects=True,
        ready_flag_probe_on_startup=False,
        shadow_sampler_adc_freshness_qualified=False,
        gated_sampler=True, gated_sampler_hardware_tested=False,
        gated_sampler_on_startup=True, gated_sampler_gui_updates=True,
        experimental_gui_meter=True, gui_meter_hardware_tested=False,
        settings_prefix_dual_read_bytes=240, settings_value_writes=False,
        gui_voltage_limit_V=5.5, gui_current_magnitude_limit_A=1.1,
        gui_cache_expiry_ms=500, gui_max_ram_only=True,
        gui_history_energy_enabled=False, gui_runtime_renews_sampler_lease=True,
        gated_sampler_requires_observed_clear_then_set=True,
        gated_sampler_reads_diag_alert=True, gated_sampler_read_to_clear_side_effects=True,
        gated_sampler_clear_wait_limit_ms=500, gated_sampler_set_wait_limit_ms=500,
        gated_sampler_post_ready_limit_ms=150, gated_sampler_cycle_limit_ms=1200,
        gated_sampler_pair_limit_ms=75, gated_sampler_transaction_limit_ms=12,
        gated_sampler_minimum_cycle_idle_ms=200, gated_sampler_host_lease_ms=2000,
        gated_sampler_delay_spin_divisor=2, gated_sampler_i2c_timing_hardware_qualified=False,
        gated_sampler_adc_freshness_hardware_qualified=False,
        meter_sensor_register_value_writes=False, meter_id_i2c_address='0x40',
        meter_id_pins={'SCL':'PB8', 'SDA':'PB9'},
        stock_v85_payload_sha256='51d57d31a3d3b2fafbc18defcadeedf964bd418e0954543426ac6fc818e51682')
    (out / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf8')
    inputs = [ROOT/'Cargo.toml', ROOT/'Cargo.lock', ROOT/'upstream-tree.json', ROOT/'upstream-patches.json', *list((ROOT/'src').glob('*.rs')), *list((ROOT/'native').glob('*')), *list((ROOT/'tools').rglob('*.py')), *list(ROOT.glob('*.ps1')), *list((ROOT/'tests').glob('*.rs')), *list((ROOT/'examples').glob('*.rs')), ROOT/'upstream/firmware-core/src/power_history.rs']
    (out / 'source-hashes.json').write_text(json.dumps({str(f.relative_to(ROOT)):sha(f.read_bytes()) for f in inputs}, indent=2) + '\n', encoding='utf8')
    print(json.dumps(manifest, indent=2))
    print('Built GUI candidate; physical boot/display/keys remain unverified.')

if __name__ == '__main__': main()
