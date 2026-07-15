from typing import List, Optional
from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings
from langchain_openai import OpenAIEmbeddings

# Import modular pipeline components
from agents.src.rag.document_processor import DocumentProcessor
from agents.src.rag.vector_store import VectorStoreManager
from agents.src.rag.sparse_retriever import SparseRetrieverManager
from agents.src.rag.hybrid_retriever import HybridRetrieverManager

class RAGPipeline:
    """
    Orchestrator that ties together document extraction, chunking,
    vector storage, sparse indexing, and hybrid retrieval.
    """

    def __init__(
        self,
        persist_directory: str = "./chroma_db",
        embeddings: Optional[Embeddings] = None
    ):
        self.embeddings = embeddings or OpenAIEmbeddings()
        self.vector_store_manager = VectorStoreManager(persist_directory, self.embeddings)
        self.sparse_retriever_manager = SparseRetrieverManager()
        self.hybrid_retriever_manager = HybridRetrieverManager()

    def ingest_directory(
        self,
        directory_path: str,
        glob_pattern: str = "**/*.*",
        chunk_size: int = 1000,
        chunk_overlap: int = 200
    ):
        """
        Runs the full ingestion cycle across components.
        """
        # 1. Extract documents
        raw_docs = DocumentProcessor.extract_documents(directory_path, glob_pattern)
        if not raw_docs:
            print(f"No documents found in directory '{directory_path}' matching pattern '{glob_pattern}'.")
            return

        # 2. Chunk text recursively
        chunks = DocumentProcessor.chunk_documents(raw_docs, chunk_size, chunk_overlap)
        print(f"Segmented {len(raw_docs)} documents into {len(chunks)} chunks.")

        # 3. Add to Chroma vector database
        self.vector_store_manager.add_documents(chunks)
        print("Populated dense vector store.")

        # 4. Initialize BM25 search index
        self.sparse_retriever_manager.initialize(chunks)
        print("Initialized sparse keyword index.")

        # 5. Connect retrievers in an ensemble hybrid layout
        dense_retriever = self.vector_store_manager.as_retriever(k=4)
        sparse_retriever = self.sparse_retriever_manager.get_retriever(k=4)
        self.hybrid_retriever_manager.initialize(dense_retriever, sparse_retriever)
        print("Hybrid search integration ready.")

    def hybrid_search(self, query: str, k: int = 4) -> List[Document]:
        """
        Ensemble retrieval merging vector scores and keyword rank.
        """
        return self.hybrid_retriever_manager.search(query, k=k)
