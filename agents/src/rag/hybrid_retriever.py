from typing import List, Optional
from langchain_core.documents import Document
from langchain_community.retrievers import EnsembleRetriever

class HybridRetrieverManager:
    """
    Manages hybrid search by combining dense semantic retrievers and sparse keyword retrievers
    using Reciprocal Rank Fusion (RRF).
    """

    def __init__(self):
        self.ensemble_retriever = None

    def initialize(
        self, 
        dense_retriever, 
        sparse_retriever, 
        weights: Optional[List[float]] = None
    ):
        """
        Builds the EnsembleRetriever incorporating both retrievers and weight distributions.
        """
        weights = weights or [0.5, 0.5]
        self.ensemble_retriever = EnsembleRetriever(
            retrievers=[dense_retriever, sparse_retriever],
            weights=weights
        )

    def search(self, query: str, k: int = 4) -> List[Document]:
        """
        Runs the RRF hybrid retrieval.
        """
        if not self.ensemble_retriever:
            raise ValueError("Hybrid retriever has not been initialized.")
            
        # Dynamically set top-k values for sub-retrievers
        for retriever in self.ensemble_retriever.retrievers:
            if hasattr(retriever, "k"):
                retriever.k = k
            elif hasattr(retriever, "search_kwargs"):
                retriever.search_kwargs["k"] = k
                
        return self.ensemble_retriever.invoke(query)
