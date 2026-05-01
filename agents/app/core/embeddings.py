import numpy as np
from sentence_transformers import SentenceTransformer

class Embedder:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(Embedder, cls).__new__(cls)
            # Use a lightweight, fast model optimized for semantic search
            cls._instance.model = SentenceTransformer("all-MiniLM-L6-v2")
        return cls._instance

    def get_embedding(self, text: str):
        """Generates a 384-dimensional vector for the given text."""
        return self.model.encode(text).tolist()

    @staticmethod
    def cosine_similarity(v1, v2):
        """Calculates cosine similarity between two vectors."""
        a = np.array(v1)
        b = np.array(v2)
        return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))

# Global instance
embedder = Embedder()
