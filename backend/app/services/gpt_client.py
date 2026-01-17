"""Wrapper around the OpenAI API with retries and backoff.

This client sends prompts to OpenAI's chat completion API. It enforces
timeouts, a maximum number of retries with exponential backoff, and captures
response metadata such as token counts and latency. To use this client, set
the OPENAI_API_KEY environment variable. Without a key, the client will raise
an error.
"""
from __future__ import annotations
import os
import time
import logging
from typing import Dict, Any

import requests

logger = logging.getLogger(__name__)


class GPTClient:
    """Client for interacting with OpenAI's GPT models."""

    def __init__(self, api_key: str | None = None, timeout: float = 10.0, max_retries: int = 3):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.timeout = timeout
        self.max_retries = max_retries

    def send_prompt(self, prompt: str) -> Dict[str, Any]:
        """Send a prompt to the GPT API and return response details."""
        if not self.api_key:
            raise ValueError("OpenAI API key not configured.")
        url = "https://api.openai.com/v1/chat/completions"
        headers = {"Authorization": f"Bearer {self.api_key}"}
        data = {
            "model": "gpt-4",
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 512,
            "temperature": 0.2,
        }
        for attempt in range(1, self.max_retries + 1):
            start_time = time.time()
            try:
                response = requests.post(url, headers=headers, json=data, timeout=self.timeout)
                latency_ms = int((time.time() - start_time) * 1000)
                if response.status_code == 200:
                    resp_json = response.json()
                    content = resp_json["choices"][0]["message"]["content"]
                    tokens = resp_json.get("usage", {}).get("total_tokens")
                    return {
                        "raw": response.text,
                        "parsed": content,
                        "tokens": tokens,
                        "latency_ms": latency_ms,
                    }
                else:
                    logger.warning(f"GPT call failed with status {response.status_code}: {response.text}")
            except Exception as e:
                logger.error(f"GPT call attempt {attempt} failed: {e}")
            # Exponential backoff
            time.sleep(2 ** attempt)
        raise RuntimeError("GPT call failed after maximum retries.")
