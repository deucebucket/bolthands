"""Synthetic data generator for cross-domain multi-service scenarios."""

import random

from .base import BaseGenerator, GeneratedExample, Message, Scenario, ToolCall, ToolResponse


class CrossDomainGenerator(BaseGenerator):
    domain = "cross_domain"
    schema_files = ["arr.json", "plex.json", "dashboard.json", "windows.json",
                    "systemd.json", "llm.json", "comfyui.json", "tts.json"]

    def _build_scenarios(self) -> list[Scenario]:
        return [
            Scenario(
                domain="cross_domain", category="arr_and_plex", difficulty="medium",
                expected_tools=["sonarr.queue", "plex.now_playing"],
                user_prompts=[
                    "What's downloading in Sonarr and is anyone watching Plex?",
                    "Check the download queue and who's streaming",
                    "Sonarr status and Plex sessions",
                ]),
            Scenario(
                domain="cross_domain", category="vram_swap", difficulty="hard",
                expected_tools=["dashboard.service_stop", "dashboard.service_start", "dashboard.gpu_status"],
                user_prompts=[
                    "Stop the LLM and start ComfyUI",
                    "Swap to image generation mode",
                    "I need VRAM for image gen, kill the chat server",
                    "Switch from coding to art mode",
                ]),
            Scenario(
                domain="cross_domain", category="media_workflow", difficulty="hard",
                expected_tools=["radarr.movie_add", "plex.library_scan"],
                user_prompts=[
                    "Add Dune Part Two to Radarr and scan Plex when it downloads",
                    "Download the new Marvel movie and add it to my collection",
                    "Find and download Oppenheimer, then scan Plex",
                ]),
            Scenario(
                domain="cross_domain", category="system_health", difficulty="medium",
                expected_tools=["dashboard.gpu_status", "dashboard.system_status", "systemd.unit_list"],
                user_prompts=[
                    "Full system health check — GPU, CPU, services",
                    "How's everything running?",
                    "Give me the full status of the machine",
                ]),
            Scenario(
                domain="cross_domain", category="windows_and_plex", difficulty="medium",
                expected_tools=["win.system_info", "plex.now_playing"],
                user_prompts=[
                    "How's the gaming PC and is anyone on Plex?",
                    "Check the Windows machine health and Plex status",
                ]),
            Scenario(
                domain="cross_domain", category="model_and_generate", difficulty="hard",
                expected_tools=["llm.swap_model", "comfyui.generate_image"],
                user_prompts=[
                    "Load the image model and generate a landscape",
                    "Switch to the art model and make me a portrait",
                ]),
            Scenario(
                domain="cross_domain", category="tts_and_llm", difficulty="medium",
                expected_tools=["llm.server_status", "tts.synthesize"],
                user_prompts=[
                    "Is the LLM running? If so, generate some text and read it aloud",
                    "Use the chat model to write a poem and then TTS it with Jerry's voice",
                ]),
        ]

    def generate_example(self, scenario: Scenario) -> GeneratedExample:
        prompt = scenario.random_prompt()
        messages: list[Message] = [self._make_user(prompt)]

        if scenario.category == "arr_and_plex":
            messages.append(self._make_assistant_with_tool(
                "Let me check both.",
                ToolCall("sonarr.queue", {})))
            queue_items = random.randint(0, 5)
            messages.append(self._make_tool_response(ToolResponse("sonarr.queue", {
                "items": [{"title": f"Show S0{random.randint(1,5)}E{random.randint(1,20):02d}",
                           "status": "downloading", "progress": round(random.uniform(10, 90), 1)}
                          for _ in range(queue_items)]
            })))
            messages.append(self._make_assistant_with_tool(
                f"{'Got ' + str(queue_items) + ' downloads in Sonarr.' if queue_items else 'Sonarr queue is empty.'} Checking Plex.",
                ToolCall("plex.now_playing", {})))
            sessions = random.randint(0, 3)
            messages.append(self._make_tool_response(ToolResponse("plex.now_playing", {
                "sessions": [{"user": random.choice(["sarah", "mike", "guest"]),
                              "title": random.choice(["Severance S02E08", "Dune Part Two", "The Bear S03E01"]),
                              "quality": "1080p", "transcode": False}
                             for _ in range(sessions)]
            })))
            if sessions:
                messages.append(self._make_assistant_summary(
                    f"Sonarr: {queue_items} downloads in progress. "
                    f"Plex: {sessions} active stream(s). Everyone's direct playing, no transcoding."
                ))
            else:
                messages.append(self._make_assistant_summary(
                    f"Sonarr: {queue_items} downloads. Plex: nobody's watching right now."
                ))

        elif scenario.category == "vram_swap":
            messages.append(self._make_assistant_with_tool(
                "Checking GPU first.",
                ToolCall("dashboard.gpu_status", {})))
            messages.append(self._make_tool_response(ToolResponse("dashboard.gpu_status", {
                "vram_used_gb": 18, "vram_total_gb": 24, "vram_free_gb": 6, "temperature_c": 55,
            })))
            messages.append(self._make_assistant_with_tool(
                "18GB VRAM in use. Stopping the LLM server to free up space.",
                ToolCall("dashboard.service_stop", {"service": "llm-chat"})))
            messages.append(self._make_tool_response(ToolResponse("dashboard.service_stop", {
                "success": True, "service": "llm-chat", "vram_freed_gb": 14,
            })))
            messages.append(self._make_assistant_with_tool(
                "Freed 14GB. Starting ComfyUI.",
                ToolCall("dashboard.service_start", {"service": "comfyui"})))
            messages.append(self._make_tool_response(ToolResponse("dashboard.service_start", {
                "success": True, "service": "comfyui", "port": 8188,
            })))
            messages.append(self._make_assistant_summary(
                "Swapped — LLM server stopped, ComfyUI running at localhost:8188. You're in art mode."
            ))

        elif scenario.category == "media_workflow":
            movie = random.choice(["Dune: Part Two", "Oppenheimer", "Deadpool & Wolverine"])
            messages.append(self._make_assistant_with_tool(
                f"Adding {movie} to Radarr.",
                ToolCall("radarr.movie_add", {"title": movie, "search_now": True})))
            messages.append(self._make_tool_response(ToolResponse("radarr.movie_add", {
                "success": True, "title": movie, "year": 2024, "search_initiated": True,
            })))
            messages.append(self._make_assistant_summary(
                f"Added {movie} to Radarr — search is running. "
                f"Once it downloads and imports, I'll scan the Plex library so it shows up. "
                f"I'll keep an eye on the queue."
            ))

        elif scenario.category == "system_health":
            messages.append(self._make_assistant_with_tool(
                "Running full health check.",
                ToolCall("dashboard.gpu_status", {})))
            messages.append(self._make_tool_response(ToolResponse("dashboard.gpu_status", {
                "vram_used_gb": 8, "vram_total_gb": 24, "temperature_c": 50, "gpu_utilization_pct": 15,
            })))
            messages.append(self._make_assistant_with_tool(
                "GPU looks good. Checking system.",
                ToolCall("dashboard.system_status", {})))
            messages.append(self._make_tool_response(ToolResponse("dashboard.system_status", {
                "cpu_usage_pct": 12, "ram_used_gb": 20, "ram_total_gb": 64, "disk_used_pct": 45,
            })))
            messages.append(self._make_assistant_with_tool(
                "System healthy. Checking services.",
                ToolCall("systemd.unit_list", {"type": "service", "state": "failed"})))
            messages.append(self._make_tool_response(ToolResponse("systemd.unit_list", {"units": []})))
            messages.append(self._make_assistant_summary(
                "Everything looks great:\n"
                "- GPU: 8/24GB VRAM, 50°C, 15% utilization\n"
                "- CPU: 12%, RAM: 20/64GB, Disk: 45%\n"
                "- No failed services\n"
                "All systems nominal."
            ))

        elif scenario.category == "windows_and_plex":
            messages.append(self._make_assistant_with_tool(
                "Checking both.",
                ToolCall("win.system_info", {"host": "GAMING-PC", "category": "overview"})))
            messages.append(self._make_tool_response(ToolResponse("win.system_info", {
                "hostname": "GAMING-PC", "os": "Windows 11 Pro", "cpu_usage": 8,
                "memory_used_gb": 12, "memory_total_gb": 32,
            })))
            messages.append(self._make_assistant_with_tool(
                "Gaming PC is fine. Checking Plex.",
                ToolCall("plex.now_playing", {})))
            messages.append(self._make_tool_response(ToolResponse("plex.now_playing", {"sessions": []})))
            messages.append(self._make_assistant_summary(
                "Gaming PC: Windows 11 Pro, 8% CPU, 12/32GB RAM — all good. "
                "Plex: nobody's watching anything right now."
            ))

        elif scenario.category == "model_and_generate":
            messages.append(self._make_assistant_with_tool(
                "Let me set up the image generation stack.",
                ToolCall("dashboard.service_start", {"service": "comfyui"})))
            messages.append(self._make_tool_response(ToolResponse("dashboard.service_start", {
                "success": True, "service": "comfyui", "port": 8188,
            })))
            style = random.choice(["landscape", "portrait", "cyberpunk", "fantasy"])
            messages.append(self._make_assistant_with_tool(
                f"ComfyUI is up. Generating a {style} image.",
                ToolCall("comfyui.generate_image", {
                    "prompt": f"beautiful {style}, highly detailed, 8k",
                    "model": "FLUX.1-dev",
                    "steps": 20,
                })))
            messages.append(self._make_tool_response(ToolResponse("comfyui.generate_image", {
                "success": True, "output_path": f"/output/{style}_001.png",
                "seed": random.randint(100000, 999999), "time_seconds": round(random.uniform(8, 25), 1),
            })))
            messages.append(self._make_assistant_summary(
                f"Generated a {style} image with FLUX.1-dev — saved to the output folder."
            ))

        elif scenario.category == "tts_and_llm":
            messages.append(self._make_assistant_with_tool(
                "Checking if the LLM is running.",
                ToolCall("llm.server_status", {})))
            messages.append(self._make_tool_response(ToolResponse("llm.server_status", {
                "running": True, "model": "Qwen3.5-27B-Q5_K_XL", "port": 8080,
            })))
            messages.append(self._make_assistant_with_tool(
                "LLM is up. Let me generate some text and read it aloud with Jerry's voice.",
                ToolCall("tts.synthesize", {"text": "The stars above the mountain glowed with ancient light.",
                                            "voice": "jerry", "speed": 1.0})))
            messages.append(self._make_tool_response(ToolResponse("tts.synthesize", {
                "success": True, "output_path": "/tmp/tts_output.wav",
                "duration_seconds": 4.2, "voice": "jerry",
            })))
            messages.append(self._make_assistant_summary(
                "Done — generated the text and spoke it in Jerry's voice. Audio saved to /tmp/tts_output.wav."
            ))

        return GeneratedExample(messages=messages, domain=self.domain,
                                category=scenario.category, difficulty=scenario.difficulty,
                                tools_used=scenario.expected_tools)
