# ManimGX PoC — 1,000-cell paired-flip grid

This scene is deliberately synthetic. It tests import, scene construction, grid layout, text, 1,000 objects, color transitions, `inspect`, and both target render modes. It is not a SliceAudit result.

## Environment

Use a separate Python 3.13 environment so ManimGX remains optional and outside the statistical core:

```powershell
uv venv --python 3.13 .venv-render
.venv-render\Scripts\activate
uv pip install manimgx==0.1.1
```

On Linux/macOS, activate with `source .venv-render/bin/activate`.

## Run

```powershell
manimgx inspect scene.py
manimgx render scene.py -r 1280x720 --fps 30
manimgx render scene.py -r 1920x1080 --fps 60
```

Record command exit codes, render wall time, peak RAM, generated video size, and any layout warnings in `RESULTS.md`. Run the 720p30 render first. Do not claim RTX 4060 GPU acceleration unless the renderer explicitly reports using that GPU; test CPU and GPU paths separately if the CLI exposes them.

## Acceptance checklist

- [ ] import succeeds on Python 3.13
- [ ] `inspect` exits 0 and reports no layout issues
- [ ] 720p30 render exits 0
- [ ] 1080p60 render exits 0
- [ ] all 1,000 cells are visible and not clipped
- [ ] green corrected and red broken groups are distinguishable
- [ ] fixture label remains visible: `SYNTHETIC FIXTURE`
- [ ] wall time, peak RAM, output size, OS, CPU/GPU path, and exact ManimGX version recorded
