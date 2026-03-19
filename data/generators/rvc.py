"""Synthetic data generator for RVC (Retrieval-based Voice Conversion) scenarios."""

import random

from .base import (
    BaseGenerator,
    GeneratedExample,
    Message,
    Scenario,
    ToolCall,
    ToolResponse,
)

RVC_MODELS = [
    ("jerry", "Jerry (epoch 79)", "jerry_79e_9401s_best_epoch.pth"),
    ("drake", "Drake AI", "drake_v2_40e.pth"),
    ("morgan_freeman", "Morgan Freeman", "morgan_freeman_60e.pth"),
    ("anime_girl", "Anime Girl", "anime_girl_v3_50e.pth"),
    ("deep_bass", "Deep Bass Male", "deep_bass_30e.pth"),
]

AUDIO_INPUTS = [
    "~/Music/input/song_vocals.wav",
    "~/Music/input/podcast_clip.mp3",
    "~/Music/input/singing_sample.wav",
    "~/Music/input/voice_memo.m4a",
    "~/Music/input/cover_vocals.wav",
    "/tmp/tts_output.wav",
]

AUDIO_OUTPUTS = [
    "~/Music/Jericho Marz - Jerry Voice/",
    "~/Music/converted/",
    "~/Music/output/",
]

TRAINING_DATASETS = [
    ("jerry_dataset", "~/ai-suite/RVC/assets/datasets/jerry/", 205, 27.0),
    ("narrator_dataset", "~/ai-suite/RVC/assets/datasets/narrator/", 150, 18.5),
    ("singer_dataset", "~/ai-suite/RVC/assets/datasets/singer/", 300, 35.0),
]

PITCH_METHODS = ["rmvpe", "crepe", "harvest", "pm"]


class RVCGenerator(BaseGenerator):
    domain = "rvc"
    schema_files = ["rvc.json"]

    def _build_scenarios(self) -> list[Scenario]:
        return [
            Scenario(
                domain="rvc",
                category="convert_voice",
                difficulty="medium",
                expected_tools=["rvc.convert"],
                user_prompts=[
                    "Convert this song to Jerry's voice",
                    "Run RVC on the vocal track",
                    "Change the vocals to sound like Morgan Freeman",
                    "Convert my voice memo using the anime voice model",
                    "Process the singing sample with the Drake model",
                    "Make this audio sound like Jerry",
                ],
            ),
            Scenario(
                domain="rvc",
                category="train_model",
                difficulty="hard",
                expected_tools=["rvc.train"],
                user_prompts=[
                    "Train a new RVC model from my dataset",
                    "Start training with the narrator voice samples",
                    "Create a new voice model from these audio files",
                    "Begin RVC training — 50 epochs",
                    "Train a model using the Jerry dataset with more epochs",
                ],
            ),
            Scenario(
                domain="rvc",
                category="list_models",
                difficulty="easy",
                expected_tools=["rvc.list_models"],
                user_prompts=[
                    "What RVC models do I have?",
                    "List available voice models",
                    "Show me the trained RVC models",
                    "Which voice conversion models are available?",
                ],
            ),
            Scenario(
                domain="rvc",
                category="infer",
                difficulty="medium",
                expected_tools=["rvc.infer"],
                user_prompts=[
                    "Quick inference with the Jerry model on this clip",
                    "Run a fast voice conversion test",
                    "Test the new model with a short sample",
                    "Do a quick RVC inference",
                    "Preview how this would sound with the Drake voice",
                ],
            ),
        ]

    def generate_example(self, scenario: Scenario) -> GeneratedExample:
        prompt = scenario.random_prompt()
        messages: list[Message] = [self._make_user(prompt)]

        if scenario.category == "convert_voice":
            model = random.choice(RVC_MODELS)
            input_audio = random.choice(AUDIO_INPUTS)
            pitch_shift = random.choice([0, 0, -2, 2, -4, 4, 12, -12])
            pitch_method = random.choice(PITCH_METHODS)

            messages.append(
                self._make_assistant_with_tool(
                    f"Converting with the {model[1]} model.",
                    ToolCall("rvc.convert", {
                        "model": model[2],
                        "input_audio": input_audio,
                        "pitch_shift": pitch_shift,
                        "pitch_method": pitch_method,
                        "index_rate": 0.75,
                        "filter_radius": 3,
                    }),
                )
            )
            duration = round(random.uniform(30.0, 300.0), 1)
            output = f"{random.choice(AUDIO_OUTPUTS)}{model[0]}_{random.randint(1000, 9999)}.wav"
            messages.append(
                self._make_tool_response(
                    ToolResponse("rvc.convert", {
                        "success": True,
                        "model": model[2],
                        "input_audio": input_audio,
                        "output_audio": output,
                        "duration_s": duration,
                        "processing_time_s": round(duration * random.uniform(0.3, 0.8), 1),
                        "pitch_shift": pitch_shift,
                    })
                )
            )
            messages.append(self._make_assistant_summary(
                f"Voice conversion complete using {model[1]}. "
                f"Output saved to {output}. "
                f"{'Pitch shifted ' + str(pitch_shift) + ' semitones. ' if pitch_shift != 0 else ''}"
                f"Give it a listen."
            ))

        elif scenario.category == "train_model":
            dataset = random.choice(TRAINING_DATASETS)
            epochs = random.choice([30, 50, 80, 100])
            batch_size = random.choice([8, 16])

            messages.append(
                self._make_assistant_with_tool(
                    f"Starting RVC training with the {dataset[0]} dataset ({dataset[2]} segments, {dataset[3]} minutes of audio).",
                    ToolCall("rvc.train", {
                        "dataset_name": dataset[0],
                        "dataset_path": dataset[1],
                        "epochs": epochs,
                        "batch_size": batch_size,
                        "sample_rate": 40000,
                        "save_interval": 10,
                    }),
                )
            )
            best_epoch = random.randint(int(epochs * 0.6), epochs)
            messages.append(
                self._make_tool_response(
                    ToolResponse("rvc.train", {
                        "success": True,
                        "dataset_name": dataset[0],
                        "epochs_completed": epochs,
                        "best_epoch": best_epoch,
                        "best_model": f"{dataset[0]}_{best_epoch}e.pth",
                        "training_time_min": round(epochs * random.uniform(1.5, 4.0), 1),
                        "final_loss": round(random.uniform(0.02, 0.15), 4),
                        "segments": dataset[2],
                    })
                )
            )
            messages.append(self._make_assistant_summary(
                f"Training complete — {epochs} epochs finished. "
                f"Best model at epoch {best_epoch} (loss: {round(random.uniform(0.02, 0.15), 4)}). "
                f"Model saved as {dataset[0]}_{best_epoch}e.pth. Ready for inference."
            ))

        elif scenario.category == "list_models":
            messages.append(
                self._make_assistant_with_tool(
                    "Checking available RVC models.",
                    ToolCall("rvc.list_models", {}),
                )
            )
            messages.append(
                self._make_tool_response(
                    ToolResponse("rvc.list_models", {
                        "models": [
                            {"name": m[0], "display_name": m[1], "file": m[2],
                             "size_mb": random.randint(50, 200),
                             "has_index": random.choice([True, True, False])}
                            for m in RVC_MODELS
                        ],
                        "total": len(RVC_MODELS),
                    })
                )
            )
            model_names = [m[1] for m in RVC_MODELS]
            messages.append(self._make_assistant_summary(
                f"{len(RVC_MODELS)} RVC models available: {', '.join(model_names)}."
            ))

        elif scenario.category == "infer":
            model = random.choice(RVC_MODELS)
            input_audio = random.choice(AUDIO_INPUTS)

            messages.append(
                self._make_assistant_with_tool(
                    f"Running quick inference with {model[1]}.",
                    ToolCall("rvc.infer", {
                        "model": model[2],
                        "input_audio": input_audio,
                        "pitch_shift": 0,
                    }),
                )
            )
            messages.append(
                self._make_tool_response(
                    ToolResponse("rvc.infer", {
                        "success": True,
                        "model": model[2],
                        "output_audio": f"/tmp/rvc_preview_{random.randint(1000, 9999)}.wav",
                        "duration_s": round(random.uniform(5.0, 30.0), 1),
                        "processing_time_s": round(random.uniform(1.0, 10.0), 1),
                    })
                )
            )
            messages.append(self._make_assistant_summary(
                f"Quick inference done with {model[1]}. Preview audio is ready — have a listen."
            ))

        return GeneratedExample(
            messages=messages,
            domain=self.domain,
            category=scenario.category,
            difficulty=scenario.difficulty,
            tools_used=scenario.expected_tools,
        )
