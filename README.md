# BioAgent：基于 RAG 与大模型的生物医学学习助手

BioAgent 是一款面向生物医学学习场景的任务型智能体系统。系统融合本地教材知识库、DeepSeek 大语言模型、RAG 检索增强生成、AI 主观题批改、错题本、间隔重复复习和学习数据分析，形成“知识问答 → 智能练习 → 错题沉淀 → 复习巩固 → 数据反馈”的闭环学习流程。

> 说明：本仓库计划只上传源代码和必要配置文件，不上传本地数据、向量库、数据库、教材 PDF、大模型权重和展示文档。使用者需要自行准备 `data/` 目录和本地 embedding / reranker 模型。

## 1. 功能概览

- 知识问答：基于本地教材 PDF 构建的向量知识库回答问题，并展示引用原文。
- 智能闯关：支持题库练习、AI 动态出题和错题回练。
- 知识点定向出题：AI 动态出题模式支持输入指定知识点，例如 DNA 复制、细胞信号传导、蛋白质合成等。
- AI 智能批改：对简答题进行 0-10 分评分，给出反馈和关键缺失知识点。
- 错题本：自动或手动收录错题，支持 AI 生成错题解析。
- 间隔重复复习：根据掌握情况安排下次复习时间。
- 单词学习：支持 Excel 导入词库、闪卡背诵、拼写测试、例句填空和学习统计。
- 学习报告：展示答题、错题和词汇学习数据。
- RAG 效果评估：提供 baseline LLM 与 RAG Agent 的对比评估脚本。

## 2. 仓库内容说明

为了避免仓库体积过大，以及避免上传教材、数据库、模型权重等大文件，本 GitHub 仓库不包含以下内容：

```text
data/                         # 教材 PDF、chunks.pkl、Chroma 向量库、SQLite 数据库、评估结果等
bge-m3/                       # 本地 embedding 模型，不上传
bge-reranker-v2-m3/           # 本地 reranker 模型，不上传
BioAgent_Presentation.md      # 项目展示稿，不上传
venv/                         # Python 虚拟环境，不上传
```

如果你从 GitHub 克隆本项目，需要按本 README 的步骤重新准备模型、数据和向量库。

## 3. 目录结构

上传到 GitHub 后，推荐保留的核心代码结构如下：

```text
biomed-rag-deepseek/
├── app.py                         # Streamlit 主应用入口
├── requirements.txt               # Python 依赖
├── README.md                      # 项目说明
├── exam_questions.json             # 示例题库数据，可选保留
├── import_exam_questions.py        # 题库导入脚本
├── import_ielts_vocab.py           # 词汇导入脚本
├── utils/
│   ├── config.py                   # 路径与 API Key 配置
│   ├── rag_chain.py                # RAG 检索、重排与回答链
│   ├── ai_grader.py                # AI 批改、错题解析、动态出题
│   └── study_db.py                 # SQLite 学习数据库
└── scripts/
    ├── pdf_processor.py            # PDF 解析与文档切分
    ├── build_vector_db.py          # 构建 Chroma 向量库
    ├── generate_qa_pairs.py        # 从教材片段生成问答数据
    ├── run_evaluation.py           # RAG 与 baseline 对比评估
    ├── create_vocab_template.py    # 词汇模板生成
    └── add_examples.py             # 单词例句生成
```

本地运行时，需要额外补充：

```text
biomed-rag-deepseek/
├── data/
│   ├── *.pdf                       # 自行准备的教材或学习资料 PDF
│   ├── chunks.pkl                  # PDF 切分后生成
│   ├── chroma_db/                  # 构建向量库后生成
│   └── study_data.db               # 运行应用后自动生成
├── bge-m3/                         # 下载得到的 embedding 模型
└── bge-reranker-v2-m3/             # 下载得到的 reranker 模型
```

## 4. 环境准备

建议使用 Python 3.10 或 3.11。

```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

如果你使用的是 Windows PowerShell：

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## 5. API Key 配置

系统使用 DeepSeek Chat 作为生成模型。程序会从环境变量 `DEEPSEEK_API_KEY` 中读取 API Key。

PowerShell：

```powershell
$env:DEEPSEEK_API_KEY="你的 DeepSeek API Key"
```

CMD：

```cmd
set DEEPSEEK_API_KEY=你的 DeepSeek API Key
```

如果你只是本地测试，也可以在 `utils/config.py` 中临时填写自己的 Key；但如果要公开上传 GitHub，建议不要把真实 API Key 提交到仓库。

## 6. 下载本地模型

本项目默认使用两个本地模型目录：

```text
./bge-m3
./bge-reranker-v2-m3
```

对应模型为：

- embedding 模型：`BAAI/bge-m3`
- reranker 模型：`BAAI/bge-reranker-v2-m3`

模型下载完成后，目录名称必须与代码配置保持一致，否则需要同步修改 `utils/config.py` 和 `utils/rag_chain.py` 中的模型路径。

### 方法一：使用 huggingface-cli 下载

先安装 Hugging Face Hub 工具：

```bash
pip install huggingface_hub
```

在项目根目录执行：

```bash
huggingface-cli download BAAI/bge-m3 --local-dir bge-m3
huggingface-cli download BAAI/bge-reranker-v2-m3 --local-dir bge-reranker-v2-m3
```

下载完成后，项目根目录下应出现：

```text
bge-m3/
bge-reranker-v2-m3/
```

### 方法二：使用 Git LFS 克隆模型仓库

如果你已安装 Git LFS，可以执行：

```bash
git lfs install
git clone https://huggingface.co/BAAI/bge-m3
git clone https://huggingface.co/BAAI/bge-reranker-v2-m3
```

注意：模型文件较大，下载时间取决于网络环境。若网络无法直接访问 Hugging Face，可以在浏览器中打开模型页面手动下载，或使用你可用的镜像方式下载，但最终本地目录名仍需保持为 `bge-m3` 和 `bge-reranker-v2-m3`。

## 7. 准备 data 目录和教材 PDF

由于 `data/` 不会上传到 GitHub，首次运行前需要自己创建目录并放入 PDF：

```bash
mkdir data
```

将你希望构建知识库的教材或资料 PDF 放入：

```text
data/
├── your_book_1.pdf
├── your_book_2.pdf
└── ...
```

本项目原始实验使用的是生物医学、分子生物学相关教材 PDF，但这些文件不会随仓库上传。你可以替换为自己的课程资料或公开可用资料。

## 8. 构建本地知识库

在模型和 PDF 准备完成后，按顺序执行：

```bash
python scripts/pdf_processor.py
python scripts/build_vector_db.py
```

处理流程：

1. `scripts/pdf_processor.py` 扫描 `data/` 目录下的 PDF 文件。
2. 使用 `PyPDFLoader` 读取 PDF 页面文本。
3. 使用 `RecursiveCharacterTextSplitter` 将文本切分为文档块。
4. 将文档块保存为 `data/chunks.pkl`。
5. `scripts/build_vector_db.py` 使用本地 `bge-m3` 模型向量化文档块。
6. 将向量索引持久化到 `data/chroma_db`。

如果没有执行这一步，知识问答、AI 动态出题和 RAG 评估功能将无法正常使用。

## 9. 初始化题库和词库

导入示例题库：

```bash
python import_exam_questions.py --json exam_questions.json
```

如果需要覆盖式重新导入：

```bash
python import_exam_questions.py --json exam_questions.json --overwrite
```

词汇学习模块支持两种方式：

1. 在 Web 界面的“单词学习 → 单词库管理”中上传 Excel 文件。
2. 使用脚本导入本地词汇表：

```bash
python import_ielts_vocab.py
```

注意：如果 GitHub 仓库中不包含原始词汇 Excel 文件，需要你自行准备符合格式的 Excel。字段建议包括：

```text
word, translation, category, phonetic, example_en, example_cn, difficulty
```

也可以运行模板脚本生成词汇表模板：

```bash
python scripts/create_vocab_template.py
```

## 10. 启动应用

```bash
streamlit run app.py
```

启动后浏览器会打开 BioAgent Web 界面，主要功能位于六个标签页中：

1. 知识问答
2. 知识闯关
3. 我的错题本
4. 今日复习
5. 单词学习
6. 学习报告

## 11. AI 动态出题说明

在“知识闯关”中选择“AI 动态出题”后，可以输入练习知识点，例如：

- DNA复制机制
- 蛋白质合成过程
- 细胞信号传导
- 基因表达调控
- 细胞周期与凋亡

系统会将该知识点作为检索提示，从教材向量库中召回相关片段，再生成新的简答题或选择题。若不填写知识点，系统会从内置生物医学核心主题中随机选择。

## 12. RAG 效果评估

项目提供 baseline LLM 与 RAG Agent 的对比评估脚本：

```bash
python scripts/run_evaluation.py
```

评估流程：

1. 从 `data/training_data.json` 读取测试样本。
2. 分别调用普通 DeepSeek 和 RAG Agent 回答问题。
3. 使用 DeepSeek Judge 从准确性、完整性、术语精准性三个维度评分。
4. 将结果保存到 `data/evaluation_results.csv`。

评分公式：

```text
Final = Accuracy × 0.5 + Completeness × 0.3 + Precision × 0.2
```

如果 `data/training_data.json` 不存在，可以先运行：

```bash
python scripts/generate_qa_pairs.py
```

## 13. 主要技术栈

- Streamlit：Web 图形界面
- DeepSeek Chat：问答、出题、批改和解析生成
- LangChain：模型调用与链式编排
- bge-m3：本地文本向量化模型
- Chroma：本地向量数据库
- bge-reranker-v2-m3：Cross-Encoder 重排模型
- SQLite：学习记录和长期记忆存储
- pandas / openpyxl：Excel 词汇文件处理
- PyPDF / LangChain PDF Loader：PDF 文档解析

## 14. 常见问题

### 14.1 启动后 RAG 问答报错或没有结果

请检查：

1. `data/` 目录是否存在。
2. `data/chunks.pkl` 是否已生成。
3. `data/chroma_db/` 是否已生成。
4. `bge-m3/` 模型目录是否存在。
5. `bge-reranker-v2-m3/` 模型目录是否存在。
6. `DEEPSEEK_API_KEY` 是否正确配置。

### 14.2 模型目录名能不能改？

可以，但需要同步修改代码中的路径：

- `utils/config.py` 中的 `EMBEDDING_MODEL_NAME`
- `utils/rag_chain.py` 中的 reranker 路径 `./bge-reranker-v2-m3`

如果不想改代码，请保持目录名为：

```text
bge-m3
bge-reranker-v2-m3
```

### 14.3 GitHub 上传时建议忽略哪些文件？

建议不要上传以下内容：

```text
data/
bge-m3/
bge-reranker-v2-m3/
BioAgent_Presentation.md
venv/
__pycache__/
*.pyc
.env
```

## 15. 当前局限与后续改进

- 当前仓库默认不包含数据和模型，首次运行需要用户自行下载模型并构建知识库。
- PDF 上传构建知识库主要通过离线脚本完成，后续可加入 Web 端实时上传与增量入库。
- 暂未实现语音输入输出和图片解析。
- 当前更接近 RAG 学习智能体，尚未实现通用多智能体协作框架。
- LLM 批改和 LLM Judge 评估仍可能存在主观性，需要结合人工抽查。
- 公开项目时应避免提交真实 API Key，建议使用环境变量或 `.env` 文件管理密钥。
