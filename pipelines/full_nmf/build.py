"""Attach existing bounded evidence objects to the full-corpus NMF catalogue."""
from pathlib import Path
import argparse
import hashlib
import json
import sys
import numpy as np
import pandas as pd

REPO=Path(__file__).resolve().parents[2];ROOT=REPO.parent
sys.path[:0]=[str(REPO),str(REPO/'pipelines/nmf500')]
from mapping import ranked_links
from trl_crl.pipeline import assess


def current_contexts():
    def read(name):return json.loads((REPO/'data'/(name+'.json')).read_text())
    evidence=read('evidence');sources={s['source_id']:s for s in read('sources')};rows=[]
    for obj in read('objects'):
        own=[e for e in evidence if e['case_id']==obj['case_id']]
        text='\n'.join([obj['canonical_name'],obj['object_configuration'],obj['application_or_target_function']]+
            [sources[e['source_id']]['title']+'\n'+e['quote'] for e in own])
        rows.append({'entity_type':'case','entity_id':obj['case_id'],'name':obj['canonical_name'],'text':text})
    for direction in read('technology_registry'):
        if direction['entity_level']=='direction_candidate':
            rows.append({'entity_type':'direction','entity_id':direction['technology_id'],'name':direction['canonical_name'],
                'text':direction['canonical_name']+'\n'+direction.get('function','')})
    return rows


def build(source,hotspots,out,context):
    summary=json.loads((source/'SUMMARY.json').read_text())
    if not (source/'COMPLETE.json').exists() or not all(summary[x] for x in ['full_training','full_inference','full_transfer']):
        raise ValueError('Completed full classification required')
    completion=json.loads((source/'COMPLETE.json').read_text())
    if hashlib.sha256((source/'SUMMARY.json').read_bytes()).hexdigest()!=completion['summary_sha256']:
        raise ValueError('Classification summary hash mismatch')
    if hashlib.sha256((source/'VALIDATION.json').read_bytes()).hexdigest()!=completion['validation_sha256'] or not json.loads((source/'VALIDATION.json').read_text()).get('passed'):
        raise ValueError('Classification validation mismatch')
    if hashlib.sha256((source/'topic_centroids.npy').read_bytes()).hexdigest()!=summary['centroids_sha256']:
        raise ValueError('Classification centroid hash mismatch')
    hot_summary=json.loads((hotspots/'SUMMARY.json').read_text())
    if hot_summary['classification_summary_sha256']!=completion['summary_sha256']:
        raise ValueError('Hotspots and maturity use different classifications')
    rows=json.loads((context/'contexts.json').read_text())
    audit=json.loads((context/'ENCODING.json').read_text())
    signature=hashlib.sha256(json.dumps(rows,ensure_ascii=False,sort_keys=True).encode()).hexdigest()
    if signature!=audit['input_sha256'] or audit['model']!='BAAI/bge-m3':
        raise ValueError('Context embedding provenance mismatch')
    if rows!=current_contexts():
        raise ValueError('Evidence contexts changed; re-encode before maturity mapping')
    catalog=pd.read_csv(source/'topic_catalog.csv')
    centers=np.load(source/'topic_centroids.npy')
    vectors=np.load(context/'embeddings.npy')
    links=ranked_links(rows,vectors,centers,catalog)
    links['category_id']=links.topic_id.map(catalog.set_index('topic_id').category_id)
    out.mkdir(parents=True,exist_ok=True)
    links.to_csv(out/'theme_context_top3.csv',index=False)
    _,results=assess(REPO/'data')
    units=pd.DataFrame(results['assessment_units'])
    cases=links[links.entity_type.eq('case') & links['rank'].eq(1)].set_index('entity_id')
    units['legacy_category_id']=units['category_id'] if 'category_id' in units else ''
    units['category_id']=units.case_id.map(cases.category_id)
    units['mapping_cosine']=units.case_id.map(cases.cosine)
    units['mapping_needs_review']=True
    if units.category_id.isna().any():
        raise ValueError('Missing bounded case mapping')
    hot=pd.read_csv(hotspots/'hotspot_metrics.csv').set_index('category_id')
    for field in ['core_score','emerging_score','core_numeric_candidate','emerging_numeric_candidate']:
        units[field]=units.category_id.map(hot[field])
    units.to_csv(out/'case_hotspot_links.csv',index=False)
    profiles=catalog.copy()
    profiles['candidate_case_count']=profiles.category_id.map(units.category_id.value_counts()).fillna(0).astype(int)
    profiles['theme_trl']=None;profiles['theme_crl']=None
    profiles['mapping_review_required']=True
    profiles.to_csv(out/'theme_evidence_profiles.csv',index=False)
    report={'full_source_records':summary['population_records'],'full_papers':summary['papers'],'full_patents':summary['patents'],'full_policies':summary['policies'],
        'topic_count':len(catalog),'bounded_cases_recomputed':len(units),'context_entities_remapped':len(rows),
        'theme_level_maturity_assigned':False,'new_external_evidence_added':False,
        'classification_centroids_sha256':summary['centroids_sha256'],'original_evidence_preserved':True}
    report['classification_summary_sha256']=completion['summary_sha256']
    (out/'SUMMARY.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    (out/'REPORT.md').write_text(f"# 全量主题与技术成熟度关联\n\n主题目录覆盖{summary['population_records']:,}条原始记录；{len(units)}个已有有界对象依据现有证据重新评估并关联新主题。\n\n主题内全部已归类论文形成BGE-M3中心。主题关联为候选检索结果，主题级TRL/CRL留空。未新增外部成熟度证据；全量文档分类不代表每篇文档或每个主题都已有成熟度证据。\n")
    print(json.dumps(report,ensure_ascii=False),flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--classification',type=Path,default=ROOT/'energy-topic-identification/work/full_nmf500_20260926');p.add_argument('--hotspots',type=Path,default=ROOT/'energy-topic-hotspots/outputs/full_nmf500_20260926');p.add_argument('--output',type=Path,default=REPO/'results/full_nmf500_20260926');p.add_argument('--context',type=Path,default=REPO/'work/nmf500/context');a=p.parse_args();build(a.classification,a.hotspots,a.output,a.context)
