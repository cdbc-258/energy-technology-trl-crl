"""将保存的成熟度实验结果写成可阅读的中文报告。"""
from pathlib import Path
import argparse
import json
import pandas as pd


def table(headers,rows):
    return '| '+' | '.join(headers)+' |\n| '+' | '.join(['---']*len(headers))+' |\n'+''.join('| '+' | '.join(map(str,row))+' |\n' for row in rows)


def render(folder):
    folder=Path(folder);s=json.loads((folder/'SUMMARY.json').read_text())
    scenarios=pd.read_csv(folder/'evidence_scenarios.csv');mapping=pd.read_csv(folder/'mapping_sensitivity.csv')
    text='# TRL/CRL：证据消融与灵敏度实验报告\n\n## 结论\n\n'
    text+=f"在 {s['cases']} 个有明确评估边界的案例中，{s['source_loo_cases_with_any_axis_changed']} 个在撤回某一来源后至少一个成熟度轴变化。结果较依赖现有证据，不能把全量主题匹配误解为全部主题都有可靠成熟度等级。\n\n"
    text+=table(['覆盖项','数量'],[['案例',s['cases']],['来源',s['sources']],['段落',s['passages']],['事实观察',s['observations']],['实验情景',s['scenario_count']],['撤回后反而升级',s['upgrades']]])
    text+='\n## 实验验证什么\n\nTRL 衡量技术就绪程度，CRL 衡量商业就绪程度，两个轴独立判定。逐次撤回来源、段落或观察，改变证据类型、可知日期及主题关联条件，再检查等级变化。每个情景分别记录两个轴，所以情景表行数是情景数的两倍。\n\n这是冻结证据的稳健性检查，不是准确率测试，也没有补采新证据。采用保守撤回规则：移除必需引用会使对应门槛回到“未知”，没有重新人工裁决剩余证据能否支撑原判断。\n\n## 单一来源依赖\n\n'
    text+=table(['指标','案例数'],[['已知TRL受至少一次来源撤回影响',s['source_loo_fragile_known_trl']],['已知CRL受至少一次来源撤回影响',s['source_loo_fragile_known_crl']],['任一轴受来源撤回影响',s['source_loo_cases_with_any_axis_changed']]])
    text+='\n不能只看每次撤回后全体案例的“不变比例”：删除某个案例的证据本来就不会影响大量无关案例。[逐案例脆弱性](case_fragility.csv) 更能体现依赖关系。\n\n## 撤回不同类型证据的影响\n\n'
    types={'papers':'论文','paper':'论文','government_case_compilation':'政府案例汇编','patent':'专利','policy':'政策','public_project_or_research_source':'公开项目/研究来源','public_research_source':'公开研究来源'}
    subset=scenarios[scenarios.kind.str.contains('type')]
    text+=table(['撤回类型','评估轴','删除段落','等级变化案例','已知变未知'],[(types.get(r.scenario,r.scenario),r.axis,r.removed_evidence,r.changed_cases,r.known_to_unknown) for r in subset.itertuples()])
    text+='\n若某类证据实际删除数量为零，“没有变化”不能证明稳健。跨轴独立性检查通过仅说明两个轴没有错误串用证据，不证明等级准确。\n\n## 主题关联门槛\n\n固定余弦下限为 0，以下展示 Top1 检索随第一、第二主题相似度差距门槛变化的结果。\n\n'
    subset=mapping[(mapping.top_k==1)&(mapping.cosine_min==0)]
    text+=table(['对象','最低相似度差距','保留对象','覆盖主题','自动赋TRL主题','自动赋CRL主题'],[('案例' if r.entity_type=='case' else '技术方向',r.top1_margin_min,r.retained_entities,r.covered_topics,r.theme_trl_assigned,r.theme_crl_assigned) for r in subset.itertuples()])
    text+='\nTop3 仅扩大候选检索范围。相似度不能把案例的等级转移给整个主题；[完整参数网格](mapping_sensitivity.csv) 中的关联仍需语义审核。\n\n## 日期和覆盖边界\n\n分类底座覆盖全量冻结来源，但成熟度证据仅覆盖上述案例。全部 126 个段落的可知日期为 2026-09-25，更早的知识截止日会得到未知，不能据此还原真实历史成熟度。应优先为单一来源依赖的案例补充独立证据，再人工复核。\n\n明细：[摘要及输入指纹](SUMMARY.json)、[逐情景结果](evidence_scenarios.csv)、[关联主题后的案例脆弱性](full_topic_case_fragility.csv)。\n'
    (folder/'REPORT.md').write_text(text)
    return text


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input',type=Path,required=True)
    render(parser.parse_args().input)
