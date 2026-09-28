"""Evidence-dependence diagnostics using the current TRL/CRL engine.

python pipelines/nmf500/experiments.py
Requires pandas/numpy in addition to the core package; no GPU or remote sources.
"""
from __future__ import annotations

import argparse
import copy
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0,str(REPO))
from trl_crl.pipeline import load_inputs
from trl_crl.engine import evaluate_case


def ablate_review(review, observations, removed_observations=(), gate_target=None):
    """Withdraw an entire reviewed gate if any of its cited supports is removed.

    Conservative evidence withdrawal, not re-review of remaining passages and
    never deletion/relaxation of a criterion. Qualification measurements are
    cleared with the gate, preventing stale or partial supporting references.
    """
    removed = set(removed_observations)
    revised = copy.deepcopy(review)
    for axis, stages in revised['axes'].items():
        for stage in stages:
            for gate in stage['gates']:
                targeted = gate_target and (gate_target == axis or gate_target == f'{axis}:{gate["key"]}')
                if removed.intersection(gate['observation_ids']) or targeted:
                    gate.update(status='unknown',observation_ids=[],measurements=[],
                                rationale='Diagnostic evidence withdrawal; no remaining-support semantic re-review')
    return revised, [o for o in observations if o['observation_id'] not in removed]


def run(data_dir, mapping_file, output):
    output.mkdir(parents=True,exist_ok=True)
    data = load_inputs(data_dir)
    evidence = {e['evidence_id']:e for e in data['evidence']}
    reviews = {r['case_id']:r for r in data['gate_reviews']}
    profiles = {p['case_id']:p for p in data['technical_profiles']}
    own = {c['case_id']:[o for o in data['observations'] if o['case_id']==c['case_id']] for c in data['objects']}
    cutoff = data['dataset']['assessment_cutoff']
    def evaluate(case, review, observations, ev):
        result = evaluate_case(case,review,observations,ev,profiles[case['case_id']],cutoff)
        return {a:result['axes'][a]['public_evidence_stage'] for a in ['TRL','CRL']}
    baseline = {c['case_id']:evaluate(c,reviews[c['case_id']],own[c['case_id']],evidence) for c in data['objects']}
    scenarios, changes = [], []
    # This dataset contains only supporting observations. With contradictions,
    # removing negative evidence need not be monotone; reject that unsupported audit.
    assert all(o['polarity'] in {'support','context'} for o in data['observations'])

    def trial(kind,name,removed_evidence=(),removed_observations=(),target=None):
        removed_evidence, removed_observations = set(removed_evidence),set(removed_observations)
        removed_observations.update(o['observation_id'] for o in data['observations'] if o['evidence_id'] in removed_evidence)
        ev = {k:v for k,v in evidence.items() if k not in removed_evidence}
        new = {}
        for case in data['objects']:
            cid = case['case_id']
            if target or any(o['observation_id'] in removed_observations for o in own[cid]):
                review, obs = ablate_review(reviews[cid],own[cid],removed_observations,target)
                new[cid] = evaluate(case,review,obs,ev)
            else:
                new[cid] = baseline[cid]
        for axis in ['TRL','CRL']:
            changed = [cid for cid in baseline if baseline[cid][axis]!=new[cid][axis]]
            known = sum(v[axis] is not None for v in new.values())
            upgrades = sum((new[cid][axis] or 0)>(baseline[cid][axis] or 0) for cid in baseline)
            assert upgrades==0, (kind,name,axis)
            # Removing all support for one axis must not affect the other axis.
            if target in ['TRL','CRL'] and axis!=target:
                assert not changed
            lost = sum(baseline[cid][axis] is not None and new[cid][axis] is None for cid in baseline)
            drops = [baseline[cid][axis]-new[cid][axis] for cid in changed if new[cid][axis] is not None]
            scenarios.append(dict(kind=kind,scenario=name,axis=axis,removed_evidence=len(removed_evidence),
                removed_observations=len(removed_observations),changed_cases=len(changed),
                unchanged_fraction=1-len(changed)/len(baseline),known_cases=known,
                unknown_fraction=1-known/len(baseline),known_to_unknown=lost,
                mean_drop_among_still_known=float(np.mean(drops)) if drops else None,upgrades=upgrades))
            for cid in changed:
                changes.append(dict(kind=kind,scenario=name,axis=axis,case_id=cid,
                    baseline_stage=baseline[cid][axis],ablated_stage=new[cid][axis],
                    interpretation='Loss of documented support, not a claim of technology regression'))

    for source in data['sources']:
        trial('source_loo',source['source_id'],[k for k,e in evidence.items() if e['source_id']==source['source_id']])
    for eid in evidence:
        trial('passage_loo',eid,[eid])
    for obs in data['observations']:
        trial('observation_loo',obs['observation_id'],removed_observations=[obs['observation_id']])
    source_types = {s['source_id']:s['source_type'] for s in data['sources']}
    for source_type in sorted(set(source_types.values())):
        trial('source_type_ablation',source_type,[k for k,e in evidence.items() if source_types[e['source_id']]==source_type])
    targets = sorted({f'{axis}:{g["key"]}' for r in reviews.values() for axis,stages in r['axes'].items() for s in stages for g in s['gates'] if g['status']=='met'})
    for target in ['TRL','CRL'] + targets:
        trial('gate_support_ablation',target,target=target)
    for date in ['2025-12-31','2026-06-30','2026-09-24','2026-09-25']:
        trial('availability_cutoff',date,[k for k,e in evidence.items() if e['available_by'][:10]>date or (e.get('published_at') or '')[:10]>date])
    result, change = pd.DataFrame(scenarios),pd.DataFrame(changes)
    result.to_csv(output/'evidence_scenarios.csv',index=False,encoding='utf-8-sig')
    change.to_csv(output/'changed_cases.csv',index=False,encoding='utf-8-sig')
    fragility = []
    for cid,v in baseline.items():
        for axis in ['TRL','CRL']:
            own_source_ids = {e['source_id'] for e in evidence.values() if e['case_id']==cid}
            fragility.append(dict(case_id=cid,axis=axis,baseline_stage=v[axis],source_count=len(own_source_ids),
                source_deletions_changing_stage=int(((change.kind=='source_loo')&(change.case_id==cid)&(change.axis==axis)).sum()),
                passage_deletions_changing_stage=int(((change.kind=='passage_loo')&(change.case_id==cid)&(change.axis==axis)).sum()),
                observation_deletions_changing_stage=int(((change.kind=='observation_loo')&(change.case_id==cid)&(change.axis==axis)).sum())))
    fragility = pd.DataFrame(fragility)
    fragility.to_csv(output/'case_fragility.csv',index=False,encoding='utf-8-sig')
    mapping = pd.read_csv(mapping_file)
    mapping_rows = []
    for top in [1,3]:
        for cosine in [0.,.60,.65,.70,.75]:
            for margin in [0.,.01,.02]:
                for entity_type in ['case','direction']:
                    selected = mapping[(mapping['rank']<=top)&mapping.cosine.ge(cosine)&mapping.top1_top2_margin.ge(margin)&mapping.entity_type.eq(entity_type)]
                    mapping_rows.append(dict(top_k=top,cosine_min=cosine,top1_margin_min=margin,entity_type=entity_type,
                        retained_entities=selected.entity_id.nunique(),candidate_links=len(selected),
                        covered_topics=selected.category_id.nunique(),theme_trl_assigned=0,theme_crl_assigned=0,
                        mapping_still_requires_semantic_review=True))
    mapping_frame = pd.DataFrame(mapping_rows)
    mapping_frame.to_csv(output/'mapping_sensitivity.csv',index=False,encoding='utf-8-sig')
    summary = dict(cases=len(baseline),sources=len(data['sources']),passages=len(evidence),observations=len(data['observations']),
        scenario_count=len(scenarios)//2,source_loo_cases_with_any_axis_changed=int(change[change.kind.eq('source_loo')].case_id.nunique()),
        source_loo_fragile_known_trl=int(((fragility.axis=='TRL')&fragility.source_deletions_changing_stage.gt(0)).sum()),
        source_loo_fragile_known_crl=int(((fragility.axis=='CRL')&fragility.source_deletions_changing_stage.gt(0)).sum()),
        upgrades=int(result.upgrades.sum()),cross_axis_ablation_independence_passed=True,
        frozen_evidence_only=True,new_remote_evidence_added=0,
        limitation='Conservative withdrawal: any removed citation resets the gate to unknown; remaining support is not semantically re-adjudicated. Not an accuracy experiment.',
        time_limit='All 126 available_by values are 2026-09-25. Earlier knowledge-date tests return unknown; they cannot reconstruct historical maturity.',
        mapping_limit='Top3 expands candidate coverage only. No cosine threshold certifies semantic correctness or transfers grades.')
    (output/'SUMMARY.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n')
    aggregate=result[result.kind.isin(['source_loo','passage_loo','observation_loo'])].rename(columns={'axis':'evidence_axis'}).groupby(['kind','evidence_axis'])[['changed_cases','unchanged_fraction','known_to_unknown']].agg(['min','mean','max'])
    report='# TRL/CRL 灵敏度与证据消融\n\n'+json.dumps(summary,ensure_ascii=False,indent=2)+'\n\n## 留一实验\n\n'+aggregate.to_markdown()+'\n\n整体平均保持率会被每次未受影响的对象抬高，应重点读取 case_fragility.csv 中各对象自身证据脆弱性。未知不是 0 级，等级降幅只对消融后仍有等级者计算。\n\n## 来源类型与时间\n\n'+result[result.kind.isin(['source_type_ablation','availability_cutoff'])].to_markdown(index=False)+'\n\n## 映射阈值（Top1，无间隔门槛）\n\n'+mapping_frame[(mapping_frame.top_k==1)&(mapping_frame.top1_margin_min==0)].to_markdown(index=False)+'\n\n当前引擎执行时间、对象和判据绑定校验；删证据检验支持依赖性，不等于删掉标准中的必要条件。全部结果仍为公开证据初评，未经独立专家验证。\n'
    (output/'REPORT.md').write_text(report)
    print(json.dumps(summary,ensure_ascii=False,indent=2))


if __name__=='__main__':
    p=argparse.ArgumentParser()
    p.add_argument('--data',type=Path,default=REPO/'data')
    p.add_argument('--mapping',type=Path,default=REPO/'tests/fixtures/nmf500_results/theme_context_top3.csv')
    p.add_argument('--output',type=Path,default=REPO/'tests/fixtures/nmf500_results/experiments')
    args=p.parse_args()
    run(args.data,args.mapping,args.output)
