"""Synthetic data generator for ComfyUI image/video generation scenarios."""

import random

from .base import (
    BaseGenerator,
    GeneratedExample,
    Message,
    Scenario,
    ToolCall,
    ToolResponse,
)

IMAGE_PROMPTS = [
    "a cyberpunk city at night with neon reflections on wet streets",
    "portrait of a woman with flowing red hair, studio lighting, 8k",
    "a medieval castle on a cliff overlooking a stormy sea",
    "astronaut riding a horse on mars, cinematic lighting",
    "a cozy cabin in a snowy forest with warm light from windows",
    "hyperrealistic cat sitting on a stack of books, golden hour",
    "dark fantasy warrior with glowing sword in a misty forest",
    "japanese garden with cherry blossoms and a koi pond, serene",
    "steampunk airship flying over victorian london at sunset",
    "underwater scene with bioluminescent jellyfish, deep blue",
]

VIDEO_PROMPTS = [
    "a timelapse of clouds rolling over a mountain peak",
    "a woman walking through a field of sunflowers, camera tracking",
    "ocean waves crashing on rocks in slow motion",
    "a spaceship landing on an alien planet, cinematic",
    "rain falling on a city street at night, moody atmosphere",
]

FLUX_MODELS = [
    "flux1-dev.safetensors",
    "flux1-dev-fp8.safetensors",
]

WAN_MODELS = [
    "wan2.1_i2v_720p_14B_bf16.safetensors",
    "wan2.1_t2v_14B_bf16.safetensors",
]

LORAS = [
    ("celebrity/margot-robbie.safetensors", "Margot Robbie"),
    ("celebrity/ana-de-armas.safetensors", "Ana de Armas"),
    ("celebrity/chris-hemsworth.safetensors", "Chris Hemsworth"),
    ("style/anime-flat-color.safetensors", "Anime Flat Color"),
    ("style/oil-painting-v2.safetensors", "Oil Painting"),
    ("style/cinematic-film.safetensors", "Cinematic Film"),
    ("style/pixel-art.safetensors", "Pixel Art"),
    ("character/ahsoka-flux.safetensors", "Ahsoka Tano"),
    ("character/harley-quinn-flux.safetensors", "Harley Quinn"),
    ("wan/smooth-motion.safetensors", "Smooth Motion (Wan2.1)"),
    ("wan/camera-zoom.safetensors", "Camera Zoom (Wan2.1)"),
]

RESOLUTIONS = ["1024x1024", "1024x768", "768x1024", "1280x720", "1920x1080"]


class ComfyUIGenerator(BaseGenerator):
    domain = "comfyui"
    schema_files = ["comfyui.json"]

    def _build_scenarios(self) -> list[Scenario]:
        return [
            Scenario(
                domain="comfyui",
                category="generate_image",
                difficulty="medium",
                expected_tools=["comfyui.generate_image"],
                user_prompts=[
                    f"Generate an image: {p}" for p in IMAGE_PROMPTS[:5]
                ] + [
                    "Make me a cool cyberpunk wallpaper",
                    "Generate a fantasy landscape",
                    "Create a portrait with the oil painting LoRA",
                    "Make an image of a cat in pixel art style",
                ],
            ),
            Scenario(
                domain="comfyui",
                category="generate_video",
                difficulty="hard",
                expected_tools=["comfyui.generate_video"],
                user_prompts=[
                    f"Generate a video: {p}" for p in VIDEO_PROMPTS[:3]
                ] + [
                    "Make a short video of ocean waves",
                    "Generate a video of a spaceship landing",
                    "Create a timelapse video of clouds",
                ],
            ),
            Scenario(
                domain="comfyui",
                category="list_models",
                difficulty="easy",
                expected_tools=["comfyui.list_models"],
                user_prompts=[
                    "What models are available in ComfyUI?",
                    "List the loaded models",
                    "What checkpoints do I have?",
                    "Show me available diffusion models",
                ],
            ),
            Scenario(
                domain="comfyui",
                category="list_loras",
                difficulty="easy",
                expected_tools=["comfyui.list_loras"],
                user_prompts=[
                    "What LoRAs do I have?",
                    "List available LoRAs",
                    "Show me the celebrity LoRAs",
                    "What style LoRAs are loaded?",
                    "Which LoRAs can I use for images?",
                ],
            ),
            Scenario(
                domain="comfyui",
                category="run_workflow",
                difficulty="hard",
                expected_tools=["comfyui.run_workflow"],
                user_prompts=[
                    "Run the Z-Image Turbo workflow",
                    "Execute the FLUX base workflow",
                    "Run the Wan2.1 video workflow",
                    "Use the anime style workflow",
                    "Run the celebrity portrait workflow with Margot Robbie LoRA",
                ],
            ),
            Scenario(
                domain="comfyui",
                category="queue_status",
                difficulty="easy",
                expected_tools=["comfyui.queue_status"],
                user_prompts=[
                    "What's in the ComfyUI queue?",
                    "How many jobs are pending?",
                    "Is ComfyUI busy right now?",
                    "Check the generation queue",
                    "Any images being generated?",
                ],
            ),
        ]

    def generate_example(self, scenario: Scenario) -> GeneratedExample:
        prompt = scenario.random_prompt()
        messages: list[Message] = [self._make_user(prompt)]

        if scenario.category == "generate_image":
            img_prompt = random.choice(IMAGE_PROMPTS)
            resolution = random.choice(RESOLUTIONS[:3])  # square/landscape/portrait
            model = random.choice(FLUX_MODELS)
            use_lora = random.random() > 0.5
            lora = random.choice([l for l in LORAS if "wan" not in l[0]]) if use_lora else None

            args = {
                "prompt": img_prompt,
                "model": model,
                "resolution": resolution,
                "steps": random.choice([20, 25, 30]),
                "cfg_scale": round(random.uniform(3.0, 7.0), 1),
                "seed": random.randint(0, 2**32),
            }
            if lora:
                args["lora"] = lora[0]
                args["lora_strength"] = round(random.uniform(0.6, 1.0), 2)

            reasoning = f"Generating with FLUX"
            if lora:
                reasoning += f" and {lora[1]} LoRA"
            reasoning += "."

            messages.append(
                self._make_assistant_with_tool(reasoning, ToolCall("comfyui.generate_image", args))
            )
            gen_time = round(random.uniform(8.0, 45.0), 1)
            messages.append(
                self._make_tool_response(
                    ToolResponse("comfyui.generate_image", {
                        "success": True,
                        "output_path": f"/output/ComfyUI_{random.randint(10000, 99999)}.png",
                        "resolution": resolution,
                        "generation_time_s": gen_time,
                        "model": model,
                        "seed": args["seed"],
                    })
                )
            )
            messages.append(self._make_assistant_summary(
                f"Image generated in {gen_time}s at {resolution}. "
                f"Saved to the output folder. Seed: {args['seed']} (save this if you want to reproduce it)."
            ))

        elif scenario.category == "generate_video":
            vid_prompt = random.choice(VIDEO_PROMPTS)
            model = random.choice(WAN_MODELS)
            frames = random.choice([49, 81, 121])

            messages.append(
                self._make_assistant_with_tool(
                    "Generating video with Wan2.1. This will take a while.",
                    ToolCall("comfyui.generate_video", {
                        "prompt": vid_prompt,
                        "model": model,
                        "frames": frames,
                        "resolution": "1280x720",
                        "fps": 24,
                        "steps": random.choice([20, 30]),
                        "seed": random.randint(0, 2**32),
                    }),
                )
            )
            gen_time = round(random.uniform(120.0, 600.0), 1)
            messages.append(
                self._make_tool_response(
                    ToolResponse("comfyui.generate_video", {
                        "success": True,
                        "output_path": f"/output/ComfyUI_video_{random.randint(1000, 9999)}.mp4",
                        "frames": frames,
                        "duration_s": round(frames / 24, 1),
                        "generation_time_s": gen_time,
                        "model": model,
                    })
                )
            )
            messages.append(self._make_assistant_summary(
                f"Video generated — {frames} frames ({round(frames / 24, 1)}s at 24fps). "
                f"Took {round(gen_time / 60, 1)} minutes. Saved to the output folder."
            ))

        elif scenario.category == "list_models":
            messages.append(
                self._make_assistant_with_tool(
                    "Checking available models.",
                    ToolCall("comfyui.list_models", {}),
                )
            )
            messages.append(
                self._make_tool_response(
                    ToolResponse("comfyui.list_models", {
                        "checkpoints": [
                            {"name": m, "size_gb": round(random.uniform(5.0, 25.0), 1),
                             "type": "FLUX" if "flux" in m else "Wan2.1"}
                            for m in FLUX_MODELS + WAN_MODELS
                        ],
                        "clip_models": ["clip-l.safetensors", "t5-xxl-fp16.safetensors"],
                        "vae": ["flux-vae.safetensors"],
                    })
                )
            )
            messages.append(self._make_assistant_summary(
                f"You have {len(FLUX_MODELS)} FLUX models and {len(WAN_MODELS)} Wan2.1 models loaded. "
                f"Plus CLIP-L, T5-XXL, and the FLUX VAE. Ready to generate images and videos."
            ))

        elif scenario.category == "list_loras":
            messages.append(
                self._make_assistant_with_tool(
                    "Listing available LoRAs.",
                    ToolCall("comfyui.list_loras", {}),
                )
            )
            messages.append(
                self._make_tool_response(
                    ToolResponse("comfyui.list_loras", {
                        "loras": [
                            {"path": l[0], "name": l[1],
                             "type": "Wan2.1" if "wan" in l[0] else "FLUX",
                             "size_mb": random.randint(50, 500)}
                            for l in LORAS
                        ],
                        "total": len(LORAS),
                    })
                )
            )
            flux_loras = [l[1] for l in LORAS if "wan" not in l[0]]
            wan_loras = [l[1] for l in LORAS if "wan" in l[0]]
            messages.append(self._make_assistant_summary(
                f"{len(LORAS)} LoRAs available:\n"
                f"- FLUX ({len(flux_loras)}): {', '.join(flux_loras)}\n"
                f"- Wan2.1 ({len(wan_loras)}): {', '.join(wan_loras)}"
            ))

        elif scenario.category == "run_workflow":
            workflow = random.choice([
                "z-image-turbo", "flux-base", "wan21-video",
                "anime-style", "celebrity-portrait",
            ])
            workflow_label = workflow.replace("-", " ").title()
            messages.append(
                self._make_assistant_with_tool(
                    f"Running the {workflow_label} workflow.",
                    ToolCall("comfyui.run_workflow", {
                        "workflow": workflow,
                        "prompt": random.choice(IMAGE_PROMPTS),
                        "seed": random.randint(0, 2**32),
                    }),
                )
            )
            gen_time = round(random.uniform(5.0, 120.0), 1)
            messages.append(
                self._make_tool_response(
                    ToolResponse("comfyui.run_workflow", {
                        "success": True,
                        "workflow": workflow,
                        "output_path": f"/output/ComfyUI_{random.randint(10000, 99999)}.png",
                        "generation_time_s": gen_time,
                        "nodes_executed": random.randint(5, 25),
                    })
                )
            )
            messages.append(self._make_assistant_summary(
                f"{workflow_label} workflow complete in {gen_time}s. Output saved."
            ))

        elif scenario.category == "queue_status":
            messages.append(
                self._make_assistant_with_tool(
                    "Checking the queue.",
                    ToolCall("comfyui.queue_status", {}),
                )
            )
            pending = random.randint(0, 5)
            running = 1 if pending > 0 or random.random() > 0.5 else 0
            messages.append(
                self._make_tool_response(
                    ToolResponse("comfyui.queue_status", {
                        "running": running,
                        "pending": pending,
                        "completed_today": random.randint(0, 50),
                        "current_job": {
                            "workflow": random.choice(["flux-base", "z-image-turbo", "wan21-video"]),
                            "progress_pct": random.randint(0, 99),
                            "elapsed_s": random.randint(5, 300),
                        } if running else None,
                    })
                )
            )
            if running:
                messages.append(self._make_assistant_summary(
                    f"ComfyUI is currently generating ({pending} more in queue). "
                    f"Current job is in progress."
                ))
            elif pending > 0:
                messages.append(self._make_assistant_summary(
                    f"{pending} jobs queued, waiting to start."
                ))
            else:
                messages.append(self._make_assistant_summary(
                    "ComfyUI queue is empty — ready for new jobs."
                ))

        return GeneratedExample(
            messages=messages,
            domain=self.domain,
            category=scenario.category,
            difficulty=scenario.difficulty,
            tools_used=scenario.expected_tools,
        )
