"""Owner C5/ASD/CY4500 5 V comparison using the existing instrument CLIs.

No firmware/IC writes. ASD load control is bounded to Fixed 5 V and <=1 A.
ASD/CY source files are imported read-only; all new artifacts stay in C5 build/.
"""
import argparse
import contextlib
import datetime as dt
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import secrets
import sys
import threading
import time

import monitor
import probe_meter

ROOT = Path(__file__).resolve().parents[1]
ASD = Path('D:/ASD-PD31/src/current/asd_pd31_cli.py')
CY = Path('D:/CY4500EPR/CLI/cy4500_cli.py')
OFF = bytes.fromhex('01 11 04 03 00 00 00')


def stamp():
    return dict(utc=dt.datetime.now(dt.timezone.utc).isoformat(), monotonic_ns=time.monotonic_ns())


def reference(value):
    values = [value.voltage_v, value.current_a, value.power_w]
    if any(x is None or not math.isfinite(x) for x in values):
        raise ValueError('Missing/nonfinite ASD measurement')
    if not 0 <= values[0] <= 5.5 or abs(values[1]) > 1.1 or abs(values[2]) > 6:
        raise ValueError('ASD reading exceeds this 5 V / 1 A comparison envelope')
    return dict(voltage_V=values[0], current_A=values[1], power_W=values[2],
                raw_hex=value.raw_response.hex())


def paired_read(measure, sample, stop, health):
    """Bracket a C5 read with two measured references; stop load on any failure."""
    try:
        health()
        started = stamp(); first = measure(); a = reference(first); first_end = stamp()
        c5_start = stamp(); c5 = sample(); c5_end = stamp()
        last_start = stamp(); last = reference(measure()); ended = stamp()
        health()
        return first, dict(start=started, asd_before=a, asd_before_end=first_end,
            c5_start=c5_start, c5=c5, c5_end=c5_end, asd_after_start=last_start,
            asd_after=last, end=ended, exactly_synchronous=False)
    except BaseException:
        stop()
        raise


def load_module(name, path):
    sys.path.insert(0, str(path.parent))
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def asd_arguments(args, out):
    return ['--port', args.port, '--hold', f'5:{args.current:g}:{args.seconds:g}:fixed',
        '--hold-sample-interval', '1', '--hold-settle', '1',
        '--request-current', '1', '--official-prime-current', '0',
        '--official-prime-request-current', '1', '--query-pdo-official', '--no-pdo-auto-reconcile',
        '--current-policy', 'skip', '--voltage-tolerance', '0.5',
        '--power-limit', '6', '--csv', str(out/'asd.csv'),
        '--source-name', 'Framework (owner label; exact model unconfirmed)',
        '--cable-name', 'Sumitomo 1.0m; CY4500-EPR -> C5 -> ASD-PD31',
        '--quiet', '--no-color']


def load_is_off(status):
    return status.as_dict()['output_state_raw'] == 0


def ensure_capture_health(state, alive, now):
    # EP81 idle reads alone did not detect the observed EP83/STOP timeout.
    if (not alive or state['error'] or now-state['updated']>3 or
            not state.get('scope_samples',0) or now-state.get('scope_progress_at',0)>3):
        raise RuntimeError('CY capture is stopped, failed, stale or has no live scope stream')


class C5:
    def __init__(self, trace):
        import hid
        devices = hid.enumerate(0x0716, 0x5053)
        if len(devices) != 1 or devices[0].get('serial_number') != '20211222':
            raise RuntimeError('Expected the previously qualified owner C5')
        self.trace = trace; self.seq = 0; self.nonce = secrets.token_bytes(8)
        self.device = hid.device()
        try:
            self.device.open_path(devices[0]['path']); self.device.set_nonblocking(True)
            for _ in range(16):
                if not self.device.read(65):
                    break
            else:
                raise RuntimeError('Other C5 HID client is active')
            self.device.set_nonblocking(False)
            self.gui()
        except BaseException:
            self.device.close()
            raise

    def exchange(self, make, parse):
        seq = self.seq; self.seq += 1
        tx = make(seq, self.nonce); entry = dict(start=stamp(), tx=tx.hex())
        try:
            if self.device.write(b'\0' + tx) != 65:
                raise IOError('Short C5 HID write')
            raw = bytes(self.device.read(65, 1500)); entry['rx'] = raw.hex()
            if not raw:
                raise TimeoutError('No C5 reply; no retry')
            return parse(raw, seq, self.nonce)
        finally:
            entry['end'] = stamp()
            self.trace.write(json.dumps(entry) + '\n'); self.trace.flush()

    def gui(self):
        status = self.exchange(monitor.request, monitor.parse)
        if status['state'] != 'GUI' or status['error'] or status['unused_guard_bytes'] < 1024:
            raise RuntimeError('C5 GUI/guard unhealthy')
        return status

    def sample(self):
        raw = self.exchange(probe_meter.raw_request, probe_meter.parse_raw)
        if raw['status'] != 'identified' or raw['model'] != 'INA228':
            raise RuntimeError('C5 raw sample failed or identity changed')
        return dict(raw=raw, gui=self.gui())


class ShadowC5(C5):
    """Consume a newly completed v0.1.6 cache, never the initial old counter."""
    shadow_started = False
    sampler_generation = 0

    def shadow_exchange(self, command):
        import shadow_monitor as shadow
        return self.exchange(lambda seq,nonce:shadow.request(command,seq,nonce),
                             lambda raw,seq,nonce:shadow.parse(command,raw,seq,nonce))

    def sample(self):
        first=self.shadow_exchange(0x9a)
        if first['state']=='FAULT' or first['error']:
            raise RuntimeError('Shadow sampler fault; no automatic restart')
        old=first['sample_number']
        self.shadow_started=True
        if first['state']=='OFF':
            self.shadow_exchange(0x98)
            self.sampler_generation+=1
            old=0
        deadline=time.monotonic()+2
        while True:
            cache=self.shadow_exchange(0x9a)
            if cache['state']=='FAULT' or cache['error'] or cache['state']=='OFF':
                raise RuntimeError('Shadow sampler stopped or failed during acquisition')
            if cache['cache_current'] and cache['sample_number']!=old:
                break
            if time.monotonic()>=deadline:
                raise TimeoutError('No new shadow cache within 2 s')
            time.sleep(.02)
        raw=dict(status='identified',model='INA228',
            raw_registers={'0x00':cache['config'],'0x01':cache['adc_config'],
                           '0x04':cache['shunt_raw'],'0x05':cache['bus_raw']},
            calibrated=False,freshness_qualified=False,gui_measurement_updates=False)
        return dict(raw=raw,gui=self.gui(),shadow_cache=cache,
                    sampler_generation=self.sampler_generation,read_source='shadow-cache')

    def stop_shadow(self):
        if not self.shadow_started:
            return None
        stopped=self.shadow_exchange(0x9c)
        self.shadow_started=False
        if stopped['state']!='OFF':raise RuntimeError('Shadow sampler did not stop')
        return stopped


class GatedC5(ShadowC5):
    """Require a new cache and its matching clear/set evidence inside the bracket."""
    def gated_exchange(self, command):
        import gated_monitor as gated
        return self.exchange(lambda seq,nonce:gated.request(command,seq,nonce),
                             lambda raw,seq,nonce:gated.parse(command,raw,seq,nonce))

    def sample(self):
        import gated_monitor as gated
        first=self.gated_exchange(0xa2)
        if first['state']=='FAULT' or first['error']:
            raise RuntimeError('Gated sampler fault; no automatic restart')
        old=first['sample_number'];self.shadow_started=True
        if first['state']=='OFF':
            self.gated_exchange(0xa0);self.sampler_generation+=1;old=0
        deadline=time.monotonic()+2
        while True:
            cache=self.gated_exchange(0xa2)
            if cache['state'] in ('FAULT','OFF') or cache['error']:
                raise RuntimeError('Gated sampler stopped or failed during acquisition')
            if cache['cache_current'] and cache['sample_number']!=old:
                evidence=self.gated_exchange(0xa6)
                if not cache['completion_gate_observed']:
                    raise RuntimeError('New cache has no completion gate')
                if gated.validate_evidence(cache,evidence):break
            if time.monotonic()>=deadline:raise TimeoutError('No new associated gated cache within 2 s')
            time.sleep(.02)
        raw=dict(status='identified',model='INA228',
            raw_registers={'0x00':cache['config'],'0x01':cache['adc_config'],
                           '0x04':cache['shunt_raw'],'0x05':cache['bus_raw']},
            calibrated=False,freshness_qualified=False,gui_measurement_updates=False)
        return dict(raw=raw,gui=self.gui(),gated_cache=cache,gate_evidence=evidence,
                    sampler_generation=self.sampler_generation,read_source='gated-cache')

    def stop_shadow(self):
        if not self.shadow_started:return None
        stopped=self.gated_exchange(0xa4);self.shadow_started=False
        if stopped['state']!='OFF':raise RuntimeError('Gated sampler did not stop')
        return stopped


class DisplayC5(GatedC5):
    """Pair raw gate evidence with the exact conversion consumed by Overview."""
    def display_status(self):
        import display_monitor as display
        return self.exchange(display.request,display.parse)

    def sample(self):
        for _ in range(3):
            result=super().sample();display=self.display_status()
            if display['settings_state']!='READY' or display['settings_error'] or display['conversion_error'] or not display['reading_valid']:
                raise RuntimeError('GUI measurement unavailable or faulted')
            if display['sample_number']==result['gated_cache']['sample_number']:
                result['display']=display
                result['raw']['gui_measurement_updates']=True
                result['read_source']='display-gated-cache'
                return result
        raise RuntimeError('No matching raw/GUI sequence in three association attempts')

    def stop_shadow(self):
        stopped=super().stop_shadow()
        if stopped is None:return None
        time.sleep(.1);display=self.display_status()
        if display['reading_valid'] or display['autonomous_enabled']:
            raise RuntimeError('GUI remains live after stop')
        return dict(sampler=stopped,display=display)


def run(args, out, report):
    asd = load_module('c5_asd_cli', ASD)
    cy = load_module('c5_cy_cli', CY)
    report['asd_cli_version'] = asd.CONTROL_VERSION
    identity_evidence=json.loads(args.identity_json.read_text(encoding='utf8'))['results']['module_information']
    expected_mac=int(identity_evidence['module_mac_hex'],16)
    if identity_evidence['module_class_hex']!='0x04' or identity_evidence['module_model_numeric']!=130:
        raise RuntimeError('Expected previously qualified owner ASD identity evidence')
    argv = asd_arguments(args, out)
    asd.build_parser().parse_args(argv)  # Validate before opening either device.
    report['asd_arguments'] = argv
    ready = threading.Event(); stopped = threading.Event()
    health_state = dict(updated=0.0, error=None, result=None,scope_samples=0,scope_progress_at=0.0)
    original_capture = cy.CY4500EPR.capture
    original_engine = asd.ProtocolEngine
    c5 = None; worker = None
    with (out/'c5-wire.jsonl').open('x', encoding='utf8') as trace, \
         (out/'pairs.jsonl').open('x', encoding='utf8') as pairs, \
         (out/'cy-health.jsonl').open('x', encoding='utf8') as health_log:
        def capture(device, seconds, **kwargs):
            original_status = kwargs.get('status_callback')
            def status(stats):
                health_state['updated'] = time.monotonic()
                if stats.scope_samples>health_state['scope_samples']:
                    health_state['scope_progress_at']=health_state['updated']
                    health_state['scope_samples']=stats.scope_samples
                row = dict(**stamp(), usb_reads=stats.usb_reads, records=stats.records,
                           scope_samples=stats.scope_samples)
                health_log.write(json.dumps(row) + '\n'); health_log.flush()
                if stats.usb_reads and stats.scope_samples:
                    ready.set()
                if original_status:
                    original_status(stats)
                if stopped.is_set():
                    raise KeyboardInterrupt()  # Native capture catches and sends STOP.
            kwargs['status_callback'] = status
            return original_capture(device, seconds, **kwargs)

        def health():
            ensure_capture_health(health_state,worker is not None and worker.is_alive(),time.monotonic())

        class Engine(original_engine):
            owner_ok = False
            def open(self):
                super().open()
                try:
                    identity = self.query_module_information_diagnostic()
                    if (identity.module_mac != expected_mac or identity.module_class != 4 or
                            identity.module_model_numeric != 130):
                        raise RuntimeError('ASD owner identity mismatch')
                    self.owner_ok = True
                    report['asd_identity'] = identity.as_dict()
                    self.load_off()
                except BaseException:
                    super().close()
                    raise

            def send_body(self, body, *positional, **keywords):
                if len(body) > 1 and body[1] == 0x11 and body != OFF:
                    if not self.owner_ok:
                        raise RuntimeError('ASD identity not verified')
                    health()
                return super().send_body(body, *positional, **keywords)

            def measure_once(self, *positional, **keywords):
                def measure():
                    return super(Engine, self).measure_once(*positional, **keywords)
                first, pair = paired_read(measure, c5.sample, self.load_off, health)
                pair['number'] = report['pairs'] + 1
                pairs.write(json.dumps(pair) + '\n'); pairs.flush()
                report['pairs'] += 1
                return first

            def close(self):
                try:
                    if self.owner_ok and self.ser is not None:
                        self.load_off()
                        status = self.query_standard_power_load_status_diagnostic()
                        report['asd_final_status'] = status.as_dict()
                        report['load_off_confirmed'] = load_is_off(status)
                        if not report['load_off_confirmed']:
                            raise RuntimeError('ASD LOAD OFF not confirmed')
                finally:
                    super().close()

        def cy_worker():
            try:
                health_state['result'] = cy.main(['capture', '--seconds', '120',
                    '--scope', '--scope-raw', '--status-interval', '0.25', '--quiet',
                    '--out-prefix', str(out/'cy')])
            except BaseException as error:
                health_state['error'] = f'{type(error).__name__}: {error}'
                ready.set()

        cy.CY4500EPR.capture = capture
        asd.ProtocolEngine = Engine
        try:
            c5 = DisplayC5(trace) if args.display else GatedC5(trace) if args.gated else ShadowC5(trace) if args.shadow else C5(trace)
            report['gui_before'] = c5.gui()
            worker = threading.Thread(target=cy_worker, daemon=True)
            worker.start()
            if not ready.wait(10):
                raise RuntimeError('CY capture did not become ready in 10 s')
            health()
            report['asd_exit_code'] = asd.main(argv)
            if report['asd_exit_code'] != 0 or report['pairs'] < 3:
                raise RuntimeError('ASD hold failed or fewer than three paired reads')
            if not report['load_off_confirmed']:
                raise RuntimeError('LOAD OFF was not verified')
            report['gui_after'] = c5.gui()
        finally:
            stopped.set()
            try:
                if worker is not None:
                    worker.join(timeout=10)
                    if worker.is_alive():
                        raise RuntimeError('CY did not stop/export within 10 s')
            finally:
                if c5 is not None:
                    try:
                        if isinstance(c5,ShadowC5):
                            report['display_stop' if isinstance(c5,DisplayC5) else 'gated_stop' if isinstance(c5,GatedC5) else 'shadow_stop']=c5.stop_shadow()
                    finally:c5.device.close()
                asd.ProtocolEngine = original_engine
                cy.CY4500EPR.capture = original_capture
        report['cy_result'] = health_state
        if health_state['error'] or health_state['result'] != 0:
            raise RuntimeError('CY capture/export failed')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port', default='COM3')
    parser.add_argument('--current', type=float, default=0.1)
    parser.add_argument('--seconds', type=float, default=10)
    parser.add_argument('--output-dir', type=Path)
    mode=parser.add_mutually_exclusive_group()
    mode.add_argument('--shadow',action='store_true',help='Use a new v0.1.6 shadow-cache sample for each bracket')
    mode.add_argument('--gated',action='store_true',help='Use a new v0.1.8 cache with matching clear/set evidence')
    mode.add_argument('--display',action='store_true',help='Match v0.1.9 Overview conversion to its raw/gate sequence')
    parser.add_argument('--identity-json',type=Path,default=ROOT/'build/captures/asd-identify-20261117-130327/identity-status.json')
    args = parser.parse_args()
    if args.port != 'COM3' or not math.isfinite(args.current) or not 0 <= args.current <= 1:
        parser.error('Only the verified COM3 and 0..1 A are supported for this session')
    if not math.isfinite(args.seconds) or not 5 <= args.seconds <= 20:
        parser.error('Duration must be 5..20 seconds')
    if not args.identity_json.is_file():parser.error('Previously qualified owner ASD identity JSON is required')
    out = (args.output_dir or ROOT/'build/captures'/('bench-'+dt.datetime.now().strftime('%Y%m%d-%H%M%S-%f'))).resolve()
    if not out.is_relative_to((ROOT/'build').resolve()):
        parser.error('New evidence must stay under this C5 build directory')
    out.mkdir(parents=True, exist_ok=False)
    os.environ['PYTHONDONTWRITEBYTECODE'] = '1'
    report = dict(schema='c5-asd-cy-bench-v1', start=stamp(), complete=False, pairs=0,
        load_off_confirmed=False, requested_voltage_V=5, requested_current_A=args.current,
        connection='Framework -> Sumitomo 1.0m -> CY4500-EPR -> C5 -> ASD-PD31',
        c5_switch='PD OFF', exact_clock_alignment_established=False,
        c5_adc_freshness_qualified=False, c5_firmware_gui_measurements=bool(args.display),
        c5_read_source='display-gated-cache' if args.display else 'gated-cache' if args.gated else 'shadow-cache' if args.shadow else 'explicit-raw',
        c5_status_read_to_clear_side_effects=bool(args.gated or args.display),
        private_identity_evidence=str(args.identity_json.resolve()),
        private_identity_evidence_sha256=hashlib.sha256(args.identity_json.read_bytes()).hexdigest(),
        source_hashes={str(p): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in (ASD, ASD.parent/'asd_pd31_modules/engine.py',
                      ASD.parent/'asd_pd31_modules/csvlog.py', CY, CY.parent/'ezpd_protocol.py',
                      Path(__file__).resolve(), ROOT/'tools/probe_meter.py',
                      ROOT/'tools/monitor.py', ROOT/'tools/shadow_monitor.py', ROOT/'tools/gated_monitor.py',ROOT/'tools/display_monitor.py')})
    with (out/'console.log').open('x', encoding='utf8') as console:
        try:
            with contextlib.redirect_stdout(console), contextlib.redirect_stderr(console):
                run(args, out, report)
            report['complete'] = True
        except BaseException as error:
            report['error'] = f'{type(error).__name__}: {error}'
        finally:
            report['end'] = stamp()
            console.flush()
            report['files'] = {p.name: dict(bytes=p.stat().st_size,
                sha256=hashlib.sha256(p.read_bytes()).hexdigest()) for p in out.iterdir() if p.is_file()}
            (out/'manifest.json').write_text(json.dumps(report, indent=2)+'\n', encoding='utf8')
    print('Evidence:', out)
    print(json.dumps({key: report.get(key) for key in ('complete','pairs','load_off_confirmed','error')}, indent=2))
    return 0 if report['complete'] else 2


if __name__ == '__main__':
    raise SystemExit(main())
