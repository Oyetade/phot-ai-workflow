from __future__ import annotations

from pathlib import Path

import gradio as gr
import pandas as pd


def launch_review_ui(csv_path: Path) -> None:
    df = pd.read_csv(csv_path)
    if "manual_label" not in df.columns:
        df["manual_label"] = "unreviewed"
    idx = {"value": 0}

    def current_row() -> tuple[str, str]:
        if len(df) == 0:
            return "", "No rows"
        i = idx["value"] % len(df)
        row = df.iloc[i]
        meta = f"{i+1}/{len(df)} | score={row.get('aesthetic_score', 'na')} | cluster={row.get('cluster', 'na')}"
        return str(row["path"]), meta

    def label_and_next(label: str) -> tuple[str, str]:
        if len(df) == 0:
            return "", "No rows"
        i = idx["value"] % len(df)
        df.at[i, "manual_label"] = label
        idx["value"] = i + 1
        return current_row()

    def save_labels() -> str:
        out = csv_path.with_name(csv_path.stem + "_manual_labels.csv")
        df.to_csv(out, index=False)
        return f"Saved {out}"

    # Gradio only allows serving file paths from approved roots.
    allowed_paths: list[str] = [str(csv_path.parent.resolve())]
    if "path" in df.columns:
        image_roots = {
            str(Path(p).resolve().parent)
            for p in df["path"].dropna().astype(str).tolist()
            if p.strip()
        }
        allowed_paths.extend(sorted(image_roots))
    allowed_paths = sorted(set(allowed_paths))

    with gr.Blocks(title="Photo shortlist reviewer") as demo:
        gr.Markdown("# Human-in-the-loop review")
        img = gr.Image(type="filepath", label="Image")
        meta = gr.Textbox(label="Metadata")
        with gr.Row():
            keep = gr.Button("Keep")
            trash = gr.Button("Trash")
            maybe = gr.Button("Maybe")
        save = gr.Button("Save Labels")
        status = gr.Textbox(label="Status")

        demo.load(current_row, outputs=[img, meta])
        keep.click(lambda: label_and_next("keep"), outputs=[img, meta])
        trash.click(lambda: label_and_next("trash"), outputs=[img, meta])
        maybe.click(lambda: label_and_next("maybe"), outputs=[img, meta])
        save.click(save_labels, outputs=[status])

    demo.launch(allowed_paths=allowed_paths)
