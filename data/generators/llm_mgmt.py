"""Synthetic data generator for LLM management scenarios."""

import random

from .base import (
    BaseGenerator,
    GeneratedExample,
    Message,
    Scenario,
    ToolCall,
    ToolResponse,
)

MODELS = [
    ("qwen35-27b", "Qwen3.5-27B UD-Q5_K_XL", 20.0, "coding, general"),
    ("glm-flash", "GLM-4.7-Flash Q4_K_XL", 17.0, "agentic, coding"),
    ("gemma3-27b", "Gemma 3 27B QAT Q4_0", 14.0, "uncensored, vision"),
    ("glm-heretic", "GLM-4.7 Flash Heretic Q4_K_M", 17.0, "uncensored, coding"),
    ("qwen35-4b", "Qwen3.5-4B Q4_K_M", 3.0, "gaming sidecar, vision"),
    ("qwen35-9b", "Qwen3.5-9B abliterated Q4_K_M", 7.0, "uncensored, multimodal"),
    ("qwen3-vl-32b", "Qwen3-VL-32B abliterated Q4_K_M", 21.0, "max uncensored vision"),
    ("qwen25-vl-3b", "Qwen2.5-VL-3B", 3.0, "Mantella NPC vision"),
]

SWAP_ALIASES = {
    "coder": "qwen35-27b",
    "glm": "glm-flash",
    "gemma": "gemma3-27b",
    "heretic": "glm-heretic",
    "mini": "qwen35-4b",
    "qwen35": "qwen35-27b",
    "qwen3vl": "qwen3-vl-32b",
}

LORAS = [
    ("coding-assist-lora", "Coding assistant fine-tune", 200),
    ("roleplay-v2", "Roleplay personality LoRA", 150),
    ("function-calling", "Enhanced function calling", 180),
    ("creative-writing", "Creative writing boost", 120),
]


class LLMGenerator(BaseGenerator):
    domain = "llm"
    schema_files = ["llm.json"]

    def _build_scenarios(self) -> list[Scenario]:
        return [
            Scenario(
                domain="llm",
                category="swap_model",
                difficulty="medium",
                expected_tools=["llm.swap_model"],
                user_prompts=[
                    "Switch to the Qwen3.5 model",
                    "Load GLM Flash for coding",
                    "Swap to the uncensored Gemma model",
                    "Switch to the heretic model",
                    "Load the small Qwen model for gaming",
                    "I need the big vision model, load Qwen3-VL-32B",
                    "Change the LLM to the coding model",
                    "Swap to GLM for agentic tasks",
                ],
            ),
            Scenario(
                domain="llm",
                category="server_status",
                difficulty="easy",
                expected_tools=["llm.server_status"],
                user_prompts=[
                    "Is the LLM server running?",
                    "What model is currently loaded?",
                    "Check the LLM server status",
                    "How's the language model doing?",
                    "What's the current LLM setup?",
                ],
            ),
            Scenario(
                domain="llm",
                category="list_models",
                difficulty="easy",
                expected_tools=["llm.list_models"],
                user_prompts=[
                    "What LLM models do I have?",
                    "List available language models",
                    "Show me the downloaded models",
                    "What models can I load?",
                    "Which LLMs are on the AI drive?",
                ],
            ),
            Scenario(
                domain="llm",
                category="load_lora",
                difficulty="medium",
                expected_tools=["llm.load_lora"],
                user_prompts=[
                    "Load the coding LoRA",
                    "Apply the roleplay LoRA",
                    "Add the function calling LoRA",
                    "Enable the creative writing LoRA",
                    "Load a LoRA adapter for coding assistance",
                ],
            ),
            Scenario(
                domain="llm",
                category="unload_lora",
                difficulty="easy",
                expected_tools=["llm.unload_lora"],
                user_prompts=[
                    "Remove the LoRA adapter",
                    "Unload the current LoRA",
                    "Disable the LoRA",
                    "Go back to the base model without LoRA",
                    "Clear all LoRA adapters",
                ],
            ),
        ]

    def generate_example(self, scenario: Scenario) -> GeneratedExample:
        prompt = scenario.random_prompt()
        messages: list[Message] = [self._make_user(prompt)]

        if scenario.category == "swap_model":
            target = random.choice(MODELS)
            current = random.choice([m for m in MODELS if m[0] != target[0]])
            alias = None
            for k, v in SWAP_ALIASES.items():
                if v == target[0]:
                    alias = k
                    break

            messages.append(
                self._make_assistant_with_tool(
                    f"Swapping from {current[1]} to {target[1]}.",
                    ToolCall("llm.swap_model", {
                        "model": alias or target[0],
                    }),
                )
            )
            messages.append(
                self._make_tool_response(
                    ToolResponse("llm.swap_model", {
                        "success": True,
                        "previous_model": current[1],
                        "new_model": target[1],
                        "vram_gb": target[2],
                        "load_time_s": round(random.uniform(5.0, 30.0), 1),
                        "context_size": random.choice([8192, 16384, 32768]),
                    })
                )
            )
            messages.append(self._make_assistant_summary(
                f"Swapped to {target[1]} ({target[2]}GB VRAM). "
                f"Best for {target[3]}. Ready to go."
            ))

        elif scenario.category == "server_status":
            model = random.choice(MODELS)
            running = random.random() > 0.1
            messages.append(
                self._make_assistant_with_tool(
                    "Checking LLM server.",
                    ToolCall("llm.server_status", {}),
                )
            )
            if running:
                tokens_per_sec = round(random.uniform(20.0, 110.0), 1)
                messages.append(
                    self._make_tool_response(
                        ToolResponse("llm.server_status", {
                            "status": "running",
                            "model": model[1],
                            "vram_gb": model[2],
                            "port": 8080,
                            "context_size": 32768,
                            "tokens_per_second": tokens_per_sec,
                            "uptime": f"{random.randint(1, 48)}h",
                            "requests_served": random.randint(0, 500),
                            "lora_loaded": None,
                        })
                    )
                )
                messages.append(self._make_assistant_summary(
                    f"LLM server is running — {model[1]} loaded, using {model[2]}GB VRAM. "
                    f"Running at {tokens_per_sec} tokens/s on port 8080."
                ))
            else:
                messages.append(
                    self._make_tool_response(
                        ToolResponse("llm.server_status", {
                            "status": "stopped",
                            "model": None,
                            "port": 8080,
                        })
                    )
                )
                messages.append(self._make_assistant_summary(
                    "LLM server is not running. Want me to start it with a specific model?"
                ))

        elif scenario.category == "list_models":
            messages.append(
                self._make_assistant_with_tool(
                    "Listing available models.",
                    ToolCall("llm.list_models", {}),
                )
            )
            messages.append(
                self._make_tool_response(
                    ToolResponse("llm.list_models", {
                        "models": [
                            {"id": m[0], "name": m[1], "size_gb": m[2], "tags": m[3],
                             "path": f"~/ai-drive/ai-suite/models/{m[0]}.gguf"}
                            for m in MODELS
                        ],
                        "total": len(MODELS),
                        "models_dir": "~/ai-drive/ai-suite/models/",
                    })
                )
            )
            lines = []
            for m in MODELS:
                lines.append(f"- {m[1]} ({m[2]}GB) — {m[3]}")
            messages.append(self._make_assistant_summary(
                f"{len(MODELS)} models available:\n" + "\n".join(lines)
            ))

        elif scenario.category == "load_lora":
            lora = random.choice(LORAS)
            messages.append(
                self._make_assistant_with_tool(
                    f"Loading the {lora[0]} LoRA adapter.",
                    ToolCall("llm.load_lora", {
                        "lora_name": lora[0],
                    }),
                )
            )
            messages.append(
                self._make_tool_response(
                    ToolResponse("llm.load_lora", {
                        "success": True,
                        "lora_name": lora[0],
                        "description": lora[1],
                        "size_mb": lora[2],
                        "additional_vram_mb": random.randint(100, 500),
                    })
                )
            )
            messages.append(self._make_assistant_summary(
                f"Loaded the {lora[0]} LoRA ({lora[1]}). "
                f"The model will now have enhanced {lora[1].lower().split()[0]} capabilities."
            ))

        elif scenario.category == "unload_lora":
            lora = random.choice(LORAS)
            messages.append(
                self._make_assistant_with_tool(
                    "Removing the LoRA adapter.",
                    ToolCall("llm.unload_lora", {"lora_name": lora[0]}),
                )
            )
            messages.append(
                self._make_tool_response(
                    ToolResponse("llm.unload_lora", {
                        "success": True,
                        "lora_name": lora[0],
                        "vram_freed_mb": random.randint(100, 500),
                    })
                )
            )
            messages.append(self._make_assistant_summary(
                f"LoRA adapter removed. Back to the base model. "
                f"Freed up some VRAM too."
            ))

        return GeneratedExample(
            messages=messages,
            domain=self.domain,
            category=scenario.category,
            difficulty=scenario.difficulty,
            tools_used=scenario.expected_tools,
        )
