"""Fill empty TRL/CRL stages in case_hotspot_links.csv with the recorded gap.

Re-runs the existing assess() and, for each object whose TRL or CRL stage is
empty, quotes the object's own remaining_gaps verbatim into the corresponding
cell instead of leaving it blank. Objects with a stage keep their level, shown
as TRLx / CRLx. It does not modify trl_crl/pipeline.py.

The gap text is not generated here: it is copied from data/objects.json
remaining_gaps, the object-level record of what evidence is still missing.
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
TRL_GAP_KEYWORDS = ('测试', '试验', '验证', '验收', '调试', '指标', '性能', '可靠性',
                    '成熟度', '型式', '实测', '对照', '推广', '达标', '效率', '纯度',
                    '产氢', '发电', 'TRL')


def gap_reason(case, keywords):
    rel = [g for g in (case.get('remaining_gaps') or [])
           if any(k in g for k in keywords)]
    return '；'.join(rel)


def build(data_dir, source_csv, out_csv):
    d, results = assess(data_dir)
    units = results['assessment_units']
    um = {u['case_id']: u for u in units}
    trl_reason = {}
    crl_reason = {}
    for u in units:
        if u['trl_public_evidence_stage'] is None:
            trl_reason[u['case_id']] = gap_reason(u, TRL_GAP_KEYWORDS)
        if u['crl_public_evidence_stage'] is None:
            crl_reason[u['case_id']] = gap_reason(u, CRL_GAP_KEYWORDS)
    df = pd.read_csv(source_csv, encoding='utf-8-sig')
    df['trl_public_evidence_stage'] = [
        f"TRL{int(um[cid]['trl_public_evidence_stage'])}" if um[cid]['trl_public_evidence_stage'] is not None
        else trl_reason.get(cid, '')
        for cid in df['case_id']
    ]
    df['crl_public_evidence_stage'] = [
        f"CRL{int(um[cid]['crl_public_evidence_stage'])}" if um[cid]['crl_public_evidence_stage'] is not None
        else crl_reason.get(cid, '')
        for cid in df['case_id']
    ]
    df.to_csv(out_csv, index=False, encoding='utf-8-sig')
    return len(df), len(trl_reason), len(crl_reason)


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--data', type=Path, default=REPO / 'data')
    p.add_argument('--source', type=Path, default=REPO / 'assets/full_nmf500/case_hotspot_links.csv')
    p.add_argument('--out', type=Path, default=REPO / 'assets/full_nmf500/case_hotspot_links.csv')
    a = p.parse_args()
    n, t_filled, c_filled = build(a.data, a.source, a.out)
    print(json.dumps({'rows': n, 'trl_reason_filled': t_filled, 'crl_reason_filled': c_filled}, ensure_ascii=False))
