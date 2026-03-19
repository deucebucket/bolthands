"""Synthetic data generator for cross-domain multi-service scenarios."""

import random

from .base import (
    BaseGenerator,
    GeneratedExample,
    Message,
    Scenario,
    ToolCall,
    ToolResponse,
)


class CrossDomainGenerator(BaseGenerator):
    domain = "cross_domain"
    schema_files = [
        "dashboard.json", "plex.json", "arr.json", "comfyui.json",
        "tts.json", "llm.json", "windows.json", "tailscale.json",
        "systemd.json",
    ]

    def _build_scenarios(self) -> list[Scenario]:
        return [
            Scenario(
                domain="cross_domain",
                category="arr_plex",
                difficulty="hard",
                expected_tools=["sonarr.queue", "plex.now_playing"],
                user_prompts=[
                    "Check what's downloading in Sonarr and who's watching Plex",
                    "Show me the download queue AND active Plex streams",
                    "What's going on with my media — downloads and playback?",
                    "Give me a media status report",
                ],
            ),
            Scenario(
                domain="cross_domain",
                category="service_swap",
                difficulty="hard",
                expected_tools=["dashboard.service_stop", "dashboard.service_start"],
                user_prompts=[
                    "Stop the LLM server and start ComfyUI",
                    "Swap to image generation mode",
                    "Kill the language model and fire up image gen — I need VRAM",
                    "Switch from coding to art mode",
                ],
            ),
            Scenario(
                domain="cross_domain",
                category="radarr_plex_scan",
                difficulty="hard",
                expected_tools=["radarr.add_movie", "plex.library_scan"],
                user_prompts=[
                    "Add Dune Part Two to Radarr and scan Plex when it's ready",
                    "Download Oppenheimer and update the Plex library",
                    "Grab Inception via Radarr, then refresh Plex",
                    "Add a movie to Radarr and kick off a Plex scan",
                ],
            ),
            Scenario(
                domain="cross_domain",
                category="windows_gpu_check",
                difficulty="medium",
                expected_tools=["windows.system_info", "dashboard.gpu_status"],
                user_prompts=[
                    "Check the Windows PC health AND my GPU status",
                    "Give me a full system report — Windows box and GPU",
                    "How are both my machines doing?",
                    "System status for the Windows PC and the Linux GPU rig",
                ],
            ),
            Scenario(
                domain="cross_domain",
                category="comfyui_tts",
                difficulty="hard",
                expected_tools=["comfyui.generate_image", "tts.synthesize"],
                user_prompts=[
                    "Generate an image with ComfyUI and then describe it with TTS",
                    "Make a cyberpunk wallpaper and narrate a description of it",
                    "Create an image and have Jerry describe what it looks like",
                    "Generate art and read out a description using TTS",
                ],
            ),
            Scenario(
                domain="cross_domain",
                category="full_media_report",
                difficulty="hard",
                expected_tools=["plex.server_status", "sonarr.calendar", "radarr.queue"],
                user_prompts=[
                    "Give me a full media report — Plex, Sonarr, and Radarr",
                    "What's the status of my entire media stack?",
                    "Media overview: what's playing, downloading, and upcoming",
                    "Full status report for all media services",
                ],
            ),
            Scenario(
                domain="cross_domain",
                category="tailscale_service",
                difficulty="medium",
                expected_tools=["tailscale.ping", "dashboard.service_list"],
                user_prompts=[
                    "Check if the NAS is reachable and what services are running locally",
                    "Ping the remote PC and show me my dashboard status",
                    "Is my home network accessible? And what's running on this machine?",
                ],
            ),
            Scenario(
                domain="cross_domain",
                category="system_health",
                difficulty="medium",
                expected_tools=["dashboard.gpu_status", "dashboard.system_status", "systemd.unit_list"],
                user_prompts=[
                    "Full system health check — GPU, CPU, services",
                    "How's everything running?",
                    "Give me the full status of the machine",
                ],
            ),
            Scenario(
                domain="cross_domain",
                category="model_and_generate",
                difficulty="hard",
                expected_tools=["dashboard.service_start", "comfyui.generate_image"],
                user_prompts=[
                    "Make sure ComfyUI is running and then generate a landscape",
                    "Start the image gen stack and make me a portrait",
                    "Fire up ComfyUI and create some cyberpunk art",
                ],
            ),
            Scenario(
                domain="cross_domain",
                category="tts_and_llm",
                difficulty="medium",
                expected_tools=["llm.server_status", "tts.synthesize"],
                user_prompts=[
                    "Is the LLM running? If so, generate some text and read it aloud",
                    "Use the chat model to write a poem and then TTS it with Jerry's voice",
                    "Check the LLM and narrate something with TTS",
                ],
            ),
        ]

    def generate_example(self, scenario: Scenario) -> GeneratedExample:
        prompt = scenario.random_prompt()
        messages: list[Message] = [self._make_user(prompt)]

        if scenario.category == "arr_plex":
            # Step 1: Check Sonarr queue
            messages.append(
                self._make_assistant_with_tool(
                    "Let me check both. Starting with the download queue.",
                    ToolCall("sonarr.queue", {}),
                )
            )
            shows = [
                ("The Last of Us - S02E05", "HD-1080p", 62),
                ("Arcane - S02E08", "Ultra-HD", 88),
            ]
            messages.append(
                self._make_tool_response(
                    ToolResponse("sonarr.queue", {
                        "items": [
                            {"title": s[0], "quality": s[1], "progress_pct": s[2],
                             "size_gb": round(random.uniform(1.5, 8.0), 1),
                             "eta": f"{random.randint(5, 60)}min", "status": "downloading"}
                            for s in shows
                        ],
                        "total": len(shows),
                    })
                )
            )
            # Step 2: Check Plex
            messages.append(
                self._make_assistant_with_tool(
                    "Now checking Plex streams.",
                    ToolCall("plex.now_playing", {}),
                )
            )
            num_streams = random.choice([0, 1, 2])
            streams = []
            if num_streams > 0:
                stream_data = [
                    ("deuce", "Blade Runner 2049", "4K HDR", "Shield TV"),
                    ("sarah", "Severance S02E08", "1080p", "Apple TV"),
                    ("mike", "The Bear S03E01", "1080p", "Plex Web"),
                ]
                streams = [
                    {"user": s[0], "title": s[1], "quality": s[2],
                     "progress_pct": random.randint(15, 85), "transcode": False, "player": s[3]}
                    for s in random.sample(stream_data, k=min(num_streams, len(stream_data)))
                ]
            messages.append(
                self._make_tool_response(
                    ToolResponse("plex.now_playing", {
                        "streams": streams,
                        "total_streams": len(streams),
                    })
                )
            )
            dl_summary = ", ".join(f"{s[0]} ({s[2]}%)" for s in shows)
            if streams:
                stream_summary = ", ".join(f"{s['user']} watching {s['title']}" for s in streams)
                messages.append(self._make_assistant_summary(
                    f"Media status:\n"
                    f"- Downloads: {len(shows)} items — {dl_summary}\n"
                    f"- Plex: {stream_summary}"
                ))
            else:
                messages.append(self._make_assistant_summary(
                    f"Downloads: {len(shows)} items — {dl_summary}. Plex: nobody's watching right now."
                ))

        elif scenario.category == "service_swap":
            # Step 1: Stop LLM
            messages.append(
                self._make_assistant_with_tool(
                    "Stopping the LLM server first to free VRAM.",
                    ToolCall("dashboard.service_stop", {"service": "llm-chat"}),
                )
            )
            vram_freed = random.choice([14, 16, 18, 20])
            messages.append(
                self._make_tool_response(
                    ToolResponse("dashboard.service_stop", {
                        "success": True,
                        "service": "llm-chat",
                        "status": "stopped",
                        "vram_freed_gb": vram_freed,
                    })
                )
            )
            # Step 2: Start ComfyUI
            messages.append(
                self._make_assistant_with_tool(
                    f"Freed {vram_freed}GB VRAM. Now starting ComfyUI.",
                    ToolCall("dashboard.service_start", {"service": "comfyui"}),
                )
            )
            messages.append(
                self._make_tool_response(
                    ToolResponse("dashboard.service_start", {
                        "success": True,
                        "service": "comfyui",
                        "status": "running",
                        "port": 8188,
                        "url": "http://localhost:8188",
                    })
                )
            )
            messages.append(self._make_assistant_summary(
                f"Done — stopped the LLM server (freed {vram_freed}GB VRAM) and started ComfyUI at localhost:8188. "
                f"You're in image generation mode now."
            ))

        elif scenario.category == "radarr_plex_scan":
            movie = random.choice([
                ("Dune: Part Two", "tt15239678", 2024),
                ("Oppenheimer", "tt15398776", 2023),
                ("Inception", "tt1375666", 2010),
            ])
            # Step 1: Add to Radarr
            messages.append(
                self._make_assistant_with_tool(
                    f"Adding \"{movie[0]}\" to Radarr.",
                    ToolCall("radarr.add_movie", {
                        "title": movie[0],
                        "imdb_id": movie[1],
                        "quality_profile": "Ultra-HD",
                        "monitored": True,
                        "search_now": True,
                    }),
                )
            )
            messages.append(
                self._make_tool_response(
                    ToolResponse("radarr.add_movie", {
                        "success": True,
                        "title": movie[0],
                        "year": movie[2],
                        "quality_profile": "Ultra-HD",
                        "status": "searching",
                    })
                )
            )
            # Step 2: Scan Plex
            messages.append(
                self._make_assistant_with_tool(
                    f"\"{movie[0]}\" is being searched for. Scanning Plex so it picks up anything new.",
                    ToolCall("plex.library_scan", {"library": "Movies"}),
                )
            )
            messages.append(
                self._make_tool_response(
                    ToolResponse("plex.library_scan", {
                        "success": True,
                        "library": "Movies",
                        "status": "scanning",
                        "items_before": random.randint(200, 1500),
                    })
                )
            )
            messages.append(self._make_assistant_summary(
                f"Added \"{movie[0]}\" to Radarr (searching for Ultra-HD release) and kicked off a Plex Movies library scan. "
                f"Once Radarr downloads it, Plex will pick it up on the next scan."
            ))

        elif scenario.category == "windows_gpu_check":
            hostname = random.choice(["DESKTOP-7K3M1NQ", "GAMING-RIG"])
            # Step 1: Windows system info
            messages.append(
                self._make_assistant_with_tool(
                    "Checking the Windows PC first.",
                    ToolCall("windows.system_info", {"hostname": hostname}),
                )
            )
            messages.append(
                self._make_tool_response(
                    ToolResponse("windows.system_info", {
                        "hostname": hostname,
                        "os": "Windows 11 Pro 23H2",
                        "build": "22631.3296",
                        "cpu": "Intel Core i7-13700K",
                        "ram_gb": 32,
                        "uptime": f"{random.randint(1, 14)}d",
                    })
                )
            )
            # Step 2: Local GPU
            vram_used = random.randint(4, 18)
            temp = random.randint(45, 75)
            messages.append(
                self._make_assistant_with_tool(
                    "Now checking the local GPU.",
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
                        "gpu_utilization_pct": random.randint(5, 60),
                        "power_draw_w": random.randint(80, 250),
                    })
                )
            )
            messages.append(self._make_assistant_summary(
                f"System report:\n"
                f"- Windows ({hostname}): Win 11 Pro, i7-13700K, 32GB RAM — running fine\n"
                f"- Local GPU (RTX 3090): {vram_used}/24GB VRAM, {temp}C — looking good"
            ))

        elif scenario.category == "comfyui_tts":
            img_prompt = random.choice([
                "a cyberpunk city at night with neon reflections on wet streets",
                "a medieval castle on a cliff overlooking a stormy sea",
                "an astronaut floating in space with Earth in the background",
            ])
            # Step 1: Generate image
            messages.append(
                self._make_assistant_with_tool(
                    "Generating the image first.",
                    ToolCall("comfyui.generate_image", {
                        "prompt": img_prompt,
                        "model": "flux1-dev.safetensors",
                        "resolution": "1024x1024",
                        "steps": 25,
                        "cfg_scale": 4.5,
                        "seed": random.randint(0, 2**32),
                    }),
                )
            )
            output_path = f"/output/ComfyUI_{random.randint(10000, 99999)}.png"
            gen_time = round(random.uniform(10.0, 30.0), 1)
            messages.append(
                self._make_tool_response(
                    ToolResponse("comfyui.generate_image", {
                        "success": True,
                        "output_path": output_path,
                        "resolution": "1024x1024",
                        "generation_time_s": gen_time,
                    })
                )
            )
            # Step 2: TTS description
            descriptions = {
                "cyberpunk": "A sprawling cyberpunk cityscape at night, bathed in neon light. Rain-slicked streets reflect holographic advertisements, while towering skyscrapers pierce the smog-filled sky.",
                "medieval": "A majestic medieval castle perched atop a rocky cliff, its ancient stones battered by crashing waves below. Storm clouds gather ominously overhead as lightning illuminates the scene.",
                "astronaut": "A lone astronaut floats weightlessly in the void of space, the brilliant blue marble of Earth glowing behind them. Stars stretch infinitely in every direction.",
            }
            key = "cyberpunk" if "cyberpunk" in img_prompt else "medieval" if "medieval" in img_prompt else "astronaut"
            description = descriptions[key]
            messages.append(
                self._make_assistant_with_tool(
                    "Image generated. Now narrating a description.",
                    ToolCall("tts.synthesize", {
                        "text": description,
                        "voice": "jerry",
                        "language": "en",
                    }),
                )
            )
            messages.append(
                self._make_tool_response(
                    ToolResponse("tts.synthesize", {
                        "success": True,
                        "voice": "jerry",
                        "output_path": f"/tmp/tts_output_{random.randint(1000, 9999)}.wav",
                        "duration_s": round(random.uniform(6.0, 12.0), 1),
                        "sample_rate": 32000,
                    })
                )
            )
            messages.append(self._make_assistant_summary(
                f"Done — generated the image and narrated a description in Jerry's voice. "
                f"Image at {output_path}, audio ready to play."
            ))

        elif scenario.category == "full_media_report":
            # Step 1: Plex status
            movies_count = random.randint(300, 1200)
            shows_count = random.randint(50, 300)
            active_streams = random.randint(0, 2)
            messages.append(
                self._make_assistant_with_tool(
                    "Pulling everything together. Starting with Plex.",
                    ToolCall("plex.server_status", {}),
                )
            )
            messages.append(
                self._make_tool_response(
                    ToolResponse("plex.server_status", {
                        "online": True,
                        "version": "1.41.2.9200",
                        "libraries": {"Movies": movies_count, "TV Shows": shows_count},
                        "active_streams": active_streams,
                        "transcode_hw": "NVIDIA NVENC",
                    })
                )
            )
            # Step 2: Sonarr calendar
            messages.append(
                self._make_assistant_with_tool(
                    "Plex is online. Checking upcoming episodes.",
                    ToolCall("sonarr.calendar", {"days": 7}),
                )
            )
            upcoming = [
                {"series": "The Last of Us", "episode": "S02E06", "title": "The Crossing", "air_date": "2026-03-21"},
                {"series": "Severance", "episode": "S02E10", "title": "Finale", "air_date": "2026-03-22"},
            ]
            messages.append(
                self._make_tool_response(
                    ToolResponse("sonarr.calendar", {"episodes": upcoming})
                )
            )
            # Step 3: Radarr queue
            messages.append(
                self._make_assistant_with_tool(
                    "Now checking movie downloads.",
                    ToolCall("radarr.queue", {}),
                )
            )
            radarr_items = random.randint(0, 2)
            rqueue = [
                {"title": random.choice(["John Wick: Chapter 4", "Dune: Part Two", "Oppenheimer"]),
                 "quality": "Ultra-HD", "size_gb": round(random.uniform(20.0, 50.0), 1),
                 "progress_pct": random.randint(10, 90), "eta": f"{random.randint(10, 120)}min",
                 "status": "downloading"}
                for _ in range(radarr_items)
            ]
            messages.append(
                self._make_tool_response(
                    ToolResponse("radarr.queue", {"items": rqueue, "total": radarr_items})
                )
            )
            report_lines = [
                f"- Plex: Online ({movies_count} movies, {shows_count} shows), {active_streams} active stream(s)",
                f"- Sonarr: {len(upcoming)} episodes this week — " + ", ".join(f"{e['series']} {e['episode']} ({e['air_date']})" for e in upcoming),
            ]
            if radarr_items > 0:
                report_lines.append(f"- Radarr: {radarr_items} movie(s) downloading — " + ", ".join(f"{r['title']} ({r['progress_pct']}%)" for r in rqueue))
            else:
                report_lines.append("- Radarr: Queue empty, nothing downloading")
            messages.append(self._make_assistant_summary(
                "Full media report:\n" + "\n".join(report_lines)
            ))

        elif scenario.category == "tailscale_service":
            target = random.choice([
                ("nas-synology", "100.64.1.5"),
                ("pi-homelab", "100.64.1.6"),
                ("windows-pc", "100.64.1.4"),
            ])
            # Step 1: Tailscale ping
            latency = round(random.uniform(2.0, 30.0), 1)
            messages.append(
                self._make_assistant_with_tool(
                    f"Pinging {target[0]} through Tailscale.",
                    ToolCall("tailscale.ping", {"hostname": target[0]}),
                )
            )
            messages.append(
                self._make_tool_response(
                    ToolResponse("tailscale.ping", {
                        "hostname": target[0],
                        "ip": target[1],
                        "latency_ms": latency,
                        "direct": True,
                        "via": "direct",
                        "pong": True,
                    })
                )
            )
            # Step 2: Dashboard service list
            messages.append(
                self._make_assistant_with_tool(
                    f"{target[0]} is reachable. Now checking local services.",
                    ToolCall("dashboard.service_list", {}),
                )
            )
            services = [
                ("comfyui", "ComfyUI", "running", 8188),
                ("llm-chat", "LLM Chat", "stopped", None),
                ("f5tts", "F5-TTS", "stopped", None),
                ("ace-step", "ACE-Step", "stopped", None),
                ("searxng", "SearXNG", "running", 8888),
            ]
            messages.append(
                self._make_tool_response(
                    ToolResponse("dashboard.service_list", {
                        "services": [
                            {"id": s[0], "name": s[1], "status": s[2], "port": s[3]}
                            for s in services
                        ]
                    })
                )
            )
            running = [s[1] for s in services if s[2] == "running"]
            messages.append(self._make_assistant_summary(
                f"Network & services:\n"
                f"- {target[0]} reachable via Tailscale ({latency}ms, direct connection)\n"
                f"- Local: {', '.join(running)} running. Everything else stopped."
            ))

        elif scenario.category == "system_health":
            # Step 1: GPU
            vram_used = random.randint(4, 18)
            temp = random.randint(40, 70)
            gpu_util = random.randint(5, 50)
            messages.append(
                self._make_assistant_with_tool(
                    "Running full health check.",
                    ToolCall("dashboard.gpu_status", {}),
                )
            )
            messages.append(
                self._make_tool_response(
                    ToolResponse("dashboard.gpu_status", {
                        "gpu": "NVIDIA RTX 3090",
                        "vram_used_gb": vram_used,
                        "vram_total_gb": 24,
                        "temperature_c": temp,
                        "gpu_utilization_pct": gpu_util,
                    })
                )
            )
            # Step 2: System
            cpu = random.randint(5, 40)
            ram = random.randint(12, 40)
            disk = random.randint(30, 70)
            messages.append(
                self._make_assistant_with_tool(
                    "GPU looks good. Checking system.",
                    ToolCall("dashboard.system_status", {}),
                )
            )
            messages.append(
                self._make_tool_response(
                    ToolResponse("dashboard.system_status", {
                        "cpu_usage_pct": cpu,
                        "ram_used_gb": ram,
                        "ram_total_gb": 64,
                        "disk_used_pct": disk,
                        "uptime": f"{random.randint(1, 30)}d",
                    })
                )
            )
            # Step 3: Failed services
            messages.append(
                self._make_assistant_with_tool(
                    "System healthy. Checking for failed services.",
                    ToolCall("systemd.unit_list", {"type": "service", "state": "failed"}),
                )
            )
            messages.append(
                self._make_tool_response(
                    ToolResponse("systemd.unit_list", {"units": []})
                )
            )
            messages.append(self._make_assistant_summary(
                f"Everything looks great:\n"
                f"- GPU: {vram_used}/24GB VRAM, {temp}C, {gpu_util}% utilization\n"
                f"- CPU: {cpu}%, RAM: {ram}/64GB, Disk: {disk}%\n"
                f"- No failed services\n"
                f"All systems nominal."
            ))

        elif scenario.category == "model_and_generate":
            # Step 1: Start ComfyUI
            messages.append(
                self._make_assistant_with_tool(
                    "Making sure ComfyUI is running.",
                    ToolCall("dashboard.service_start", {"service": "comfyui"}),
                )
            )
            messages.append(
                self._make_tool_response(
                    ToolResponse("dashboard.service_start", {
                        "success": True,
                        "service": "comfyui",
                        "status": "running",
                        "port": 8188,
                    })
                )
            )
            # Step 2: Generate
            style = random.choice(["landscape", "portrait", "cyberpunk city", "fantasy castle"])
            img_prompt = f"beautiful {style}, highly detailed, cinematic lighting, 8k resolution"
            messages.append(
                self._make_assistant_with_tool(
                    f"ComfyUI is up. Generating a {style} image.",
                    ToolCall("comfyui.generate_image", {
                        "prompt": img_prompt,
                        "model": "flux1-dev.safetensors",
                        "resolution": "1024x1024",
                        "steps": 25,
                        "cfg_scale": 4.5,
                        "seed": random.randint(0, 2**32),
                    }),
                )
            )
            gen_time = round(random.uniform(8.0, 25.0), 1)
            seed = random.randint(100000, 999999)
            messages.append(
                self._make_tool_response(
                    ToolResponse("comfyui.generate_image", {
                        "success": True,
                        "output_path": f"/output/{style.replace(' ', '_')}_{seed}.png",
                        "resolution": "1024x1024",
                        "generation_time_s": gen_time,
                        "seed": seed,
                    })
                )
            )
            messages.append(self._make_assistant_summary(
                f"Generated a {style} image with FLUX in {gen_time}s. Saved to the output folder. Seed: {seed}."
            ))

        elif scenario.category == "tts_and_llm":
            # Step 1: Check LLM
            messages.append(
                self._make_assistant_with_tool(
                    "Checking if the LLM is running.",
                    ToolCall("llm.server_status", {}),
                )
            )
            model = random.choice(["Qwen3.5-27B UD-Q5_K_XL", "GLM-4.7-Flash Q4_K_XL"])
            messages.append(
                self._make_tool_response(
                    ToolResponse("llm.server_status", {
                        "status": "running",
                        "model": model,
                        "port": 8080,
                        "tokens_per_second": round(random.uniform(30.0, 90.0), 1),
                    })
                )
            )
            # Step 2: TTS
            text = random.choice([
                "The stars above the mountain glowed with ancient light, whispering secrets of a forgotten age.",
                "In the quiet hours before dawn, the city sleeps beneath a blanket of mist and possibility.",
                "Beyond the horizon lies a world untouched by time, where rivers run silver and forests sing.",
            ])
            messages.append(
                self._make_assistant_with_tool(
                    f"LLM is up running {model}. Now synthesizing speech.",
                    ToolCall("tts.synthesize", {
                        "text": text,
                        "voice": "jerry",
                        "language": "en",
                    }),
                )
            )
            duration = round(random.uniform(3.0, 8.0), 1)
            messages.append(
                self._make_tool_response(
                    ToolResponse("tts.synthesize", {
                        "success": True,
                        "voice": "jerry",
                        "output_path": f"/tmp/tts_output_{random.randint(1000, 9999)}.wav",
                        "duration_s": duration,
                        "sample_rate": 32000,
                    })
                )
            )
            messages.append(self._make_assistant_summary(
                f"Done — LLM is running ({model}) and I've generated {duration}s of speech in Jerry's voice. Audio ready to play."
            ))

        return GeneratedExample(
            messages=messages,
            domain=self.domain,
            category=scenario.category,
            difficulty=scenario.difficulty,
            tools_used=scenario.expected_tools,
        )
