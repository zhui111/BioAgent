# scripts/pdf_processor.py
import pickle
import sys
sys.path.append('.')
import os
import glob
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from utils.config import PDF_DIR, CHUNKS_PKL_PATH

def process_pdf():
    documents = []
    pdf_files = glob.glob(os.path.join(PDF_DIR, "*.pdf"))
    
    print(f"Found {len(pdf_files)} PDFs...")
    for pdf_file in pdf_files:
        print(f"Loading {pdf_file}...")
        loader = PyPDFLoader(pdf_file)
        documents.extend(loader.load())
    
    print(f"Total loaded {len(documents)} pages.")
    # 分块策略：每块500字符，重叠50字符
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=512,   # 减小块大小
        chunk_overlap=100, # 增加重叠度，防止关键术语被切断
        separators=["\n\n", "\n", "。", ". ", "！", "？", "!", "?", " ", ""] # 加上中文句号
    )
    chunks = text_splitter.split_documents(documents)
    print(f"Created {len(chunks)} chunks.")

    # 保存分块数据
    with open(CHUNKS_PKL_PATH, "wb") as f:
        pickle.dump(chunks, f)
    print(f"Chunks saved to {CHUNKS_PKL_PATH}")

if __name__ == "__main__":
    process_pdf()