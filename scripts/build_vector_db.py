# scripts/build_vector_db.py
import pickle
import sys
sys.path.append('.')
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma
from utils.config import CHUNKS_PKL_PATH, CHROMA_PERSIST_DIR, EMBEDDING_MODEL_NAME

def build_vector_db():
    # 加载分块数据
    with open(CHUNKS_PKL_PATH, "rb") as f:
        chunks = pickle.load(f)
    print(f"Loaded {len(chunks)} chunks.")

    # 初始化Embedding模型
    embeddings = HuggingFaceEmbeddings(
        model_name=EMBEDDING_MODEL_NAME,
        model_kwargs={'device': 'cpu'},
        encode_kwargs={'normalize_embeddings': True}
    )

    # 构建Chroma向量库并持久化
    vectorstore = Chroma.from_documents(
        documents=chunks,
        embedding=embeddings,
        persist_directory=CHROMA_PERSIST_DIR
    )
    vectorstore.persist()
    print(f"Vector DB built and saved to {CHROMA_PERSIST_DIR}")

if __name__ == "__main__":
    build_vector_db()