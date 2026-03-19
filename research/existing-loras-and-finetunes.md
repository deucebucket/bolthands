# Existing LoRAs and Fine-Tunes for Qwen 9B Variants

Research date: 2026-03-18

This document catalogs existing LoRA adapters, full fine-tunes, and relevant training datasets for Qwen 3.5 9B (and compatible Qwen 2.5/3 variants) found on HuggingFace. There are currently **57 adapter models** listed for Qwen3.5-9B on the HuggingFace hub.

---

## 1. Agentic Coding

### Tesslate/OmniCoder-9B (TOP PICK)
- **URL**: https://huggingface.co/Tesslate/OmniCoder-9B
- **GGUF**: https://huggingface.co/Tesslate/OmniCoder-9B-GGUF
- **Type**: LoRA SFT (r=64, alpha=32), merged into full model
- **Base**: Qwen3.5-9B
- **Training data**: 425,000+ curated agentic coding trajectories from Claude Opus 4.6, GPT-5.4, GPT-5.3-Codex, Gemini 3.1 Pro. Scaffolding patterns from Claude Code, OpenCode, Codex, Droid.
- **Capabilities added**:
  - Error recovery (read-before-write patterns, LSP diagnostics)
  - Efficient editing (minimal diffs instead of full rewrites)
  - Thinking mode (`<think>...</think>` chains)
  - Real-world agentic coding behavior
- **Benchmarks**:
  - GPQA Diamond pass@1: 83.8% (+2.1 vs base)
  - AIME 2025 pass@5: 90%
  - Terminal-Bench 2.0: 23.6% (+61% improvement vs base)
- **Compatibility**: Qwen3.5-9B native
- **License**: Apache 2.0
- **Downloads**: ~8,700/month
- **Verdict**: Best agentic coding fine-tune available for 9B. Directly trained on agent trajectories.

---

## 2. Tool Calling / Function Calling

### Vikhrmodels/Qwen2.5-7B-Instruct-Tool-Planning-v0.1
- **URL**: https://huggingface.co/Vikhrmodels/Qwen2.5-7B-Instruct-Tool-Planning-v0.1
- **Type**: Full fine-tune (SFT)
- **Base**: Qwen2.5-7B-Instruct
- **Training data**: [Vikhrmodels/tool-plannings-v0.1](https://huggingface.co/datasets/Vikhrmodels/tool-plannings-v0.1) - 10.5k synthetic samples
- **Capabilities added**:
  - Tool Planning with reasoning (`<|start_thinking|>...<|end_thinking|>` tokens)
  - Simple, multiple, parallel, and parallel-multiple function calling
  - Tool relevance detection (knows when NOT to call tools)
  - Tool error handling
- **Benchmarks**:
  - Simple: 73.25%, Multiple: 93.00%, Parallel: 90.00%
  - Parallel Multiple: 81.00%, Relevance Detection: 64.71%
- **Compatibility**: Qwen2.5-7B only (NOT directly compatible with Qwen3.5-9B architecture)
- **License**: Apache 2.0
- **Verdict**: Interesting approach but built on older Qwen2.5 architecture. The dataset is reusable.

### Salesforce xLAM Function Calling (Dataset + Models)
- **Dataset URL**: https://huggingface.co/datasets/Salesforce/xlam-function-calling-60k
- **Type**: Training dataset (60k verified function-calling examples)
- **Details**: 3,673 executable APIs across 21 categories, 95%+ human-evaluated correctness
- **Format**: JSON with query/tools/answers structure
- **License**: CC-BY-4.0
- **Pre-trained models**: xLAM-7b-fc-r (#3 on Berkeley FCL, 88.24%), xLAM-1b-fc-r (#25, 78.94%)
- **Existing Qwen fine-tune**: [ermiaazarkhalili/Qwen2.5-14B-Instruct_Function_Calling_xLAM](https://huggingface.co/ermiaazarkhalili/Qwen2.5-14B-Instruct_Function_Calling_xLAM) (14B, not 9B)
- **Verdict**: Excellent dataset for DIY function-calling fine-tuning on Qwen3.5-9B. No existing 9B fine-tune found.

### Note on Base Qwen3.5-9B
Qwen3.5-9B already has native tool calling support via Qwen-Agent. Use the `qwen3_coder` tool-call parser with SGLang. Consider fine-tuning only if base performance is insufficient.

---

## 3. Sysadmin / DevOps / Shell Commands

### lakhera2023/devops-slm-v1
- **URL**: https://huggingface.co/lakhera2023/devops-slm-v1
- **Type**: LoRA fine-tune
- **Base**: lakhera2023/Qwen-model (custom Qwen variant)
- **Capabilities**: Kubernetes, Docker, CI/CD (GitHub Actions, GitLab CI, Jenkins), Terraform, Ansible, monitoring (Prometheus, Grafana, ELK)
- **Limitation**: DevOps-only filter (refuses non-DevOps questions)
- **Compatibility**: Unknown base Qwen version, likely NOT directly compatible with Qwen3.5-9B
- **Verdict**: Niche. Shows concept is viable but not a production-ready adapter for Qwen3.5-9B.

### Zest (Command Line Assistant)
- **URL**: Mentioned in HuggingFace forums (https://discuss.huggingface.co/t/zest-a-fine-tuned-a-small-qwen-model-to-work-as-a-command-line-assistant/174088)
- **Type**: Fine-tuned small Qwen model for shell command generation
- **Details**: Translates natural language to CLI commands, runs fully locally
- **Verdict**: Concept reference. No PowerShell/sysadmin-specific LoRA found for Qwen 9B.

### Gap Assessment
**No dedicated sysadmin/PowerShell/bash LoRA exists for Qwen 9B variants.** This is a gap that could be filled with custom training.

---

## 4. API Interaction

### Gap Assessment
**No dedicated REST API interaction LoRA found for Qwen 9B.** The closest options are:
- Salesforce xLAM dataset (covers API calling patterns, could be used for DIY training)
- OmniCoder-9B (includes some tool-use patterns but focused on coding agents)
- Base Qwen3.5-9B already handles API calling reasonably well via native tool support

---

## 5. Abliterated / Uncensored Variants

### huihui-ai/Huihui-Qwen3.5-9B-abliterated (RECOMMENDED)
- **URL**: https://huggingface.co/huihui-ai/Huihui-Qwen3.5-9B-abliterated
- **GGUF**: https://huggingface.co/Abhiray/Huihui-Qwen3.5-9B-abliterated-GGUF
- **Type**: Abliterated (orthogonal projection + LoRA fine-tune)
- **Method**: Two-stage: 3 iterative passes of orthogonal projection, then LoRA fine-tuning on stubborn refusal categories
- **Result**: 18/18 test prompts answered (0/18 on base)
- **Downloads**: ~16,900/month (most popular abliterated variant)
- **Compatibility**: Qwen3.5-9B native
- **License**: Apache 2.0
- **Verdict**: Most thorough abliteration. Two-stage approach is more reliable than single-pass methods.

### HauhauCS/Qwen3.5-9B-Uncensored-HauhauCS-Aggressive
- **URL**: https://huggingface.co/HauhauCS/Qwen3.5-9B-Uncensored-HauhauCS-Aggressive
- **Type**: Uncensored (method not detailed, described as "lossless")
- **Result**: 0/465 refusals, claims zero capability loss
- **Formats**: BF16 (17GB), Q8_0 (8.9GB), Q6_K (6.9GB), Q4_K_M (5.3GB)
- **Compatibility**: Qwen3.5-9B native, multimodal (text/image/video)
- **Verdict**: Most aggressive uncensoring. Zero refusals. May occasionally append disclaimers.

### lukey03/Qwen3.5-9B-abliterated
- **URL**: https://huggingface.co/lukey03/Qwen3.5-9B-abliterated
- **GGUF**: https://huggingface.co/lukey03/Qwen3.5-9B-abliterated-GGUF
- **Type**: Abliterated (3 passes orthogonal projection + QLoRA fine-tune)
- **Method**: Custom script adapted for Qwen3.5 hybrid DeltaNet/Attention architecture
- **Result**: 18/18 test prompts answered
- **GGUF note**: Replaces 400 text tensors with abliterated weights, keeps 441 vision + 15 MTP tensors from official model
- **Verdict**: Good alternative with proper vision support in GGUF.

### jwest33/qwen3.5-9b-null-space-abliterated-GGUF
- **URL**: https://huggingface.co/jwest33/qwen3.5-9b-null-space-abliterated-GGUF
- **Type**: Null-space abliteration (advanced method)
- **Method**: Winsorization (99th percentile clipping), null-space projection to preserve capabilities, adaptive Gaussian-weighted per-layer ablation (focused on middle-to-later layers), Frobenius norm preservation
- **Status**: v20260303 marked as "low quality" with more versions planned
- **Quants**: Q6_K (7.36GB), Q8_0 (9.53GB)
- **Verdict**: Most technically sophisticated method but still experimental. Based on AlphaEdit research.

### trohrbaugh/Qwen3.5-9B-heretic-v2
- **URL**: https://huggingface.co/trohrbaugh/Qwen3.5-9B-heretic-v2
- **GGUF**: https://huggingface.co/AIImageStudio/Qwen3.5-9b-heretic-v2-GGUF
- **Type**: HERETIC abliteration (full fine-tune from base)
- **Base**: Qwen3.5-9B-Base
- **Method**: HERETIC method — removes censorship with claimed minimal capability damage
- **Verdict**: Popular base for further fine-tuning. Used as foundation by DavidAU and Crownelius models.

---

## 6. Full Fine-Tunes (Multi-Skill / Combined Capabilities)

### crownelius/Crow-9B-Opus-4.6-Distill-Heretic_Qwen3.5 (TOP PICK)
- **URL**: https://huggingface.co/crownelius/Crow-9B-Opus-4.6-Distill-Heretic_Qwen3.5
- **GGUF**: https://huggingface.co/mradermacher/Crow-9B-Opus-4.6-Distill-Heretic_Qwen3.5-GGUF
- **Type**: Full fine-tune (distillation + heretic uncensoring)
- **Base**: trohrbaugh/Qwen3.5-9B-heretic-v2 (already HERETIC'd)
- **Training data**:
  - openbmb/UltraData-Math (math reasoning)
  - peteromallet/dataclaw-peteromallet (general instruction)
  - microsoft/rStar-Coder (code generation + reasoning)
- **Capabilities**: Reasoning, writing, coding, multilingual, long-form dialogue, uncensored
- **Framework**: Unsloth (2x faster training)
- **Downloads**: ~56,400/month (#10 trending on HF)
- **License**: Apache 2.0
- **Verdict**: Best all-rounder. Combines uncensored base + Claude distillation + math + code. Extremely popular.

### DavidAU/Qwen3.5-9B-Claude-4.6-HighIQ-THINKING-HERETIC-UNCENSORED
- **URL**: https://huggingface.co/DavidAU/Qwen3.5-9B-Claude-4.6-HighIQ-THINKING-HERETIC-UNCENSORED
- **Type**: Full fine-tune via Unsloth
- **Base**: Qwen3.5-9B
- **Training data**: Claude 4.6 large distill dataset
- **Method**: Conservative "mild" training post-HERETIC to preserve benchmarks
- **Results**: KL Divergence 0.0793 (excellent), 6/100 refusals
- **Benchmarks (mxfp8)**: ARC 0.432, BoolQ 0.625, HellaSwag 0.658, PIQA 0.748
- **Vision**: Images tested working, video maintained
- **Variants**: Also has INSTRUCT version with better benchmarks (ARC 0.574, BoolQ 0.869)
- **Verdict**: Good for creative writing/thinking. DavidAU's conservative approach preserves base quality.

### DavidAU/Qwen3.5-9B-Claude-4.6-OS-Auto-Variable-HERETIC-UNCENSORED-THINKING-MAX-NEOCODE-Imatrix-GGUF
- **URL**: https://huggingface.co/DavidAU/Qwen3.5-9B-Claude-4.6-OS-Auto-Variable-HERETIC-UNCENSORED-THINKING-MAX-NEOCODE-Imatrix-GGUF
- **Type**: Full fine-tune + GGUF with dual iMatrix optimization
- **Training data**: 4 Claude 4.6-OS datasets (reasoning + output generation)
- **Special features**:
  - DI-MATRIX (dual iMatrix): NEO + NEO-CODE datasets for enhanced quant quality
  - BF16 output tensor for better thinking/output quality
  - Custom Jinja template that stabilizes Qwen3.5 overthinking
  - Tool calling support (Q6/Q8 quants recommended for tools)
- **Quant sizes**: IQ2_M (4.76GB) to BF16 (17.9GB), recommended IQ4_XS (6.28GB)
- **Vision**: Working with mmproj file
- **Verdict**: Best GGUF-optimized variant. NEOCODE iMatrix improves code/reasoning at lower quants. Tool support at Q6+.

### Jackrong/Qwen3.5-9B-Claude-4.6-Opus-Reasoning-Distilled-v2
- **URL**: https://huggingface.co/Jackrong/Qwen3.5-9B-Claude-4.6-Opus-Reasoning-Distilled-v2
- **GGUF**: https://huggingface.co/Jackrong/Qwen3.5-9B-Claude-4.6-Opus-Reasoning-Distilled-v2-GGUF
- **Type**: LoRA SFT via Unsloth (response-only training)
- **Training data**:
  - nohurry/Opus-4.6-Reasoning-3000x-filtered
  - Roman1111111/claude-opus-4.6-10000x
  - TeichAI/claude-4.5-opus-high-reasoning-250x
  - Jackrong/Qwen3.5-reasoning-700x
  - Total: 14,000+ premium reasoning samples
- **Key improvement**: 22% shorter reasoning traces with BETTER accuracy
  - HumanEval pass@1: +5.5 pts (0.872 vs 0.817 at temp 0.6)
  - HumanEval+ pass@1: +5.5 pts (0.817 vs 0.762)
- **Verdict**: Best reasoning efficiency fine-tune. "Think smarter, not longer." NOT uncensored.

### LuffyTheFox/Qwen3.5-9B-Claude-4.6-Opus-Uncensored-Distilled-GGUF
- **URL**: https://huggingface.co/LuffyTheFox/Qwen3.5-9B-Claude-4.6-Opus-Uncensored-Distilled-GGUF
- **Type**: Uncensored variant of Jackrong's reasoning distillation
- **Downloads**: ~9,900/month
- **Verdict**: Combines reasoning distillation + uncensoring. Good middle ground.

### ToastyPigeon/Qwen3.5-9B-Antirep
- **URL**: https://huggingface.co/ToastyPigeon/Qwen3.5-9B-Antirep
- **Type**: QLoRA DPO, merged into base
- **Training data**: 481 on-policy preference pairs (general/reasoning/code/math/safety categories)
- **Problem solved**: Eliminates repetition loops
  - Repetition rate: 10% -> 0%
  - Sub-threshold repetition reduced 50-70%
- **Training**: 48 minutes on single RTX 3090, LoRA r=32
- **Compatibility**: Qwen3.5-9B native
- **License**: Apache 2.0
- **Verdict**: Useful utility fine-tune. Could be applied as a LoRA on top of other models to fix repetition.

### Burnt-Toast/fujin-9b
- **URL**: https://huggingface.co/Burnt-Toast/fujin-9b
- **GGUF**: https://huggingface.co/mradermacher/fujin-9b-GGUF
- **Type**: QLoRA (LoRA r=128, alpha=16, 4-bit NF4)
- **Base**: Qwen3.5-9B-Base
- **Training data**: rpDungeon/some-revised-datasets/rosier_inf_strict_text.parquet (36,438 samples, 65M tokens)
- **Focus**: Roleplay/creative writing
- **Verdict**: RP-focused fine-tune. High LoRA rank (128) for significant adaptation.

### mirazrafi/NSFW-RP-RolePlay-LoRA-Qwen-3.5-9B
- **URL**: https://huggingface.co/mirazrafi/NSFW-RP-RolePlay-LoRA-Qwen-3.5-9B
- **Type**: LoRA adapter (PEFT)
- **Base**: Qwen3.5-9B
- **Training**: SFT with TRL + Unsloth
- **Focus**: NSFW roleplay
- **License**: Apache 2.0
- **Verdict**: Adult RP LoRA. Minimal details available.

---

## 7. Reusable Training Datasets

These datasets were used by the fine-tunes above and could be reused for custom training:

| Dataset | Size | Purpose | Used By |
|---------|------|---------|---------|
| [Salesforce/xlam-function-calling-60k](https://huggingface.co/datasets/Salesforce/xlam-function-calling-60k) | 60k samples | Function calling (3,673 APIs, 21 categories) | xLAM models |
| [Vikhrmodels/tool-plannings-v0.1](https://huggingface.co/datasets/Vikhrmodels/tool-plannings-v0.1) | 10.5k samples | Tool planning with reasoning | Vikhr Tool Planning |
| [nvidia/Nemotron-SWE-v1](https://huggingface.co/datasets/nvidia/Nemotron-SWE-v1) | 59k trajectories | Software engineering agent tasks (OpenHands) | Nemotron |
| [nvidia/Nemotron-Agentic-v1](https://huggingface.co/datasets/nvidia/Nemotron-Agentic-v1) | Unknown | Multi-turn conversational tool use | Nemotron |
| [AlicanKiraz0/Agentic-Chain-of-Thought-Coding-SFT-Dataset](https://huggingface.co/datasets/AlicanKiraz0/Agentic-Chain-of-Thought-Coding-SFT-Dataset) | ~20GB raw | Agentic coding with CoT reasoning | Community |
| [nohurry/Opus-4.6-Reasoning-3000x-filtered](https://huggingface.co/datasets/nohurry/Opus-4.6-Reasoning-3000x-filtered) | 3,000 samples | Claude 4.6 Opus reasoning traces | Jackrong v2 |
| [Roman1111111/claude-opus-4.6-10000x](https://huggingface.co/datasets/Roman1111111/claude-opus-4.6-10000x) | 10,000 samples | Claude 4.6 Opus distillation | Jackrong v2 |
| [microsoft/rStar-Coder](https://huggingface.co/datasets/microsoft/rStar-Coder) | Unknown | Code generation + reasoning | Crow-9B |
| [openbmb/UltraData-Math](https://huggingface.co/datasets/openbmb/UltraData-Math) | Unknown | Math reasoning | Crow-9B |
| rpDungeon/some-revised-datasets | 36k samples | Roleplay/creative writing | fujin-9b |

---

## 8. Summary & Recommendations

### What Already Exists (No Need to Train)

| Capability | Best Option | Notes |
|------------|-------------|-------|
| **Agentic coding** | OmniCoder-9B | 425k trajectories, huge improvement on Terminal-Bench |
| **Uncensored** | Huihui-Qwen3.5-9B-abliterated or HauhauCS Aggressive | Two-stage abliteration vs zero-refusal |
| **Reasoning** | Jackrong v2 Reasoning Distilled | 22% shorter thinking, better accuracy |
| **All-rounder (uncensored + coding + reasoning)** | Crow-9B-Opus-4.6-Distill-Heretic | #10 trending, 56k downloads/month |
| **Anti-repetition** | Qwen3.5-9B-Antirep | DPO fix, trainable in 48min on RTX 3090 |
| **Creative writing/RP** | DavidAU HERETIC variants or fujin-9b | Multiple options depending on preference |
| **GGUF with tool support** | DavidAU NEOCODE iMatrix | Tool calling works at Q6/Q8 quants |

### Gaps (Would Need Custom Training)

| Capability | Status | Recommended Dataset |
|------------|--------|-------------------|
| **Tool calling LoRA** for Qwen3.5-9B | No dedicated LoRA exists | Salesforce/xlam-function-calling-60k |
| **Sysadmin / PowerShell / DevOps** | Nothing for Qwen 9B | Would need custom dataset |
| **REST API interaction** | No dedicated model | xlam-function-calling-60k partially covers this |
| **Combined tool-calling + uncensored** | No single model | Stack abliteration + tool-calling LoRA |

### Compatibility Notes

- **Qwen3.5-9B** (Feb 2026) uses a hybrid GDN + attention architecture (24 DeltaNet + 8 full attention layers). LoRAs from Qwen2.5 or Qwen3 are NOT compatible.
- **Qwen3-8B** (2025) has a different architecture. Models trained on it won't work on Qwen3.5-9B.
- **Qwen2.5-7B** (2024) is entirely different. Datasets can be reused but weights cannot.
- All models listed in section 5 and 6 are confirmed Qwen3.5-9B compatible unless noted otherwise.

### Quick-Start Recommendations

1. **For the Bolthands project (agentic + tool calling + uncensored)**:
   - Start with **Crow-9B** as the all-rounder base
   - Or use **OmniCoder-9B** for maximum coding capability
   - Fine-tune a tool-calling LoRA on top using **xlam-function-calling-60k**
   - Apply abliteration if using OmniCoder (it's not uncensored)

2. **For gaming sidecar (fast, small, tool-calling)**:
   - Qwen3.5-4B base already handles this well
   - Consider fine-tuning on xlam-60k for better function calling

3. **For maximum uncensored quality**:
   - HauhauCS Aggressive (0/465 refusals, multimodal)
   - Or Huihui-ai abliterated (most rigorous method, 16.9k downloads)
