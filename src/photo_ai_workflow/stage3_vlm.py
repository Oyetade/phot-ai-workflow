from __future__ import annotations

import json
import logging
import os
import re
from pathlib import Path
from typing import Any

import requests

from .config import Stage3Config
from .utils import to_base64, to_data_url


logger = logging.getLogger(__name__)


REVIEW_PROMPT = (
    "You are an expert photo editor. Return strict JSON with keys: "
    "eyes_closed (boolean), distracting_elements (array of strings), "
    "composition_comment (string), keep_recommendation (boolean), reason (string)."
)


def _parse_json(text: str) -> dict[str, Any]:
    raw = text.strip()
    try:
        return json.loads(raw)
    except Exception:
        m = re.search(r"\{.*\}", raw, flags=re.DOTALL)
        if m:
            try:
                return json.loads(m.group(0))
            except Exception:
                pass
    return {
        "eyes_closed": False,
        "distracting_elements": [],
        "composition_comment": "",
        "keep_recommendation": False,
        "reason": raw[:500],
    }


def _review_openai(image_path: Path, cfg: Stage3Config) -> dict[str, Any]:
    api_key = os.environ.get("OPENAI_API_KEY", "")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is required for provider=openai")

    payload = {
        "model": cfg.openai_model,
        "temperature": cfg.temperature,
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": REVIEW_PROMPT},
                    {"type": "image_url", "image_url": {"url": to_data_url(image_path)}},
                ],
            }
        ],
    }
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    resp = requests.post(cfg.openai_api_url, headers=headers, json=payload, timeout=cfg.timeout_sec)
    resp.raise_for_status()
    content = resp.json()["choices"][0]["message"]["content"]
    return _parse_json(content)


def _review_ollama(image_path: Path, cfg: Stage3Config) -> dict[str, Any]:
    payload = {
        "model": cfg.ollama_model,
        "prompt": REVIEW_PROMPT,
        "images": [to_base64(image_path)],
        "stream": False,
        "format": "json",
        "options": {"temperature": cfg.temperature},
    }
    resp = requests.post(cfg.ollama_url, json=payload, timeout=cfg.timeout_sec)
    resp.raise_for_status()
    content = str(resp.json().get("response", ""))
    return _parse_json(content)


def run_stage3(image_paths: list[Path], cfg: Stage3Config) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    review_count = min(len(image_paths), cfg.max_images)
    logger.info("Stage 3 reviewing %d images via %s model=%s", review_count, cfg.provider, cfg.ollama_model if cfg.provider == "ollama" else cfg.openai_model)
    for i, p in enumerate(image_paths, start=1):
        if i > cfg.max_images:
            break
        if cfg.provider == "openai":
            out = _review_openai(p, cfg)
        else:
            out = _review_ollama(p, cfg)
        out["path"] = str(p)
        rows.append(out)
        if review_count and (i == review_count or i % 10 == 0):
            logger.info("Stage 3 progress: %d/%d images reviewed", i, review_count)
    return rows
