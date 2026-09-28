# 项目结构与逐文件用途

## 从哪里开始

当前计算入口是 `pipelines/full_nmf/`，当前成果仅在 `assets/full_nmf500/`。`tests/fixtures/` 是固定回归输入，不是另一套待选用成果。共享模块和兼容实现因当前调用或测试需要而保留，不应直接替代全量入口。

阅读 [当前报告](../assets/full_nmf500/experiments/REPORT.md)、[方法](METHOD.md) 和 [复现步骤](REPRODUCING.md)。下面逐项列出全部 Git 管理的文件及目录，不用省略号隐藏文件。

## 完整结构图

```text
energy-technology-trl-crl/  # 当前发布源码与紧凑成果
├── .github/  # 远端自动化配置
│   └── workflows/  # 持续集成工作流
│       └── validate.yml  # 自动安装依赖并运行测试和校验
├── assets/  # 发布用的紧凑结果；不是原始语料
│   └── full_nmf500/  # 当前全量 500 主题流程或成果
│       ├── experiments/  # 已完成消融与灵敏度实验的表格、报告和校验记录
│       │   ├── COMPLETE.json  # 完成标记、输入绑定和输出指纹
│       │   ├── REPORT.md  # 面向读者的结果报告
│       │   ├── SUMMARY.json  # 机器可读统计摘要
│       │   ├── case_fragility.csv  # 逐案例证据依赖程度
│       │   ├── changed_cases.csv  # 逐实验情景发生等级变化的案例及变化内容
│       │   ├── evidence_scenarios.csv  # 逐证据撤回情景的双轴变化
│       │   ├── full_topic_case_fragility.csv  # 连接当前主题的案例证据依赖
│       │   └── mapping_sensitivity.csv  # 主题关联参数网格及覆盖变化
│       ├── MANIFEST.json  # 当前发布结果的 SHA-256 指纹
│       ├── POSTPROCESS_DELIVERY.json  # 三仓库交付及实验绑定记录
│       ├── REPORT.md  # 面向读者的结果报告
│       ├── SUMMARY.json  # 机器可读统计摘要
│       ├── case_hotspot_links.csv  # 案例与热点指标连接
│       ├── theme_context_top3.csv  # 案例和技术方向的前三个候选主题
│       └── theme_evidence_profiles.csv  # 各主题可检索证据概况，不是主题等级
├── data/  # 有边界的成熟度证据输入，必须保留
│   ├── case_technology_links.json  # 案例与技术对象关系
│   ├── dataset.json  # 证据数据集元信息
│   ├── evidence.json  # 证据段落与可知日期
│   ├── gate_reviews.json  # 成熟度门槛审核决定
│   ├── objects.json  # 成熟度评估案例边界
│   ├── observations.json  # 从证据提取的事实观察
│   ├── observed_facts.json  # 规范化事实登记
│   ├── sources.json  # 证据来源登记
│   ├── technical_profiles.json  # 案例技术任务与边界画像
│   ├── technology_registry.json  # 技术方向登记
│   ├── theme_direction_links.json  # 主题与技术方向关系
│   └── themes.json  # 证据库主题实体
├── docs/  # 方法、数据、复现与目录说明
│   ├── CORE_FILES.md  # 核心文件与外部大文件边界
│   ├── DATA_SCHEMA.md  # 数据字段约定
│   ├── FULL_EXPERIMENTS.md  # 实验设计和解释限制
│   ├── FULL_NMF.md  # 全量主题流程说明
│   ├── METHOD.md  # 当前算法与适用边界
│   ├── PROJECT_STRUCTURE.md  # 本文件：全部受版本管理文件的用途索引
│   └── REPRODUCING.md  # 环境、输入和复现步骤
├── pipelines/  # 计算与复现入口
│   ├── full_nmf/  # 当前全量主流程
│   │   ├── build.py  # 构建本阶段计算结果
│   │   ├── experiments.py  # 执行消融及灵敏度实验
│   │   └── report.py  # 生成人类可读结果报告
│   └── nmf500/  # 共享计算模块或固定回归流程；当前入口见 full_nmf
│       ├── encode_context.py  # 编码案例和技术方向以关联主题
│       ├── experiments.py  # 执行消融及灵敏度实验
│       ├── mapping.py  # 候选主题相似度匹配及边界约束
│       └── replay.py  # 固定输入的离线兼容回放
├── provenance/  # 文件指纹与审计元数据
│   └── CORE_FILES.json  # 当前核心文件完整性清单
├── tests/  # 自动化测试及固定输入
│   ├── fixtures/  # 仅用于兼容回归，不代表当前成果
│   │   ├── nmf500/  # 固定回归目录；不作为当前结果使用
│   │   │   ├── taxonomy_overlay/  # 固定回归目录；不作为当前结果使用
│   │   │   │   ├── case_technology_links.json  # 固定回归输入/期望值；不作为当前结果使用：案例与技术对象关系
│   │   │   │   ├── dataset.json  # 固定回归输入/期望值；不作为当前结果使用：证据数据集元信息
│   │   │   │   ├── objects.json  # 固定回归输入/期望值；不作为当前结果使用：成熟度评估案例边界
│   │   │   │   ├── theme_direction_links.json  # 固定回归输入/期望值；不作为当前结果使用：主题与技术方向关系
│   │   │   │   └── themes.json  # 固定回归输入/期望值；不作为当前结果使用：证据库主题实体
│   │   │   └── MANIFEST.json  # 固定回归输入/期望值；不作为当前结果使用：当前发布结果的 SHA-256 指纹
│   │   └── nmf500_results/  # 固定回归目录；不作为当前结果使用
│   │       ├── experiments/  # 固定回归目录；不作为当前结果使用
│   │       │   ├── SUMMARY.json  # 固定回归输入/期望值；不作为当前结果使用：机器可读统计摘要
│   │       │   ├── case_fragility.csv  # 固定回归输入/期望值；不作为当前结果使用：逐案例证据依赖程度
│   │       │   ├── changed_cases.csv  # 固定回归输入/期望值；不作为当前结果使用：逐实验情景发生等级变化的案例及变化内容
│   │       │   ├── evidence_scenarios.csv  # 固定回归输入/期望值；不作为当前结果使用：逐证据撤回情景的双轴变化
│   │       │   └── mapping_sensitivity.csv  # 固定回归输入/期望值；不作为当前结果使用：主题关联参数网格及覆盖变化
│   │       ├── 500主题热点与TRL_CRL.xlsx  # 固定回归输入/期望值；不作为当前结果使用
│   │       ├── INPUT_CHECKSUMS.json  # 固定回归输入/期望值；不作为当前结果使用
│   │       ├── MAPPING_SUMMARY.json  # 固定回归输入/期望值；不作为当前结果使用
│   │       ├── PROVENANCE.json  # 固定回归输入/期望值；不作为当前结果使用
│   │       ├── SUMMARY.json  # 固定回归输入/期望值；不作为当前结果使用：机器可读统计摘要
│   │       ├── VALIDATION.json  # 固定回归输入/期望值；不作为当前结果使用：数据完整性检查结果
│   │       ├── assessment_units.csv  # 固定回归输入/期望值；不作为当前结果使用
│   │       ├── assessment_units.json  # 固定回归输入/期望值；不作为当前结果使用
│   │       ├── assessments.json  # 固定回归输入/期望值；不作为当前结果使用
│   │       ├── axis_recalculation_check.csv  # 固定回归输入/期望值；不作为当前结果使用
│   │       ├── case_hotspot_links.csv  # 固定回归输入/期望值；不作为当前结果使用：案例与热点指标连接
│   │       ├── direction_evidence_profiles.json  # 固定回归输入/期望值；不作为当前结果使用
│   │       ├── evidence_gaps.json  # 固定回归输入/期望值；不作为当前结果使用
│   │       ├── same_case_coordinates.json  # 固定回归输入/期望值；不作为当前结果使用
│   │       ├── theme_context_top3.csv  # 固定回归输入/期望值；不作为当前结果使用：案例和技术方向的前三个候选主题
│   │       ├── theme_evidence_profiles.csv  # 固定回归输入/期望值；不作为当前结果使用：各主题可检索证据概况，不是主题等级
│   │       ├── theme_evidence_profiles.json  # 固定回归输入/期望值；不作为当前结果使用
│   │       └── 技术_TRL_CRL评估结果.xlsx  # 固定回归输入/期望值；不作为当前结果使用
│   ├── test_assessment.py  # 回归测试：assessment
│   ├── test_current_release.py  # 回归测试：current / release
│   ├── test_evidence_boundaries.py  # 回归测试：evidence / boundaries
│   ├── test_full_experiments.py  # 回归测试：full / experiments
│   ├── test_full_nmf.py  # 回归测试：full / nmf
│   ├── test_mapping_boundaries.py  # 回归测试：mapping / boundaries
│   ├── test_nmf500_diagnostics.py  # 回归测试：nmf500 / diagnostics
│   └── test_readable_report.py  # 回归测试：readable / report
├── tools/  # 发布校验、清单及维护工具
│   ├── bind_review_scopes.py  # 将审核记录绑定到明确对象边界
│   ├── check_current_release.py  # 校验核心代码、成果指纹和文档链接
│   └── project_structure.py  # 重建本结构图及逐文件用途
├── trl_crl/  # 成熟度双轴评估引擎
│   ├── __init__.py  # Python 包初始化
│   ├── __main__.py  # 模块命令行入口
│   ├── common.py  # 公共路径、配置和辅助函数
│   ├── engine.py  # 逐对象双轴成熟度推理
│   ├── pipeline.py  # 数据加载、评估与成果输出
│   ├── report.py  # 生成人类可读结果报告
│   ├── research.py  # 研究证据整理辅助
│   └── rules.py  # TRL/CRL 门槛规则
├── .gitattributes  # Git 文本与二进制属性
├── .gitignore  # 排除缓存、本地大数据和运行输出
├── NOTICE.md  # 数据来源和使用声明
├── README.md  # 项目入口：当前方法、结果及运行说明
├── pyproject.toml  # 包元数据、依赖与命令入口
├── requirements-nmf500.txt  # 运行/测试依赖版本约束（用途由文件后缀区分）
└── requirements.txt  # 运行/测试依赖版本约束（用途由文件后缀区分）
```

## 不随仓库发布的本地内容

`work/`、`outputs/` 或 `results/` 中的全量运行目录保存训练权重、向量、逐条分类、数据库和日志；原始文献及编码器权重也属于外部运行输入。这些文件体量大，不是本结构图漏列的源码，具体输入位置与生成步骤见复现说明。删除仓库中的旧发布快照不会删除这些运行数据。

## 维护本图

新增、移动或删除文件后运行 `python tools/project_structure.py`。只扫描 Git 可见文件，不扫描原始语料；发布前还应运行核心文件校验。每个文件名后为其作用；测试数据不可用于宣称当前模型效果。
