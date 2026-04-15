from __future__ import annotations

import logging
from pathlib import Path

import pandas as pd

from .clustering import cluster_survivors
from .config import PipelineConfig
from .stage1_technical import run_stage1
from .stage2_aesthetic import CLIPAestheticScorer, run_stage2
from .stage3_vlm import run_stage3
from .utils import discover_images


logger = logging.getLogger(__name__)


def run_pipeline(input_dir: Path, output_dir: Path, cfg: PipelineConfig, skip_stage1: bool = False) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    logger.info("Discovering images in %s", input_dir)

    images = discover_images(input_dir)
    if not images:
        raise RuntimeError(f"No images found in {input_dir}")
    logger.info("Discovered %d images", len(images))

    if skip_stage1:
        logger.info("Stage 1 skipped; forwarding all images")
        stage1 = pd.DataFrame(
            {
                "path": [str(p) for p in images],
                "stage1_pass": [True] * len(images),
                "stage1_skipped": [True] * len(images),
            }
        )
    else:
        logger.info("Stage 1 started")
        stage1 = run_stage1(images, cfg.technical)
        stage1["stage1_skipped"] = False
    stage1.to_csv(output_dir / "stage1_technical.csv", index=False)
    s1_paths = [Path(p) for p in stage1.loc[stage1["stage1_pass"], "path"].tolist()]
    logger.info("Stage 1 complete: %d/%d images passed", len(s1_paths), len(images))

    logger.info("Stage 2 started")
    stage2, scorer = run_stage2(s1_paths, cfg.aesthetic)
    stage2.to_csv(output_dir / "stage2_aesthetic.csv", index=False)
    s2_paths = [Path(p) for p in stage2.loc[stage2["stage2_pass"], "path"].tolist()]
    logger.info("Stage 2 complete: %d/%d images passed aesthetic filter", len(s2_paths), len(s1_paths))

    logger.info("Clustering %d Stage 2 survivors into up to %d clusters", len(s2_paths), cfg.cluster_count)
    clusters = cluster_survivors(s2_paths, scorer, cfg.cluster_count)
    clusters.to_csv(output_dir / "stage2_scene_clusters.csv", index=False)
    logger.info("Clustering complete")

    logger.info("Stage 3 started")
    stage3_rows = run_stage3(s2_paths, cfg.stage3)
    stage3 = pd.DataFrame(stage3_rows)
    if not stage3.empty:
        stage3.to_csv(output_dir / "stage3_ai_review.csv", index=False)
    logger.info("Stage 3 complete: reviewed %d images", len(stage3_rows))

    merged = stage1.merge(stage2, on="path", how="left").merge(clusters, on="path", how="left")
    if not stage3.empty:
        merged = merged.merge(stage3, on="path", how="left")
    merged.to_csv(output_dir / "final_shortlist.csv", index=False)
    logger.info("Wrote final shortlist to %s", output_dir / "final_shortlist.csv")


def warmup_clip_model(cfg: PipelineConfig) -> CLIPAestheticScorer:
    return CLIPAestheticScorer(cfg.aesthetic)
