# 数据说明

## 输入

|文件|内容|
|---|---|
|`data/objects.json`|122个有界对象；无预先填入的TRL/CRL值|
|`data/technology_registry.json`|391候选方向与122对象的登记信息|
|`data/themes.json`|证据登记的来源主题上下文；当前输出目录以assets/full_nmf500中的F主题为准|
|`data/theme_direction_links.json`|主题—候选方向关联|
|`data/case_technology_links.json`|对象—方向关联及关系类型|
|`data/technical_profiles.json`|技术分解建议、性能要求和评审状态|
|`data/gate_reviews.json`|两轴各阶段门槛、状态、理由与观测引用|
|`data/observations.json`|支持/反证观测，对象、范围、断言状态及引文区间|
|`data/evidence.json`|126段已接受引文，来源链接、区间、时间及哈希|
|`data/sources.json`|114个来源URL及性质、日期信息|
|`data/observed_facts.json`|17条独立注明数据类型的工程/商业事实|
|`data/dataset.json`|截止时间、范围、依据和检索覆盖说明|

`case_id`为对象主键，`scope_id`用于范围约束；`technology_id`中`TD-`为候选方向，`TR-`为有界路线对象。C/W对象前缀只用于追踪采集来源，不改变判级尺度。

`quote_start`和`quote_end`是抓取/提取的原文Unicode字符偏移，不是PDF页码。`quote_sha256`验证仓库中引文；`original_body_sha256`记录来源正文摘要值，因全文不随库发布，不能在缺少全文时声称已经重新核对它。

观测无需重复储存引文文本：运行时根据证据段和区间重建。`assertion`区分`completed`、`application_concept`、`confirmed_absence`、`planned`、`background`；`polarity`区分`support`、`contradict`、`context`。

## 输出

- `assessment_units.json` / `.csv`：对象名称、配置、场景、时期、TRL、CRL和限制。
- `assessments.json`：每个对象两轴独立计算结果和所有门槛。
- `direction_evidence_profiles.json`：方向关联案例分布，方向等级为`null`。
- `same_case_coordinates.json`：仅同对象双轴有值的二维坐标。
- `evidence_gaps.json`：当前未知轴及所需证据。
- `SUMMARY.json`：当前计数与口径。
- `INPUT_CHECKSUMS.json`：当前输入文件的SHA256。
- `VALIDATION.json`：离线验证记录。
- `技术_TRL_CRL评估结果.xlsx` / `评估报告.md`：面向阅读的当前结果。

`trl_public_evidence_stage`和`crl_public_evidence_stage`是公开证据阶段；`formal_trl`、`formal_crl`均为空。JSON中`null`在Excel/CSV显示为空，不使用0或1替代未知。

事实类型包括`reported_actual`（来源报告实际值）、`installed`（实际安装）、`nameplate`（额定）、`planned_total`（规划）、`synthetic_price_calculation`（合成价格计算）。这些类型不能互相替代。
