from __future__ import annotations

from dataclasses import asdict
import logging
from pathlib import Path

import cv2
import imagehash
import numpy as np
import pandas as pd
from PIL import Image

from .config import TechnicalThresholds


logger = logging.getLogger(__name__)


def _laplacian_variance(gray: np.ndarray) -> float:
    return float(cv2.Laplacian(gray, cv2.CV_64F).var())


def _center_crop(gray: np.ndarray, frac: float = 0.5) -> np.ndarray:
    h, w = gray.shape
    ch = max(8, int(h * frac))
    cw = max(8, int(w * frac))
    y0 = max(0, (h - ch) // 2)
    x0 = max(0, (w - cw) // 2)
    return gray[y0 : y0 + ch, x0 : x0 + cw]


def _max_patch_laplacian_variance(gray: np.ndarray, grid: int = 3) -> float:
    h, w = gray.shape
    ys = np.linspace(0, h, grid + 1, dtype=int)
    xs = np.linspace(0, w, grid + 1, dtype=int)
    best = 0.0
    for yi in range(grid):
        for xi in range(grid):
            patch = gray[ys[yi] : ys[yi + 1], xs[xi] : xs[xi + 1]]
            if patch.size == 0:
                continue
            best = max(best, _laplacian_variance(patch))
    return float(best)


def _compute_metrics(image_path: Path) -> dict[str, float | bool | str]:
    gray = cv2.imread(str(image_path), cv2.IMREAD_GRAYSCALE)
    if gray is None:
        return {
            "blur_variance": 0.0,
            "subject_blur_variance": 0.0,
            "max_patch_blur_variance": 0.0,
            "weighted_blur_variance": 0.0,
            "mean_intensity": 0.0,
            "is_blurry": True,
            "is_bad_exposure": True,
            "phash": "",
            "error": "failed_to_read",
        }

    blur_variance = _laplacian_variance(gray)
    subject_blur_variance = _laplacian_variance(_center_crop(gray, frac=0.5))
    max_patch_blur_variance = _max_patch_laplacian_variance(gray, grid=3)
    mean_intensity = float(gray.mean())
    phash = str(imagehash.phash(Image.open(image_path)))
    return {
        "blur_variance": blur_variance,
        "subject_blur_variance": subject_blur_variance,
        "max_patch_blur_variance": max_patch_blur_variance,
        "mean_intensity": mean_intensity,
        "phash": phash,
        "error": "",
    }


def run_stage1(image_paths: list[Path], cfg: TechnicalThresholds) -> pd.DataFrame:
    logger.info(
        "Stage 1 processing %d images (blur_checks=%s, dedupe_distance=%d)",
        len(image_paths),
        cfg.enable_blur_checks,
        cfg.dedupe_hamming_distance_max,
    )
    rows: list[dict[str, object]] = []
    total = len(image_paths)
    for index, path in enumerate(image_paths, start=1):
        m = _compute_metrics(path)
        weighted_blur_variance = (
            cfg.center_weight * float(m["subject_blur_variance"])
            + (1.0 - cfg.center_weight) * float(m["blur_variance"])
        )
        subject_is_sharp = bool(
            float(m["subject_blur_variance"]) >= cfg.subject_laplacian_variance_min
            or float(m["max_patch_blur_variance"]) >= cfg.sharp_patch_laplacian_variance_min
        )
        global_is_very_blurry = bool(float(m["blur_variance"]) < cfg.global_laplacian_hard_fail_max)
        weighted_is_low = bool(weighted_blur_variance < cfg.blur_laplacian_variance_min)
        # Two-threshold gate: only reject for blur if likely subject detail is weak and
        # the global/weighted sharpness indicates an actually soft frame.
        is_blurry = bool((not subject_is_sharp) and (global_is_very_blurry or weighted_is_low))
        if not cfg.enable_blur_checks:
            is_blurry = False
        bad_exposure = bool(
            m["mean_intensity"] < cfg.mean_intensity_min
            or m["mean_intensity"] > cfg.mean_intensity_max
        )
        rows.append(
            {
                "path": str(path),
                "blur_variance": m["blur_variance"],
                "subject_blur_variance": m["subject_blur_variance"],
                "max_patch_blur_variance": m["max_patch_blur_variance"],
                "weighted_blur_variance": weighted_blur_variance,
                "subject_is_sharp": subject_is_sharp,
                "global_is_very_blurry": global_is_very_blurry,
                "mean_intensity": m["mean_intensity"],
                "is_blurry": is_blurry,
                "is_bad_exposure": bad_exposure,
                "phash": m["phash"],
                "error": m["error"],
            }
        )
        if total and (index == total or index % 50 == 0):
            logger.info("Stage 1 progress: %d/%d images analyzed", index, total)

    df = pd.DataFrame(rows)
    if df.empty:
        return df

    # Greedy duplicate grouping by pHash distance, then keep the highest-quality item per group.
    group_ids: list[int] = []
    representatives: list[tuple[int, imagehash.ImageHash]] = []
    group_counter = 0

    for _, row in df.iterrows():
        current_hash = imagehash.hex_to_hash(str(row["phash"])) if row["phash"] else None
        assigned = None
        if current_hash is not None:
            for gid, rep_hash in representatives:
                if current_hash - rep_hash <= cfg.dedupe_hamming_distance_max:
                    assigned = gid
                    break
        if assigned is None:
            assigned = group_counter
            if current_hash is not None:
                representatives.append((assigned, current_hash))
            group_counter += 1
        group_ids.append(assigned)

    df["dupe_group"] = group_ids
    df["quality_score"] = (
        df["weighted_blur_variance"].astype(float)
        - (df["mean_intensity"].astype(float) - 128.0).abs() * 0.5
    )

    best_in_group = (
        df.sort_values(["dupe_group", "quality_score"], ascending=[True, False])
        .groupby("dupe_group")["path"]
        .first()
        .to_dict()
    )
    df["is_duplicate"] = df.apply(lambda r: best_in_group.get(r["dupe_group"]) != r["path"], axis=1)

    df["stage1_pass"] = (~df["is_blurry"]) & (~df["is_bad_exposure"]) & (~df["is_duplicate"])
    logger.info(
        "Stage 1 summary: blurry=%d bad_exposure=%d duplicates=%d passed=%d",
        int(df["is_blurry"].sum()),
        int(df["is_bad_exposure"].sum()),
        int(df["is_duplicate"].sum()),
        int(df["stage1_pass"].sum()),
    )
    return df


def technical_config_dict(cfg: TechnicalThresholds) -> dict[str, object]:
    return asdict(cfg)
