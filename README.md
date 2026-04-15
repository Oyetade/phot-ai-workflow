# Photo AI Workflow

A raw shoot gives you thousands of frames. This pipeline takes them down to a curated shortlist — automatically rejecting blurry shots, duplicates, and poor exposures, then ranking survivors by aesthetic quality using CLIP, and finally running an optional AI vision review (eyes closed, distracting elements, composition). A 2 000-image card typically produces a reviewed shortlist of ~100–200 keepers in under 15 minutes on CPU.

## Pipeline stages

| Stage | What it does | Key flags |
|-------|-------------|-----------|
| 1 — Technical filter | Rejects blurry, over/under-exposed, and duplicate frames | `--blur-threshold`, `--disable-blur-checks`, `--dedupe-distance` |
| 2 — Aesthetic score | Scores every survivor with CLIP; drops below threshold | `--aesthetic-threshold`, `--clip-model`, `--cluster-count` |
| 3 — VLM review | Ollama (LLaVA) or OpenAI reviews top N for eyes, composition | `--provider`, `--stage3-max-images` |

Also includes K-Means scene clustering on CLIP embeddings and a Gradio human review UI.

## Example terminal output

```
09:14:02 INFO [photo_ai_workflow.pipeline] Discovering images in E:\shoot
09:14:02 INFO [photo_ai_workflow.pipeline] Discovered 1847 images
09:14:02 INFO [photo_ai_workflow.pipeline] Stage 1 started
09:14:18 INFO [photo_ai_workflow.stage1_technical] Stage 1 progress: 50/1847 images analyzed
09:14:32 INFO [photo_ai_workflow.stage1_technical] Stage 1 progress: 100/1847 images analyzed
...
09:21:04 INFO [photo_ai_workflow.pipeline] Stage 1 complete: 1203/1847 images passed
09:21:04 INFO [photo_ai_workflow.pipeline] Stage 2 started
09:21:09 INFO [photo_ai_workflow.stage2_aesthetic] CLIP scorer ready on cpu (openai/clip-vit-base-patch32)
09:21:34 INFO [photo_ai_workflow.stage2_aesthetic] Stage 2 progress: 25/1203 images scored
...
09:29:11 INFO [photo_ai_workflow.pipeline] Stage 2 complete: 312/1203 images passed aesthetic filter
09:29:11 INFO [photo_ai_workflow.pipeline] Stage 3 started
09:29:12 INFO [photo_ai_workflow.stage3_vlm] Stage 3: provider=ollama model=llava max_images=300
...
09:51:43 INFO [photo_ai_workflow.pipeline] Wrote final shortlist to E:\shoot\workflow_outputs\final_shortlist.csv
```

## Setup

```powershell
cd photo_ai_workflow

# Install PyTorch first (CPU-only is fine; swap the URL for a CUDA index if you have a GPU)
pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu

# Install the package and all other dependencies
pip install -e .

# Set up secrets (only needed for --provider openai)
copy .env.example .env
```

## Run pipeline

```powershell
python -m photo_ai_workflow.cli run `
  --input-dir "C:\path\to\images" `
  --output-dir "C:\path\to\workflow_outputs" `
  --provider ollama `
  --ollama-model llava `
  --aesthetic-threshold 0.70 `
  --cluster-count 8 `
  --stage3-max-images 300 `
  --log-level INFO
```

To keep dedupe and exposure checks while disabling blur rejection:

```powershell
python -m photo_ai_workflow.cli run `
  --input-dir "C:\path\to\images" `
  --output-dir "C:\path\to\workflow_outputs" `
  --provider ollama `
  --disable-blur-checks
```

## Launch review UI

```powershell
python -m photo_ai_workflow.cli review-ui `
  --csv-path "C:\path\to\workflow_outputs\final_shortlist.csv"
```

## Outputs

- `stage1_technical.csv`
- `stage2_aesthetic.csv`
- `stage2_scene_clusters.csv`
- `stage3_ai_review.csv`
- `final_shortlist.csv`

## Notes

- Hardware acceleration is auto-selected in this order: `cuda`, `mps`, `cpu`.
- Stage 3 is intentionally run last and can be capped with `--stage3-max-images` to control cost.
- You can tune thresholds per shoot style and camera body.
- If `--clip-model` points to a local folder, offline mode is enabled automatically for Hugging Face/Transformers.
