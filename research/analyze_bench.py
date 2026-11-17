"""Offline summaries of paired ASD/C5 reads and a conservative CY scope interval."""
import argparse
import csv
import hashlib
import json
import math
from pathlib import Path
import re
import statistics
from calibration_decode import decode_settings, reconstruct

ROOT = Path(__file__).resolve().parents[1]
CAL = ROOT/'build/private-storage/read-20261117-122246'


def stats(values):
    if not values or any(not math.isfinite(x) for x in values):
        raise ValueError('Expected finite nonempty data')
    return dict(count=len(values), minimum=min(values), maximum=max(values),
                mean=statistics.mean(values), median=statistics.median(values))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('capture', type=Path)
    args = parser.parse_args(); folder = args.capture.resolve()
    if not folder.is_relative_to((ROOT/'build').resolve()):
        raise ValueError('Expected C5 build evidence')
    manifest = json.loads((folder/'manifest.json').read_text(encoding='utf8'))
    if not manifest['complete'] or not manifest['load_off_confirmed']:
        raise ValueError('Capture did not complete with verified LOAD OFF')
    console_hash_matches=True
    for name, evidence in manifest['files'].items():
        if name == 'console.log':
            # The redirected log was still open when its original hash was made.
            console_hash_matches=hashlib.sha256((folder/name).read_bytes()).hexdigest()==evidence['sha256']
            continue
        if hashlib.sha256((folder/name).read_bytes()).hexdigest() != evidence['sha256']:
            raise ValueError('Capture file changed: '+name)
    a=(CAL/'storage-pass1.bin').read_bytes();b=(CAL/'storage-pass2.bin').read_bytes()
    saved=json.loads((CAL/'manifest.json').read_text(encoding='utf8'))
    if a != b or any(hashlib.sha256(a).hexdigest()!=p['sha256'] for p in saved['passes']):
        raise ValueError('Private settings backup mismatch')
    fields=decode_settings(a)
    pairs=[json.loads(s) for s in (folder/'pairs.jsonl').read_text(encoding='utf8').splitlines()]
    if len(pairs) != manifest['pairs'] or len(pairs)<3:
        raise ValueError('Paired record count mismatch')
    with (folder/'asd.csv').open(encoding='utf-8-sig',newline='') as stream:
        asd_rows=list(csv.DictReader(stream))
    result=[];row_index=0;steady_pairs=[]
    for pair in pairs:
        raw_hex=pair['asd_before']['raw_hex'].lower()
        while row_index<len(asd_rows) and asd_rows[row_index].get('raw_measure_response','').replace(' ','').lower()!=raw_hex:
            row_index+=1
        if row_index==len(asd_rows):
            raise ValueError('ASD pair has no matching CLI measurement row')
        mode=asd_rows[row_index]['mode'];row_index+=1
        if mode=='hold-fixed':steady_pairs.append(pair)
        model=reconstruct(pair['c5']['raw']['raw_registers'],fields)
        ref_v=(pair['asd_before']['voltage_V']+pair['asd_after']['voltage_V'])/2
        ref_i=(pair['asd_before']['current_A']+pair['asd_after']['current_A'])/2
        gui=pair['c5']['gui']
        if gui['error'] or gui['unused_guard_bytes']<1024:
            raise ValueError('C5 GUI/guard error')
        result.append(dict(number=pair['number'],asd_cli_mode=mode,c5_voltage_V=model['stock_model_voltage_V'],
            c5_signed_current_A=model['stock_model_current_A'],asd_bracket_mean_voltage_V=ref_v,
            asd_bracket_mean_current_A=ref_i,
            current_magnitude_difference_mA=(abs(model['stock_model_current_A'])-ref_i)*1000,
            voltage_difference_mV=(model['stock_model_voltage_V']-ref_v)*1000,
            total_bracket_ms=(pair['end']['monotonic_ns']-pair['start']['monotonic_ns'])/1e6,
            c5_exchange_span_ms=(pair['c5_end']['monotonic_ns']-pair['c5_start']['monotonic_ns'])/1e6))
    health=[json.loads(s) for s in (folder/'cy-health.jsonl').read_text(encoding='utf8').splitlines()]
    steady=[r for r in result if r['asd_cli_mode']=='hold-fixed']
    if len(steady)<3:raise ValueError('Fewer than three steady hold pairs')
    first=next(h for h in health if h['monotonic_ns']>=steady_pairs[0]['end']['monotonic_ns'])
    last=next(h for h in reversed(health) if h['monotonic_ns']<=steady_pairs[-1]['start']['monotonic_ns'])
    start,end=first['scope_samples'],last['scope_samples']
    if end<=start:
        raise ValueError('No interior scope interval')
    with (folder/'cy.scope.csv').open(encoding='utf-8-sig',newline='') as stream:
        scope=[row for index,row in enumerate(csv.DictReader(stream)) if start<=index<end]
    summary=(folder/'cy.summary.txt').read_text(encoding='utf8')
    requests=summary.split('Request sequence:',1)[1].split('PS_RDY VBUS samples:',1)[0]
    request_lines=[s for s in requests.splitlines() if 'REQUEST:' in s]
    voltages=[]
    for line in request_lines:
        match=re.search(r'PDO\d+ FIXED ([0-9.]+)V',line)
        if not match:
            raise ValueError('Unsupported/unresolved request in PD capture: '+line)
        voltages.append(float(match.group(1)))
    if not voltages or any(v!=5 for v in voltages):
        raise ValueError('Capture does not exclusively prove Fixed 5 V requests')
    report=dict(schema='c5-paired-bench-analysis-v2',capture=str(folder),
        requested_current_A=manifest['requested_current_A'],connection=manifest['connection'],
        pairs=result,steady_pair_count=len(steady),precheck_pair_count=len(result)-len(steady),
        phase_classification='Matched actual ASD CLI CSV mode and raw response in sequence; no value-based rejection',
        current_difference_mA=stats([r['current_magnitude_difference_mA'] for r in steady]),
        voltage_difference_mV=stats([r['voltage_difference_mV'] for r in steady]),
        c5_current_magnitude_A=stats([abs(r['c5_signed_current_A']) for r in steady]),
        asd_bracket_current_A=stats([r['asd_bracket_mean_current_A'] for r in steady]),
        bracket_ms=stats([r['total_bracket_ms'] for r in steady]),
        cy_interior_scope=dict(sample_index_start=start,sample_index_end_exclusive=end,
            current_A=stats([float(s['Ibus(A)']) for s in scope]),
            voltage_V=stats([float(s['Vbus(V)']) for s in scope]),
            interval_basis='Host health sample counts inside first/last ASD-C5 bracket, not a synchronized device-clock mapping',
            absolute_calibration_qualified=False),
        pd_request_voltages_V=voltages,all_decoded_requests_fixed_5V=True,
        load_off_confirmed=True,gui_errors=[0],guard_min_bytes=min(p['c5']['gui']['unused_guard_bytes'] for p in pairs),
        exactly_synchronous=False,c5_adc_freshness_qualified=False,full_range_accuracy_qualified=False,
        calibration_coefficients_fitted=False,
        capture_data_file_hashes_match=True,console_log_hash_matches_original_manifest=console_hash_matches,
        analysis_source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        settings_backup_sha256=hashlib.sha256(a).hexdigest())
    with (folder/'comparison-analysis-v2.json').open('x',encoding='utf8') as stream:
        json.dump(report,stream,indent=2);stream.write('\n')
    print(json.dumps({key:report[key] for key in ('requested_current_A','current_difference_mA',
        'c5_current_magnitude_A','asd_bracket_current_A','all_decoded_requests_fixed_5V','load_off_confirmed')},indent=2))


if __name__=='__main__':main()
