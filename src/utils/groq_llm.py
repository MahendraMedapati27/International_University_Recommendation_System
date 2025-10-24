"""
Groq LLM wrapper for CrewAI integration
Provides a compatible interface for CrewAI agents
"""

import os
from typing import Optional, Dict, Any, List
from groq import Groq
import logging

logger = logging.getLogger(__name__)


class GroqLLM:
    """
    Groq LLM wrapper for CrewAI integration
    """
    
    def __init__(self, 
                 model: str = "llama-3.3-70b-versatile",
                 temperature: float = 0.7,
                 api_key: Optional[str] = None,
                 max_tokens: int = 4096):
        """
        Initialize Groq LLM
        
        Args:
            model: Groq model name
            temperature: Sampling temperature
            api_key: Groq API key
            max_tokens: Maximum tokens to generate
        """
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        
        # Initialize Groq client
        api_key = api_key or os.getenv('GROQ_API_KEY')
        if not api_key:
            raise ValueError("GROQ_API_KEY environment variable is required")
        
        self.client = Groq(api_key=api_key)
        
        # CrewAI compatibility attributes
        self.model_name = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        
        logger.info(f"Initialized Groq LLM with model: {model}")
    
    def generate(self, 
                 prompt: str,
                 system_prompt: Optional[str] = None,
                 **kwargs) -> str:
        """
        Generate text using Groq
        
        Args:
            prompt: User prompt
            system_prompt: System prompt (optional)
            **kwargs: Additional parameters
            
        Returns:
            Generated text
        """
        try:
            # Prepare messages
            messages = []
            
            if system_prompt:
                messages.append({
                    "role": "system",
                    "content": system_prompt
                })
            
            messages.append({
                "role": "user", 
                "content": prompt
            })
            
            # Generate response
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
                **kwargs
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            logger.error(f"Groq generation failed: {e}")
            raise
    
    def stream(self, 
               prompt: str,
               system_prompt: Optional[str] = None,
               **kwargs):
        """
        Stream text generation using Groq
        
        Args:
            prompt: User prompt
            system_prompt: System prompt (optional)
            **kwargs: Additional parameters
            
        Yields:
            Generated text chunks
        """
        try:
            # Prepare messages
            messages = []
            
            if system_prompt:
                messages.append({
                    "role": "system",
                    "content": system_prompt
                })
            
            messages.append({
                "role": "user",
                "content": prompt
            })
            
            # Stream response
            stream = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
                stream=True,
                **kwargs
            )
            
            for chunk in stream:
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
                    
        except Exception as e:
            logger.error(f"Groq streaming failed: {e}")
            raise
    
    def get_available_models(self) -> list:
        """
        Get available Groq models
        
        Returns:
            List of available model names
        """
        return [
            "llama-3.3-70b-versatile",
            "llama-3.1-8b-instant", 
            "openai/gpt-oss-120b",
            "openai/gpt-oss-20b"
        ]
    
    def get_model_info(self) -> Dict[str, Any]:
        """
        Get model information
        
        Returns:
            Dictionary with model information
        """
        return {
            "model": self.model,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "provider": "groq"
        }
    
    def call(self, messages: List[Dict], **kwargs) -> str:
        """
        CrewAI compatibility method for calling the LLM
        
        Args:
            messages: List of message dictionaries
            **kwargs: Additional parameters
            
        Returns:
            Generated response
        """
        try:
            # Extract system and user messages
            system_prompt = None
            user_prompt = ""
            
            for message in messages:
                if message.get("role") == "system":
                    system_prompt = message.get("content", "")
                elif message.get("role") == "user":
                    user_prompt = message.get("content", "")
            
            return self.generate(
                prompt=user_prompt,
                system_prompt=system_prompt,
                **kwargs
            )
        except Exception as e:
            logger.error(f"Groq call failed: {e}")
            raise
    
    def invoke(self, messages: List[Dict], **kwargs) -> str:
        """
        CrewAI compatibility method (alias for call)
        
        Args:
            messages: List of message dictionaries
            **kwargs: Additional parameters
            
        Returns:
            Generated response
        """
        return self.call(messages, **kwargs)
    
    def __call__(self, messages: List[Dict], **kwargs) -> str:
        """
        Make the object callable for CrewAI compatibility
        
        Args:
            messages: List of message dictionaries
            **kwargs: Additional parameters
            
        Returns:
            Generated response
        """
        return self.call(messages, **kwargs)


def create_groq_llm(model: str = "llama-3.1-8b-instant", 
                   temperature: float = 0.7,
                   api_key: Optional[str] = None) -> GroqLLM:
    """
    Factory function to create Groq LLM instance
    
    Args:
        model: Groq model name
        temperature: Sampling temperature
        api_key: Groq API key
        
    Returns:
        GroqLLM instance
    """
    return GroqLLM(
        model=model,
        temperature=temperature,
        api_key=api_key
    )


# Available Groq models
GROQ_MODELS = {
    "llama3-8b": "llama3-8b-8192",
    "llama3-70b": "llama3-70b-8192",
    "mixtral": "mixtral-8x7b-32768",
    "gemma": "gemma-7b-it"
}


if __name__ == "__main__":
    # Test the Groq LLM
    print("Testing Groq LLM...")
    
    try:
        llm = create_groq_llm()
        
        # Test generation
        response = llm.generate(
            prompt="What is the capital of France?",
            system_prompt="You are a helpful assistant."
        )
        
        print(f"Response: {response}")
        print(f"Model info: {llm.get_model_info()}")
        print(f"Available models: {llm.get_available_models()}")
        
    except Exception as e:
        print(f"Error: {e}")
        print("Make sure GROQ_API_KEY is set in your environment")
