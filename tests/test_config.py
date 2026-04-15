"""Smoke tests for config dataclasses — no I/O, no models required."""
import pytest
from photo_ai_workflow.config import (
    AestheticConfig,
    PipelineConfig,
    Stage3Config,
    TechnicalThresholds,
)


class TestTechnicalThresholds:
    def test_defaults(self):
        t = TechnicalThresholds()
        assert t.blur_laplacian_variance_min == 100.0
        assert t.mean_intensity_min == 35.0
        assert t.mean_intensity_max == 220.0
        assert t.dedupe_hamming_distance_max == 8
        assert t.enable_blur_checks is True

    def test_blur_checks_can_be_disabled(self):
        t = TechnicalThresholds(enable_blur_checks=False)
        assert t.enable_blur_checks is False

    def test_custom_thresholds(self):
        t = TechnicalThresholds(blur_laplacian_variance_min=50.0, dedupe_hamming_distance_max=4)
        assert t.blur_laplacian_variance_min == 50.0
        assert t.dedupe_hamming_distance_max == 4


class TestAestheticConfig:
    def test_defaults(self):
        a = AestheticConfig()
        assert 0.0 < a.min_score_to_survive < 1.0
        assert "clip" in a.model_name.lower()

    def test_custom_threshold(self):
        a = AestheticConfig(min_score_to_survive=0.80)
        assert a.min_score_to_survive == 0.80


class TestStage3Config:
    def test_defaults(self):
        s = Stage3Config()
        assert s.provider in ("ollama", "openai")
        assert s.timeout_sec > 0
        assert s.max_images > 0

    def test_custom_provider(self):
        s = Stage3Config(provider="openai", openai_model="gpt-4.1")
        assert s.provider == "openai"
        assert s.openai_model == "gpt-4.1"


class TestPipelineConfig:
    def test_nested_defaults(self):
        cfg = PipelineConfig()
        assert isinstance(cfg.technical, TechnicalThresholds)
        assert isinstance(cfg.aesthetic, AestheticConfig)
        assert isinstance(cfg.stage3, Stage3Config)
        assert cfg.cluster_count > 0

    def test_nested_override(self):
        cfg = PipelineConfig(cluster_count=12)
        assert cfg.cluster_count == 12
