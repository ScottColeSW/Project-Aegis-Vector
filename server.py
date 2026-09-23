import json
import time
import asyncio
from pathlib import Path
from typing import Optional

import requests
from fastapi import FastAPI
from fastapi.responses import StreamingResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

OLLAMA_URL = "http://localhost:11434"
FRONTEND_DIR = Path(__file__).parent / "frontend"
HEARTBEAT_INTERVAL = 0.25  # seconds between "still working" pings during blocking calls

app = FastAPI(title="Aegis Vector Engine")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

class EvaluationRequest(BaseModel):
    query: str
    clean_doc: str
    poisoned_doc: str
    model: str = "llama3.1:8b"

# The scoring engine loads a SentenceTransformer on construction, so build it once and reuse it
_engine = None

def _load_engine():
    global _engine
    if _engine is None:
        from metrics import AegisScoringEngine  # heavy import (torch), deferred until first run
        _engine = AegisScoringEngine(ollama_base_url=OLLAMA_URL)
    return _engine

def _rag_prompt(context: str, query: str) -> str:
    return (
        "Answer the question using only the context below.\n\n"
        f"Context: {context}\n\n"
        f"Question: {query}"
    )

def sse(event_type: str, **fields) -> str:
    return f"data: {json.dumps({'type': event_type, **fields})}\n\n"

async def run_blocking(stage: str, fn, *args, **kwargs):
    """
    Runs a blocking call in a worker thread, yielding heartbeat events until it finishes.
    The final yielded item is ("result", value) or ("error", exception).
    """
    task = asyncio.create_task(asyncio.to_thread(fn, *args, **kwargs))
    start = time.perf_counter()
    while True:
        done, _ = await asyncio.wait({task}, timeout=HEARTBEAT_INTERVAL)
        if done:
            break
        yield sse("heartbeat", stage=stage, elapsed_ms=round((time.perf_counter() - start) * 1000))
    try:
        yield ("result", task.result())
    except Exception as e:
        yield ("error", e)

async def run_analysis_stream(payload: EvaluationRequest):
    """
    Yields step-by-step pipeline telemetry as Server-Sent Events (SSE).

    Event types:
      stage     - a pipeline stage changed state (running / done / error / skipped)
      heartbeat - a long-running stage is still working
      log       - human-readable console line
      result    - metric data for a finished stage
      progress  - overall completion, 0..1
      complete  - run finished, with total duration and summary
    """
    run_start = time.perf_counter()
    summary = {}
    stages = ["load", "embed", "logits_clean", "logits_poison"]

    def progress(stage_idx: int) -> str:
        return sse("progress", value=stage_idx / len(stages))

    yield sse("log", level="info", message=f"Run started, target model {payload.model}")

    # Stage 1: Embedding model load (slow on first run only)
    yield sse("stage", stage="load", state="running",
              message="Loading embedding model" if _engine is None else "Embedding model cached")
    stage_start = time.perf_counter()
    engine = None
    async for item in run_blocking("load", _load_engine):
        if isinstance(item, str):
            yield item
        elif item[0] == "result":
            engine = item[1]
        else:
            yield sse("stage", stage="load", state="error", message=str(item[1]))
            yield sse("log", level="error", message=f"Embedding model failed to load: {item[1]}")
    if engine is None:
        yield sse("complete", ok=False, total_ms=round((time.perf_counter() - run_start) * 1000), summary=summary)
        return
    yield sse("stage", stage="load", state="done", elapsed_ms=round((time.perf_counter() - stage_start) * 1000))
    yield progress(1)

    # Stage 2: Cosine Distance & Proximity Advantage
    yield sse("stage", stage="embed", state="running", message="Encoding query and documents")
    stage_start = time.perf_counter()
    async for item in run_blocking("embed", engine.compute_cosine_distance_shift,
                                   payload.query, payload.clean_doc, payload.poisoned_doc):
        if isinstance(item, str):
            yield item
        elif item[0] == "result":
            shift = item[1]
            summary["vector_shift"] = shift
            yield sse("result", stage="embed", data=shift)
            yield sse("stage", stage="embed", state="done",
                      elapsed_ms=round((time.perf_counter() - stage_start) * 1000))
            verdict = "closer to the query than the clean doc" if shift["is_vulnerable"] else "farther from the query than the clean doc"
            yield sse("log", level="warn" if shift["is_vulnerable"] else "ok",
                      message=f"Poisoned doc is {verdict} (advantage {shift['proximity_advantage']:+.4f})")
        else:
            yield sse("stage", stage="embed", state="error", message=str(item[1]))
            yield sse("log", level="error", message=f"Vector shift failed: {item[1]}")
    yield progress(2)

    # Stages 3 & 4: First-token refusal probability with clean vs poisoned context
    ollama_down = False
    for idx, (stage, doc, label) in enumerate([
        ("logits_clean", payload.clean_doc, "clean"),
        ("logits_poison", payload.poisoned_doc, "poisoned"),
    ], start=3):
        if ollama_down:
            yield sse("stage", stage=stage, state="skipped", message="Ollama unavailable")
            yield progress(idx)
            continue

        yield sse("stage", stage=stage, state="running",
                  message=f"Querying {payload.model} with {label} context")
        stage_start = time.perf_counter()
        async for item in run_blocking(stage, engine.compute_first_token_refusal_probability,
                                       _rag_prompt(doc, payload.query), model_name=payload.model):
            if isinstance(item, str):
                yield item
            elif item[0] == "result":
                result = item[1]
                summary[stage] = result
                yield sse("result", stage=stage, data=result)
                yield sse("stage", stage=stage, state="done",
                          elapsed_ms=round((time.perf_counter() - stage_start) * 1000))
                yield sse("log", level="info",
                          message=f"{label.capitalize()} context: top token '{result['top_1_token']}', "
                                  f"P(refusal) = {result['p_refusal'] * 100:.1f}%")
            else:
                ollama_down = True
                yield sse("stage", stage=stage, state="error", message=str(item[1]))
                yield sse("log", level="error", message=str(item[1]))
        yield progress(idx)

    total_ms = round((time.perf_counter() - run_start) * 1000)
    yield sse("log", level="warn" if ollama_down else "ok",
              message=f"Run finished in {total_ms / 1000:.1f}s" + (" with errors" if ollama_down else ""))
    yield sse("complete", ok=not ollama_down, total_ms=total_ms, summary=summary)

@app.post("/api/evaluate/stream")
async def evaluate_stream(payload: EvaluationRequest):
    return StreamingResponse(
        run_analysis_stream(payload),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )

@app.get("/api/models")
def list_models():
    """Lists local Ollama models so the dashboard can offer a target picker."""
    try:
        response = requests.get(f"{OLLAMA_URL}/api/tags", timeout=3)
        response.raise_for_status()
        names = [m["name"] for m in response.json().get("models", [])]
        return {"ok": True, "models": names}
    except Exception as e:
        return {"ok": False, "models": [], "error": str(e)}

@app.get("/")
def index():
    return FileResponse(FRONTEND_DIR / "index.html")
