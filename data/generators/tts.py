"""Synthetic data generator for TTS (GPT-SoVITS + F5-TTS) scenarios."""

import random

from .base import (
    BaseGenerator,
    GeneratedExample,
    Message,
    Scenario,
    ToolCall,
    ToolResponse,
)

VOICES = [
    ("jerry", "Jerry (GPT-SoVITS v2, cloned)"),
    ("default", "Default (GPT-SoVITS built-in)"),
    ("en_female_1", "English Female 1 (F5-TTS)"),
    ("en_male_1", "English Male 1 (F5-TTS)"),
    ("narrator", "Narrator (F5-TTS, deep male)"),
]

TEXTS = [
    "Welcome to the wasteland, wanderer. It's dangerous out here alone.",
    "The quick brown fox jumps over the lazy dog.",
    "In a world where technology has surpassed human understanding, one man dares to ask why.",
    "Hey, what's going on? I haven't seen you around here before.",
    "The settlement needs your help. I'll mark it on your map.",
    "War. War never changes. But men do, through the roads they walk.",
    "Attention all personnel, this is a level five security alert.",
    "Good morning! Today's forecast calls for partly cloudy skies with a high of 72.",
    "I used to be an adventurer like you, then I took an arrow to the knee.",
    "The night is dark and full of terrors, but the fire burns them all away.",
]

REFERENCE_AUDIOS = [
    "data/jerry/ref_v3.wav",
    "data/samples/narrator_ref.wav",
    "data/samples/female_ref.wav",
    "data/samples/male_ref.wav",
]

LANGUAGES = ["en", "zh", "ja", "auto"]


class TTSGenerator(BaseGenerator):
    domain = "tts"
    schema_files = ["tts.json"]

    def _build_scenarios(self) -> list[Scenario]:
        return [
            Scenario(
                domain="tts",
                category="synthesize_speech",
                difficulty="easy",
                expected_tools=["tts.synthesize"],
                user_prompts=[
                    "Say 'Welcome to the wasteland' in Jerry's voice",
                    "Generate speech: 'The quick brown fox jumps over the lazy dog'",
                    "Have the TTS say 'Good morning everyone'",
                    "Speak this text: 'War never changes'",
                    "Use the narrator voice to say 'In a world beyond imagination'",
                    "Read this out loud: 'Hey, what's going on?'",
                    "TTS this for me: 'Attention all personnel'",
                ],
            ),
            Scenario(
                domain="tts",
                category="synthesize_f5",
                difficulty="easy",
                expected_tools=["f5tts.synthesize"],
                user_prompts=[
                    "Use F5-TTS to say 'Hello world'",
                    "Generate speech with F5-TTS: 'Testing one two three'",
                    "Have F5 speak this text",
                    "Use the F5 voice cloner to say something",
                ],
            ),
            Scenario(
                domain="tts",
                category="clone_voice",
                difficulty="hard",
                expected_tools=["tts.clone_voice"],
                user_prompts=[
                    "Clone a voice from this audio sample",
                    "Create a new TTS voice from a recording",
                    "I have a voice sample, can you clone it?",
                    "Set up voice cloning with this reference audio",
                    "Train a new voice from my audio file",
                ],
            ),
            Scenario(
                domain="tts",
                category="list_voices",
                difficulty="easy",
                expected_tools=["tts.list_voices"],
                user_prompts=[
                    "What voices are available?",
                    "List TTS voices",
                    "Show me the available voices",
                    "What voices can I use?",
                    "Which voice models are loaded?",
                ],
            ),
            Scenario(
                domain="tts",
                category="set_voice",
                difficulty="easy",
                expected_tools=["tts.set_voice"],
                user_prompts=[
                    "Switch to Jerry's voice",
                    "Use the narrator voice",
                    "Change the TTS voice to the default",
                    "Set the voice to en_female_1",
                    "Switch to the male voice",
                ],
            ),
        ]

    def generate_example(self, scenario: Scenario) -> GeneratedExample:
        prompt = scenario.random_prompt()
        messages: list[Message] = [self._make_user(prompt)]

        if scenario.category == "synthesize_speech":
            voice = random.choice(VOICES[:2])  # GPT-SoVITS voices
            text = random.choice(TEXTS)
            messages.append(
                self._make_assistant_with_tool(
                    f"Generating speech with {voice[1]}.",
                    ToolCall("tts.synthesize", {
                        "text": text,
                        "voice": voice[0],
                        "language": "en",
                    }),
                )
            )
            duration = round(random.uniform(1.5, 8.0), 1)
            messages.append(
                self._make_tool_response(
                    ToolResponse("tts.synthesize", {
                        "success": True,
                        "voice": voice[0],
                        "output_path": f"/tmp/tts_output_{random.randint(1000, 9999)}.wav",
                        "duration_s": duration,
                        "sample_rate": 32000,
                        "text_length": len(text),
                        "generation_time_s": round(random.uniform(0.5, 3.0), 1),
                    })
                )
            )
            messages.append(self._make_assistant_summary(
                f"Done — generated {duration}s of speech in {voice[0]}'s voice. Audio saved and ready to play."
            ))

        elif scenario.category == "synthesize_f5":
            text = random.choice(TEXTS)
            ref = random.choice(REFERENCE_AUDIOS)
            messages.append(
                self._make_assistant_with_tool(
                    "Generating with F5-TTS.",
                    ToolCall("f5tts.synthesize", {
                        "text": text,
                        "reference_audio": ref,
                    }),
                )
            )
            duration = round(random.uniform(2.0, 10.0), 1)
            messages.append(
                self._make_tool_response(
                    ToolResponse("f5tts.synthesize", {
                        "success": True,
                        "output_path": f"/tmp/f5tts_output_{random.randint(1000, 9999)}.wav",
                        "duration_s": duration,
                        "sample_rate": 24000,
                        "reference_audio": ref,
                        "generation_time_s": round(random.uniform(1.0, 5.0), 1),
                    })
                )
            )
            messages.append(self._make_assistant_summary(
                f"F5-TTS generated {duration}s of audio using the reference voice. Ready to play."
            ))

        elif scenario.category == "clone_voice":
            ref = random.choice(REFERENCE_AUDIOS)
            voice_name = random.choice(["custom_voice", "new_character", "npc_voice_01"])
            messages.append(
                self._make_assistant_with_tool(
                    "Starting voice cloning from the reference audio.",
                    ToolCall("tts.clone_voice", {
                        "reference_audio": ref,
                        "voice_name": voice_name,
                    }),
                )
            )
            messages.append(
                self._make_tool_response(
                    ToolResponse("tts.clone_voice", {
                        "success": True,
                        "voice_name": voice_name,
                        "reference_audio": ref,
                        "reference_duration_s": round(random.uniform(5.0, 30.0), 1),
                        "model_path": f"SoVITS_weights_v2/{voice_name}.pth",
                        "quality_score": round(random.uniform(0.7, 0.95), 2),
                    })
                )
            )
            # Test the cloned voice
            test_text = "Hello, this is a test of the cloned voice."
            messages.append(
                self._make_assistant_with_tool(
                    f"Voice cloned. Let me test it with a sample phrase.",
                    ToolCall("tts.synthesize", {
                        "text": test_text,
                        "voice": voice_name,
                        "language": "en",
                    }),
                )
            )
            messages.append(
                self._make_tool_response(
                    ToolResponse("tts.synthesize", {
                        "success": True,
                        "voice": voice_name,
                        "output_path": f"/tmp/tts_test_{random.randint(1000, 9999)}.wav",
                        "duration_s": 3.2,
                        "sample_rate": 32000,
                    })
                )
            )
            messages.append(self._make_assistant_summary(
                f"Voice \"{voice_name}\" cloned successfully from the reference audio. "
                f"Test sample generated — give it a listen to check the quality."
            ))

        elif scenario.category == "list_voices":
            messages.append(
                self._make_assistant_with_tool(
                    "Checking available voices.",
                    ToolCall("tts.list_voices", {}),
                )
            )
            messages.append(
                self._make_tool_response(
                    ToolResponse("tts.list_voices", {
                        "voices": [
                            {"id": v[0], "name": v[1],
                             "engine": "GPT-SoVITS" if i < 2 else "F5-TTS",
                             "language": "en"}
                            for i, v in enumerate(VOICES)
                        ],
                        "total": len(VOICES),
                    })
                )
            )
            sovits_voices = [v[1] for v in VOICES[:2]]
            f5_voices = [v[1] for v in VOICES[2:]]
            messages.append(self._make_assistant_summary(
                f"{len(VOICES)} voices available:\n"
                f"- GPT-SoVITS: {', '.join(sovits_voices)}\n"
                f"- F5-TTS: {', '.join(f5_voices)}"
            ))

        elif scenario.category == "set_voice":
            voice = random.choice(VOICES)
            messages.append(
                self._make_assistant_with_tool(
                    f"Switching to {voice[1]}.",
                    ToolCall("tts.set_voice", {"voice": voice[0]}),
                )
            )
            messages.append(
                self._make_tool_response(
                    ToolResponse("tts.set_voice", {
                        "success": True,
                        "voice": voice[0],
                        "name": voice[1],
                        "engine": "GPT-SoVITS" if "Jerry" in voice[1] or "Default" in voice[1] else "F5-TTS",
                    })
                )
            )
            messages.append(self._make_assistant_summary(
                f"Voice set to {voice[1]}. All future TTS output will use this voice."
            ))

        return GeneratedExample(
            messages=messages,
            domain=self.domain,
            category=scenario.category,
            difficulty=scenario.difficulty,
            tools_used=scenario.expected_tools,
        )
