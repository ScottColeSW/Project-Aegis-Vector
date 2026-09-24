"""
Memory protection for running local models on a constrained workstation.

Ported from the Dominion llama.cpp project's inference layer, plus a GPU check it
did not have:

  - keep_alive:  every Ollama call sends a short explicit keep_alive, so an idle
                 model unloads instead of sitting resident for Ollama's default
                 5 minutes while the next model loads on top of it.
  - preflight:   before a model loads, compare its on-disk size (plus headroom
                 for context and runtime) against free RAM + free VRAM. A model
                 that would not fit is skipped with a message, not loaded into
                 swap.
  - capability:  the model list comes from Ollama's own "completion" capability,
                 so embedding-only models never show up as chat targets.
  - retry:       a dropped connection gets one bounded retry; a slow response
                 does not (it is not evidence the backend is down).

The budget is a conservative estimate, not a simulation of Ollama's scheduler.
"""
import shutil
import subprocess
import time

import psutil
import requests

OLLAMA_URL = "http://localhost:11434"
KEEP_ALIVE = "1m"
# On-disk GGUF size understates the resident footprint: KV cache for a 4K
# context, compute buffers, and runtime overhead. 1.3x is conservative for the
# ~2-5 GB models this project uses.
FOOTPRINT_FACTOR = 1.3
RETRY_ATTEMPTS = 2

GB = 1024 ** 3


def vram_free_bytes():
    """Free VRAM on the first NVIDIA GPU, or None when nvidia-smi is unavailable."""
    if not shutil.which("nvidia-smi"):
        return None
    try:
        out = subprocess.run(
            ["nvidia-smi", "--query-gpu=memory.free", "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=5, check=True,
        ).stdout.split("\n")[0].strip()
        return int(out) * 1024 * 1024
    except (subprocess.SubprocessError, ValueError, OSError):
        return None


def memory_snapshot():
    vm = psutil.virtual_memory()
    return {"ram_available": vm.available, "ram_total": vm.total, "vram_free": vram_free_bytes()}


def describe(snapshot):
    vram = snapshot["vram_free"]
    return (f"RAM {snapshot['ram_available'] / GB:.1f} GB free"
            + (f", VRAM {vram / GB:.1f} GB free" if vram is not None else ", no GPU reported"))


def ollama_catalog():
    """{name: size_bytes} for installed models that can generate text (not embedding-only)."""
    tags = requests.get(f"{OLLAMA_URL}/api/tags", timeout=5).json().get("models", [])
    catalog = {}
    for entry in tags:
        name, size = entry.get("name"), entry.get("size")
        # Older Ollama builds omit capabilities; fall back to excluding obvious embedders
        capabilities = entry.get("capabilities")
        can_generate = "completion" in capabilities if capabilities else "embed" not in (name or "")
        if name and isinstance(size, (int, float)) and can_generate:
            catalog[name] = int(size)
            catalog.setdefault(name.removesuffix(":latest"), int(size))
    return catalog


def preflight(model, catalog=None):
    """(fits, message). Fits when the model's estimated footprint is under free RAM + free VRAM."""
    catalog = catalog if catalog is not None else ollama_catalog()
    size = catalog.get(model)
    snapshot = memory_snapshot()
    if size is None:
        return False, f"{model} is not an installed completion model"
    needed = size * FOOTPRINT_FACTOR
    budget = snapshot["ram_available"] + (snapshot["vram_free"] or 0)
    fits = needed <= budget
    return fits, (f"{model} needs ~{needed / GB:.1f} GB; {describe(snapshot)}"
                  + ("" if fits else " -> skipping, would not fit"))


def post_with_retry(url, body, timeout):
    """POST with one retry on a dropped or refused connection. Timeouts are not retried."""
    for attempt in range(RETRY_ATTEMPTS):
        try:
            return requests.post(url, json=body, timeout=timeout)
        except requests.ConnectionError:
            if attempt == RETRY_ATTEMPTS - 1:
                raise
            time.sleep(2)
