#!/usr/bin/env python3
"""Offline-only reduction of the frozen 60/90 checkpoint after the preregistered stop."""
from __future__ import annotations
import csv, importlib.util, json, math
from pathlib import Path
HERE=Path(__file__).resolve().parent
STAGE_PATH=HERE.parent/'run_stage.py'
spec=importlib.util.spec_from_file_location('frozen_a42',STAGE_PATH)
stage=importlib.util.module_from_spec(spec); spec.loader.exec_module(stage)

def read_csv(p):
    with p.open(newline='',encoding='utf-8') as f:return list(csv.DictReader(f))
def write_csv(p,rows,fields=None):
    if fields is None: fields=list(rows[0]) if rows else ['status']
    with p.open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=fields,lineterminator='\n',extrasaction='ignore');w.writeheader();w.writerows(rows)

def main():
    plan=read_csv(HERE/'planned_cells.csv'); rows=read_csv(HERE/'per_run.csv')
    if len(rows)!=60 or any(r['status']!='success' for r in rows): raise SystemExit('checkpoint mismatch; expected 60 successful rows')
    done={r['run_id']:r for r in rows}
    for item in plan:
        if item['run_id'] in done:
            item['status']='success'; item['error']=''
        else:
            item['status']='not_attempted_projection_checkpoint_stop'
            item['error']='updated total projection exceeded 24 h after 60 attempts; frozen stop rule; no retry'
    write_csv(HERE/'planned_cells.csv',plan)
    # Use the frozen registered summaries/classifier on observed data, then distinguish unattempted cells.
    stage.HERE=HERE
    stage.analyze_results(rows)
    miss=read_csv(HERE/'miss_table.csv')
    for r in miss:
        if int(r['family_cells'])==0:
            r.update({'flagged_n':'not_attempted','flagged_fraction':'not_measured','readiness_gt_120_n':'not_attempted',
                      'readiness_gt_120_fraction':'not_measured','readiness_undefined_n':'not_attempted'})
        else:
            r['flagged_fraction']=stage.fmt(int(r['flagged_n'])/5)
            r['readiness_gt_120_fraction']=stage.fmt(int(r['readiness_gt_120_n'])/5)
    write_csv(HERE/'miss_table.csv',miss)
    status=read_csv(HERE/'status_matrix.csv')
    for r in status:
        n=int(r['N']);
        if n==162:
            for role in ('phi1','phi5','phi10'): r[role+'_status']='not_attempted_projection_checkpoint_stop'
            r['per_cell_highest_passing_phi']='not_measured'
    write_csv(HERE/'status_matrix.csv',status)
    candidates=read_csv(HERE/'operating_candidates.csv')
    for r in candidates:
        if int(r['N'])==162:
            r.update({'lowest_load_passed_family_protocol_cells':'not_measured','common_operating_role':'not_measured','common_operating_phi':'not_measured'})
        r['coverage']='complete_registered_grid' if int(r['N']) in (42,92) else '0_of_30_cells_attempted'
    write_csv(HERE/'operating_candidates.csv',candidates)
    projection=read_csv(HERE/'runtime_projection_after_60.csv')[0]
    total_actual=float(projection['actual_elapsed_wall_s']); projected=float(projection['projected_total_s'])
    attempted=len(rows); failed=sum(r['status']!='success' for r in rows)
    misses=sum(int(r['flagged_n']) for r in miss if r['flagged_n'].isdigit())
    lines=[
      '# A4.2 repair-v1 — stopped at preregistered 60-run projection checkpoint','',
      '**A4.2 is incomplete and closed at the frozen checkpoint stop.** The user requested completion of A4.2, but the preregistered rule explicitly requires stopping when a corrected total exceeds 24 h. Do not describe 60/90 as complete or start A4.3.',
      '',f"Addendum 1 SHA-256 `5d203dc1f1201f2d5f06512d1653d6eb2ba3a77cb6226f6af35eaf378ce3058e`; addendum 3 (AODV correction) SHA-256 `9f0ee2c3a57ef40444dcd73d0a0a72e04ed0d5e65c5b529e1d2d5f1d181b1a46`.",
      '',f'**Initial gate:** frozen successful-pilot projection {float(json.loads((HERE/"projection_initial.json").read_text())["projected_total_h"]):.3f} h; passed the registered ≤24 h gate. **Checkpoint after 60:** actual serial wall time {total_actual/3600:.3f} h; median actual/projected correction {float(projection["median_actual_projected_correction"]):.4f}; updated total {projected/3600:.3f} h >24 h. Frozen instruction: stop. The remaining 30 runs were not launched.',
      '',f'**Attempts and budget:** 60/90 A4.2 cells attempted; {60-failed} successful, {failed} unsuccessful; cumulative Alpha charge {75+attempted}/300. The five authorized repair/diagnostic attempts are separately recorded. No retries or substitutions.',
      '', 'All 60 A4.2 runs that started completed successfully. Fully observed registered grids: N=42 and N=92 (30/30 cells each). N=162: 0/30 attempted. Exact plan states and reason: [planned_cells.csv](planned_cells.csv). Per-run data: [per_run.csv](per_run.csv); per-flow post-readiness records: [per_flow_post_readiness.csv](per_flow_post_readiness.csv).',
      '',f'Readiness flags among the 60 completed runs: {misses}/60. Detailed protocol×N×load counts, using the preregistered five-family denominator: [miss_table.csv](miss_table.csv). Completed-size status matrix and unattempted N=162 cells: [status_matrix.csv](status_matrix.csv).',
      '', 'Per-cell highest passing loads and common candidates are summarized in [operating_candidates.csv](operating_candidates.csv). N=42 and N=92 cover their full registered grid; N=162 has no measured candidate. No 2% loads or other replacements were run.',
      '', 'Interpretation is limited to the two completed network sizes and tested A1 realization. The 30 N=162 cells are unknown/not attempted, not failures. Since this stage stopped at the frozen projection rule, no further continuation is authorized by this report.',
      '', 'The repeated AODV failure was diagnosed as signed `1 << 31` overflow at RREQ count 32 with configured retry limit 2. The bounded backoff / terminal `>=` correction is recorded in [AODV correction note](aodv_retry_correction.md), applied to all AODV sweep runs, and source/library hashes are in [pre-run identities](PRE_RUN_IDENTITY.md). OLSR source was unchanged. Historical failed pilot attempts remain failed.',
      '', '**STOP. No A4.3, no more A4.2 variants, no detector/warm-up changes, no DSDV reinstatement. A separate user decision and registered continuation would be required to exceed the frozen 24-hour stop rule.**']
    if len(lines)>150: raise SystemExit(f'report too long {len(lines)}')
    (HERE/'report.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    stage.create_manifest()
    print(f'wrote partial report; attempted={attempted}/90; total projection={projected/3600:.3f}h; manifest entries={len((HERE/"MANIFEST.sha256").read_text().splitlines())}')
if __name__=='__main__': main()
