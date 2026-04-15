from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import pandas as pd
import torch
from PIL import Image

from .config import AestheticConfig
from .devices import pick_torch_device


logger = logging.getLogger(__name__)


def _load_clip_classes() -> tuple[Any, Any]:
    try:
        from transformers import CLIPModel, CLIPProcessor  # type: ignore[import-not-found]
    except Exception as exc:  # pragma: no cover
        raise RuntimeError(
            "Failed to import CLIP dependencies from transformers. "
            "Your Python environment likely has a broken numpy/transformers install. "
            "Try: python -m pip install --upgrade --force-reinstall numpy transformers"
        ) from exc
    return CLIPModel, CLIPProcessor


class CLIPAestheticScorer:
    def __init__(self, cfg: AestheticConfig) -> None:
        self.cfg = cfg
        self.device = pick_torch_device()
        logger.info("Initializing CLIP scorer model=%s device=%s", cfg.model_name, self.device)
        CLIPModel, CLIPProcessor = _load_clip_classes()
        try:
            self.model = CLIPModel.from_pretrained(cfg.model_name, low_cpu_mem_usage=False).to(self.device)
        except ValueError as exc:
            msg = str(exc)
            model_path = Path(cfg.model_name)
            tf_ckpt = model_path / "tf_model.h5"
            if "torch.load" in msg and "at least v2.6" in msg and tf_ckpt.exists():
                # Fallback for local CLIP checkpoints without safetensors when torch<2.6.
                self.model = CLIPModel.from_pretrained(
                    cfg.model_name,
                    from_tf=True,
                    low_cpu_mem_usage=False,
                ).to(self.device)
            else:
                raise
        self.processor = CLIPProcessor.from_pretrained(cfg.model_name)
        self.model.eval()

    @torch.inference_mode()
    def score(self, image_path: Path) -> float:
        image = Image.open(image_path).convert("RGB")
        inputs = self.processor(
            text=[self.cfg.positive_prompt, self.cfg.negative_prompt],
            images=image,
            return_tensors="pt",
            padding=True,
        )
        inputs = {k: v.to(self.device) for k, v in inputs.items()}
        out = self.model(**inputs)
        probs = out.logits_per_image.softmax(dim=1)
        return float(probs[0][0].item())

    @torch.inference_mode()
    def embedding(self, image_path: Path) -> list[float]:
        image = Image.open(image_path).convert("RGB")
        inputs = self.processor(images=image, return_tensors="pt")
        inputs = {k: v.to(self.device) for k, v in inputs.items()}
        # Use image-only code path; some CLIP forward variants require text inputs.
        pixel_values = inputs["pixel_values"]
        feats = self.model.get_image_features(pixel_values=pixel_values)
        if not isinstance(feats, torch.Tensor):
            if hasattr(feats, "pooler_output"):
                feats = feats.pooler_output
            elif hasattr(feats, "last_hidden_state"):
                feats = feats.last_hidden_state[:, 0, :]
            else:
                raise TypeError(f"Unsupported embedding output type: {type(feats)}")
        feats = torch.nn.functional.normalize(feats, dim=-1)
        return feats[0].detach().cpu().tolist()


def run_stage2(image_paths: list[Path], cfg: AestheticConfig, scorer: CLIPAestheticScorer | None = None) -> tuple[pd.DataFrame, CLIPAestheticScorer]:
    local_scorer = scorer or CLIPAestheticScorer(cfg)
    rows: list[dict[str, object]] = []
    total = len(image_paths)
    logger.info("Stage 2 scoring %d images with threshold %.3f", total, cfg.min_score_to_survive)
    for index, p in enumerate(image_paths, start=1):
        s = local_scorer.score(p)
        rows.append(
            {
                "path": str(p),
                "aesthetic_score": s,
                "stage2_pass": s >= cfg.min_score_to_survive,
            }
        )
        if total and (index == total or index % 25 == 0):
            logger.info("Stage 2 progress: %d/%d images scored", index, total)
    return pd.DataFrame(rows), local_scorer
