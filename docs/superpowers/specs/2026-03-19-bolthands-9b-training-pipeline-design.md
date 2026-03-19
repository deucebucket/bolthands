# BoltHands 9B Training Pipeline — Design Spec

**Date:** 2026-03-19
**Goal:** Build the complete data pipeline and training tooling to fine-tune Qwen 3.5 9B into an all-purpose, abliterated, tool-calling model via Unsloth QLoRA.

---

## Scope

A unified LoRA adapter (rank 64) trained on ~150K+ examples across all domains the user interacts with daily. The pipeline produces training data, validates it, trains the model, exports to GGUF, and evaluates the result.

## Domains (20)

| # | Domain | Tool Prefix | Key Operations |
|---|--------|-------------|----------------|
| 1 | Core | `bash`, `file_*`, `web_*` | Shell, files, web search/fetch |
| 2 | Windows/PowerShell | `win.*` | WinRM, services, updates, registry, event logs, users |
| 3 | Plex | `plex.*` | Library, playback, collections, playlists, maintenance |
| 4 | Sonarr | `sonarr.*` | Series, episodes, calendar, queue, search |
| 5 | Radarr | `radarr.*` | Movies, queue, search |
| 6 | Lidarr | `lidarr.*` | Artists, albums, search |
| 7 | Prowlarr | `prowlarr.*` | Indexers, search, app status |
| 8 | OpenClaw | `openclaw.*` | Agent routing, personality, delegation |
| 9 | Systemd | `systemd.*` | Unit management, journal, timers |
| 10 | Flipper Zero | `flipper.*` | BadUSB, IR, NFC, Sub-GHz, Amiibo, GPIO |
| 11 | ComfyUI/SwarmUI | `comfyui.*` | Workflows, image gen, video gen, LoRA selection |
| 12 | GPT-SoVITS | `tts.*` | Voice synthesis, reference audio, model selection |
| 13 | F5-TTS | `f5tts.*` | Voice cloning, narration generation |
| 14 | RVC/Applio | `rvc.*` | Voice conversion, model training, inference |
| 15 | ACE-Step | `music.*` | Music generation, style control |
| 16 | llama.cpp | `llm.*` | Model swap, server status, LoRA hot-swap |
| 17 | AI Dashboard | `dashboard.*` | Service start/stop, GPU monitoring |
| 18 | Mantella | `mantella.*` | NPC AI config, server control |
| 19 | Steam/Gaming | `steam.*` | Mod management, launch options |
| 20 | Tailscale | `tailscale.*` | Network status, device management |

## Architecture

```
data/
├── schemas/           # Tool JSON schemas (source of truth)
│   ├── core.json
│   ├── windows.json
│   ├── plex.json
│   ├── arr.json       # sonarr + radarr + lidarr + prowlarr
│   ├── openclaw.json
│   ├── systemd.json
│   ├── flipper.json
│   ├── comfyui.json
│   ├── tts.json       # gpt-sovits + f5-tts
│   ├── rvc.json
│   ├── music.json     # ace-step
│   ├── llm.json       # llama.cpp management
│   ├── dashboard.json
│   ├── mantella.json
│   ├── steam.json
│   └── tailscale.json
├── converters/        # HF dataset → ChatML converters
│   ├── base.py        # Base converter with ChatML formatting
│   ├── hermes.py
│   ├── xlam.py
│   ├── glaive.py
│   └── nemotron.py
├── generators/        # Synthetic data generators
│   ├── base.py        # Base: loads schema, generates via LLM or templates
│   ├── windows.py
│   ├── plex.py
│   ├── arr.py
│   ├── openclaw.py
│   ├── systemd.py
│   ├── flipper.py
│   ├── comfyui.py
│   ├── tts.py
│   ├── rvc.py
│   ├── music.py
│   ├── llm_mgmt.py
│   ├── dashboard.py
│   ├── mantella.py
│   ├── steam.py
│   ├── tailscale.py
│   └── cross_domain.py
├── validator.py       # JSON syntax, schema compliance, dedup
├── mixer.py           # Domain ratio balancing + anti-forgetting
└── pipeline.py        # Orchestrates: download → convert → generate → validate → mix
```

## Data Format

All output is Qwen 3.5 ChatML with Hermes-style tool calling:

```
<|im_start|>system
You are BoltHands, an all-purpose AI assistant.
<tools>[...tool schemas...]</tools>
<|im_end|>
<|im_start|>user
{request}
<|im_end|>
<|im_start|>assistant
{reasoning}
<tool_call>
{"name": "tool.name", "arguments": {...}}
</tool_call>
<|im_end|>
<|im_start|>tool
<tool_response>
{"name": "tool.name", "content": {...}}
</tool_response>
<|im_end|>
<|im_start|>assistant
{natural language summary of result}
<|im_end|>
```

## Training Data Mix

| Source | Examples | Purpose |
|--------|----------|---------|
| HF datasets (converted) | ~45K | Base function calling |
| Synthetic per-domain | ~100K | Domain-specific tool calling |
| Cross-domain synthetic | ~10K | Multi-service workflows |
| General conversation | ~10K | Anti-forgetting |
| **Total** | **~165K** | |

## Training Config

- **Base:** Qwen 3.5 9B (unsloth/Qwen3.5-9B)
- **Method:** QLoRA (4-bit NF4)
- **LoRA:** rank 64, alpha 128, all 7 linear module types
- **Epochs:** 3
- **Seq length:** 4096
- **Batch:** 2 × 8 accumulation = effective 16
- **LR:** 2e-4 cosine with 5% warmup
- **Hardware:** RTX 3090 24GB via distrobox "ai"
- **Tool:** `unsloth train -c training/config.yaml`
- **Export:** GGUF Q4_K_M + Q5_K_M

## Evaluation

1. **Tool call accuracy** — valid JSON, correct tool name, valid args
2. **Cross-domain** — multi-service workflow scenarios
3. **Regression** — general chat and coding ability preserved
4. **A/B comparison** — base Qwen3.5-9B vs fine-tuned on same prompts

## Testing Strategy

Tests mock at the LLM boundary (no actual model needed):
- Converter tests: feed sample HF data, verify ChatML output format
- Generator tests: mock LLM responses, verify scenario templates produce valid data
- Validator tests: feed good/bad examples, verify accept/reject
- Mixer tests: verify domain ratios and shuffling
- Integration: run full pipeline on small sample data
