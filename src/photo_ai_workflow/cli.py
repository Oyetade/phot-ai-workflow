from __future__ import annotations

import argparse
import logging
import os
from pathlib import Path

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover
    def load_dotenv() -> bool:
        return False


logger = logging.getLogger(__name__)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Professional photographer workflow")
    sub = p.add_subparsers(dest="command", required=True)

    run_p = sub.add_parser("run", help="Run 3-stage culling pipeline")
    run_p.add_argument("--input-dir", required=True)
    run_p.add_argument("--output-dir", required=True)
    run_p.add_argument("--provider", choices=["ollama", "openai"], default="ollama")
    run_p.add_argument("--ollama-model", default="llava")
    run_p.add_argument("--openai-model", default="gpt-4.1-mini")
    run_p.add_argument("--clip-model", default="openai/clip-vit-base-patch32")
    run_p.add_argument("--aesthetic-threshold", type=float, default=0.70)
    run_p.add_argument("--blur-threshold", type=float, default=100.0)
    run_p.add_argument("--subject-blur-threshold", type=float, default=120.0)
    run_p.add_argument("--global-blur-hard-fail", type=float, default=45.0)
    run_p.add_argument("--sharp-patch-threshold", type=float, default=160.0)
    run_p.add_argument(
        "--disable-blur-checks",
        action="store_true",
        help="Run Stage 1 without blur-based rejection while keeping deduplication and exposure checks.",
    )
    run_p.add_argument("--center-weight", type=float, default=0.7)
    run_p.add_argument("--dedupe-distance", type=int, default=8)
    run_p.add_argument("--cluster-count", type=int, default=8)
    run_p.add_argument("--stage3-max-images", type=int, default=300)
    run_p.add_argument("--log-level", default="INFO", choices=["DEBUG", "INFO", "WARNING", "ERROR"])
    run_p.add_argument(
        "--skip-stage1",
        action="store_true",
        help="Bypass technical filtering and run Stage 2/3 on all discovered images.",
    )

    ui_p = sub.add_parser("review-ui", help="Launch Gradio shortlist review")
    ui_p.add_argument("--csv-path", required=True)

    return p.parse_args()


def _auto_configure_local_clip_offline(clip_model: str) -> None:
    clip_path = Path(clip_model)
    if clip_path.exists() and clip_path.is_dir():
        os.environ.setdefault("HF_HUB_OFFLINE", "1")
        os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")
        os.environ.setdefault("HF_HUB_DISABLE_XET", "1")


def main() -> int:
    load_dotenv()
    args = parse_args()

    from .logging_utils import configure_logging

    configure_logging(args.log_level if hasattr(args, "log_level") else "INFO")

    if args.command == "review-ui":
        from .ui_gradio import launch_review_ui

        logger.info("Launching review UI for %s", args.csv_path)
        launch_review_ui(Path(args.csv_path))
        return 0

    from .config import PipelineConfig
    from .pipeline import run_pipeline

    cfg = PipelineConfig()
    cfg.stage3.provider = args.provider
    cfg.stage3.ollama_model = args.ollama_model
    cfg.stage3.openai_model = args.openai_model
    cfg.stage3.max_images = args.stage3_max_images

    cfg.aesthetic.model_name = args.clip_model
    cfg.aesthetic.min_score_to_survive = args.aesthetic_threshold
    _auto_configure_local_clip_offline(args.clip_model)

    cfg.technical.blur_laplacian_variance_min = args.blur_threshold
    cfg.technical.subject_laplacian_variance_min = args.subject_blur_threshold
    cfg.technical.global_laplacian_hard_fail_max = args.global_blur_hard_fail
    cfg.technical.sharp_patch_laplacian_variance_min = args.sharp_patch_threshold
    cfg.technical.enable_blur_checks = not args.disable_blur_checks
    cfg.technical.center_weight = args.center_weight
    cfg.technical.dedupe_hamming_distance_max = args.dedupe_distance

    cfg.cluster_count = args.cluster_count

    logger.info(
        "Starting pipeline input=%s output=%s provider=%s clip_model=%s skip_stage1=%s blur_checks=%s",
        args.input_dir,
        args.output_dir,
        args.provider,
        args.clip_model,
        args.skip_stage1,
        not args.disable_blur_checks,
    )

    run_pipeline(Path(args.input_dir), Path(args.output_dir), cfg, skip_stage1=args.skip_stage1)
    logger.info("Pipeline finished successfully")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
