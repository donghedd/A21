"""
Ollama Service - LLM Integration
"""
import requests
import json
from typing import Generator, List, Dict, Any, Optional
from flask import current_app
import logging

logger = logging.getLogger(__name__)


class OllamaService:
    """Service for interacting with Ollama API"""
    
    def __init__(self, base_url: str = None):
        self.base_url = base_url or current_app.config.get('OLLAMA_BASE_URL', 'http://localhost:11434')
    
    def get_models(self) -> List[Dict[str, Any]]:
        """Get list of available models"""
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=10)
            response.raise_for_status()
            data = response.json()
            return data.get('models', [])
        except Exception as e:
            logger.error(f"Failed to get models: {e}")
            return []
    
    def generate(self, model: str, prompt: str, system: str = None,
                 context: List[int] = None, options: dict = None) -> str:
        """Generate response (non-streaming)"""
        try:
            payload = {
                "model": model,
                "prompt": prompt,
                "stream": False
            }
            
            if system:
                payload["system"] = system
            if context:
                payload["context"] = context
            if options:
                payload["options"] = options
            
            response = requests.post(
                f"{self.base_url}/api/generate",
                json=payload,
                timeout=300
            )
            response.raise_for_status()
            result = response.json()
            return result.get('response', '')
            
        except Exception as e:
            logger.error(f"Generation failed: {e}")
            raise
    
    def generate_stream(self, model: str, prompt: str, system: str = None,
                        context: List[int] = None, options: dict = None) -> Generator:
        """Generate response with streaming"""
        try:
            payload = {
                "model": model,
                "prompt": prompt,
                "stream": True
            }
            
            if system:
                payload["system"] = system
            if context:
                payload["context"] = context
            if options:
                payload["options"] = options
            
            response = requests.post(
                f"{self.base_url}/api/generate",
                json=payload,
                stream=True,
                timeout=300
            )
            response.raise_for_status()
            
            for line in response.iter_lines():
                if line:
                    try:
                        data = json.loads(line)
                        yield data
                    except json.JSONDecodeError:
                        continue
                        
        except Exception as e:
            logger.error(f"Streaming generation failed: {e}")
            raise
    
    def chat(self, model: str, messages: List[Dict[str, str]],
             options: dict = None, think: bool = None) -> str:
        """Chat completion (non-streaming)"""
        try:
            payload = {
                "model": model,
                "messages": messages,
                "stream": False
            }

            if options:
                payload["options"] = options
            if think is not None:
                payload["think"] = think

            response = requests.post(
                f"{self.base_url}/api/chat",
                json=payload,
                timeout=300
            )
            response.raise_for_status()
            result = response.json()
            return result.get('message', {}).get('content', '')
            
        except Exception as e:
            logger.error(f"Chat failed: {e}")
            raise
    
    def _messages_to_prompt(self, messages: List[Dict[str, str]]) -> tuple:
        """Convert chat messages to prompt + system for /api/generate fallback"""
        system = ''
        prompt_parts = []
        
        for msg in messages:
            role = msg.get('role', '')
            content = msg.get('content', '')
            if role == 'system':
                system = content
            elif role == 'user':
                prompt_parts.append(f"User: {content}")
            elif role == 'assistant':
                prompt_parts.append(f"Assistant: {content}")
        
        prompt_parts.append("Assistant:")
        return '\n\n'.join(prompt_parts), system
    
    def chat_stream(self, model: str, messages: List[Dict[str, str]],
                    options: dict = None, think: bool = True) -> Generator:
        """Chat completion with streaming. Falls back to /api/generate if /api/chat is unavailable."""
        try:
            # Try /api/chat first
            payload = {
                "model": model,
                "messages": messages,
                "stream": True,
                "think": think
            }
            if options:
                payload["options"] = options
            
            response = requests.post(
                f"{self.base_url}/api/chat",
                json=payload,
                stream=True,
                timeout=300
            )
            
            if response.status_code == 404:
                logger.warning("/api/chat not found, falling back to /api/generate")
                yield from self._chat_stream_via_generate(model, messages, options)
                return
            
            response.raise_for_status()
            
            for line in response.iter_lines():
                if line:
                    try:
                        data = json.loads(line)
                        yield data
                    except json.JSONDecodeError:
                        continue
                        
        except requests.exceptions.HTTPError as e:
            if e.response is not None and e.response.status_code == 404:
                logger.warning("/api/chat returned 404, falling back to /api/generate")
                yield from self._chat_stream_via_generate(model, messages, options)
            else:
                logger.error(f"Streaming chat failed: {e}")
                raise
        except Exception as e:
            logger.error(f"Streaming chat failed: {e}")
            raise
    
    def _chat_stream_via_generate(self, model: str, messages: List[Dict[str, str]],
                                   options: dict = None) -> Generator:
        """Fallback: use /api/generate when /api/chat is unavailable"""
        prompt, system = self._messages_to_prompt(messages)
        
        payload = {
            "model": model,
            "prompt": prompt,
            "stream": True
        }
        if system:
            payload["system"] = system
        if options:
            payload["options"] = options
        
        response = requests.post(
            f"{self.base_url}/api/generate",
            json=payload,
            stream=True,
            timeout=300
        )
        response.raise_for_status()
        
        for line in response.iter_lines():
            if line:
                try:
                    data = json.loads(line)
                    # Convert /api/generate format to /api/chat format
                    yield {
                        'message': {'role': 'assistant', 'content': data.get('response', '')},
                        'done': data.get('done', False)
                    }
                except json.JSONDecodeError:
                    continue
    
    def is_available(self) -> bool:
        """Check if Ollama is available"""
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=5)
            return response.status_code == 200
        except Exception:
            return False


def get_ollama_service() -> OllamaService:
    """Get Ollama service instance"""
    return OllamaService()
