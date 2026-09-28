"""Rerun the real evidence engine against a synthetic new-taxonomy mapping."""
from pathlib import Path
import hashlib
import importlib.util
import json
import pandas as pd

REPO=Path(__file__).resolve().parents[1]


def test_full_evidence_experiments_bind_new_mapping(tmp_path):
    spec=importlib.util.spec_from_file_location('full_maturity_experiments',REPO/'pipelines/full_nmf/experiments.py')
    m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
    source=tmp_path/'source';source.mkdir();inp=tmp_path/'input';inp.mkdir()
    sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
    (source/'SUMMARY.json').write_text(json.dumps({'full_training':True,'full_inference':True,'full_transfer':True,'population_records':5119004}))
    (source/'VALIDATION.json').write_text('{"passed":true}')
    digest=sha(source/'SUMMARY.json')
    (source/'COMPLETE.json').write_text(json.dumps({'summary_sha256':digest,'validation_sha256':sha(source/'VALIDATION.json')}))
    pd.DataFrame({'category_id':[f'F{i+1:04d}' for i in range(500)]}).to_csv(source/'topic_catalog.csv',index=False)
    # Test fixture only: never replace actual full-run mappings with this data.
    links=pd.read_csv(REPO/'tests/fixtures/nmf500_results/theme_context_top3.csv')
    links['category_id']=links.category_id.str.replace('N','F',regex=False)
    links.to_csv(inp/'theme_context_top3.csv',index=False)
    objects=json.loads((REPO/'data/objects.json').read_text())
    pd.DataFrame({'case_id':[o['case_id'] for o in objects],'category_id':'F0001','core_score':0.,'emerging_score':0.}).to_csv(inp/'case_hotspot_links.csv',index=False)
    (inp/'SUMMARY.json').write_text(json.dumps({'classification_summary_sha256':digest,'bounded_cases_recomputed':len(objects)}))
    out=tmp_path/'output';m.run(source,inp,out)
    report=json.loads((out/'SUMMARY.json').read_text())
    assert report['rerun_with_full_mapping'] and report['scenario_count']>=700 and report['upgrades']==0
    assert report['cases']==len(objects) and report['mapping_sha256']==sha(inp/'theme_context_top3.csv')
    assert len(pd.read_csv(out/'mapping_sensitivity.csv'))==60
    assert json.loads((out/'COMPLETE.json').read_text())['passed']
