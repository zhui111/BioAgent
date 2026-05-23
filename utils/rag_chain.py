# utils/rag_chain.py 完整版（不依赖任何有路径问题的类）
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_deepseek import ChatDeepSeek
from langchain_community.cross_encoders import HuggingFaceCrossEncoder

from utils.config import DEEPSEEK_API_KEY, CHROMA_PERSIST_DIR, EMBEDDING_MODEL_NAME

def load_rag_chain():
    # 1. Embedding
    embeddings = HuggingFaceEmbeddings(
        model_name=EMBEDDING_MODEL_NAME,
        model_kwargs={'device': 'cpu'},
        encode_kwargs={'normalize_embeddings': True}
    )

    # 2. 向量库
    vectorstore = Chroma(
        persist_directory=CHROMA_PERSIST_DIR,
        embedding_function=embeddings
    )

    # 3. 基础检索器（MMR）
    base_retriever = vectorstore.as_retriever(
        search_type="mmr",
        search_kwargs={"k": 10, "fetch_k": 20, "lambda_mult": 0.6}
    )

    # 4. 手动实现 Cross-Encoder 重排序
    reranker = HuggingFaceCrossEncoder(model_name="./bge-reranker-v2-m3")

    def rerank_docs(query, docs, top_n=3):
        """用 Cross-Encoder 对检索结果重新打分排序"""
        pairs = [(query, doc.page_content) for doc in docs]
        scores = reranker.score(pairs)
        scored_docs = sorted(zip(scores, docs), key=lambda x: x[0], reverse=True)
        return [doc for _, doc in scored_docs[:top_n]]

    # 5. LLM
    llm = ChatDeepSeek(
        model="deepseek-chat",
        api_key=DEEPSEEK_API_KEY,
        temperature=0.1,
        max_tokens=2048
    )

    # 6. Prompt
    template = """你是一位专业的生物医学专家。请根据以下从教材中检索到的内容回答问题。
教材内容可能来自中文或英文书籍，请统一用中文回答。

要求：
- 优先使用下方教材原文内容作答，中英文内容都可以使用
- 如果教材内容能部分回答问题，先用教材内容，再补充专业知识并注明"（补充）"
- 如果教材中完全没有相关内容，回答"教材中未找到该问题的直接答案"
- 引用英文教材内容时，请翻译成中文后再引用
- 使用规范的生物医学术语，保持学术准确性

教材内容：
{context}

问题：{question}

回答："""
    prompt = PromptTemplate.from_template(template)
    chain = prompt | llm | StrOutputParser()

    # 7. 组合成完整调用函数
    def rag_chain_with_sources(inputs):
        query = inputs["query"]
        # 先用 MMR 召回10个
        docs = base_retriever.invoke(query)
        # 再用 Cross-Encoder 重排，取前3个
        reranked_docs = rerank_docs(query, docs, top_n=3)
        context = "\n\n".join(doc.page_content for doc in reranked_docs)
        answer = chain.invoke({"context": context, "question": query})
        return {
            "result": answer,
            "source_documents": reranked_docs
        }

    return rag_chain_with_sources