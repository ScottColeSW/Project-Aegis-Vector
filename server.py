import json
import asyncio
from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

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

async def run_analysis_stream(payload: EvaluationRequest):
    """
    Yields step-by-step pipeline telemetry as Server-Sent Events (SSE).
    """
    # Step 1: Ingestion & Vector Encoding Event
    yield f"data: {json.dumps({'step': 'EMBEDDING', 'status': 'encoding_vectors', 'progress': 0.25})}\n\n"
    await asyncio.sleep(0.3)  # Simulating async vector calculation

    # Step 2: Cosine Distance & Proximity Advantage calculation
    # (Hook into your AegisScoringEngine math here)
    delta_phi_clean = 0.42
    delta_phi_poison = 0.18
    proximity_adv = delta_phi_clean - delta_phi_poison
    
    yield f"data: {json.dumps({'step': 'VECTOR_SHIFT', 'data': {'delta_phi_clean': delta_phi_clean, 'delta_phi_poison': delta_phi_poison, 'proximity_advantage': proximity_adv}, 'progress': 0.50})}\n\n"
    await asyncio.sleep(0.3)

    # Step 3: First-Token Logit / Refusal Probability Extraction
    # (Hook into Ollama / api/generate logprobs endpoint here)
    p_refusal = 0.87
    top_tokens = {"I": 0.45, "Sorry": 0.32, "Sure": 0.12, "Here": 0.08}
    
    yield f"data: {json.dumps({'step': 'LOGIT_EVAL', 'data': {'p_refusal': p_refusal, 'top_tokens': top_tokens}, 'progress': 0.75})}\n\n"
    await asyncio.sleep(0.3)

    # Step 4: Final Payload Output
    yield f"data: {json.dumps({'step': 'COMPLETE', 'status': 'done', 'progress': 1.00})}\n\n"

@app.post("/api/evaluate/stream")
async def evaluate_stream(payload: EvaluationRequest):
    return StreamingResponse(
        run_analysis_stream(payload), 
        media_type="text/event-stream"
    )