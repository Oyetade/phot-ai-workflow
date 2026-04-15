from __future__ import annotations

import logging
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.cluster import KMeans

from .stage2_aesthetic import CLIPAestheticScorer


logger = logging.getLogger(__name__)


def cluster_survivors(image_paths: list[Path], scorer: CLIPAestheticScorer, cluster_count: int) -> pd.DataFrame:
    if not image_paths:
        logger.info("Clustering skipped because there are no Stage 2 survivors")
        return pd.DataFrame(columns=["path", "cluster"])

    n_clusters = max(1, min(cluster_count, len(image_paths)))
    logger.info("Computing embeddings for %d images and fitting %d clusters", len(image_paths), n_clusters)
    embs = np.array([scorer.embedding(p) for p in image_paths], dtype=np.float32)
    km = KMeans(n_clusters=n_clusters, n_init="auto", random_state=42)
    labels = km.fit_predict(embs)
    return pd.DataFrame({"path": [str(p) for p in image_paths], "cluster": labels})
