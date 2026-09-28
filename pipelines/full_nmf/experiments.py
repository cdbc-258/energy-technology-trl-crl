"""Rerun every bounded evidence experiment with the new full-population mapping."""
from pathlib import Path
import argparse
import hashlib
import importlib.util
import json
import pandas as pd

REPO=Path(__file__).resolve().parents[2]


def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def run(source,inp,out):
    complete=json.loads((source/'COMPLETE.json').read_text())
    full=json.loads((source/'SUMMARY.json').read_text())
    maturity=json.loads((inp/'SUMMARY.json').read_text())
    if complete['summary_sha256']!=sha(source/'SUMMARY.json') or maturity['classification_summary_sha256']!=complete['summary_sha256']:
        raise ValueError('Mismatched full classification')
    if not all(full[k] for k in ['full_training','full_inference','full_transfer']):raise ValueError('Full population required')
    if not json.loads((source/'VALIDATION.json').read_text())['passed'] or sha(source/'VALIDATION.json')!=complete['validation_sha256']:
        raise ValueError('Invalid classification audit')
    mapping=inp/'theme_context_top3.csv'
    links=pd.read_csv(mapping);catalog=pd.read_csv(source/'topic_catalog.csv')
    if not set(links.category_id)<=set(catalog.category_id) or not links.category_id.str.startswith('F').all():
        raise ValueError('Mapping belongs to a sample or a different taxonomy')
    input_hashes={p.name:sha(p) for p in sorted((REPO/'data').glob('*.json'))}
    spec=importlib.util.spec_from_file_location('full_evidence_experiment_engine',REPO/'pipelines/nmf500/experiments.py')
    engine=importlib.util.module_from_spec(spec);spec.loader.exec_module(engine)
    engine.run(REPO/'data',mapping,out)
    if input_hashes!={p.name:sha(p) for p in sorted((REPO/'data').glob('*.json'))}:raise ValueError('Evidence changed during experiments')
    summary=json.loads((out/'SUMMARY.json').read_text())
    summary.update(full_population_records=full['population_records'],classification_summary_sha256=complete['summary_sha256'],
        mapping_sha256=sha(mapping),input_evidence_sha256=input_hashes,rerun_with_full_mapping=True,
        classification_scope='all frozen sources',maturity_scope='all existing bounded evidence objects; no fabricated grades for 500 themes')
    if summary['cases']!=maturity['bounded_cases_recomputed'] or summary['upgrades']!=0:raise ValueError('Evidence experiment invariant failed')
    case_links=pd.read_csv(inp/'case_hotspot_links.csv')[['case_id','category_id','core_score','emerging_score']]
    fragility=pd.read_csv(out/'case_fragility.csv').merge(case_links,on='case_id',validate='many_to_one')
    fragility.to_csv(out/'full_topic_case_fragility.csv',index=False)
    (out/'SUMMARY.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n')
    import runpy
    runpy.run_path(str(REPO/'pipelines/full_nmf/report.py'))['render'](out)
    (out/'COMPLETE.json').write_text(json.dumps({'passed':True,'classification_summary_sha256':complete['summary_sha256'],
        'files':{p.name:sha(p) for p in out.iterdir() if p.is_file() and p.name!='COMPLETE.json'}},indent=2)+'\n')


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--classification',type=Path,required=True);p.add_argument('--input',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True);a=p.parse_args();run(a.classification,a.input,a.output)
