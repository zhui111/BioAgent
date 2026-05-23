# utils/config.py
import os

# DeepSeek API Key - 请替换为你自己的
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "You API key!!!")

# 向量数据库路径
CHROMA_PERSIST_DIR = "data/chroma_db"

# 分块数据路径
CHUNKS_PKL_PATH = "data/chunks.pkl"

# PDF路径
PDF_DIR = "data"

# Embedding模型名称
EMBEDDING_MODEL_NAME = "./bge-m3"
