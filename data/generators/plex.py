"""Synthetic data generator for Plex media server scenarios."""

import random

from .base import (
    BaseGenerator,
    GeneratedExample,
    Message,
    Scenario,
    ToolCall,
    ToolResponse,
)

MOVIES = [
    ("The Dark Knight", 2008, "Action, Crime, Drama"),
    ("Inception", 2010, "Action, Sci-Fi, Thriller"),
    ("Interstellar", 2014, "Adventure, Drama, Sci-Fi"),
    ("Blade Runner 2049", 2017, "Action, Drama, Sci-Fi"),
    ("Dune: Part Two", 2024, "Action, Adventure, Drama"),
    ("The Matrix", 1999, "Action, Sci-Fi"),
    ("Parasite", 2019, "Comedy, Drama, Thriller"),
    ("Oppenheimer", 2023, "Biography, Drama, History"),
    ("Everything Everywhere All at Once", 2022, "Action, Adventure, Comedy"),
    ("Mad Max: Fury Road", 2015, "Action, Adventure, Sci-Fi"),
    ("John Wick: Chapter 4", 2023, "Action, Crime, Thriller"),
    ("Spider-Man: Across the Spider-Verse", 2023, "Animation, Action, Adventure"),
]

TV_SHOWS = [
    ("Breaking Bad", 5, 62),
    ("The Last of Us", 2, 17),
    ("Severance", 2, 19),
    ("Arcane", 2, 18),
    ("Shogun", 1, 10),
    ("The Bear", 3, 28),
    ("House of the Dragon", 2, 18),
    ("Fallout", 1, 8),
    ("Andor", 1, 12),
    ("Silo", 2, 20),
]

PLEX_USERS = ["deuce", "sarah", "mike", "guest", "family_room"]

QUALITIES = ["4K HDR", "1080p", "720p", "4K Dolby Vision", "1080p SDR"]


class PlexGenerator(BaseGenerator):
    domain = "plex"
    schema_files = ["plex.json"]

    def _build_scenarios(self) -> list[Scenario]:
        return [
            Scenario(
                domain="plex",
                category="library_scan",
                difficulty="easy",
                expected_tools=["plex.library_scan"],
                user_prompts=[
                    "Scan the Plex movie library",
                    "Refresh the Plex library",
                    "I added new movies, scan Plex",
                    "Update the TV shows library in Plex",
                    "Kick off a Plex library scan",
                ],
            ),
            Scenario(
                domain="plex",
                category="search",
                difficulty="easy",
                expected_tools=["plex.search"],
                user_prompts=[
                    f"Search Plex for {movie[0]}" for movie in MOVIES[:5]
                ] + [
                    "Find sci-fi movies in Plex",
                    "Do I have Inception in Plex?",
                    "Search for Breaking Bad on Plex",
                ],
            ),
            Scenario(
                domain="plex",
                category="now_playing",
                difficulty="easy",
                expected_tools=["plex.now_playing"],
                user_prompts=[
                    "What's playing on Plex right now?",
                    "Who's watching Plex?",
                    "Any active streams on Plex?",
                    "Is anyone using Plex right now?",
                    "Show me current Plex streams",
                ],
            ),
            Scenario(
                domain="plex",
                category="recently_added",
                difficulty="easy",
                expected_tools=["plex.recently_added"],
                user_prompts=[
                    "What's new on Plex?",
                    "Show me recently added movies",
                    "What was added to Plex this week?",
                    "Any new shows on Plex?",
                    "What's the latest stuff on Plex?",
                ],
            ),
            Scenario(
                domain="plex",
                category="collection_manage",
                difficulty="medium",
                expected_tools=["plex.collection_manage"],
                user_prompts=[
                    "Create a Plex collection called 'Best Sci-Fi'",
                    "Add Inception to the Sci-Fi Essentials collection",
                    "List my Plex collections",
                    "What's in the Marvel collection on Plex?",
                    "Remove Parasite from the Awards Winners collection",
                ],
            ),
            Scenario(
                domain="plex",
                category="playlist_manage",
                difficulty="medium",
                expected_tools=["plex.playlist_manage"],
                user_prompts=[
                    "Create a Plex playlist called 'Movie Night'",
                    "Add The Dark Knight to my watchlist playlist",
                    "What playlists do I have on Plex?",
                    "Show me the Movie Night playlist",
                    "Delete the old playlist on Plex",
                ],
            ),
            Scenario(
                domain="plex",
                category="maintenance",
                difficulty="medium",
                expected_tools=["plex.maintenance"],
                user_prompts=[
                    "Clean up Plex bundles",
                    "Optimize the Plex database",
                    "Run Plex maintenance tasks",
                    "Clean up old Plex thumbnails",
                    "Empty the Plex trash",
                ],
            ),
            Scenario(
                domain="plex",
                category="server_status",
                difficulty="easy",
                expected_tools=["plex.server_status"],
                user_prompts=[
                    "Is Plex running?",
                    "Check Plex server status",
                    "How's the Plex server doing?",
                    "Is Plex online?",
                    "Show me Plex server info",
                ],
            ),
        ]

    def generate_example(self, scenario: Scenario) -> GeneratedExample:
        prompt = scenario.random_prompt()
        messages: list[Message] = [self._make_user(prompt)]

        if scenario.category == "library_scan":
            library = random.choice(["Movies", "TV Shows", "Anime", "Music"])
            messages.append(
                self._make_assistant_with_tool(
                    f"Scanning the {library} library.",
                    ToolCall("plex.library_scan", {"library": library}),
                )
            )
            messages.append(
                self._make_tool_response(
                    ToolResponse("plex.library_scan", {
                        "success": True,
                        "library": library,
                        "status": "scanning",
                        "items_before": random.randint(200, 2000),
                    })
                )
            )
            messages.append(self._make_assistant_summary(
                f"Plex is scanning the {library} library. This might take a few minutes depending on how much was added."
            ))

        elif scenario.category == "search":
            movie = random.choice(MOVIES)
            messages.append(
                self._make_assistant_with_tool(
                    f"Searching Plex for \"{movie[0]}\".",
                    ToolCall("plex.search", {"query": movie[0]}),
                )
            )
            found = random.random() > 0.2
            if found:
                messages.append(
                    self._make_tool_response(
                        ToolResponse("plex.search", {
                            "results": [{
                                "title": movie[0],
                                "year": movie[1],
                                "type": "movie",
                                "genre": movie[2],
                                "quality": random.choice(QUALITIES),
                                "duration_min": random.randint(90, 180),
                                "rating": round(random.uniform(7.0, 9.5), 1),
                            }]
                        })
                    )
                )
                messages.append(self._make_assistant_summary(
                    f"Found \"{movie[0]}\" ({movie[1]}) in your Plex library — "
                    f"{movie[2]}, available in {random.choice(QUALITIES)}."
                ))
            else:
                messages.append(
                    self._make_tool_response(
                        ToolResponse("plex.search", {"results": []})
                    )
                )
                messages.append(self._make_assistant_summary(
                    f"\"{movie[0]}\" isn't in your Plex library. Want me to add it via Radarr?"
                ))

        elif scenario.category == "now_playing":
            messages.append(
                self._make_assistant_with_tool(
                    "Checking active streams.",
                    ToolCall("plex.now_playing", {}),
                )
            )
            num_streams = random.choice([0, 1, 2, 3])
            streams = []
            for _ in range(num_streams):
                if random.random() > 0.5:
                    movie = random.choice(MOVIES)
                    streams.append({
                        "user": random.choice(PLEX_USERS),
                        "title": movie[0],
                        "type": "movie",
                        "quality": random.choice(QUALITIES),
                        "progress_pct": random.randint(5, 95),
                        "transcode": random.choice([True, False]),
                        "player": random.choice(["Plex Web", "Apple TV", "Roku", "Shield TV", "iPhone"]),
                    })
                else:
                    show = random.choice(TV_SHOWS)
                    streams.append({
                        "user": random.choice(PLEX_USERS),
                        "title": f"{show[0]} - S{random.randint(1, show[1]):02d}E{random.randint(1, 10):02d}",
                        "type": "episode",
                        "quality": random.choice(QUALITIES),
                        "progress_pct": random.randint(5, 95),
                        "transcode": random.choice([True, False]),
                        "player": random.choice(["Plex Web", "Apple TV", "Roku", "Shield TV", "iPhone"]),
                    })
            messages.append(
                self._make_tool_response(
                    ToolResponse("plex.now_playing", {
                        "streams": streams,
                        "total_streams": num_streams,
                    })
                )
            )
            if num_streams == 0:
                messages.append(self._make_assistant_summary("No one's watching Plex right now."))
            else:
                lines = []
                for s in streams:
                    tc = " (transcoding)" if s["transcode"] else " (direct play)"
                    lines.append(f"- {s['user']} watching {s['title']} on {s['player']} at {s['quality']}{tc} ({s['progress_pct']}% through)")
                messages.append(self._make_assistant_summary(
                    f"{num_streams} active stream(s):\n" + "\n".join(lines)
                ))

        elif scenario.category == "recently_added":
            messages.append(
                self._make_assistant_with_tool(
                    "Checking what's been added recently.",
                    ToolCall("plex.recently_added", {"count": 10}),
                )
            )
            recent = random.sample(MOVIES, k=min(5, len(MOVIES)))
            items = [
                {"title": m[0], "year": m[1], "type": "movie",
                 "added_at": f"2026-03-{random.randint(15, 19):02d}T{random.randint(8, 22):02d}:00:00",
                 "quality": random.choice(QUALITIES)}
                for m in recent
            ]
            messages.append(
                self._make_tool_response(
                    ToolResponse("plex.recently_added", {"items": items})
                )
            )
            titles = [m[0] for m in recent]
            messages.append(self._make_assistant_summary(
                f"Recently added to Plex: {', '.join(titles)}. All added in the last few days."
            ))

        elif scenario.category == "collection_manage":
            action = random.choice(["list", "create", "add_item"])
            if action == "list":
                messages.append(
                    self._make_assistant_with_tool(
                        "Checking your collections.",
                        ToolCall("plex.collection_manage", {"action": "list"}),
                    )
                )
                collections = ["Sci-Fi Essentials", "Awards Winners", "90s Classics", "Director's Cuts", "Marvel"]
                messages.append(
                    self._make_tool_response(
                        ToolResponse("plex.collection_manage", {
                            "collections": [{"name": c, "item_count": random.randint(5, 30)} for c in collections]
                        })
                    )
                )
                messages.append(self._make_assistant_summary(
                    f"You have {len(collections)} collections: {', '.join(collections)}."
                ))
            elif action == "create":
                name = random.choice(["Weekend Binge", "Comfort Movies", "Hidden Gems"])
                messages.append(
                    self._make_assistant_with_tool(
                        f"Creating the \"{name}\" collection.",
                        ToolCall("plex.collection_manage", {"action": "create", "name": name}),
                    )
                )
                messages.append(
                    self._make_tool_response(
                        ToolResponse("plex.collection_manage", {"success": True, "name": name, "action": "created"})
                    )
                )
                messages.append(self._make_assistant_summary(f"Created the \"{name}\" collection. You can start adding movies to it."))
            else:
                movie = random.choice(MOVIES)
                collection = "Sci-Fi Essentials"
                messages.append(
                    self._make_assistant_with_tool(
                        f"Adding \"{movie[0]}\" to {collection}.",
                        ToolCall("plex.collection_manage", {"action": "add_item", "name": collection, "item": movie[0]}),
                    )
                )
                messages.append(
                    self._make_tool_response(
                        ToolResponse("plex.collection_manage", {"success": True, "name": collection, "item": movie[0], "action": "added"})
                    )
                )
                messages.append(self._make_assistant_summary(f"Added \"{movie[0]}\" to the {collection} collection."))

        elif scenario.category == "playlist_manage":
            action = random.choice(["list", "create", "add_item"])
            if action == "list":
                messages.append(
                    self._make_assistant_with_tool(
                        "Checking your playlists.",
                        ToolCall("plex.playlist_manage", {"action": "list"}),
                    )
                )
                playlists = ["Movie Night", "Background Shows", "Weekend Marathon"]
                messages.append(
                    self._make_tool_response(
                        ToolResponse("plex.playlist_manage", {
                            "playlists": [{"name": p, "item_count": random.randint(3, 20), "duration_min": random.randint(120, 600)} for p in playlists]
                        })
                    )
                )
                messages.append(self._make_assistant_summary(
                    f"You have {len(playlists)} playlists: {', '.join(playlists)}."
                ))
            elif action == "create":
                name = "Date Night Picks"
                messages.append(
                    self._make_assistant_with_tool(
                        f"Creating playlist \"{name}\".",
                        ToolCall("plex.playlist_manage", {"action": "create", "name": name}),
                    )
                )
                messages.append(
                    self._make_tool_response(
                        ToolResponse("plex.playlist_manage", {"success": True, "name": name, "action": "created"})
                    )
                )
                messages.append(self._make_assistant_summary(f"Playlist \"{name}\" created. Ready to add stuff."))
            else:
                movie = random.choice(MOVIES)
                messages.append(
                    self._make_assistant_with_tool(
                        f"Adding \"{movie[0]}\" to Movie Night.",
                        ToolCall("plex.playlist_manage", {"action": "add_item", "name": "Movie Night", "item": movie[0]}),
                    )
                )
                messages.append(
                    self._make_tool_response(
                        ToolResponse("plex.playlist_manage", {"success": True, "name": "Movie Night", "item": movie[0], "action": "added"})
                    )
                )
                messages.append(self._make_assistant_summary(f"Added \"{movie[0]}\" to Movie Night."))

        elif scenario.category == "maintenance":
            task = random.choice(["clean_bundles", "optimize_db", "empty_trash"])
            task_label = {"clean_bundles": "Cleaning bundles", "optimize_db": "Optimizing database", "empty_trash": "Emptying trash"}
            messages.append(
                self._make_assistant_with_tool(
                    f"{task_label[task]}.",
                    ToolCall("plex.maintenance", {"task": task}),
                )
            )
            messages.append(
                self._make_tool_response(
                    ToolResponse("plex.maintenance", {
                        "success": True,
                        "task": task,
                        "message": "Task completed successfully",
                        "space_freed_mb": random.randint(50, 2000) if task != "optimize_db" else 0,
                    })
                )
            )
            freed = f" Freed up {random.randint(50, 2000)}MB." if task != "optimize_db" else ""
            messages.append(self._make_assistant_summary(f"Done — {task_label[task].lower()} complete.{freed}"))

        elif scenario.category == "server_status":
            messages.append(
                self._make_assistant_with_tool(
                    "Checking Plex server.",
                    ToolCall("plex.server_status", {}),
                )
            )
            messages.append(
                self._make_tool_response(
                    ToolResponse("plex.server_status", {
                        "online": True,
                        "version": "1.41.2.9200",
                        "platform": "Linux",
                        "libraries": {"Movies": random.randint(200, 2000), "TV Shows": random.randint(50, 500)},
                        "active_streams": random.randint(0, 3),
                        "uptime": f"{random.randint(1, 60)}d",
                        "transcode_hw": "NVIDIA NVENC",
                    })
                )
            )
            messages.append(self._make_assistant_summary(
                "Plex is online and healthy — running v1.41.2 on Linux with NVIDIA hardware transcoding. All libraries accessible."
            ))

        return GeneratedExample(
            messages=messages,
            domain=self.domain,
            category=scenario.category,
            difficulty=scenario.difficulty,
            tools_used=scenario.expected_tools,
        )
