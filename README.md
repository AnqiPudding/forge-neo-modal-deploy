# Forge-Neo on Modal

Deploy-only repo for Forge-Neo. It pulls the prebuilt image:

```text
ghcr.io/anqipudding/forge-neo-modal-deploy:latest
```

No Docker build files are needed here.

## Quick Start

1. Run `login_modal.bat` once to install the Modal client and connect this Windows user to Modal.
2. Run `deploy_l40s_and_open.bat`.
3. The batch file deploys the app on L40S, then opens:
   - Forge WebUI: `https://<workspace>--forge.modal.run`
   - JupyterLab: `https://<workspace>--jupyter.modal.run/lab?token=forge-neo`

## Persistent Volume

The Modal Volume is mounted at `/data`.

Put models in:

```text
/data/models/Stable-diffusion
/data/models/Lora
/data/models/VAE
/data/models/embeddings
/data/models/adetailer
```

Outputs are saved under:

```text
/data/output
```

JupyterLab uses `/data` as its root, so files downloaded from the Jupyter terminal are already in the attached volume. The app commits the volume periodically; after adding models, wait a short moment and click Forge's checkpoint/model refresh button so the patched refresh path reloads the volume.

Extensions are baked into the image and are not stored on the volume. Anything installed later through the Forge extensions UI is intentionally lost when the container scales down.

## Settings

Default environment values:

```text
MODAL_APP_NAME=forge-neo
MODAL_GPU=L40S
MODAL_VOLUME_NAME=forge-neo-data
FORGE_NEO_IMAGE=ghcr.io/anqipudding/forge-neo-modal-deploy:latest
JUPYTER_TOKEN=forge-neo
MODAL_SCALEDOWN_WINDOW=120
MODAL_MIN_CONTAINERS=0
```

Closing the Forge tab leaves the app deployed but lets the GPU container scale down after the idle window.
