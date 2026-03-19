"""Synthetic data generator for Steam gaming management scenarios."""

import random

from .base import (
    BaseGenerator,
    GeneratedExample,
    Message,
    Scenario,
    ToolCall,
    ToolResponse,
)

GAMES = [
    (377160, "Fallout 4", "RPG, Open World, Post-Apocalyptic", 30.5),
    (1091500, "Cyberpunk 2077", "RPG, Open World, Sci-Fi", 65.2),
    (1174180, "Red Dead Redemption 2", "Action, Adventure, Open World", 120.0),
    (1716740, "Starfield", "RPG, Open World, Sci-Fi", 125.0),
    (1458140, "Oblivion Remastered", "RPG, Fantasy, Open World", 45.0),
    (2399830, "Fallout 76", "RPG, Online, Multiplayer", 80.0),
    (546560, "Half-Life: Alyx", "VR, Action, Sci-Fi", 48.0),
    (620980, "Beat Saber", "VR, Rhythm, Music", 12.0),
    (1245620, "Elden Ring", "RPG, Action, Fantasy", 50.0),
    (292030, "The Witcher 3", "RPG, Fantasy, Open World", 35.0),
    (1593500, "God of War", "Action, Adventure", 70.0),
    (1938090, "Call of Duty: MW3", "FPS, Multiplayer", 140.0),
]

LAUNCH_OPTIONS = [
    "MANGOHUD=1 %command%",
    "DXVK_ASYNC=1 %command%",
    "gamemoderun %command%",
    "WINEDLLOVERRIDES='d3d11=n' %command%",
    "PROTON_ENABLE_NVAPI=1 DXVK_ENABLE_NVAPI=1 %command%",
    "QT_QPA_PLATFORM=xcb WAYLAND_DISPLAY='' %command%",
]

MODS = [
    "Unofficial Patch v4.2.9",
    "True Storms",
    "Sim Settlements 2",
    "CyberEngineTweaks",
    "Lenny's Simple Trainer",
    "Address Library AIO",
    "F4SE / SFSE / SKSE",
    "Baka Achievement Enabler",
    "ReShade 6.7.3",
    "ENB Series",
    "MangoHud",
    "ScriptHookRDR2",
]

PROTON_VERSIONS = [
    "Proton Experimental",
    "Proton 9.0-4",
    "Proton 8.0-5",
    "GE-Proton9-20",
    "GE-Proton9-18",
]


class SteamGenerator(BaseGenerator):
    domain = "steam"
    schema_files = ["steam.json"]

    def _build_scenarios(self) -> list[Scenario]:
        return [
            Scenario(
                domain="steam",
                category="list_games",
                difficulty="easy",
                expected_tools=["steam.list_games"],
                user_prompts=[
                    "What games do I have installed?",
                    "List my Steam games",
                    "Show me my game library",
                    "Which games are on my system?",
                    "How many games do I have installed?",
                ],
            ),
            Scenario(
                domain="steam",
                category="game_info",
                difficulty="easy",
                expected_tools=["steam.game_info"],
                user_prompts=[
                    f"Show me info about {game[1]}" for game in GAMES[:5]
                ] + [
                    "What Proton version is Cyberpunk using?",
                    "How big is Starfield?",
                    "Check the compatibility of Fallout 4",
                    "What are the details for RDR2?",
                ],
            ),
            Scenario(
                domain="steam",
                category="set_launch_options",
                difficulty="medium",
                expected_tools=["steam.set_launch_options"],
                user_prompts=[
                    "Enable MangoHud for Cyberpunk 2077",
                    "Set launch options for Fallout 4",
                    "Add DXVK_ASYNC to Starfield's launch options",
                    "Enable gamemode for Elden Ring",
                    "Set the Proton override for RDR2",
                    "Add NVAPI support to Cyberpunk's launch options",
                ],
            ),
            Scenario(
                domain="steam",
                category="list_mods",
                difficulty="easy",
                expected_tools=["steam.list_mods"],
                user_prompts=[
                    "What mods do I have installed for Fallout 4?",
                    "List Cyberpunk 2077 mods",
                    "Show me mods for Starfield",
                    "What's installed for RDR2?",
                    "Check the mod list for Oblivion Remastered",
                ],
            ),
        ]

    def generate_example(self, scenario: Scenario) -> GeneratedExample:
        prompt = scenario.random_prompt()
        messages: list[Message] = [self._make_user(prompt)]

        if scenario.category == "list_games":
            installed = random.sample(GAMES, k=random.randint(5, len(GAMES)))
            messages.append(
                self._make_assistant_with_tool(
                    "Checking your Steam library.",
                    ToolCall("steam.list_games", {}),
                )
            )
            messages.append(
                self._make_tool_response(
                    ToolResponse("steam.list_games", {
                        "games": [
                            {"app_id": g[0], "name": g[1], "tags": g[2],
                             "size_gb": g[3], "proton": random.choice(PROTON_VERSIONS),
                             "last_played": f"2026-03-{random.randint(1, 19):02d}"}
                            for g in installed
                        ],
                        "total_installed": len(installed),
                        "total_size_gb": round(sum(g[3] for g in installed), 1),
                    })
                )
            )
            game_names = [g[1] for g in installed]
            total_size = round(sum(g[3] for g in installed), 1)
            messages.append(self._make_assistant_summary(
                f"You have {len(installed)} games installed ({total_size}GB total):\n"
                + "\n".join(f"- {g[1]} ({g[3]}GB)" for g in installed)
            ))

        elif scenario.category == "game_info":
            game = random.choice(GAMES)
            proton = random.choice(PROTON_VERSIONS)
            playtime = random.randint(5, 500)
            messages.append(
                self._make_assistant_with_tool(
                    f"Getting info for {game[1]}.",
                    ToolCall("steam.game_info", {"app_id": game[0]}),
                )
            )
            messages.append(
                self._make_tool_response(
                    ToolResponse("steam.game_info", {
                        "app_id": game[0],
                        "name": game[1],
                        "tags": game[2],
                        "size_gb": game[3],
                        "proton_version": proton,
                        "proton_compatibility": random.choice(["Platinum", "Gold", "Silver"]),
                        "playtime_hours": playtime,
                        "last_played": f"2026-03-{random.randint(10, 19):02d}",
                        "install_path": f"~/.local/share/Steam/steamapps/common/{game[1].replace(' ', '')}/",
                        "launch_options": random.choice(LAUNCH_OPTIONS + [""]),
                        "has_mods": random.choice([True, False]),
                    })
                )
            )
            messages.append(self._make_assistant_summary(
                f"{game[1]} (AppID {game[0]}):\n"
                f"- Size: {game[3]}GB\n"
                f"- Proton: {proton}\n"
                f"- Playtime: {playtime} hours\n"
                f"- Tags: {game[2]}"
            ))

        elif scenario.category == "set_launch_options":
            game = random.choice(GAMES)
            launch_opt = random.choice(LAUNCH_OPTIONS)
            messages.append(
                self._make_assistant_with_tool(
                    f"Setting launch options for {game[1]}.",
                    ToolCall("steam.set_launch_options", {
                        "app_id": game[0],
                        "launch_options": launch_opt,
                    }),
                )
            )
            messages.append(
                self._make_tool_response(
                    ToolResponse("steam.set_launch_options", {
                        "success": True,
                        "app_id": game[0],
                        "name": game[1],
                        "launch_options": launch_opt,
                        "previous_options": random.choice(["", "%command%"]),
                        "note": "Steam must be restarted for changes to take effect" if random.random() > 0.5 else None,
                    })
                )
            )
            messages.append(self._make_assistant_summary(
                f"Launch options for {game[1]} set to: `{launch_opt}`"
                + ("\nNote: restart Steam for the changes to apply." if random.random() > 0.5 else "")
            ))

        elif scenario.category == "list_mods":
            game = random.choice(GAMES[:6])  # Only modded games
            num_mods = random.randint(3, 10)
            game_mods = random.sample(MODS, k=min(num_mods, len(MODS)))
            messages.append(
                self._make_assistant_with_tool(
                    f"Checking mods for {game[1]}.",
                    ToolCall("steam.list_mods", {"app_id": game[0]}),
                )
            )
            messages.append(
                self._make_tool_response(
                    ToolResponse("steam.list_mods", {
                        "app_id": game[0],
                        "name": game[1],
                        "mods": [
                            {"name": m, "enabled": random.random() > 0.1,
                             "source": random.choice(["Nexus Mods", "Manual", "Steam Workshop"])}
                            for m in game_mods
                        ],
                        "total": len(game_mods),
                    })
                )
            )
            disabled = [m for m in game_mods if random.random() < 0.1]
            messages.append(self._make_assistant_summary(
                f"{game[1]} has {len(game_mods)} mods installed:\n"
                + "\n".join(f"- {m}" for m in game_mods)
                + (f"\nNote: {', '.join(disabled)} disabled." if disabled else "")
            ))

        return GeneratedExample(
            messages=messages,
            domain=self.domain,
            category=scenario.category,
            difficulty=scenario.difficulty,
            tools_used=scenario.expected_tools,
        )
