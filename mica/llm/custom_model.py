import json
from typing import Any, Optional, Dict, Text, List

import httpx

from mica.event import BotUtter, FunctionCall
from mica.llm.base import BaseModel
from mica.tracker import Tracker
from mica.utils import logger


class CustomLLMModel(BaseModel):
    """
    A generic LLM model that can work with any OpenAI-compatible API.
    This allows you to use custom LLM servers or open-source models.
    """
    
    def __init__(self,
                 server: Text,
                 api_key: Optional[Text] = None,
                 model: Optional[Text] = "gpt-4",
                 temperature: Optional[float] = 0.0,
                 top_p: Optional[float] = 0.8,
                 presence_penalty: Optional[float] = 0.1,
                 frequency_penalty: Optional[float] = 0.1,
                 max_tokens: Optional[int] = 512,
                 headers: Optional[Dict] = None,
                 timeout: Optional[int] = 60,
                 **kwargs):
        """
        Initialize a custom LLM model.
        
        Args:
            server: The base URL of the LLM API server (e.g., "http://localhost:8000")
            api_key: Optional API key for authentication
            model: Model name to use
            temperature: Sampling temperature (0.0 to 1.0)
            top_p: Nucleus sampling parameter
            presence_penalty: Presence penalty parameter
            frequency_penalty: Frequency penalty parameter
            max_tokens: Maximum tokens to generate
            headers: Optional custom headers
            timeout: Request timeout in seconds
        """
        self.server = server.rstrip('/')
        self.model = model
        self.temperature = temperature
        self.top_p = top_p
        self.presence_penalty = presence_penalty
        self.frequency_penalty = frequency_penalty
        self.max_tokens = max_tokens
        self.timeout = timeout
        
        # Construct the full URL
        if '/v1/chat/completions' not in self.server:
            self.url = f"{self.server}/v1/chat/completions"
        else:
            self.url = self.server
            
        # Setup headers
        self.headers = headers or {}
        if 'Content-Type' not in self.headers:
            self.headers['Content-Type'] = 'application/json'
        
        if api_key:
            if 'Authorization' not in self.headers:
                self.headers['Authorization'] = f"Bearer {api_key}"
        
        self.client = httpx.AsyncClient(timeout=timeout)
        logger.info(f"Initialized CustomLLMModel with server: {self.url}, model: {self.model}")

    @classmethod
    def create(cls, llm_config: Optional[Dict] = None):
        """
        Create a CustomLLMModel from configuration.
        
        Args:
            llm_config: Dictionary containing model configuration
            
        Returns:
            CustomLLMModel instance
        """
        if llm_config is None:
            raise ValueError("llm_config is required for CustomLLMModel")
        
        if 'server' not in llm_config:
            raise ValueError("'server' must be specified in llm_config for CustomLLMModel")
        
        return cls(**llm_config)

    async def generate_message(self,
                               prompts: Any,
                               tracker: Optional[Tracker] = None,
                               functions: Optional[Any] = None,
                               provider: Optional[Text] = None,
                               **kwargs: Any) -> List:
        """
        Generate a message using the custom LLM API.
        
        Args:
            prompts: List of message dictionaries
            tracker: Optional conversation tracker
            functions: Optional list of function definitions
            provider: Optional provider name
            
        Returns:
            List of events (BotUtter or FunctionCall)
        """
        formatted_prompts = self._generate_prompts(prompts, functions)
        llm_result = []

        logger.debug(f"Sending request to: {self.url}")
        logger.debug(f"Request payload: {json.dumps(formatted_prompts, indent=2, ensure_ascii=False)}")
        
        try:
            response = await self.client.post(
                self.url,
                headers=self.headers,
                json=formatted_prompts
            )
            
            logger.debug(f"Response status: {response.status_code}")
            
            if response.status_code == 200:
                response_json = response.json()
                
                if (response_json is not None 
                        and response_json.get("choices") is not None 
                        and len(response_json.get("choices")) > 0):
                    
                    message: Dict = response_json.get("choices")[0].get("message")
                    logger.debug(f"LLM message: \n{json.dumps(message, indent=2, ensure_ascii=False)}")
                    
                    # Handle text content
                    if message.get("content") is not None:
                        next_response_text = message.get("content")
                        llm_result.append(BotUtter(
                            text=next_response_text,
                            metadata=provider,
                            additional=message
                        ))

                    # Handle function/tool calls
                    if message.get("tool_calls") is not None:
                        for func in message["tool_calls"]:
                            func_details = func["function"]
                            name = func_details.get("name")
                            args = json.loads(func_details.get("arguments"))
                            call_id = func.get("id")

                            llm_result.append(FunctionCall(
                                function_name=name,
                                args=args,
                                call_id=call_id,
                                metadata=message
                            ))
            else:
                logger.error(f"LLM request failed with status {response.status_code}: {response.text}")
                
        except Exception as e:
            logger.error(f"Error calling custom LLM API: {str(e)}")
            
        return llm_result

    def _generate_prompts(self, prompts: Any, functions: Optional[List] = None) -> Dict:
        """
        Format prompts into the API request format.
        
        Args:
            prompts: List of message dictionaries
            functions: Optional list of function definitions
            
        Returns:
            Dictionary ready to be sent as JSON
        """
        data = {
            "model": self.model,
            "messages": prompts,
            "temperature": self.temperature,
            "top_p": self.top_p,
            "presence_penalty": self.presence_penalty,
            "frequency_penalty": self.frequency_penalty,
            "max_tokens": self.max_tokens,
        }
        
        if functions is not None and len(functions) > 0:
            tools = []
            for function in functions:
                tools.append({
                    "type": "function",
                    "function": function
                })
            data["tools"] = tools
            data["tool_choice"] = "auto"

        return data

    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()

