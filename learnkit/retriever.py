from typing import Optional
from .backends.base import BaseBackend

class SemanticRetriever:
    """
    Semantic Retriever for fetching past memories relevant to a task.
    """
    def __init__(self, backend: BaseBackend):
        self.backend = backend

    def retrieve(
        self,
        task: str,
        domain_vector: dict[str, float],
        router=None
    ) -> list:
        # Get top domains (confidence > 0.5)
        top_domains = [d for d, c in domain_vector.items() if c > 0.5]
        domain = top_domains[0] if top_domains else None
        
        # Search backend
        results = self.backend.search(
            query=task,
            domain=domain,
            limit=20  # Retrieve more, let router filter down
        )
        
        if router:
            results = router.route(results)
            
        return results
