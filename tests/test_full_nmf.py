"""Full-taxonomy mapping must preserve bounded evidence and not assign theme TRL."""
from pathlib import Path
import hashlib
import importlib.util
import json
import numpy as np
import pandas as pd
import pytest


def test_full_mapping_preserves_case_boundary(tmp_path,monkeypatch):
    repo=Path(__file__).resolve().parents[1]
    spec=importlib.util.spec_from_file_location('full_maturity_build',repo/'pipelines/full_nmf/build.py')
    build=importlib.util.module_from_spec(spec);spec.loader.exec_module(build)
    source=tmp_path/'classification';source.mkdir()
    hotspots=tmp_path/'hotspots';hotspots.mkdir()
    context=tmp_path/'context';context.mkdir()
    digest=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
    np.save(source/'topic_centroids.npy',np.eye(3,dtype=np.float32))
    summary={'full_training':True,'full_inference':True,'full_transfer':True,
        'population_records':100,'papers':80,'patents':15,'policies':5,
        'centroids_sha256':digest(source/'topic_centroids.npy')}
    (source/'SUMMARY.json').write_text(json.dumps(summary))
    (source/'VALIDATION.json').write_text('{"passed":true}')
    (source/'COMPLETE.json').write_text(json.dumps({'summary_sha256':digest(source/'SUMMARY.json'),
        'validation_sha256':digest(source/'VALIDATION.json')}))
    catalog=pd.DataFrame({'topic_id':[0,1,2],'category_id':['F0001','F0002','F0003'],'name':['one','two','three']})
    catalog.to_csv(source/'topic_catalog.csv',index=False)
    (hotspots/'SUMMARY.json').write_text(json.dumps({'classification_summary_sha256':digest(source/'SUMMARY.json')}))
    pd.DataFrame({'category_id':catalog.category_id,'core_score':[.2,.3,.4],
        'emerging_score':[.4,.5,.6],'core_numeric_candidate':False,'emerging_numeric_candidate':False}).to_csv(hotspots/'hotspot_metrics.csv',index=False)
    rows=[{'entity_type':'case','entity_id':'c1','name':'object','text':'object function'},
        {'entity_type':'direction','entity_id':'d1','name':'direction','text':'direction function'}]
    monkeypatch.setattr(build,'current_contexts',lambda:rows)
    (context/'contexts.json').write_text(json.dumps(rows))
    (context/'ENCODING.json').write_text(json.dumps({'model':'BAAI/bge-m3',
        'input_sha256':hashlib.sha256(json.dumps(rows,ensure_ascii=False,sort_keys=True).encode()).hexdigest()}))
    np.save(context/'embeddings.npy',np.array([[1,0,0],[0,1,0]],dtype=np.float32))
    monkeypatch.setattr(build,'assess',lambda _:({}, {'assessment_units':[{'case_id':'c1','category_id':'N0009','trl':5}]}))
    out=tmp_path/'out';build.build(source,hotspots,out,context)
    result=pd.read_csv(out/'case_hotspot_links.csv')
    assert result.category_id.tolist()==['F0001']
    assert result.legacy_category_id.tolist()==['N0009'] and result.trl.tolist()==[5]
    profiles=pd.read_csv(out/'theme_evidence_profiles.csv')
    assert profiles.theme_trl.isna().all() and profiles.theme_crl.isna().all()
    links=pd.read_csv(out/'theme_context_top3.csv')
    assert len(links)==6 and links.needs_review.all() and not links.transfers_maturity.any()
    assert links.category_id.str.startswith('F').all()
    (hotspots/'SUMMARY.json').write_text('{"classification_summary_sha256":"stale"}')
    with pytest.raises(ValueError,match='different classifications'):
        build.build(source,hotspots,tmp_path/'rejected',context)
