"""Build an annotated copy of case_hotspot_links.csv with a CRL-gap explanation.

New, additive version: it does not modify trl_crl/pipeline.py nor the original
case_hotspot_links.csv. It re-runs the existing assess() and derives, from
objective fields only, why each object's CRL stage is empty.

Reason basis (docs/METHOD.md):
  4: 没找到销售资料不能证明CRL1；专利申请或授权不独立决定CRL；
     只有同对象许可、转让或产品交易的实际履约才能提供相应商业证据。
  80: 供应商自述、政府案例汇编和作者论文的证据强度不同。
Project-sourced objects surface their own recorded remaining_gaps verbatim.
"""
from pathlib import Path
import argparse
import json
import sys
import pandas as pd

REPO = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(REPO)]
from trl_crl.pipeline import assess

CRL_GAP_KEYWORDS = ('商业', '履约', '供货', '许可', '销售', '交易', '市场',
                    '经济', '收入', '签约', '买方', '结算', '商业化', 'CRL')


def crl_missing_reason(case, source_types, trl):
    if 'public_project_or_research_source' in source_types:
        rel = [g for g in (case.get('remaining_gaps') or [])
               if any(k in g for k in CRL_GAP_KEYWORDS)]
        return '；'.join(rel) if rel else '项目/调研来源，缺具体商业许可或供货履约证据'
    if 'patent' in source_types:
        return '专利申请或授权不独立决定CRL；无同对象许可、转让或产品交易履约证据'
    if trl is None:
        return '论文来源；无技术成熟度证据，亦无商业活动证据'
    if trl <= 4:
        return '论文来源，实验室阶段，无商业交易履约证据'
    if trl <= 6:
        return '论文来源，样机/原型阶段，无商业交易履约证据'
    return '论文来源，工程/产品阶段，无商业交易履约证据'


def build(data_dir, source_csv, out_csv):
    d, results = assess(data_dir)
    units = results['assessment_units']
    src = {s['source_id']: s['source_type'] for s in d['sources']}
    case_src = {}
    for e in d['evidence']:
        case_src.setdefault(e['case_id'], set()).add(src[e['source_id']])
    reason = {}
    for u in units:
        cid = u['case_id']
        reason[cid] = (crl_missing_reason(u, case_src.get(cid, set()), u['trl_public_evidence_stage'])
                       if u['crl_public_evidence_stage'] is None else None)
    df = pd.read_csv(source_csv, encoding='utf-8-sig')
    pos = list(df.columns).index('crl_public_evidence_stage') + 1
    df.insert(pos, 'crl_missing_reason', df['case_id'].map(reason))
    df.to_csv(out_csv, index=False, encoding='utf-8-sig')
    return len(df), int(df['crl_missing_reason'].notna().sum())


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--data', type=Path, default=REPO / 'data')
    p.add_argument('--source', type=Path, default=REPO / 'assets/full_nmf500/case_hotspot_links.csv')
    p.add_argument('--out', type=Path, default=REPO / 'assets/full_nmf500/case_hotspot_links_crl_reason.csv')
    a = p.parse_args()
    n, filled = build(a.data, a.source, a.out)
    print(json.dumps({'rows': n, 'crl_missing_reason_filled': filled}, ensure_ascii=False))
