# 成员4第一周交付包：交互质量分析与评分模块

本包为“课程探究式学习任务生成与交互质量评估系统”中，成员4负责模块的第一周原型成果。

## 模块目标

对学生与大模型的交互过程进行分析，不以最终答案正确性为主要标准，而重点评价：

- 是否完成规定轮数的有效交互；
- 是否使用多种交互方式；
- 是否基于上一轮回答继续追问；
- 是否包含表达理解、审辨、猜想、创新等深度行为；
- 是否对核心知识点形成基本覆盖。

## 目录说明

```text
member4_week1_evaluator/
├── evaluator/                   # 评分模块源代码
├── sample_data/                 # 接口样例与测试数据
├── output/                      # 已生成的评分结果样例
├── docs/                        # 评分规则与提交说明
├── tests/                       # 单元测试
├── run_evaluation.py            # 评分运行入口
└── README.md
```

## 快速运行

```bash
python run_evaluation.py \
  --knowledge sample_data/knowledge.json \
  --task sample_data/task.json \
  --submission sample_data/student_submission.json \
  --output output/score.json
```

本原型仅使用 Python 标准库，不需要安装额外依赖。


`sample_data/student_submission.json` 与 `output/score.json` 为统一接口名称下的默认演示文件；另保留 good/shallow 两组样例用于对比测试。
