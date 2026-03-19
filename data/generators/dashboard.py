"""Synthetic data generator for AI Dashboard management scenarios."""

import random

from .base import (
    BaseGenerator,
    GeneratedExample,
    Message,
    Scenario,
    ToolCall,
    ToolResponse,
)

SERVICES = [
    ("comfyui", "ComfyUI", 8188),
    ("swarmui", "SwarmUI", 7801),
    ("f5tts", "F5-TTS", 7861),
    ("rvc", "RVC/Applio", 6969),
    ("gpt-sovits", "GPT-SoVITS", 9880),
    ("ace-step", "ACE-Step", 7860),
    ("llm-chat", "LLM Chat", 8080),
    ("searxng", "SearXNG", 8888),
    ("mantella", "Mantella", 4999),
    ("mantella-llm", "Mantella LLM", 8090),
    ("openclaw", "OpenClaw", 18789),
]


class DashboardGenerator(BaseGenerator):
    domain = "dashboard"
    schema_files = ["dashboard.json"]

    def _build_scenarios(self) -> list[Scenario]:
        return [
            Scenario(
                domain="dashboard",
                category="service_start",
                difficulty="easy",
                expected_tools=["dashboard.service_start"],
                user_prompts=[
                    f"Start {name}" for _, name, _ in SERVICES[:6]
                ] + [
                    "Fire up ComfyUI",
                    "I need the TTS server running",
                    "Start the image generation stack",
                    "Get the LLM chat server going",
                ],
            ),
            Scenario(
                domain="dashboard",
                category="service_stop",
                difficulty="easy",
                expected_tools=["dashboard.service_stop"],
                user_prompts=[
                    f"Stop {name}" for _, name, _ in SERVICES[:6]
                ] + [
                    "Shut down ComfyUI, I'm done generating images",
                    "Kill the TTS server to free up VRAM",
                    "Stop all AI services",
                ],
            ),
            Scenario(
                domain="dashboard",
                category="service_list",
                difficulty="easy",
                expected_tools=["dashboard.service_list"],
                user_prompts=[
                    "What services are running?",
                    "Show me the dashboard status",
                    "What AI tools are active?",
                    "Which services are up right now?",
                ],
            ),
            Scenario(
                domain="dashboard",
                category="gpu_status",
                difficulty="easy",
                expected_tools=["dashboard.gpu_status"],
                user_prompts=[
                    "How's the GPU doing?",
                    "What's the VRAM usage?",
                    "Check GPU temperature",
                    "Is the GPU under load?",
                    "How much VRAM is free?",
                ],
            ),
            Scenario(
                domain="dashboard",
                category="system_status",
                difficulty="easy",
                expected_tools=["dashboard.system_status"],
                user_prompts=[
                    "System status?",
                    "How's the machine doing?",
                    "Check CPU and RAM usage",
                    "Overall system health?",
                ],
            ),
            Scenario(
                domain="dashboard",
                category="vram_management",
                difficulty="hard",
                expected_tools=["dashboard.gpu_status", "dashboard.service_stop", "dashboard.service_start"],
                user_prompts=[
                    "I need to free up VRAM for image generation",
                    "The GPU is maxed out, what should I stop?",
                    "I want to run ComfyUI but there's not enough VRAM",
                    "Swap the LLM for the image gen stack",
                ],
            ),
        ]

    def generate_example(self, scenario: Scenario) -> GeneratedExample:
        prompt = scenario.random_prompt()
        messages: list[Message] = [self._make_user(prompt)]

        if scenario.category == "service_start":
            svc_id, svc_name, port = random.choice(SERVICES)
            messages.append(
                self._make_assistant_with_tool(
                    f"Starting {svc_name}.",
                    ToolCall("dashboard.service_start", {"service": svc_id}),
                )
            )
            messages.append(
                self._make_tool_response(
                    ToolResponse("dashboard.service_start", {
                        "success": True,
                        "service": svc_id,
                        "status": "running",
                        "port": port,
                        "url": f"http://localhost:{port}",
                    })
                )
            )
            messages.append(self._make_assistant_summary(
                f"{svc_name} is up and running at localhost:{port}."
            ))

        elif scenario.category == "service_stop":
            svc_id, svc_name, port = random.choice(SERVICES)
            messages.append(
                self._make_assistant_with_tool(
                    f"Stopping {svc_name}.",
                    ToolCall("dashboard.service_stop", {"service": svc_id}),
                )
            )
            vram_freed = random.randint(2, 12)
            messages.append(
                self._make_tool_response(
                    ToolResponse("dashboard.service_stop", {
                        "success": True,
                        "service": svc_id,
                        "status": "stopped",
                        "vram_freed_gb": vram_freed,
                    })
                )
            )
            messages.append(self._make_assistant_summary(
                f"{svc_name} stopped. Freed up ~{vram_freed}GB VRAM."
            ))

        elif scenario.category == "service_list":
            running = random.sample(SERVICES, k=random.randint(2, 5))
            messages.append(
                self._make_assistant_with_tool(
                    "Checking service status.",
                    ToolCall("dashboard.service_list", {}),
                )
            )
            messages.append(
                self._make_tool_response(
                    ToolResponse("dashboard.service_list", {
                        "services": [
                            {"id": s[0], "name": s[1], "status": "running" if s in running else "stopped",
                             "port": s[2] if s in running else None}
                            for s in SERVICES
                        ]
                    })
                )
            )
            running_names = [s[1] for s in running]
            messages.append(self._make_assistant_summary(
                f"Currently running: {', '.join(running_names)}. "
                f"Everything else is stopped."
            ))

        elif scenario.category == "gpu_status":
            vram_used = random.randint(4, 22)
            temp = random.randint(45, 85)
            gpu_util = random.randint(0, 100)
            messages.append(
                self._make_assistant_with_tool(
                    "Checking GPU.",
                    ToolCall("dashboard.gpu_status", {}),
                )
            )
            messages.append(
                self._make_tool_response(
                    ToolResponse("dashboard.gpu_status", {
                        "gpu": "NVIDIA RTX 3090",
                        "vram_used_gb": vram_used,
                        "vram_total_gb": 24,
                        "vram_free_gb": 24 - vram_used,
                        "temperature_c": temp,
                        "gpu_utilization_pct": gpu_util,
                        "power_draw_w": random.randint(50, 300),
                        "fan_speed_pct": random.randint(30, 80),
                    })
                )
            )
            status = "under heavy load" if gpu_util > 70 else "mostly idle" if gpu_util < 20 else "moderate load"
            temp_status = "running hot" if temp > 75 else "temperature is fine"
            messages.append(self._make_assistant_summary(
                f"RTX 3090: {vram_used}/24GB VRAM used ({24 - vram_used}GB free), "
                f"{gpu_util}% utilization — {status}. {temp}°C — {temp_status}."
            ))

        elif scenario.category == "system_status":
            messages.append(
                self._make_assistant_with_tool(
                    "Checking system health.",
                    ToolCall("dashboard.system_status", {}),
                )
            )
            cpu = random.randint(5, 80)
            ram_used = random.randint(12, 55)
            messages.append(
                self._make_tool_response(
                    ToolResponse("dashboard.system_status", {
                        "cpu_usage_pct": cpu,
                        "ram_used_gb": ram_used,
                        "ram_total_gb": 64,
                        "disk_used_pct": random.randint(30, 80),
                        "uptime": f"{random.randint(1, 30)}d {random.randint(0, 23)}h",
                        "load_avg": [round(random.uniform(0.5, 4.0), 2) for _ in range(3)],
                    })
                )
            )
            messages.append(self._make_assistant_summary(
                f"System looks {'healthy' if cpu < 60 and ram_used < 50 else 'a bit loaded'} — "
                f"CPU at {cpu}%, RAM {ram_used}/64GB, disk usage moderate."
            ))

        elif scenario.category == "vram_management":
            # Multi-step: check GPU → stop heavy service → start desired service
            messages.append(
                self._make_assistant_with_tool(
                    "Let me check what's using VRAM first.",
                    ToolCall("dashboard.gpu_status", {}),
                )
            )
            messages.append(
                self._make_tool_response(
                    ToolResponse("dashboard.gpu_status", {
                        "gpu": "NVIDIA RTX 3090",
                        "vram_used_gb": 20,
                        "vram_total_gb": 24,
                        "vram_free_gb": 4,
                        "temperature_c": 65,
                        "gpu_utilization_pct": 30,
                    })
                )
            )
            heavy_svc = random.choice([("llm-chat", "LLM Chat"), ("gpt-sovits", "GPT-SoVITS")])
            messages.append(
                self._make_assistant_with_tool(
                    f"Only 4GB free — need to stop something. Let me shut down {heavy_svc[1]} to free VRAM.",
                    ToolCall("dashboard.service_stop", {"service": heavy_svc[0]}),
                )
            )
            messages.append(
                self._make_tool_response(
                    ToolResponse("dashboard.service_stop", {
                        "success": True, "service": heavy_svc[0],
                        "status": "stopped", "vram_freed_gb": 12,
                    })
                )
            )
            target_svc = ("comfyui", "ComfyUI", 8188)
            messages.append(
                self._make_assistant_with_tool(
                    f"Freed 12GB. Now starting {target_svc[1]}.",
                    ToolCall("dashboard.service_start", {"service": target_svc[0]}),
                )
            )
            messages.append(
                self._make_tool_response(
                    ToolResponse("dashboard.service_start", {
                        "success": True, "service": target_svc[0],
                        "status": "running", "port": target_svc[2],
                    })
                )
            )
            messages.append(self._make_assistant_summary(
                f"Done — stopped {heavy_svc[1]} (freed 12GB VRAM) and started {target_svc[1]} at localhost:{target_svc[2]}. You're good to go."
            ))

        return GeneratedExample(
            messages=messages,
            domain=self.domain,
            category=scenario.category,
            difficulty=scenario.difficulty,
            tools_used=scenario.expected_tools,
        )
