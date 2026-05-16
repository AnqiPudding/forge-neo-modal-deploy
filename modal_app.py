import os
import shlex
import socket
import subprocess
import sys
import threading
import time
from pathlib import Path

import modal


APP_NAME = os.environ.get("MODAL_APP_NAME", "forge-neo")
IMAGE_NAME = os.environ.get("FORGE_NEO_IMAGE", "ghcr.io/anqipudding/forge-neo-modal-image:latest")
GPU_TYPE = os.environ.get("MODAL_GPU", "L40S")
VOLUME_NAME = os.environ.get("MODAL_VOLUME_NAME", f"{APP_NAME}-data")
JUPYTER_TOKEN = os.environ.get("JUPYTER_TOKEN", "forge-neo")
SCALEDOWN_WINDOW = int(os.environ.get("MODAL_SCALEDOWN_WINDOW", "120"))
MIN_CONTAINERS = int(os.environ.get("MODAL_MIN_CONTAINERS", "0"))

DATA_DIR = Path("/data")
FORGE_DIR = Path("/opt/forge-neo")
LOG_DIR = DATA_DIR / "logs"
FORGE_LOG = LOG_DIR / "forge.log"

volume = modal.Volume.from_name(VOLUME_NAME, create_if_missing=True, version=2)
image = modal.Image.from_registry(IMAGE_NAME, force_build=False)
app = modal.App(APP_NAME, image=image)

COMMON_ENV = {
    "MODAL_VOLUME_NAME": VOLUME_NAME,
    "FORGE_EXTRA_ARGS": os.environ.get("FORGE_EXTRA_ARGS", ""),
    "HF_HUB_ENABLE_HF_TRANSFER": "1",
    "GRADIO_ANALYTICS_ENABLED": "False",
    "GRADIO_TEMP_DIR": str(DATA_DIR / "tmp" / "gradio"),
    "PYTORCH_CUDA_ALLOC_CONF": "expandable_segments:True",
    "PYTHONUNBUFFERED": "1",
}


def wait_for_port(port: int, timeout: int, proc: subprocess.Popen | None = None) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if proc is not None and proc.poll() is not None:
            raise RuntimeError(
                f"Process exited before localhost:{port} opened with code {proc.returncode}.\n"
                f"Last Forge log lines:\n{tail_log(100)}"
            )
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(1)
            if sock.connect_ex(("127.0.0.1", port)) == 0:
                return
        time.sleep(1)
    raise TimeoutError(f"Timed out waiting for localhost:{port}.\nLast Forge log lines:\n{tail_log(100)}")


def tail_log(lines: int = 160) -> str:
    if not FORGE_LOG.exists():
        return f"{FORGE_LOG} does not exist yet."
    return "\n".join(FORGE_LOG.read_text(errors="replace").splitlines()[-lines:])


def keep_committing(interval_seconds: int = 30, reload_after_commit: bool = False) -> None:
    while True:
        time.sleep(interval_seconds)
        try:
            volume.commit()
            print("Committed Modal volume snapshot.", flush=True)
            if reload_after_commit:
                volume.reload()
                print("Reloaded Modal volume snapshot.", flush=True)
        except Exception as exc:
            print(f"Volume sync skipped: {exc}", flush=True)


def reload_volume(context: str) -> None:
    try:
        volume.reload()
        print(f"Reloaded Modal volume snapshot ({context}).", flush=True)
    except Exception as exc:
        print(f"Volume reload skipped ({context}): {exc}", flush=True)


def ensure_data_dirs() -> None:
    for path in (
        DATA_DIR / "models" / "Stable-diffusion",
        DATA_DIR / "models" / "Lora",
        DATA_DIR / "models" / "VAE",
        DATA_DIR / "models" / "embeddings",
        DATA_DIR / "models" / "adetailer",
        DATA_DIR / "output",
        DATA_DIR / "config",
        DATA_DIR / "notebooks",
        DATA_DIR / "tmp" / "gradio",
        LOG_DIR,
    ):
        path.mkdir(parents=True, exist_ok=True)


def patch_forge_volume_refresh() -> None:
    main_entry = FORGE_DIR / "modules_forge" / "main_entry.py"
    if not main_entry.exists():
        print(f"Could not patch model refresh; missing {main_entry}", flush=True)
        return

    text = main_entry.read_text()
    if "Modal volume refresh skipped" in text:
        return

    marker = "def refresh_models() -> tuple[list[os.PathLike], list[os.PathLike]]:\n"
    patch = """def refresh_models() -> tuple[list[os.PathLike], list[os.PathLike]]:
    try:
        import modal as _modal

        _volume_name = os.environ.get("MODAL_VOLUME_NAME")
        if _volume_name:
            _volume = _modal.Volume.from_name(_volume_name, create_if_missing=True, version=2)
            _volume.commit()
            _volume.reload()
    except Exception as exc:
        logger.warning(f"Modal volume refresh skipped: {exc}")

"""
    if marker not in text:
        print("Could not patch model refresh; refresh_models() was not found.", flush=True)
        return

    main_entry.write_text(text.replace(marker, patch, 1))
    print("Patched Forge model refresh for Modal volume reloads.", flush=True)


def startup_env(extra: dict[str, str] | None = None) -> dict[str, str]:
    env = os.environ.copy()
    env.update(COMMON_ENV)
    if extra:
        env.update(extra)
    return env


@app.function(
    image=image,
    volumes={str(DATA_DIR): volume},
    timeout=5 * 60,
)
def prepare() -> str:
    ensure_data_dirs()
    volume.commit()
    return f"Volume {VOLUME_NAME} is ready at {DATA_DIR}"


@app.function(
    image=image,
    volumes={str(DATA_DIR): volume},
    timeout=60,
)
def logs(lines: int = 160) -> str:
    return tail_log(lines)


@app.function(
    image=image,
    gpu=GPU_TYPE,
    volumes={str(DATA_DIR): volume},
    timeout=24 * 60 * 60,
    scaledown_window=SCALEDOWN_WINDOW,
    min_containers=MIN_CONTAINERS,
    max_containers=1,
    env=COMMON_ENV,
)
@modal.concurrent(max_inputs=100)
@modal.web_server(7860, startup_timeout=900, label="forge")
def forge() -> None:
    reload_volume("forge startup")
    ensure_data_dirs()
    patch_forge_volume_refresh()
    volume.commit()
    threading.Thread(
        target=keep_committing,
        kwargs={"interval_seconds": 30, "reload_after_commit": False},
        daemon=True,
    ).start()

    FORGE_LOG.parent.mkdir(parents=True, exist_ok=True)
    log = FORGE_LOG.open("ab", buffering=0)
    log.write(b"\n\n=== Starting Forge-Neo on Modal ===\n")

    cmd = ["start-forge", *shlex.split(os.environ.get("FORGE_EXTRA_ARGS", ""))]
    proc = subprocess.Popen(cmd, cwd=FORGE_DIR, env=startup_env(), stdout=log, stderr=subprocess.STDOUT)
    wait_for_port(7860, timeout=900, proc=proc)


@app.function(
    image=image,
    volumes={str(DATA_DIR): volume},
    timeout=24 * 60 * 60,
    scaledown_window=10 * 60,
    max_containers=1,
    env={**COMMON_ENV, "JUPYTER_TOKEN": JUPYTER_TOKEN},
)
@modal.concurrent(max_inputs=100)
@modal.web_server(8888, startup_timeout=180, label="jupyter")
def jupyter() -> None:
    reload_volume("jupyter startup")
    ensure_data_dirs()
    volume.commit()
    threading.Thread(target=keep_committing, kwargs={"interval_seconds": 30}, daemon=True).start()

    cmd = [
        "jupyter",
        "lab",
        "--ip=0.0.0.0",
        "--port=8888",
        "--no-browser",
        "--allow-root",
        "--ServerApp.root_dir=/data",
        f"--ServerApp.token={os.environ['JUPYTER_TOKEN']}",
        "--ServerApp.password=",
        "--ServerApp.allow_origin=*",
        "--ServerApp.trust_xheaders=True",
    ]
    proc = subprocess.Popen(cmd, cwd=DATA_DIR, env=startup_env({"JUPYTER_TOKEN": os.environ["JUPYTER_TOKEN"]}))
    wait_for_port(8888, timeout=180, proc=proc)


@app.local_entrypoint()
def main(show_logs: bool = False, lines: int = 160) -> None:
    if show_logs:
        print(logs.remote(lines))
        return
    print(prepare.remote())
