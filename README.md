# Paper Reading Investigator

一个面向学术论文 PDF 的自动化分析工具。

它可以读取一篇论文 PDF，自动判断是否需要 OCR，提取论文结构与基础元数据，用更易懂的方式解释核心概念，并最终生成一份正式的“论文考察报告”。

---

## 1. 这个项目能做什么

`Paper Reading Investigator` 的目标不是简单摘要论文，而是把一篇论文拆解成一个更适合阅读、理解、复现和批判性分析的结构化报告。

它主要完成以下任务：

- 判断 PDF 是文本型还是扫描型
- 对扫描版或难提取 PDF 做 OCR
- 抽取论文正文、章节和基础元数据
- 用更通俗的方式解释论文核心思想
- 评估论文是否容易复现
- 总结优点、缺陷、风险和信息缺口
- 生成一份正式 Markdown 报告

最终输出不是一句话总结，而是一份完整的 investigation report。

---

## 2. 适用场景

这个项目适合下面几类任务：

- 你下载了一篇论文，希望快速获得结构化理解
- 你想知道这篇论文是否值得复现
- 你不想只看 abstract，而是想看“核心方法 + 证据 + 风险”
- 你需要把一篇论文整理成汇报材料或内部阅读笔记
- 你处理的是扫描版 PDF，需要 OCR 兜底

---

## 3. 项目整体流程

完整流程如下：

```text
输入 PDF
   ↓
1. 检测 PDF 类型
   ↓
2. 必要时执行 OCR
   ↓
3. 提取正文、章节、元数据
   ↓
4. 分析论文内容
   ↓
5. 生成最终 Markdown 报告
```

你可以把它理解为一个“论文分析流水线”，而不是单个脚本。

## 4. 仓库结构说明

推荐的目录理解方式如下：

```text
.
├── README.md
└── paper-reading-investigator/
    ├── SKILL.md
    ├── requirements.txt
    ├── scripts/
    │   ├── detect_pdf_type.py
    │   ├── run_ocr.py
    │   ├── extract_paper.py
    │   ├── analyze_paper.py
    │   ├── build_report.py
    │   ├── build_meeting_brief.py      # 新增：组会简报生成
    │   ├── compare_papers.py           # 新增：多论文横向比较
    │   └── utils.py
    ├── templates/
    │   ├── paper_investigation_report.md
    │   └── group_meeting_brief.md      # 新增：简报模板
    ├── references/methodology_notes.md
    └── assets/example_output.md
```

## 5. 各脚本在做什么

### 5.1 detect_pdf_type.py

这个脚本负责判断论文 PDF 属于哪一类：

- `digital`：文本型 PDF，通常可直接提取
- `scanned`：扫描件，通常需要 OCR
- `mixed`：部分是文字，部分是图片
- `poor_text`：虽然不是纯扫描，但文本质量较差

它会统计：

- 总页数
- 总字符数
- 每页字符数
- 图片密集页比例

然后给出一个简单判断结果。

用途：  
先决定后续是直接提取，还是要先走 OCR。

### 5.2 run_ocr.py

当 PDF 是扫描版，或者抽取效果很差时，用这个脚本做 OCR。

默认逻辑：

- 如果系统安装了 `ocrmypdf`，就调用它生成可搜索 PDF
- 如果没安装，则复制原始 PDF 作为 fallback，继续后续流程
- 会记录 `ocr_metadata.json`，说明是否真的用了 OCR、是否成功、输出路径是什么

注意：  
这个项目把 OCR 当成“兜底策略”，不是默认路径。

### 5.3 extract_paper.py

这是内容抽取的核心脚本之一。

它会：

- 从 PDF 中抽取文本
- 清洗文本
- 尝试识别标题、作者、单位、邮箱
- 尝试把正文切分成标准学术章节，例如：
  - abstract
  - introduction
  - related work
  - method
  - experiments
  - results
  - limitations
  - conclusion
  - references
  - appendix

它还会输出多份中间结果，方便调试和复查，例如：

- `raw_extracted.txt`
- `cleaned_text.txt`
- `sectioned_text.json`
- `metadata.json`
- `paper_content.json`

注意：  
它的标题/作者/单位抽取是启发式的，不是严格版面解析。因此它更强调“保守提取”，提不准时会明确写：

`Not clearly stated in the paper.`

### 5.4 analyze_paper.py

这个脚本负责把抽取后的内容转成“可读、可判断、可汇报”的分析结果。

它会生成的内容包括：

- 一句话 headline assessment
- 论文基础身份信息
- executive summary
- 费曼式解释
- 技术方法概括
- 实验设置和结果摘要
- 复现计划
- 缺失信息与风险
- strengths / weaknesses / limitations
- final verdict
- extraction confidence

其中比较有特色的是 Feynman 风格解释，会专门组织成下面这类问题：

- Explain it simply
- What problem it solves
- How it works step by step
- Intuitive analogy
- Where confusion usually appears
- What I still cannot verify from the paper

此外，它还会根据 method / experiments / results / limitations 这些章节是否充分，粗略评估论文的复现风险：

- Low
- Medium
- High

### 5.5 build_report.py

这个脚本负责把分析结果渲染成最终 Markdown 报告。

它会读取：

- `analysis.json`

然后使用模板：

- `paper_investigation_report.md`

生成：

- `final_report.md`

如果安装了 `jinja2`，会优先使用模板渲染；  
如果没有，也有一个简单的替换逻辑作为回退。

### 5.6 utils.py

这里放的是一些通用工具函数，例如：

- 创建目录
- 读写 JSON / 文本
- 清洗文本
- 提取邮箱
- 默认元数据模板
- 安全截断文本片段

它是整个流程的公共基础模块。

### 5.7 compare_papers.py（新增）

用于把多篇论文的输出目录做横向比较，核心维度包括：

- 可复现风险等级
- claim-evidence 支撑强度分数
- 数据集 / 模型 / 指标 / 硬件要素

输出：

- `comparison.json`
- `comparison_report.md`

### 5.8 build_meeting_brief.py（新增）

用于从 `analysis.json` 快速生成组会可读简报（Markdown/Marp 友好）。

输出：

- `meeting_brief.md`

## 6. 安装依赖

### 6.1 Python 依赖

先安装仓库里的 Python 依赖：

```bash
pip install -r requirements.txt
```

主要依赖包括：

- pymupdf
- pypdf
- pdfminer.six
- beautifulsoup4
- lxml
- markdownify
- rapidfuzz
- regex
- pydantic
- jinja2
- python-dotenv
- openai（用于可选的 claim-evidence LLM 对齐）

### 6.2 OCR 依赖（可选，但推荐）

如果你需要处理扫描版 PDF，建议系统中安装：

- ocrmypdf
- tesseract

例如在 Linux / macOS 环境中安装后，就能让 `run_ocr.py` 真正生成 OCR 结果。

说明：  
如果没有安装 OCR 工具，项目不会直接崩溃，而是走 fallback 路线，只是抽取质量可能明显下降。

## 7. 最基本的使用方法

### 方法一：按步骤手动执行

假设你的论文文件是：

`papers/demo.pdf`

你希望输出目录是：

`outputs/demo_run`

那么可以按下面的顺序执行：

第一步：检测 PDF 类型

```bash
python detect_pdf_type.py papers/demo.pdf --output outputs/demo_run/pdf_type.json
```

第二步：如果需要，执行 OCR

```bash
python run_ocr.py papers/demo.pdf outputs/demo_run
```

如果 OCR 成功，通常会得到：

`outputs/demo_run/ocr/ocr_output.pdf`

如果 OCR 工具不存在，则会得到 fallback 文件。

第三步：抽取论文内容

如果 PDF 本身是文本型，可以直接：

```bash
python extract_paper.py papers/demo.pdf outputs/demo_run
```

如果你已经执行了 OCR，建议改用 OCR 后的 PDF：

```bash
python extract_paper.py outputs/demo_run/ocr/ocr_output.pdf outputs/demo_run
```

第四步：分析论文

```bash
python analyze_paper.py outputs/demo_run
```

这一步会生成：

`outputs/demo_run/analysis.json`

第五步：生成最终报告

```bash
python build_report.py outputs/demo_run --template paper_investigation_report.md
```

最终会得到：

`outputs/demo_run/final_report.md`

## 8. 一条命令串起来的示例

对于常见场景，你也可以按下面这种顺序理解整个流程：

```bash
python detect_pdf_type.py papers/demo.pdf --output outputs/demo/pdf_type.json

python run_ocr.py papers/demo.pdf outputs/demo

python extract_paper.py outputs/demo/ocr/ocr_output.pdf outputs/demo

python analyze_paper.py outputs/demo

python build_report.py outputs/demo --template paper_investigation_report.md
```

## 9. 输出文件说明

运行后，输出目录里通常会有下面这些文件：

```text
outputs/demo/
├── analysis.json
├── claim_evidence_alignment.json
├── cleaned_text.txt
├── final_report.md
├── meeting_brief.md
├── metadata.json
├── entity_catalog.json
├── paper_content.json
├── raw_extracted.txt
├── sectioned_text.json
├── table_equation_index.json
├── figure_table_citations.json
└── ocr/
    ├── ocr_metadata.json
    └── ocr_output.pdf
```

它们分别代表什么？

- `raw_extracted.txt`  
原始抽取文本，基本不加工
- `cleaned_text.txt`  
做过简单清洗后的文本
- `sectioned_text.json`  
章节切分结果
- `metadata.json`  
提取出的论文标题、作者、单位、邮箱等信息
- `paper_content.json`  
综合后的核心结构化数据
- `analysis.json`  
分析阶段的中间结果
- `claim_evidence_alignment.json`  
claim 与证据句的对齐矩阵及支撑强度
- `final_report.md`  
最终交付给用户阅读的正式报告
- `meeting_brief.md`  
用于组会汇报的简报版输出
- `entity_catalog.json`  
自动识别的数据集、模型、指标、硬件信息
- `table_equation_index.json`  
表格与公式的细粒度索引
- `figure_table_citations.json`  
Figure/Table 引用级分析结果
- `ocr/ocr_metadata.json`  
OCR 是否执行、是否成功、输出路径等信息

## 10. 生成的报告长什么样

最终报告会被组织成比较固定的 10 个部分：

1. Headline Assessment
2. Paper Identity
3. Executive Summary
4. Core Concepts Explained with the Feynman Method
5. Method and Experimental Logic
6. Reproduction Plan
7. Defects, Limitations, and Risks
8. Author and Affiliation Information
9. Final Verdict
10. Confidence and Extraction Notes

这意味着它不是“自由发挥的摘要”，而是一个格式稳定、适合复查和汇报的文档。

## 11. 一个更通俗的理解范例

假设你有一篇机器学习论文 PDF，你不想自己花 2 小时逐页看。

那么这个项目会大致做下面这些事：

输入  
你给它一个 PDF。

它先判断  
“这是可直接读的文字 PDF，还是扫描图片 PDF？”

如果是扫描版  
它先做 OCR，把图片变成可搜索文本。

然后它尝试回答这些问题：

- 这篇论文到底在解决什么问题？
- 方法本质上是什么？
- 作者拿什么实验来支撑结论？
- 哪些地方讲清楚了，哪些地方没讲清楚？
- 如果我要复现，大概缺哪些细节？
- 这篇论文值得信吗？风险在哪？

最后输出  
不是一句“这篇论文提出了一个新方法”，而是一份带结构的报告，例如：

- 论文标题和作者是谁
- 论文核心思想怎么用大白话讲
- 方法流程是什么
- 实验和结果说明了什么
- 是否容易复现
- 缺点和盲点是什么
- 最后给一个整体判断

## 12. 这个项目的设计特点

优点：

1）流程清晰  
每个阶段都拆成独立脚本，便于替换和调试。

2）OCR 是 fallback，不是默认  
这很合理。文本型 PDF 直接抽通常更干净，没必要一上来就 OCR。

3）输出结构稳定  
最终报告格式固定，适合复用、汇报和批量处理。

4）强调“保守提取”  
对作者、单位、通信作者等字段，不会强行乱猜。

5）兼顾“解释”和“批判”  
它不是只做摘要，还会做复现风险和局限性判断。

## 13. 当前实现的局限

这部分很重要，建议用户在使用前明确知道。

1）元数据抽取仍然偏启发式  
当前 `extract_paper.py` 对标题、作者、单位的判断主要依赖前几行文本和关键词，不是严格版面解析。  
因此对复杂排版、双栏论文、脚注式单位映射，可能不够稳。

2）章节识别依赖标题匹配  
它是通过类似 `abstract / introduction / method / results` 这些标题去切分章节。  
如果论文标题命名很特殊，章节映射可能不完整。

3）没有真正深入解析图表和公式  
当前更多是基于文本抽取与章节片段摘要，不是对图表数值、公式结构做精细级理解。

4）复现评估是“第一轮判断”  
它会根据关键章节是否充分来判断复现风险，但这不是严格的 reproducibility benchmark。

5）目前更像单篇论文处理工具  
它适合一次处理一篇 PDF，不是多论文对比系统。

## 14. 推荐使用方式

建议你把它当成下面这三类工具之一：

场景 A：快速筛论文  
看一篇论文是否值得认真读、是否值得复现。

场景 B：做组会/汇报前预处理  
先让工具生成结构化报告，再人工补充。

场景 C：为后续深度分析打底  
先产出一份“基础调查报告”，再进一步做实验复现、代码实现或文献对比。

## 15. 适合谁用

- 研究生
- 做文献调研的工程师
- 需要快速理解论文的算法工程人员
- 想做复现但不想先盲目上手的人
- 需要把论文内容整理成汇报文档的人

## 16. 一段最短可复制示例

下面给一个最小使用示例：

```bash
# 1) 检测 PDF 类型
python detect_pdf_type.py sample_paper.pdf --output outputs/sample/pdf_type.json

# 2) 运行 OCR（如果是扫描版）
python run_ocr.py sample_paper.pdf outputs/sample

# 3) 提取论文内容
python extract_paper.py outputs/sample/ocr/ocr_output.pdf outputs/sample

# 4) 分析论文
python analyze_paper.py outputs/sample

# 5) 生成最终报告
python build_report.py outputs/sample --template paper_investigation_report.md
```

最终重点查看这个文件：

`outputs/sample/final_report.md`

## 17. 已实现的增强能力（v2）

基于你提出的 7 个方向，当前版本已经加入以下能力：

- 更稳健的标题/作者/单位抽取  
  `extract_paper.py` 现在会综合首屏标题块、作者候选行、单位关键词、邮箱与对应作者线索，并输出 `author_affiliation_map` 与保守的置信注释。
- 表格与公式的精细化解析  
  新增 `table_equation_index.json`，包含表格候选、页码、行列估计与公式片段（含编号标签）。
- 对 figures / tables 的引用级分析  
  新增 `figure_table_citations.json`，统计 `Figure/Table` 引用频次、上下文证据与未解析引用。
- 多篇论文横向比较  
  新增 `paper-reading-investigator/scripts/compare_papers.py`，可生成 `comparison.json` 与 `comparison_report.md`。
- 自动识别数据集、模型、指标、硬件配置  
  在抽取阶段输出 `entity_catalog.json`，并写入 `metadata.json` / `paper_content.json`。
- 结合大模型做更强 claim-evidence 对齐  
  `analyze_paper.py` 默认启发式对齐；启用 `--enable-llm-alignment` 且配置 `OPENAI_API_KEY` 后，会调用 OpenAI 做二次校准。
- 生成更适合组会展示的简报版本  
  新增 `paper-reading-investigator/scripts/build_meeting_brief.py` + `paper-reading-investigator/templates/group_meeting_brief.md`，可直接生成 `meeting_brief.md`（Marp 友好）。

## 18. 新增命令示例（v2）

### 18.1 输出带附录的正式报告（含 claim-evidence 矩阵）

```bash
python paper-reading-investigator/scripts/build_report.py outputs/sample --template paper-reading-investigator/templates/paper_investigation_report.md --with-appendix
```

### 18.2 启用大模型 claim-evidence 对齐

```bash
python paper-reading-investigator/scripts/analyze_paper.py outputs/sample --enable-llm-alignment --llm-model gpt-5-mini
```

### 18.3 生成组会简报

```bash
python paper-reading-investigator/scripts/build_meeting_brief.py outputs/sample
```

### 18.4 多论文横向比较

```bash
python paper-reading-investigator/scripts/compare_papers.py outputs/paper_a outputs/paper_b --output-dir outputs/compare_run
```

## 19. 总结

Paper Reading Investigator 是一个面向单篇论文 PDF 的结构化分析工具。  
它不追求“花哨摘要”，而是更偏向：

- 可解释
- 可审阅
- 可复现评估
- 可正式输出
- 可横向比较
- 可组会简报化

如果你经常需要看论文、拆论文、评估复现成本，或者把论文整理成正式文档，这个项目是一个很合适的基础版本。

## 20. 基于英文报告生成中文精读报告

在你已经生成英文报告 `final_report.md` 之后，可以直接追加这一步：

```bash
python scripts/build_report_zh.py outputs/sample
```

默认会读取：

- `outputs/sample/final_report.md`
- `outputs/sample/analysis.json`

并生成：

- `outputs/sample/final_report_zh.md`

中文精读报告会重点给出：

- 研究问题与方法
- 核心结论与证据强度
- 优点与不足
- 可复现性风险评级与依据
