# 复现与运行

依赖见requirements.txt。在仓库根目录可用data中的证据离线重算对象级评估：

    python -m trl_crl build --data data --output /tmp/trl-crl-current --no-excel
    python -m trl_crl validate --data data --output /tmp/trl-crl-current

上述命令验证对象判级及证据链；F主题关联由全量入口完成，不要将引擎的来源上下文目录当作当前500主题目录。

全量映射需要主题仓库的中心、热点当前结果，以及work/nmf500/context中的contexts.json、embeddings.npy、ENCODING.json。上下文编码入口为pipelines/nmf500/encode_context.py，使用同一BGE-M3模型。

在共享工作区根目录：

    .venv-hotspots/bin/python energy-technology-trl-crl/pipelines/full_nmf/build.py --classification energy-topic-identification/work/full_nmf500_20260926 --hotspots energy-topic-hotspots/outputs/full_nmf500_20260926 --output energy-technology-trl-crl/results/full_nmf500_20260926
    .venv-hotspots/bin/python energy-technology-trl-crl/pipelines/full_nmf/experiments.py --classification energy-topic-identification/work/full_nmf500_20260926 --input energy-technology-trl-crl/results/full_nmf500_20260926 --output energy-technology-trl-crl/results/full_nmf500_20260926/experiments

入口核对当前证据、上下文及分类摘要，不补造缺失证据。仓库根目录检查：

    python -m pytest -q
    python tools/check_current_release.py

大型向量保留在工作区。核心源码、证据及紧凑结果的完整性见provenance/CORE_FILES.json与assets/full_nmf500/MANIFEST.json。

## 仅重建报告和目录说明

无需重跑模型即可执行：

    python pipelines/full_nmf/report.py --input assets/full_nmf500/experiments
    python tools/project_structure.py

报告直接汇总已有 CSV/JSON；若修改了发布文件，提交前必须同步更新成果指纹与核心文件清单。
