# Installation Guide — photo-ai-workflow

This guide walks you through installing photo-ai-workflow from scratch on Windows, macOS, or Linux. The pipeline has two major external dependencies — **CLIP** (included via PyTorch/Transformers) and **Ollama** (for optional AI review) — which must be set up correctly.

## Prerequisites

### System Requirements
- **Python 3.10 or later** (check with `python --version`)
- **2 GB RAM minimum** (4+ GB recommended for Stage 2 CLIP scoring)
- **GPU optional** — CPU is fine; GPU speeds up Stage 2 by 5–10×
  - NVIDIA GPUs: CUDA 11.8 or later
  - Apple Silicon: Metal acceleration is automatic
  - AMD: Consider ROCm if you need acceleration

### Disk Space
- ~1 GB for dependencies (PyTorch, transformers, Ollama models)
- 100 MB for the photo_ai_workflow package itself
- 1–2 GB temporary during CLIP model download

---

## Step 1: Install Ollama (Required for Stage 3 AI Review)

Ollama is an LLM runtime that runs inference locally. It powers the optional Stage 3 AI review feature (eyes-closed detection, composition analysis, etc.).

### Windows

1. Download the Windows installer from [ollama.ai](https://ollama.ai)
2. Run the installer and follow the prompts
3. Ollama will auto-start on port 7869
4. Open PowerShell and verify the installation:
   ```powershell
   ollama --version
   ```

### macOS

1. Download from [ollama.ai](https://ollama.ai)
2. Open the `.dmg` and drag to Applications
3. Run Ollama from Launchpad or terminal
4. Verify:
   ```bash
   ollama --version
   ```

### Linux

```bash
curl https://ollama.ai/install.sh | sh
ollama --version
```

---

## Step 2: Pull the LLaVA Model (Required for Stage 3)

LLaVA is the vision-language model used in Stage 3 for photo review. Download it now so it's ready when you run the pipeline.

```powershell
# Windows PowerShell
ollama pull llava

# macOS / Linux
ollama pull llava
```

This downloads ~5 GB and takes 2–5 minutes depending on your connection.

**Verify the model is available:**
```powershell
ollama list
```

You should see `llava:latest` in the output.

---

## Step 3: Verify Ollama is Running

Ollama runs as a background service.

### Windows  
Ollama should start automatically at login. If not:
```powershell
# Start from terminal
ollama serve
```

### macOS / Linux  
```bash
# Keep running in terminal during pipeline execution
ollama serve
```

**Test the connection:**
```powershell
# From a new terminal/PowerShell
Invoke-WebRequest http://localhost:11434 -UseBasicParsing
```

You should get a 200 response.

---

## Step 4: Clone or Extract the Repository

```powershell
# Clone (if using Git)
git clone https://github.com/your-repo/photo-ai-workflow.git
cd photo-ai-workflow

# ... or extract the ZIP and navigate to the folder
cd photo_ai_workflow
```

---

## Step 5: Create a Python Virtual Environment (Recommended)

Isolates dependencies from your system Python.

### Windows

```powershell
# Create venv
python -m venv venv

# Activate it
.\venv\Scripts\Activate.ps1

# If you get an execution policy error:
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### macOS / Linux

```bash
python3 -m venv venv
source venv/bin/activate
```

---

## Step 6: Install PyTorch

PyTorch is large (~2 GB). Choose your platform:

### CPU Only (Recommended for First Try)

```powershell
pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu
```

### NVIDIA CUDA (GPU)

```powershell
# CUDA 12.1
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu121

# CUDA 11.8
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu118
```

Check your CUDA version with `nvidia-smi` if you have an NVIDIA GPU.

### Apple Metal (GPU)

```bash
pip install torch torchvision
```

Metal acceleration is automatic on Apple Silicon.

---

## Step 7: Install photo-ai-workflow and Dependencies

```powershell
# Install the package in editable mode
pip install -e .

# Verify installation
pip list | grep -i photo
python -c "import photo_ai_workflow; print('OK')"
```

---

## Step 8: Set Up Environment Secrets (Optional — Only for OpenAI Stage 3)

If you want to use OpenAI's GPT-4V instead of Ollama for Stage 3:

```powershell
# Copy the example
copy .env.example .env

# Edit .env and add your API key
# OPENAI_API_KEY=sk-...
```

If you skip this and use `--provider ollama`, secrets are not needed.

---

## Verification Checklist

Before running the pipeline, verify each component:

| Component | Test Command | Expected Output |
|-----------|--------------|-----------------|
| Python | `python --version` | 3.10 or later |
| PyTorch | `python -c "import torch; print(torch.__version__)"` | 2.6+ |
| Transformers | `python -c "import transformers; print(transformers.__version__)"` | 4.45+ |
| Ollama | `ollama --version` | Ollama version X.X.X |
| LLaVA Model | `ollama list` | Should show `llava:latest` |
| Ollama Service | `Invoke-WebRequest http://localhost:11434 -UseBasicParsing` | StatusCode 200 |
| photo-ai-workflow | `python -m photo_ai_workflow.cli --help` | Usage help printed |

---

## Quick Test Run

Once everything is installed, test the pipeline with a small folder of images:

```powershell
# Create a test folder with 5–10 images
mkdir C:\test_images
# Copy some JPEGs into C:\test_images

# Run the pipeline
python -m photo_ai_workflow.cli run `
  --input-dir "C:\test_images" `
  --output-dir "C:\test_images\workflow_outputs" `
  --provider ollama `
  --stage3-max-images 5 `
  --log-level INFO
```

Expected time: 2–5 minutes for ~10 images (depending on CPU/GPU).

---

## Troubleshooting

### "ModuleNotFoundError: No module named 'photo_ai_workflow'"

- Confirm you ran `pip install -e .` from the `photo_ai_workflow` folder
- Confirm your virtual environment is activated

### "ConnectionRefusedError: [Errno 111] Connection refused" — Ollama not running

- Start Ollama: `ollama serve` (Windows) or `ollama serve` (macOS/Linux)
- On Windows, check Services to see if Ollama is running as a background service
- Test connection: `Invoke-WebRequest http://localhost:11434`

### "Model 'llava' not found in Ollama"

- Run `ollama pull llava` and wait for download to complete
- Verify with `ollama list`

### "CLIP model download fails / transformers error"

- Check internet connection
- Try with CPU-only PyTorch first: `pip install torch --index-url https://download.pytorch.org/whl/cpu`
- Manually cache the model:
  ```powershell
  python -c "from transformers import CLIPProcessor, CLIPModel; m = CLIPModel.from_pretrained('openai/clip-vit-base-patch32'); print('OK')"
  ```

### "Out of memory" during Stage 2 (CLIP scoring)

- Reduce batch size in code if processing many images
- Lower `--aesthetic-threshold` to reduce images passed to Stage 3
- Use GPU version of PyTorch if available

### Stage 3 hangs or times out

- Ensure Ollama is still running: `ollama serve` in a separate terminal
- Check logs for timeout errors
- Set `--stage3-max-images 10` to test with fewer images
- If using OpenAI, verify `OPENAI_API_KEY` is set in `.env`

### "No module named 'photo_ai_workflow.cli'"

- Verify the package installed: `pip list`
- Try reinstalling: `pip install -e . --force-reinstall`

---

## Next Steps

- Read [README.md](README.md) for detailed pipeline documentation
- See [CONTRIBUTING.md](CONTRIBUTING.md) if you want to modify or extend the pipeline
- Run `python -m photo_ai_workflow.cli --help` for full CLI options

---

## Need Help?

- Open a GitHub Issue with your OS, Python version, and the exact command that failed
- Include the full error output from `--log-level DEBUG`
