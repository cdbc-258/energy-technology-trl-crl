# 能源技术 TRL / CRL 评估

将明确配置、场景和时期的技术对象关联到500个论文主题，并根据可追溯证据分别评估技术成熟度TRL与商业就绪度CRL。主题只组织文献，不直接获得成熟度等级。

## 当前怎么做

1. 从对象、来源、引文、观测、技术档案和逐门槛审阅记录构建证据链。
2. 对对象名称、配置、任务和证据形成上下文，以BGE-M3向量检索论文主题中心并保留Top3候选。
3. 依据Q/GDW 12566—2025的TRL 1—9级和项目定义的CRL 1—5级门槛独立评估两个轴。
4. 输出最高得到全部必要支持的公开证据阶段；证据不足保留未知，不传递其他对象、方向或主题的等级。
5. 执行来源、引文、观测留一及来源类型、门槛支持、证据时间、主题关联阈值实验。

当前122个有界对象、391个候选方向，共513个上下文实体。108个对象有TRL阶段、23个有CRL、13个两轴齐全、4个两轴未知。这些是公开证据初评，不是正式专家评级。

## 核心入口

|内容|入口|
|---|---|
|判据与引擎|[rules.py](trl_crl/rules.py)、[engine.py](trl_crl/engine.py)、[pipeline.py](trl_crl/pipeline.py)|
|对象及证据|[data/](data/)|
|全量主题与热点关联|[build.py](pipelines/full_nmf/build.py)|
|消融／灵敏度|[experiments.py](pipelines/full_nmf/experiments.py)|
|对象结果|[case_hotspot_links.csv](assets/full_nmf500/case_hotspot_links.csv)|
|主题证据分布|[theme_evidence_profiles.csv](assets/full_nmf500/theme_evidence_profiles.csv)|
|实验|[实验报告](assets/full_nmf500/experiments/REPORT.md)|

[方法与证据边界](docs/METHOD.md) · [字段说明](docs/DATA_SCHEMA.md) · [复现运行](docs/REPRODUCING.md) · [核心文件清单](docs/CORE_FILES.md) · [使用范围](NOTICE.md)。

## 目录导航

[完整项目结构及每个文件用途](docs/PROJECT_STRUCTURE.md)。当前成果在 `assets/full_nmf500/`；`tests/fixtures/` 只用于回归测试。
