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

    def _extract_error_message(self, response: requests.Response) -> str:
        try:
            data = response.json()
        except Exception:
            data = None

        if isinstance(data, dict):
            error = data.get('error')
            if isinstance(error, dict):
                return error.get('message') or str(error)
            if isinstance(error, str):
                return error
            message = data.get('message')
            if isinstance(message, str) and message:
                return message
        return response.text[:500] or f'HTTP {response.status_code}'

    def _raise_for_status(self, response: requests.Response):
        if response.ok:
            return
        message = self._extract_error_message(response)
        raise requests.HTTPError(
            f'{response.status_code} {response.reason}: {message}',
            response=response
        )

    def chat(self, model: str, messages: List[Dict[str, str]], options: Dict[str, Any] = None) -> str:
        payload = {
            'model': model,
            'messages': messages,
            'stream': False
        }
        if options:
            payload.update(options)

        response = requests.post(
            f'{self.base_url}/chat/completions',
            headers=self._headers(),
            json=payload,
            timeout=300
        )
        response.raise_for_status()
        data = response.json()
        choices = data.get('choices') or []
        if not choices:
            return ''
        return choices[0].get('message', {}).get('content', '')

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

    def test_connection(self, model: str) -> Dict[str, Any]:
        """Two-stage connectivity test for OpenAI-compatible providers."""
        result: Dict[str, Any] = {
            'ok': False,
            'model': model,
            'base_url': self.base_url,
            'models_endpoint_ok': False,
            'chat_endpoint_ok': False,
            'model_listed': None,
        }

        # Stage 1: test authentication and base URL against /models
        models_response = requests.get(
            f'{self.base_url}/models',
            headers=self._headers(),
            timeout=20
        )
        self._raise_for_status(models_response)
        result['models_endpoint_ok'] = True

        model_names = []
        try:
            models_data = models_response.json()
            for item in models_data.get('data', []) if isinstance(models_data, dict) else []:
                if isinstance(item, dict) and item.get('id'):
                    model_names.append(item['id'])
        except Exception:
            model_names = []

        if model_names:
            result['available_models'] = model_names[:20]
            result['model_listed'] = model in model_names

        # Stage 2: do a minimal real completion against the configured model
        payload = {
            'model': model,
            'messages': [{'role': 'user', 'content': 'ping'}],
            'stream': False,
            'max_tokens': 1,
            'temperature': 0
        }
        chat_response = requests.post(
            f'{self.base_url}/chat/completions',
            headers=self._headers(),
            json=payload,
            timeout=30
        )
        self._raise_for_status(chat_response)
        result['chat_endpoint_ok'] = True

        data = chat_response.json()
        choices = data.get('choices') or []
        result['has_choices'] = bool(choices)
        result['ok'] = True
        return result


def get_external_model_service(api_key: str, base_url: str = None) -> ExternalModelService:
    return ExternalModelService(api_key=api_key, base_url=base_url)
