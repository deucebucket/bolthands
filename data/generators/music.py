"""Synthetic data generator for AI music generation (ACE-Step) scenarios."""

import random

from .base import (
    BaseGenerator,
    GeneratedExample,
    Message,
    Scenario,
    ToolCall,
    ToolResponse,
)

MUSIC_PROMPTS = [
    "upbeat synthwave track with retro drums and pulsing bassline, 120 BPM",
    "melancholic piano ballad with strings, emotional and cinematic",
    "heavy metal riff with distorted guitars and double bass drums, 160 BPM",
    "lo-fi hip hop beat with jazzy chords and vinyl crackle, chill vibes",
    "epic orchestral score for a fantasy battle scene, brass and percussion",
    "ambient electronic track with evolving pads and gentle arpeggios",
    "acoustic folk song with fingerpicked guitar and soft vocals",
    "90s grunge rock with crunchy guitars and raw energy",
    "tropical house track with steel drums and uplifting melody, 110 BPM",
    "dark trap beat with 808s and eerie synths, 140 BPM",
]

STYLES = [
    ("synthwave", "Retro 80s electronic with analog synths and arpeggios"),
    ("lo-fi", "Relaxed lo-fi hip hop with warm tones and subtle imperfections"),
    ("orchestral", "Full orchestra with strings, brass, woodwinds, and percussion"),
    ("metal", "Heavy metal with distorted guitars, blast beats, and powerful riffs"),
    ("ambient", "Atmospheric ambient with evolving textures and spatial effects"),
    ("jazz", "Smooth jazz with piano, saxophone, upright bass, and brushed drums"),
    ("pop", "Modern pop with catchy hooks, clean production, and vocal-friendly mix"),
    ("electronic", "Electronic dance music with driving beats and synth leads"),
    ("folk", "Acoustic folk with natural instruments and warm, organic feel"),
    ("hip-hop", "Hip hop with hard-hitting drums, bass, and urban atmosphere"),
    ("cinematic", "Film score style with dramatic builds and emotional depth"),
    ("classical", "Classical composition with traditional structure and instrumentation"),
]

LYRICS_SAMPLES = [
    "[verse]\nWalking through the neon glow\nCity lights put on a show\nEvery step a brand new beat\nDancing shadows on the street\n\n[chorus]\nWe're alive tonight\nBurning bright like satellite\nNothing gonna bring us down\nWe own this town",
    "[verse]\nRain falls on the window pane\nWashing away the years of pain\nMemories like faded photographs\nLearning how to live and laugh\n\n[chorus]\nLet it go, let it flow\nLike a river down below\nEvery ending starts anew\nI'm finding my way back to you",
    "",  # instrumental
]


class MusicGenerator(BaseGenerator):
    domain = "music"
    schema_files = ["music.json"]

    def _build_scenarios(self) -> list[Scenario]:
        return [
            Scenario(
                domain="music",
                category="generate_music",
                difficulty="medium",
                expected_tools=["music.generate"],
                user_prompts=[
                    f"Generate music: {p}" for p in MUSIC_PROMPTS[:5]
                ] + [
                    "Make me a chill lo-fi beat",
                    "Create an epic orchestral track",
                    "Generate a metal song",
                    "I want a synthwave track for my game",
                    "Make some ambient background music",
                    "Create a hip hop beat with hard 808s",
                ],
            ),
            Scenario(
                domain="music",
                category="generate_with_lyrics",
                difficulty="hard",
                expected_tools=["music.generate"],
                user_prompts=[
                    "Generate a pop song with lyrics about city nights",
                    "Create a rock track with these lyrics I wrote",
                    "Make a song with vocals — something emotional",
                    "Generate a hip hop track with a chorus about freedom",
                ],
            ),
            Scenario(
                domain="music",
                category="list_styles",
                difficulty="easy",
                expected_tools=["music.list_styles"],
                user_prompts=[
                    "What music styles are available?",
                    "List the music generation styles",
                    "What genres can ACE-Step generate?",
                    "Show me available music styles",
                    "What kinds of music can you make?",
                ],
            ),
        ]

    def generate_example(self, scenario: Scenario) -> GeneratedExample:
        prompt = scenario.random_prompt()
        messages: list[Message] = [self._make_user(prompt)]

        if scenario.category == "generate_music":
            music_prompt = random.choice(MUSIC_PROMPTS)
            style = random.choice(STYLES)
            duration = random.choice([30, 60, 90, 120, 180])

            messages.append(
                self._make_assistant_with_tool(
                    f"Generating a {style[0]} track with ACE-Step.",
                    ToolCall("music.generate", {
                        "prompt": music_prompt,
                        "style": style[0],
                        "duration_s": duration,
                        "seed": random.randint(0, 2**32),
                    }),
                )
            )
            gen_time = round(random.uniform(15.0, 120.0), 1)
            messages.append(
                self._make_tool_response(
                    ToolResponse("music.generate", {
                        "success": True,
                        "output_path": f"/output/ace_step_{random.randint(10000, 99999)}.wav",
                        "style": style[0],
                        "duration_s": duration,
                        "sample_rate": 44100,
                        "generation_time_s": gen_time,
                        "seed": random.randint(0, 2**32),
                    })
                )
            )
            messages.append(self._make_assistant_summary(
                f"Generated a {duration}s {style[0]} track in {gen_time}s. "
                f"Saved to the output folder. Give it a listen."
            ))

        elif scenario.category == "generate_with_lyrics":
            music_prompt = random.choice(MUSIC_PROMPTS)
            style = random.choice(STYLES[:4])
            lyrics = random.choice([l for l in LYRICS_SAMPLES if l])
            duration = random.choice([120, 180, 240])

            messages.append(
                self._make_assistant_with_tool(
                    f"Generating a {style[0]} track with lyrics.",
                    ToolCall("music.generate", {
                        "prompt": music_prompt,
                        "style": style[0],
                        "lyrics": lyrics,
                        "duration_s": duration,
                        "seed": random.randint(0, 2**32),
                    }),
                )
            )
            gen_time = round(random.uniform(30.0, 180.0), 1)
            messages.append(
                self._make_tool_response(
                    ToolResponse("music.generate", {
                        "success": True,
                        "output_path": f"/output/ace_step_{random.randint(10000, 99999)}.wav",
                        "style": style[0],
                        "duration_s": duration,
                        "has_vocals": True,
                        "sample_rate": 44100,
                        "generation_time_s": gen_time,
                    })
                )
            )
            messages.append(self._make_assistant_summary(
                f"Generated a {duration}s {style[0]} track with vocals in {round(gen_time / 60, 1)} minutes. "
                f"The lyrics have been set to music. Check the output."
            ))

        elif scenario.category == "list_styles":
            messages.append(
                self._make_assistant_with_tool(
                    "Checking available styles.",
                    ToolCall("music.list_styles", {}),
                )
            )
            messages.append(
                self._make_tool_response(
                    ToolResponse("music.list_styles", {
                        "styles": [
                            {"name": s[0], "description": s[1]}
                            for s in STYLES
                        ],
                        "total": len(STYLES),
                    })
                )
            )
            style_names = [s[0] for s in STYLES]
            messages.append(self._make_assistant_summary(
                f"{len(STYLES)} music styles available: {', '.join(style_names)}. "
                f"You can combine styles with descriptive prompts for more specific results."
            ))

        return GeneratedExample(
            messages=messages,
            domain=self.domain,
            category=scenario.category,
            difficulty=scenario.difficulty,
            tools_used=scenario.expected_tools,
        )
