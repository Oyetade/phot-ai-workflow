from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class TechnicalThresholds:
    enable_blur_checks: bool = True
    blur_laplacian_variance_min: float = 100.0
    subject_laplacian_variance_min: float = 120.0
    global_laplacian_hard_fail_max: float = 45.0
    sharp_patch_laplacian_variance_min: float = 160.0
    center_weight: float = 0.7
    mean_intensity_min: float = 35.0
    mean_intensity_max: float = 220.0
    dedupe_hamming_distance_max: int = 8


@dataclass
class AestheticConfig:
    model_name: str = "openai/clip-vit-base-patch32"
    positive_prompt: str = "A professional, award-winning photograph"
    negative_prompt: str = "A blurry, poorly composed snapshot"
    min_score_to_survive: float = 0.70


@dataclass
class Stage3Config:
    provider: str = "ollama"  # ollama|openai
    openai_model: str = "gpt-4.1-mini"
    openai_api_url: str = "https://api.openai.com/v1/chat/completions"
    ollama_url: str = "http://localhost:11434/api/generate"
    ollama_model: str = "llava"
    temperature: float = 0.2
    timeout_sec: int = 180
    max_images: int = 300


@dataclass
class PipelineConfig:
    technical: TechnicalThresholds = field(default_factory=TechnicalThresholds)
    aesthetic: AestheticConfig = field(default_factory=AestheticConfig)
    stage3: Stage3Config = field(default_factory=Stage3Config)
    cluster_count: int = 8
