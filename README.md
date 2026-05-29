# BioAgent: A Biomedical Learning Assistant Powered by RAG and LLMs

BioAgent is a task-oriented intelligent learning system designed for biomedical education. It combines a local textbook knowledge base, the DeepSeek large language model, retrieval-augmented generation (RAG), AI-assisted grading, a mistake notebook, spaced repetition, vocabulary learning, and learning analytics into a complete learning workflow:

```text
Knowledge Q&A -> Intelligent Practice -> Mistake Review -> Spaced Repetition -> Learning Feedback
```

> Note: This repository is intended to include only source code and necessary configuration files. Local data, vector databases, SQLite databases, textbook PDFs, model weights, and presentation materials are not included. Users need to prepare the `data/` directory and local embedding / reranker models by themselves.

## 1. Features

- Knowledge Q&A: answers questions based on a local vector knowledge base built from textbook PDFs, with source references.
- Intelligent practice: supports question-bank exercises, AI-generated questions, and retrying previously missed questions.
- Topic-specific question generation: the AI-generated question mode supports user-specified topics such as DNA replication, cell signaling, and protein synthesis.
- AI-assisted grading: grades short-answer questions on a 0-10 scale and provides feedback and missing key points.
- Mistake notebook: automatically or manually records missed questions and supports AI-generated explanations.
- Spaced repetition: schedules the next review time according to the learner's mastery level.
- Vocabulary learning: supports Excel-based vocabulary import, flashcards, spelling tests, sentence completion, and learning statistics.
- Learning reports: visualizes answer records, mistake records, and vocabulary learning data.
- RAG evaluation: provides scripts for comparing a baseline LLM with the RAG agent.

## 2. Repository Contents

To keep the repository lightweight and avoid uploading large files such as textbooks, databases, and model weights, this GitHub repository does not include the following files or directories:

```text
data/                         # Textbook PDFs, chunks.pkl, Chroma vector database, SQLite database, evaluation results, etc.
bge-m3/                       # Local embedding model, not uploaded
bge-reranker-v2-m3/           # Local reranker model, not uploaded
BioAgent_Presentation.md      # Project presentation file, not uploaded
venv/                         # Python virtual environment, not uploaded
```

If you clone this project from GitHub, you need to prepare the models, data, and vector database by following the steps below.

## 3. Project Structure

The recommended core project structure after uploading to GitHub is:

```text
biomed-rag-deepseek/
├── app.py                         # Main Streamlit application
├── requirements.txt               # Python dependencies
├── README.md                      # Project documentation
├── exam_questions.json             # Sample question-bank data, optional
├── import_exam_questions.py        # Question-bank import script
├── import_ielts_vocab.py           # Vocabulary import script
├── utils/
│   ├── config.py                   # Path and API key configuration
│   ├── rag_chain.py                # RAG retrieval, reranking, and answer chain
│   ├── ai_grader.py                # AI grading, mistake explanations, and dynamic question generation
│   └── study_db.py                 # SQLite learning database
└── scripts/
    ├── pdf_processor.py            # PDF parsing and document chunking
    ├── build_vector_db.py          # Chroma vector database construction
    ├── generate_qa_pairs.py        # QA pair generation from textbook chunks
    ├── run_evaluation.py           # RAG vs. baseline evaluation
    ├── create_vocab_template.py    # Vocabulary template generation
    └── add_examples.py             # Vocabulary example sentence generation
```

For local execution, you also need to add:

```text
biomed-rag-deepseek/
├── data/
│   ├── *.pdf                       # Textbook or learning-material PDFs prepared by the user
│   ├── chunks.pkl                  # Generated after PDF chunking
│   ├── chroma_db/                  # Generated after building the vector database
│   └── study_data.db               # Automatically generated after running the app
├── bge-m3/                         # Downloaded embedding model
└── bge-reranker-v2-m3/             # Downloaded reranker model
```

## 4. Environment Setup

Python 3.10 or 3.11 is recommended.

```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

If you are using Windows PowerShell:

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## 5. API Key Configuration

This project uses DeepSeek Chat as the generation model. The application reads the API key from the `DEEPSEEK_API_KEY` environment variable.

PowerShell:

```powershell
$env:DEEPSEEK_API_KEY="your DeepSeek API key"
```

CMD:

```cmd
set DEEPSEEK_API_KEY=your DeepSeek API key
```

For local testing, you may temporarily fill in your key in `utils/config.py`. However, if you plan to publish the project on GitHub, do not commit your real API key to the repository.

## 6. Download Local Models

This project uses two local model directories by default:

```text
./bge-m3
./bge-reranker-v2-m3
```

The corresponding models are:

- Embedding model: `BAAI/bge-m3`
- Reranker model: `BAAI/bge-reranker-v2-m3`

After downloading the models, the local directory names must match the code configuration. Otherwise, you need to update the model paths in `utils/config.py` and `utils/rag_chain.py`.

### Option 1: Download with huggingface-cli

Install the Hugging Face Hub tool first:

```bash
pip install huggingface_hub
```

Run the following commands in the project root directory:

```bash
huggingface-cli download BAAI/bge-m3 --local-dir bge-m3
huggingface-cli download BAAI/bge-reranker-v2-m3 --local-dir bge-reranker-v2-m3
```

After the download is complete, the project root should contain:

```text
bge-m3/
bge-reranker-v2-m3/
```

### Option 2: Clone the model repositories with Git LFS

If Git LFS is installed, you can run:

```bash
git lfs install
git clone https://huggingface.co/BAAI/bge-m3
git clone https://huggingface.co/BAAI/bge-reranker-v2-m3
```

The model files are large, so download time depends on your network environment. If your network cannot directly access Hugging Face, you may manually download the models from the model pages or use an available mirror. The final local directory names should still be `bge-m3` and `bge-reranker-v2-m3`.

## 7. Prepare the data Directory and Textbook PDFs

Because `data/` is not uploaded to GitHub, you need to create it before the first run:

```bash
mkdir data
```

Place the textbook or learning-material PDFs that you want to use for the knowledge base into the directory:

```text
data/
├── your_book_1.pdf
├── your_book_2.pdf
└── ...
```

The original experiment used biomedical and molecular biology textbook PDFs. These files are not included in the repository. You can replace them with your own course materials or publicly available documents.

## 8. Build the Local Knowledge Base

After preparing the models and PDFs, run the following commands in order:

```bash
python scripts/pdf_processor.py
python scripts/build_vector_db.py
```

Processing workflow:

1. `scripts/pdf_processor.py` scans PDF files under `data/`.
2. `PyPDFLoader` reads text from PDF pages.
3. `RecursiveCharacterTextSplitter` splits the text into document chunks.
4. The chunks are saved to `data/chunks.pkl`.
5. `scripts/build_vector_db.py` embeds the document chunks with the local `bge-m3` model.
6. The vector index is persisted to `data/chroma_db`.

If this step is skipped, the Knowledge Q&A, AI-generated question, and RAG evaluation features will not work properly.

## 9. Initialize the Question Bank and Vocabulary Library

Import the sample question bank:

```bash
python import_exam_questions.py --json exam_questions.json
```

To overwrite existing imported questions:

```bash
python import_exam_questions.py --json exam_questions.json --overwrite
```

The vocabulary learning module supports two import methods:

1. Upload an Excel file in the web interface under `Vocabulary Learning -> Vocabulary Library Management`.
2. Import a local vocabulary file with the script:

```bash
python import_ielts_vocab.py
```

If the original vocabulary Excel file is not included in the GitHub repository, prepare your own Excel file with the expected format. Recommended fields include:

```text
word, translation, category, phonetic, example_en, example_cn, difficulty
```

You can also generate a vocabulary template by running:

```bash
python scripts/create_vocab_template.py
```

## 10. Run the Application

```bash
streamlit run app.py
```

After startup, the BioAgent web interface will open in your browser. The main features are organized into six tabs:

1. Knowledge Q&A
2. Knowledge Challenge
3. My Mistake Notebook
4. Today's Review
5. Vocabulary Learning
6. Learning Report

## 11. AI-Generated Practice Questions

In `Knowledge Challenge`, choose `AI-Generated Questions` and enter a practice topic, for example:

- DNA replication mechanisms
- Protein synthesis process
- Cell signaling
- Regulation of gene expression
- Cell cycle and apoptosis

The system uses the topic as a retrieval query, retrieves relevant passages from the textbook vector database, and generates new short-answer or multiple-choice questions. If no topic is provided, the system randomly selects a topic from the built-in biomedical core topics.

## 12. RAG Evaluation

This project provides an evaluation script for comparing a baseline LLM with the RAG agent:

```bash
python scripts/run_evaluation.py
```

Evaluation workflow:

1. Read test samples from `data/training_data.json`.
2. Call the standard DeepSeek model and the RAG agent to answer each question.
3. Use DeepSeek Judge to score the answers in terms of accuracy, completeness, and terminology precision.
4. Save the results to `data/evaluation_results.csv`.

Scoring formula:

```text
Final = Accuracy * 0.5 + Completeness * 0.3 + Precision * 0.2
```

If `data/training_data.json` does not exist, generate it first:

```bash
python scripts/generate_qa_pairs.py
```

## 13. Tech Stack

- Streamlit: web user interface
- DeepSeek Chat: question answering, question generation, grading, and explanation generation
- LangChain: model calls and chain orchestration
- bge-m3: local text embedding model
- Chroma: local vector database
- bge-reranker-v2-m3: cross-encoder reranker model
- SQLite: learning records and long-term memory storage
- pandas / openpyxl: Excel vocabulary file processing
- PyPDF / LangChain PDF Loader: PDF parsing

## 14. FAQ

### 14.1 RAG Q&A reports errors or returns no results after startup

Please check:

1. Whether the `data/` directory exists.
2. Whether `data/chunks.pkl` has been generated.
3. Whether `data/chroma_db/` has been generated.
4. Whether the `bge-m3/` model directory exists.
5. Whether the `bge-reranker-v2-m3/` model directory exists.
6. Whether `DEEPSEEK_API_KEY` is configured correctly.

### 14.2 Can I rename the model directories?

Yes, but you need to update the corresponding paths in the code:

- `EMBEDDING_MODEL_NAME` in `utils/config.py`
- The reranker path `./bge-reranker-v2-m3` in `utils/rag_chain.py`

If you do not want to modify the code, keep the directory names as:

```text
bge-m3
bge-reranker-v2-m3
```

### 14.3 Which files should be ignored when uploading to GitHub?

It is recommended not to upload the following files or directories:

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

## 15. Current Limitations and Future Improvements

- The repository does not include data or model files by default. First-time users need to download models and build the knowledge base manually.
- PDF ingestion is currently handled mainly by offline scripts. A future version may support web-based PDF upload and incremental indexing.
- Voice input/output and image parsing are not implemented yet.
- The current system is closer to a RAG-based learning agent than a general multi-agent collaboration framework.
- LLM-based grading and LLM Judge evaluation can still be subjective, so manual spot checks are recommended.
- When publishing the project, avoid committing real API keys. Use environment variables or a `.env` file for secret management.
