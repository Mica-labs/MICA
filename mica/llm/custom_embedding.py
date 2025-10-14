import json
from typing import List, Optional, Dict, Text

import httpx
from langchain_core.embeddings import Embeddings

from mica.utils import logger


class CustomEmbedding(Embeddings):
    """
    A generic embedding model that can work with any OpenAI-compatible embedding API.
    This allows you to use custom embedding servers or open-source embedding models.
    """
    
    def __init__(self,
                 server: Text,
                 api_key: Optional[Text] = None,
                 model: Optional[Text] = "text-embedding-ada-002",
                 headers: Optional[Dict] = None,
                 timeout: Optional[int] = 60,
                 **kwargs):
        """
        Initialize a custom embedding model.
        
        Args:
            server: The base URL of the embedding API server (e.g., "http://localhost:8001")
            api_key: Optional API key for authentication
            model: Model name to use for embeddings
            headers: Optional custom headers
            timeout: Request timeout in seconds
        """
        self.server = server.rstrip('/')
        self.model = model
        self.timeout = timeout
        
        # Construct the full URL
        if '/v1/embeddings' not in self.server:
            self.url = f"{self.server}/v1/embeddings"
        else:
            self.url = self.server
            
        # Setup headers
        self.headers = headers or {}
        if 'Content-Type' not in self.headers:
            self.headers['Content-Type'] = 'application/json'
        
        if api_key:
            if 'Authorization' not in self.headers:
                self.headers['Authorization'] = f"Bearer {api_key}"
        
        self.client = httpx.Client(timeout=timeout)
        logger.info(f"Initialized CustomEmbedding with server: {self.url}, model: {self.model}")

    @classmethod
    def create(cls, embedding_config: Optional[Dict] = None):
        """
        Create a CustomEmbedding from configuration.
        
        Args:
            embedding_config: Dictionary containing embedding configuration
            
        Returns:
            CustomEmbedding instance
        """
        if embedding_config is None:
            raise ValueError("embedding_config is required for CustomEmbedding")
        
        if 'server' not in embedding_config:
            raise ValueError("'server' must be specified in embedding_config for CustomEmbedding")
        
        return cls(**embedding_config)

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """
        Embed a list of documents.
        
        Args:
            texts: List of text strings to embed
            
        Returns:
            List of embedding vectors
        """
        return self._get_embeddings(texts)

    def embed_query(self, text: str) -> List[float]:
        """
        Embed a single query text.
        
        Args:
            text: Text string to embed
            
        Returns:
            Embedding vector
        """
        embeddings = self._get_embeddings([text])
        return embeddings[0] if embeddings else []

    def _get_embeddings(self, texts: List[str]) -> List[List[float]]:
        """
        Get embeddings from the API.
        
        Args:
            texts: List of text strings to embed
            
        Returns:
            List of embedding vectors
        """
        payload = {
            "model": self.model,
            "input": texts
        }
        
        try:
            logger.debug(f"Sending embedding request to: {self.url}")
            logger.debug(f"Embedding {len(texts)} texts")
            
            response = self.client.post(
                self.url,
                headers=self.headers,
                json=payload
            )
            
            if response.status_code == 200:
                response_json = response.json()
                
                # Parse embeddings from response
                if "data" in response_json:
                    # Sort by index to maintain order
                    embeddings_data = sorted(
                        response_json["data"],
                        key=lambda x: x.get("index", 0)
                    )
                    embeddings = [item["embedding"] for item in embeddings_data]
                    logger.debug(f"Successfully got {len(embeddings)} embeddings")
                    return embeddings
                else:
                    logger.error(f"Unexpected response format: {response_json}")
                    return []
            else:
                logger.error(
                    f"Embedding request failed with status {response.status_code}: "
                    f"{response.text}"
                )
                return []
                
        except Exception as e:
            logger.error(f"Error calling custom embedding API: {str(e)}")
            return []

    def close(self):
        """Close the HTTP client."""
        self.client.close()

    def __del__(self):
        """Cleanup when object is destroyed."""
        try:
            self.close()
        except:
            pass

