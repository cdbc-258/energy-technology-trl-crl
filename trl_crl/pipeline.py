"""Current assessment pipeline: curated evidence/gates -> independent axes -> exports.
No previous score is an input. Semantic gate decisions require source review.
"""
from pathlib import Path
from datetime import date
from collections import Counter
import csv,hashlib,json,copy
from .common import read,write,canonical_sha,file_sha
from .engine import evaluate_case,unique_index,validate_excerpt,validate_observation

INPUT_NAMES=['dataset','objects','technical_profiles','gate_reviews','observations','evidence','sources','technology_registry','case_technology_links','themes','theme_direction_links','observed_facts']

def load_inputs(data_dir):
 data_dir=Path(data_dir);d={n:read(data_dir/(n+'.json')) for n in INPUT_NAMES}
 cutoff=date.fromisoformat(d['dataset']['assessment_cutoff'])
 objects=unique_index(d['objects'],'case_id');sources=unique_index(d['sources'],'source_id');ev=unique_index(d['evidence'],'evidence_id')
 unique_index(d['technical_profiles'],'case_id');unique_index(d['gate_reviews'],'case_id');unique_index(d['observations'],'observation_id')
 if set(objects)!={p['case_id'] for p in d['technical_profiles']} or set(objects)!={r['case_id'] for r in d['gate_reviews']}:
  raise ValueError('Every bounded object needs one current profile and review')
 for c in d['objects']:
  if any(k in c for k in ['trl_public_evidence_stage','crl_public_evidence_stage','expected_level','formal_trl','formal_crl']):
   raise ValueError('Computed scores must not be provided as object inputs')
 for e in d['evidence']:
  validate_excerpt(e,d['dataset']['assessment_cutoff'])
  if e['case_id'] not in objects or e['source_id'] not in sources:raise ValueError('Invalid evidence foreign key')
  if e['source_url']!=sources[e['source_id']]['url']:raise ValueError('Evidence URL differs from catalog')
  if e['disposition']!='accepted':raise ValueError('Nonaccepted material cannot enter scoring')
  if not (type(e['quote_start']) is int and 0<=e['quote_start']<e['quote_end'] and len(e['quote'])==e['quote_end']-e['quote_start']):raise ValueError('Invalid excerpt bounds')
  if hashlib.sha256(e['quote'].encode()).hexdigest()!=e['quote_sha256']:raise ValueError('Excerpt hash mismatch')
  # Public excerpts permit local integrity verification, not reauthentication of the remote full text.
  available=e.get('available_by');published=e.get('published_at')
  if not available or date.fromisoformat(available[:10])>cutoff:raise ValueError('Evidence unavailable by cutoff')
  if published and date.fromisoformat(published[:10])>cutoff:raise ValueError('Evidence published after cutoff')
 materialized=[]
 for o in d['observations']:
  if o.get('case_id') not in objects or o.get('evidence_id') not in ev:raise ValueError('Invalid observation foreign key')
  e=ev[o['evidence_id']];o=copy.deepcopy(o)
  if not e['quote_start']<=o['quote_start']<o['quote_end']<=e['quote_end']:raise ValueError('Observation outside excerpt')
  o['quote']=e['quote'][o['quote_start']-e['quote_start']:o['quote_end']-e['quote_start']]
  validate_observation(o,objects[o['case_id']],ev)
  materialized.append(o)
 d['observations']=materialized
 tech=unique_index(d['technology_registry'],'technology_id');themes=unique_index(d['themes'],'category_id')
 for l in d['case_technology_links']:
  if l['case_id'] not in objects or l['technology_id'] not in tech or any(i not in tech for i in l['parent_direction_ids']):raise ValueError('Invalid case-direction association')
  if l.get('transfers_maturity') or l.get('relabels_documents'):raise ValueError('Association may not transfer grades or relabel documents')
 for l in d['theme_direction_links']:
  if l['category_id'] not in themes or l['technology_id'] not in tech:raise ValueError('Invalid theme-direction association')
 for f in d['observed_facts']:
  if f['case_id'] not in objects or f['source_id'] not in sources:raise ValueError('Invalid fact foreign key')
  if hashlib.sha256(f['quote'].encode()).hexdigest()!=f['quote_sha256']:raise ValueError('Fact excerpt hash mismatch')
 return d

def assess(data_dir):
 d=load_inputs(data_dir);cutoff=d['dataset']['assessment_cutoff'];e={x['evidence_id']:x for x in d['evidence']};p={x['case_id']:x for x in d['technical_profiles']};r={x['case_id']:x for x in d['gate_reviews']}
 assessments=[];units=[]
 for c in d['objects']:
  cid=c['case_id'];own=[o for o in d['observations'] if o['case_id']==cid]
  result=evaluate_case(c,r[cid],own,e,p[cid],cutoff);assessments.append(result)
  trl=result['axes']['TRL']['public_evidence_stage'];crl=result['axes']['CRL']['public_evidence_stage']
  units.append({**c,'trl_public_evidence_stage':trl,'crl_public_evidence_stage':crl,'paired_axes_usable':trl is not None and crl is not None,
   'formal_trl':None,'formal_crl':None,'current_industry_level':None,'assessment_status':'public_evidence_preassessment'})
 um={u['case_id']:u for u in units};directions=[]
 for t in d['technology_registry']:
  if t['entity_level']!='direction_candidate':continue
  ls=[l for l in d['case_technology_links'] if t['technology_id'] in l['parent_direction_ids']]
  ids={l['case_id'] for l in ls};rows=[um[c] for c in sorted(ids)]
  dist=lambda field:dict(Counter(str(u[field]) if u[field] is not None else 'unknown' for u in rows))
  src={x['source_id'] for x in d['evidence'] if x['case_id'] in ids}
  directions.append(dict(technology_id=t['technology_id'],canonical_name=t['canonical_name'],
   associated_case_count=len(rows),case_ids=sorted(ids),case_relations=[dict(case_id=l['case_id'],relation=l['relation_to_direction']) for l in ls],
   source_url_count=len(src),associated_case_trl_distribution=dist('trl_public_evidence_stage'),associated_case_crl_distribution=dist('crl_public_evidence_stage'),
   same_case_pairs=[dict(case_id=u['case_id'],TRL=u['trl_public_evidence_stage'],CRL=u['crl_public_evidence_stage'],period=u['evidence_period']) for u in rows if u['paired_axes_usable']],
   direction_trl=None,direction_crl=None,formal_trl=None,formal_crl=None,
   interpretation='关联案例的证据分布；不以均值或最大值替代整个技术方向的等级'))
 coords=[dict(case_id=u['case_id'],canonical_name=u['canonical_name'],TRL=u['trl_public_evidence_stage'],CRL=u['crl_public_evidence_stage'],period=u['evidence_period']) for u in units if u['paired_axes_usable']]
 gaps=[dict(case_id=u['case_id'],canonical_name=u['canonical_name'],missing_axes=[a for a,k in [('TRL','trl_public_evidence_stage'),('CRL','crl_public_evidence_stage')] if u[k] is None],evidence_period=u['evidence_period'],required_evidence=u['remaining_gaps'],formal_review_required=True) for u in units]
 summary=dict(assessment_cutoff=cutoff,theme_count=len(d['themes']),source_record_count=d['dataset']['total_source_records'],
  candidate_direction_count=len(directions),bounded_object_count=len(units),
  objects_with_trl=sum(u['trl_public_evidence_stage'] is not None for u in units),objects_with_crl=sum(u['crl_public_evidence_stage'] is not None for u in units),
  objects_with_both=len(coords),objects_with_neither=sum(u['trl_public_evidence_stage'] is None and u['crl_public_evidence_stage'] is None for u in units),
  trl_distribution=dict(Counter(str(u['trl_public_evidence_stage']) if u['trl_public_evidence_stage'] is not None else 'unknown' for u in units)),
  crl_distribution=dict(Counter(str(u['crl_public_evidence_stage']) if u['crl_public_evidence_stage'] is not None else 'unknown' for u in units)),
  formal_grade_count=0,direction_scalar_count=0,source_url_count=len(d['sources']),accepted_evidence_passages=len(d['evidence']),reviewed_gate_observations=len(d['observations']),
  observed_fact_count=len(d['observed_facts']),method='Independent evidence-gate evaluation; TRL: Q/GDW 12566—2025; CRL: tender five levels and project operational rules',
  interpretation='公开证据初评；检索覆盖不等于实质评审覆盖；来源URL不等于独立研究数')
 return d,dict(assessment_units=units,assessments=assessments,direction_evidence_profiles=directions,same_case_coordinates=coords,evidence_gaps=gaps,SUMMARY=summary)

def write_outputs(data_dir,output_dir,excel=True):
 d,outputs=assess(data_dir);dest=Path(output_dir);dest.mkdir(parents=True,exist_ok=True)
 for name,value in outputs.items():write(dest/(name+'.json'),value)
 cols=['case_id','canonical_name','trl_public_evidence_stage','crl_public_evidence_stage','paired_axes_usable','evidence_period','object_configuration','application_or_target_function','boundary','formal_trl','formal_crl']
 with (dest/'assessment_units.csv').open('w',encoding='utf-8-sig',newline='') as f:
  writer=csv.DictWriter(f,fieldnames=cols,extrasaction='ignore');writer.writeheader()
  for row in outputs['assessment_units']:
   # Spreadsheet-safe CSV: evidence itself remains exact in JSON.
   row={k:("'"+v if isinstance(v,str) and v.startswith(('=','+','-','@')) else v) for k,v in row.items()};writer.writerow(row)
 from .report import write_report,write_workbook
 write_report(dest,outputs)
 if excel:write_workbook(dest,d,outputs)
 write(dest/'INPUT_CHECKSUMS.json',{n+'.json':file_sha(Path(data_dir)/(n+'.json')) for n in INPUT_NAMES})
 return outputs['SUMMARY']
