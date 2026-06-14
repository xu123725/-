from __future__ import annotations

import logging
import os
import time
from typing import Any

import requests

from utils.logger import log_event


logger = logging.getLogger(__name__)


class LLMClient:
    def __init__(self, api_key: str, base_url: str, model: str, timeout: int = 120) -> None:
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.fallback_model = os.getenv("FALLBACK_MODEL", "deepseek-chat")
        self.timeout = timeout
        self.trace_id = ""
        if not self.api_key:
            raise ValueError("未配置 API_KEY，无法调用模型接口。")

    def set_trace_id(self, trace_id: str) -> None:
        self.trace_id = trace_id.strip()

    def _post(self, payload: dict[str, Any]) -> dict[str, Any]:
        started = time.perf_counter()
        model_name = str(payload.get("model", ""))
        log_event(logger, logging.INFO, "llm_request_start", trace_id=self.trace_id, model=model_name)
        try:
            # 确保 API Key 不包含非 ASCII 字符，避免 Header 编码错误
            clean_api_key = str(self.api_key).encode('ascii', 'ignore').decode('ascii').strip()
            response = requests.post(
                f"{self.base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {clean_api_key}",
                    "Content-Type": "application/json",
                },
                json=payload,
                timeout=self.timeout,
            )
            response.raise_for_status()
            cost_ms = int((time.perf_counter() - started) * 1000)
            log_event(
                logger,
                logging.INFO,
                "llm_request_success",
                trace_id=self.trace_id,
                model=model_name,
                status_code=response.status_code,
                duration_ms=cost_ms,
            )
            return response.json()
        except Exception as exc:
            cost_ms = int((time.perf_counter() - started) * 1000)
            log_event(
                logger,
                logging.ERROR,
                "llm_request_failed",
                trace_id=self.trace_id,
                model=model_name,
                duration_ms=cost_ms,
                error=str(exc),
            )
            raise

    def chat_completion(
        self,
        messages: list[dict[str, str]],
        response_format: dict[str, str] | None = None,
        temperature: float = 0.2,
        max_tokens: int = 1800,
    ) -> str:
        if self.model == "deepseek-reasoner" and response_format:
            fallback_payload: dict[str, Any] = {
                "model": self.fallback_model,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
                "response_format": response_format,
            }
            fallback_data = self._post(fallback_payload)
            fallback_content = fallback_data["choices"][0]["message"].get("content") or ""
            if fallback_content.strip():
                return fallback_content
            raise ValueError("结构化调用返回空内容，请检查模型配置。")
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if response_format:
            payload["response_format"] = response_format

        # DeepSeek Reasoner specific adjustments
        if self.model == "deepseek-reasoner":
            payload.pop("response_format", None)
            payload.pop("temperature", None)

        data = self._post(payload)
        content = data["choices"][0]["message"].get("content") or ""
        if content.strip():
            return content
        if self.model == "deepseek-reasoner":
            fallback_payload: dict[str, Any] = {
                "model": self.fallback_model,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
            }
            if response_format:
                fallback_payload["response_format"] = response_format
            fallback_data = self._post(fallback_payload)
            fallback_content = fallback_data["choices"][0]["message"].get("content") or ""
            if fallback_content.strip():
                return fallback_content
        raise ValueError("模型返回空内容，请检查模型配置或提示词。")

    def chat_stream(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.4,
        max_tokens: int = 1200,
    ):
        """流式获取聊天回复"""
        import json
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": True,
        }
        
        # DeepSeek Reasoner specific adjustments
        if self.model == "deepseek-reasoner":
            payload.pop("temperature", None)

        clean_api_key = str(self.api_key).encode('ascii', 'ignore').decode('ascii').strip()
        try:
            response = requests.post(
                f"{self.base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {clean_api_key}",
                    "Content-Type": "application/json",
                },
                json=payload,
                timeout=self.timeout,
                stream=True
            )
            response.raise_for_status()
            
            for line in response.iter_lines():
                if not line:
                    continue
                line_str = line.decode("utf-8")
                if line_str.startswith("data: "):
                    data_str = line_str[6:]
                    if data_str == "[DONE]":
                        break
                    try:
                        chunk = json.loads(data_str)
                        delta = chunk["choices"][0].get("delta", {})
                        content = delta.get("content", "")
                        if content:
                            yield content
                    except Exception:
                        continue
        except Exception as exc:
            log_event(logger, logging.ERROR, "llm_stream_failed", trace_id=self.trace_id, error=str(exc))
            yield f" [错误: {str(exc)}] "

