# 执行入口

本仓库包含两张主表的完整实验设计与可运行的 CPU 工具。
机器人仿真接入、视频模型适配和正式实验还需要按
[ROADMAP](ROADMAP.md) 完成。

## 1. 安装和检查

```bash
git clone https://github.com/RunyiYang/WorldEdge_Execution.git
cd WorldEdge_Execution
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e .
python -m unittest discover -s tests -v
```

## 2. 查看计划数量

```bash
python -m worldedge_eval plan \
  --config configs/experiment.yaml \
  --output runs/plan.json
```

默认是 540 条机器人 lifetime，最多 5,400 个任务。
视频模型训练、开发、测试集分别有 3,200、400、600 段 reference clips。
两个主要 2B 模型共生成 2,400 段测试预测。
这些是计划数量，不是已经完成的实验数量。

## 3. 查看必须解析的配置

```bash
python -m worldedge_eval preflight \
  --config configs/experiment.yaml \
  --output runs/preflight.json
```

当前 null 字段是尚未解析的 checkpoint、接口、物理阈值、split 和
证据 manifest。初始 preflight 返回 exit code 2 是正常的。
必须从真实环境填入，不能填假路径或假 hash 来通过。
结构检查通过也不等于模型、物理和数据已验证。

## 4. 让 coding agent 按顺序实施

读取：

1. [完整实验协议](EXPERIMENT_PROTOCOL.md)
2. [实现里程碑](ROADMAP.md)
3. [后端接入要求](ADAPTERS.md)
4. [记录和评分格式](DATA_FORMATS.md)

先跑两个开发世界，验证真实动作接口和失败状态保留。
完成 evaluator 和数据泄漏检查后，再建立完整数据和正式测试。

Table 4 的策略权重冻结。Table 5 的视频模型需要声明并执行
目标 ARX 机器人适配。十轮任务之间不能重置物理状态。
视频 Outcome 指的是明确的 30 秒阶段目标。

## 5. 汇总结果

实际可运行的 score-policy、score-video、validate、tables 命令见
[README](../README.md#commands-available-now)。

score-policy 和 score-video 接收精简评分记录。它们与 schemas/ 中的
完整物理证据记录不同，转换关系在 DATA_FORMATS 中。

没有结果时可以导出空表：

```bash
python -m worldedge_eval tables \
  --config configs/experiment.yaml \
  --output-dir runs/table_templates
```

空白结果用 --，不完整结果用 NR。所有启用行都有完整记录后，
导出时加 --require-complete。
代码里的合成测试数字不属于实验结果。
