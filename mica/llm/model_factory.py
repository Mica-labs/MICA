from typing import Optional, Dict, Text, Any

from langchain_community.embeddings import OpenAIEmbeddings

from mica.llm.base import BaseModel
from mica.llm.openai_model import OpenAIModel
from mica.llm.custom_model import CustomLLMModel
from mica.llm.custom_embedding import CustomEmbedding
from mica.utils import logger


class ModelFactory:
    """
    Factory class for creating LLM and Embedding models based on configuration.
    Supports both OpenAI and custom API providers.
    """
    
    @staticmethod
    def create_llm(config: Optional[Dict[Text, Any]] = None) -> BaseModel:
        """
        Create an LLM model based on configuration.
        
        Args:
            config: Configuration dictionary that can contain:
                - provider: 'openai' or 'custom' (default: 'openai')
                - For OpenAI:
                    - api_key: OpenAI API key
                    - model: Model name
                    - server: Optional custom server URL
                    - temperature, top_p, etc.
                - For Custom:
                    - server: Required server URL
                    - api_key: Optional API key
                    - model: Model name
                    - temperature, top_p, etc.
                    
        Returns:
            An instance of BaseModel (OpenAIModel or CustomLLMModel)
            
        Examples:
            # OpenAI model
            config = {
                'provider': 'openai',
                'api_key': 'sk-...',
                'model': 'gpt-4'
            }
            
            # Custom model (e.g., LLaMA, Mistral, etc.)
            config = {
                'provider': 'custom',
                'server': 'http://localhost:8000',
                'api_key': 'optional-key',
                'model': 'llama-3-70b'
            }
        """
        if config is None:
            logger.info("No LLM config provided, using default OpenAI model")
            return OpenAIModel.create(None)
        
        provider = config.get('provider', 'openai').lower()
        
        if provider == 'custom':
            logger.info(f"Creating custom LLM model with config: {config}")
            return CustomLLMModel.create(config)
        elif provider == 'openai':
            logger.info(f"Creating OpenAI model with config")
            return OpenAIModel.create(config)
        else:
            logger.warning(f"Unknown provider '{provider}', falling back to OpenAI")
            return OpenAIModel.create(config)
    
    @staticmethod
    def create_embedding(config: Optional[Dict[Text, Any]] = None):
        """
        Create an Embedding model based on configuration.
        
        Args:
            config: Configuration dictionary that can contain:
                - provider: 'openai' or 'custom' (default: 'openai')
                - For OpenAI:
                    - api_key: OpenAI API key
                    - model: Embedding model name
                    - base_url: Optional custom base URL
                - For Custom:
                    - server: Required server URL
                    - api_key: Optional API key
                    - model: Embedding model name
                    
        Returns:
            An embedding instance (OpenAIEmbeddings or CustomEmbedding)
            
        Examples:
            # OpenAI embeddings
            config = {
                'provider': 'openai',
                'api_key': 'sk-...',
                'model': 'text-embedding-ada-002'
            }
            
            # Custom embeddings (e.g., BGE, E5, etc.)
            config = {
                'provider': 'custom',
                'server': 'http://localhost:8001',
                'model': 'bge-large-zh'
            }
        """
        if config is None:
            logger.info("No embedding config provided, using default OpenAI embeddings")
            return OpenAIEmbeddings()
        
        provider = config.get('provider', 'openai').lower()
        
        if provider == 'custom':
            logger.info(f"Creating custom embedding model with config: {config}")
            return CustomEmbedding.create(config)
        elif provider == 'openai':
            logger.info(f"Creating OpenAI embedding model")
            # Extract OpenAI-specific parameters
            openai_config = {}
            if 'api_key' in config:
                openai_config['openai_api_key'] = config['api_key']
            if 'model' in config:
                openai_config['model'] = config['model']
            if 'server' in config:
                # For OpenAI, server is used as base_url
                openai_config['base_url'] = config['server']
                if not openai_config['base_url'].endswith('/v1'):
                    openai_config['base_url'] = f"{openai_config['base_url']}/v1"
            if 'headers' in config:
                openai_config['default_headers'] = config['headers']
                
            if openai_config:
                return OpenAIEmbeddings(**openai_config)
            else:
                return OpenAIEmbeddings()
        else:
            logger.warning(f"Unknown embedding provider '{provider}', falling back to OpenAI")
            return OpenAIEmbeddings()


# Convenience functions for backward compatibility
def create_llm_model(config: Optional[Dict[Text, Any]] = None) -> BaseModel:
    """Convenience function to create LLM model."""
    return ModelFactory.create_llm(config)


def create_embedding_model(config: Optional[Dict[Text, Any]] = None):
    """Convenience function to create embedding model."""
    return ModelFactory.create_embedding(config)

