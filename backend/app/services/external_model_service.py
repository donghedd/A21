"""
External Model Service - OpenAI-compatible API integration
"""
import json
import logging
from typing import Any, Dict, Generator, List

import requests

logger = logging.getLogger(__name__)


class ExternalModelService:
    """Service for interacting with OpenAI-compatible external model APIs"""

    def __init__(self, api_key: str, base_url: str = None):
        self.api_key = api_key
        self.base_url = (base_url or 'https://api.openai.com/v1').rstrip('/')

    def _headers(self) -> Dict[str, str]:
        return {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json'
        }

    def chat_stream(self, model: str, messages: List[Dict[str, str]]) -> Generator[Dict[str, Any], None, None]:
        payload = {
            'model': model,
            'messages': messages,
            'stream': True
        }

        response = requests.post(
            f'{self.base_url}/chat/completions',
            headers=self._headers(),
            json=payload,
            stream=True,
            timeout=300
        )
        response.raise_for_status()

        for line in response.iter_lines(decode_unicode=True):
            if not line:
                continue

            if line.startswith('data: '):
                line = line[6:]

            if line == '[DONE]':
                yield {'done': True}
                break

            try:
                data = json.loads(line)
            except json.JSONDecodeError:
                continue

            choices = data.get('choices') or []
            if not choices:
                continue

            delta = choices[0].get('delta') or {}
            content = delta.get('content')
            if content:
                yield {
                    'message': {
                        'role': delta.get('role', 'assistant'),
                        'content': content
                    },
                    'done': False
                }

            finish_reason = choices[0].get('finish_reason')
            if finish_reason:
                yield {'done': True}
                break


def get_external_model_service(api_key: str, base_url: str = None) -> ExternalModelService:
    return ExternalModelService(api_key=api_key, base_url=base_url)
