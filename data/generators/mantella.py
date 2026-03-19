"""Synthetic data generator for Mantella AI NPC mod scenarios."""

import random

from .base import (
    BaseGenerator,
    GeneratedExample,
    Message,
    Scenario,
    ToolCall,
    ToolResponse,
)

CONFIG_KEYS = [
    ("llm_api_url", "http://localhost:8090/v1", "LLM API endpoint"),
    ("tts_engine", "gpt_sovits", "TTS engine (gpt_sovits, f5tts, xtts)"),
    ("tts_api_url", "http://localhost:9880", "TTS API endpoint"),
    ("vision_enabled", "true", "Enable vision for NPCs"),
    ("vision_model", "qwen2.5-vl-3b", "Vision LLM model"),
    ("game", "fallout4", "Target game"),
    ("max_response_length", "250", "Max NPC response token length"),
    ("voice_speed", "1.0", "TTS voice speed multiplier"),
    ("npc_memory_turns", "10", "How many conversation turns NPCs remember"),
    ("language", "en", "Language for NPC dialogue"),
]

NPC_NAMES = ["Preston Garvey", "Piper Wright", "Nick Valentine", "Codsworth", "Dogmeat",
             "Cait", "Curie", "Deacon", "MacCready", "Strong"]


class MantellaGenerator(BaseGenerator):
    domain = "mantella"
    schema_files = ["mantella.json"]

    def _build_scenarios(self) -> list[Scenario]:
        return [
            Scenario(
                domain="mantella",
                category="server_start",
                difficulty="easy",
                expected_tools=["mantella.server_start"],
                user_prompts=[
                    "Start the Mantella server",
                    "Fire up Mantella for Fallout 4",
                    "I want to play with AI NPCs, start Mantella",
                    "Get Mantella running",
                    "Launch the NPC AI system",
                ],
            ),
            Scenario(
                domain="mantella",
                category="server_stop",
                difficulty="easy",
                expected_tools=["mantella.server_stop"],
                user_prompts=[
                    "Stop Mantella",
                    "Shut down the NPC AI",
                    "Kill the Mantella server",
                    "Turn off Mantella, I'm done gaming",
                    "Stop the AI NPC system",
                ],
            ),
            Scenario(
                domain="mantella",
                category="server_status",
                difficulty="easy",
                expected_tools=["mantella.server_status"],
                user_prompts=[
                    "Is Mantella running?",
                    "Check Mantella status",
                    "Is the AI NPC system online?",
                    "How's Mantella doing?",
                    "Is the NPC server up?",
                ],
            ),
            Scenario(
                domain="mantella",
                category="set_config",
                difficulty="medium",
                expected_tools=["mantella.set_config"],
                user_prompts=[
                    "Change the Mantella TTS engine to F5-TTS",
                    "Enable vision for Mantella NPCs",
                    "Set Mantella to use GPT-SoVITS for voices",
                    "Change the max NPC response length to 200",
                    "Increase NPC memory to 20 turns",
                    "Set the Mantella language to English",
                    "Switch Mantella's vision model to the 3B model",
                ],
            ),
            Scenario(
                domain="mantella",
                category="get_config",
                difficulty="easy",
                expected_tools=["mantella.get_config"],
                user_prompts=[
                    "What's the current Mantella configuration?",
                    "Show me Mantella settings",
                    "What TTS engine is Mantella using?",
                    "Is vision enabled in Mantella?",
                    "What model is Mantella using for NPC conversations?",
                ],
            ),
        ]

    def generate_example(self, scenario: Scenario) -> GeneratedExample:
        prompt = scenario.random_prompt()
        messages: list[Message] = [self._make_user(prompt)]

        if scenario.category == "server_start":
            messages.append(
                self._make_assistant_with_tool(
                    "Starting the Mantella server.",
                    ToolCall("mantella.server_start", {}),
                )
            )
            success = random.random() > 0.15
            if success:
                messages.append(
                    self._make_tool_response(
                        ToolResponse("mantella.server_start", {
                            "success": True,
                            "status": "running",
                            "port": 4999,
                            "url": "http://localhost:4999",
                            "game": "fallout4",
                            "tts_engine": random.choice(["gpt_sovits", "f5tts"]),
                            "vision_enabled": random.choice([True, False]),
                            "llm_connected": True,
                        })
                    )
                )
                messages.append(self._make_assistant_summary(
                    "Mantella is up and running on port 4999. Connected to the LLM and TTS services. "
                    "Fire up Fallout 4 and your NPCs will have AI-powered conversations."
                ))
            else:
                messages.append(
                    self._make_tool_response(
                        ToolResponse("mantella.server_start", {
                            "success": False,
                            "error": "Failed to connect to LLM server at localhost:8090 — is the LLM running?",
                        })
                    )
                )
                messages.append(
                    self._make_assistant_with_tool(
                        "Mantella needs the LLM server running first. Let me check.",
                        ToolCall("mantella.server_status", {}),
                    )
                )
                messages.append(
                    self._make_tool_response(
                        ToolResponse("mantella.server_status", {
                            "status": "error",
                            "error": "LLM server not reachable",
                            "llm_url": "http://localhost:8090",
                        })
                    )
                )
                messages.append(self._make_assistant_summary(
                    "Mantella can't start because the LLM server isn't running. "
                    "Want me to start the Mantella LLM service first? It needs the Qwen2.5-VL-3B model."
                ))

        elif scenario.category == "server_stop":
            messages.append(
                self._make_assistant_with_tool(
                    "Stopping Mantella.",
                    ToolCall("mantella.server_stop", {}),
                )
            )
            messages.append(
                self._make_tool_response(
                    ToolResponse("mantella.server_stop", {
                        "success": True,
                        "status": "stopped",
                        "active_conversations": 0,
                    })
                )
            )
            messages.append(self._make_assistant_summary(
                "Mantella server stopped. NPC AI conversations are disabled until you start it again."
            ))

        elif scenario.category == "server_status":
            running = random.choice([True, False])
            messages.append(
                self._make_assistant_with_tool(
                    "Checking Mantella status.",
                    ToolCall("mantella.server_status", {}),
                )
            )
            if running:
                active_npcs = random.randint(0, 3)
                messages.append(
                    self._make_tool_response(
                        ToolResponse("mantella.server_status", {
                            "status": "running",
                            "port": 4999,
                            "game": "fallout4",
                            "uptime": f"{random.randint(0, 12)}h {random.randint(0, 59)}m",
                            "llm_connected": True,
                            "tts_connected": True,
                            "vision_enabled": True,
                            "active_conversations": active_npcs,
                            "total_conversations": random.randint(active_npcs, 50),
                            "active_npcs": random.sample(NPC_NAMES, k=min(active_npcs, len(NPC_NAMES))) if active_npcs > 0 else [],
                        })
                    )
                )
                npc_info = ""
                if active_npcs > 0:
                    npcs = random.sample(NPC_NAMES, k=min(active_npcs, len(NPC_NAMES)))
                    npc_info = f" Currently talking to: {', '.join(npcs)}."
                messages.append(self._make_assistant_summary(
                    f"Mantella is running — connected to both the LLM and TTS.{npc_info} "
                    f"Vision is enabled for NPC awareness."
                ))
            else:
                messages.append(
                    self._make_tool_response(
                        ToolResponse("mantella.server_status", {
                            "status": "stopped",
                        })
                    )
                )
                messages.append(self._make_assistant_summary(
                    "Mantella is not running. Want me to start it?"
                ))

        elif scenario.category == "set_config":
            config = random.choice(CONFIG_KEYS)
            new_value = random.choice(["f5tts", "true", "false", "200", "20", "qwen2.5-vl-3b", "en"])
            messages.append(
                self._make_assistant_with_tool(
                    f"Updating Mantella config: {config[0]}.",
                    ToolCall("mantella.set_config", {
                        "key": config[0],
                        "value": new_value,
                    }),
                )
            )
            messages.append(
                self._make_tool_response(
                    ToolResponse("mantella.set_config", {
                        "success": True,
                        "key": config[0],
                        "old_value": config[1],
                        "new_value": new_value,
                        "requires_restart": random.choice([True, False]),
                    })
                )
            )
            restart_note = " You'll need to restart Mantella for this to take effect." if random.random() > 0.5 else ""
            messages.append(self._make_assistant_summary(
                f"Updated {config[0]} from \"{config[1]}\" to \"{new_value}\".{restart_note}"
            ))

        elif scenario.category == "get_config":
            messages.append(
                self._make_assistant_with_tool(
                    "Pulling Mantella configuration.",
                    ToolCall("mantella.get_config", {}),
                )
            )
            config_dict = {c[0]: c[1] for c in CONFIG_KEYS}
            messages.append(
                self._make_tool_response(
                    ToolResponse("mantella.get_config", {
                        "config": config_dict,
                        "config_path": "~/ai-suite/Mantella/userdata/config.ini",
                    })
                )
            )
            messages.append(self._make_assistant_summary(
                f"Current Mantella config:\n"
                f"- Game: {config_dict['game']}\n"
                f"- TTS: {config_dict['tts_engine']} at {config_dict['tts_api_url']}\n"
                f"- Vision: {config_dict['vision_enabled']} ({config_dict['vision_model']})\n"
                f"- LLM: {config_dict['llm_api_url']}\n"
                f"- NPC memory: {config_dict['npc_memory_turns']} turns"
            ))

        return GeneratedExample(
            messages=messages,
            domain=self.domain,
            category=scenario.category,
            difficulty=scenario.difficulty,
            tools_used=scenario.expected_tools,
        )
