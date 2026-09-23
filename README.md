# Aegis Vector: Quantitative Adversarial Evaluation & Visualization Engine

> **Empirical safety evaluation for enterprise AI systems.** Aegis Vector replaces qualitative "vibes-based" red-teaming with hard mathematical metrics, tracking vector manifold distortion, logit probability shifts, and token perplexity in local environments.

---

## Overview

Enterprise adoption of Large Language Models (LLMs) and Retrieval-Augmented Generation (RAG) assumes that safety alignment (e.g., RLHF, DPO) and semantic vector search provide robust boundaries against unauthorized actions. **Aegis Vector** provides a zero-leakage, locally containerized testbed designed to prove where and why these assumptions fail.

Rather than relying on binary pass/fail checks, Aegis Vector captures continuous statistical metrics—including **First-Token Refusal Probabilities ($P_{\text{refusal}}$)**, **Cosine Distance Shifts ($\Delta \Phi$)**, **Attacker Retrieval Probabilities (ARP)**, and **Token Perplexity (PPL)**—to observe the exact tipping points where safety guardrails collapse.

---

## Core Use Cases

Aegis Vector is engineered for AI safety researchers, security teams, and system architects who need to quantify and mitigate vulnerabilities across five primary operational scenarios:

### 1. Indirect RAG Poisoning & Retrieval Hijacking

* **Scenario:** An attacker embeds covert instructions inside benign documents, web scrapes, or user submissions ingested into an enterprise vector database.
* **Objective:** Quantify how easily an adversarial payload acts as a "vector gravity well" to hijack semantic search queries without altering the global document cluster distribution.
* **Key Metrics:** Cosine Distance Shift ($\Delta \Phi$), Attacker Retrieval Probability (ARP), Top-$k$ Hit Rate.

### 2. Guardrail Tipping-Point & Logit Analysis

* **Scenario:** Measuring model response stability at generation step $T_1$ when exposed to high-entropy contexts, roleplay wrapping, or soft-prompting.
* **Objective:** Track the exact mathematical decay of refusal tokens (e.g., `"I cannot"`, `"As an AI"`) down to $P_{\text{refusal}} < 1\%$ to prove where alignment breaks before harmful text is fully generated.
* **Key Metrics:** First-Token Refusal Probability ($P_{\text{refusal}}$), Top-10 Softmax Logit Distribution.

### 3. Stealth Profiling & Filter Bypassing

* **Scenario:** Evaluating whether adversarial payloads can bypass static security filters, anomaly detectors, or input inspection tools.
* **Objective:** Measure auto-regressive token perplexity (PPL) against reference models to ensure attacks maintain linguistic naturalness while executing payload objectives.
* **Key Metrics:** Token Perplexity (PPL), Attacker Control Ratio (ACR).

### 4. Multi-Agent Cross-Domain Injection

* **Scenario:** Assessing autonomous agent workflows where retrieved data is fed into secondary tool-calling or decision-making modules.
* **Objective:** Measure how indirect prompt injections force agents into executing unauthorized actions (e.g., modifying database records, overriding workflow boundaries).
* **Key Metrics:** Action Execution Rate, Attacker Control Ratio (ACR).

### 5. Interactive Visual Demonstrations for Leadership & Audit

* **Scenario:** Communicating complex technical vulnerabilities to C-suite executives, boards, or compliance auditors.
* **Objective:** Render real-time 3D vector space manifolds (PCA/t-SNE) and live logit shift distributions to visually demonstrate how semantic search and generative models can be manipulated.
* **Key Visuals:** 3D Geometric Vector Manifold, $T_1$ Logit Probability Bar Charts, ARP vs. Stealth Heatmaps.

---

## Key Metrics Framework

| Metric | Scientific Basis | Target Outcome |
| --- | --- | --- |
| **First-Token Refusal Probability ($P_{\text{refusal}}$)** | Normalized softmax sum over refusal tokens at $T_1$ | Quantifies exact alignment tipping point ($P < 0.01$) |
| **Vector Space Shift ($\Delta \Phi$)** | Cosine distance delta in embedding space | Identifies stealthy geometric positioning |
| **Attacker Retrieval Probability (ARP)** | Reciprocal rank / Top-$k$ query hit rate | Measures retrieval hijacking efficacy |
| **Token Perplexity (PPL)** | Auto-regressive cross-entropy loss | Evaluates detection probability by input filters |
| **Attacker Control Ratio (ACR)** | Normalized Levenshtein distance / Semantic match | Measures output fidelity to attacker payload |

---

## Architecture & Tech Stack

Aegis Vector runs entirely on local infrastructure with zero external API dependencies:

* **Inference Engine:** Local [Ollama](https://ollama.ai/?utm_source=gemini) running open-weights targets (`llama3.1`, `qwen2.5`, `mistral`).
* **Vector Database:** Local [Qdrant](https://qdrant.tech/?utm_source=gemini) or [ChromaDB](https://www.trychroma.com/?utm_source=gemini).
* **Embeddings Backend:** Local Sentence-Transformers (`BAAI/bge-small-en-v1.5`, `nomic-embed-text`).
* **Analytics Engine:** PyTorch, NumPy, and SciPy for probability distributions and dimensionality reduction.
* **Dashboard Suite:** Streamlit and Plotly 3D for real-time visualization.

---

## Quickstart

### Prerequisites

* Python 3.11+
* Docker & Docker Compose
* Local Ollama instance running with logprob access enabled

```bash
# 1. Clone repository
git clone https://github.com/your-org/aegis-vector.git
cd aegis-vector

# 2. Set up virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt

# 3. Start local vector store
docker-compose up -d qdrant

# 4. Launch the Aegis Vector Analytics Dashboard
streamlit run app.py

```

---

## License

This project is licensed under the MIT License - see the [LICENSE](https://www.google.com/search?q=LICENSE&utm_source=gemini) file for details.

---
