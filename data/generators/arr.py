"""Synthetic data generator for *arr stack (Sonarr, Radarr, Lidarr, Prowlarr) scenarios."""

import random

from .base import (
    BaseGenerator,
    GeneratedExample,
    Message,
    Scenario,
    ToolCall,
    ToolResponse,
)

TV_SHOWS = [
    ("Breaking Bad", 2008, "tt0903747", 62),
    ("The Last of Us", 2023, "tt3581920", 17),
    ("Severance", 2022, "tt11280740", 19),
    ("Arcane", 2021, "tt11126994", 18),
    ("Shogun", 2024, "tt2788316", 10),
    ("The Bear", 2022, "tt14452776", 28),
    ("House of the Dragon", 2022, "tt11198330", 18),
    ("Fallout", 2024, "tt12637874", 8),
    ("Andor", 2022, "tt9253284", 12),
    ("Silo", 2023, "tt14688458", 20),
]

MOVIES = [
    ("The Dark Knight", 2008, "tt0468569"),
    ("Inception", 2010, "tt1375666"),
    ("Dune: Part Two", 2024, "tt15239678"),
    ("Oppenheimer", 2023, "tt15398776"),
    ("Blade Runner 2049", 2017, "tt1856101"),
    ("Everything Everywhere All at Once", 2022, "tt6710474"),
    ("John Wick: Chapter 4", 2023, "tt10366206"),
    ("Spider-Man: Across the Spider-Verse", 2023, "tt9362722"),
    ("Interstellar", 2014, "tt0816692"),
    ("Mad Max: Fury Road", 2015, "tt1392190"),
]

ARTISTS = [
    ("Radiohead", "Alternative Rock"),
    ("Kendrick Lamar", "Hip-Hop"),
    ("Taylor Swift", "Pop"),
    ("Tool", "Progressive Metal"),
    ("Daft Punk", "Electronic"),
    ("Fleetwood Mac", "Classic Rock"),
    ("Tyler, the Creator", "Hip-Hop"),
    ("Pink Floyd", "Progressive Rock"),
]

QUALITY_PROFILES = ["HD-1080p", "Ultra-HD", "Any", "HD-720p/1080p", "Remux-2160p"]
INDEXERS = ["Jackett", "NZBgeek", "1337x", "RARBG Legacy", "TorrentLeech", "Usenet-Farm"]


class ArrGenerator(BaseGenerator):
    domain = "arr"
    schema_files = ["arr.json"]

    def _build_scenarios(self) -> list[Scenario]:
        return [
            Scenario(
                domain="arr",
                category="add_series",
                difficulty="easy",
                expected_tools=["sonarr.add_series"],
                user_prompts=[
                    f"Add {show[0]} to Sonarr" for show in TV_SHOWS[:5]
                ] + [
                    "I want to start watching Severance, add it",
                    "Add that new Fallout show to my library",
                    "Download all seasons of Breaking Bad",
                ],
            ),
            Scenario(
                domain="arr",
                category="add_movie",
                difficulty="easy",
                expected_tools=["radarr.add_movie"],
                user_prompts=[
                    f"Add {movie[0]} to Radarr" for movie in MOVIES[:5]
                ] + [
                    "Download Dune: Part Two",
                    "I want to watch Oppenheimer, grab it",
                    "Add Inception to the movie library",
                ],
            ),
            Scenario(
                domain="arr",
                category="add_artist",
                difficulty="easy",
                expected_tools=["lidarr.add_artist"],
                user_prompts=[
                    f"Add {artist[0]} to Lidarr" for artist in ARTISTS[:4]
                ] + [
                    "I want Radiohead's discography",
                    "Download everything by Daft Punk",
                    "Add Tool to the music library",
                ],
            ),
            Scenario(
                domain="arr",
                category="search",
                difficulty="easy",
                expected_tools=["sonarr.search", "radarr.search"],
                user_prompts=[
                    "Search Sonarr for The Bear",
                    "Is Inception already in Radarr?",
                    "Search for new sci-fi shows in Sonarr",
                    "Look up John Wick in Radarr",
                    "What movies do I have monitored in Radarr?",
                ],
            ),
            Scenario(
                domain="arr",
                category="queue_status",
                difficulty="medium",
                expected_tools=["sonarr.queue", "radarr.queue"],
                user_prompts=[
                    "What's downloading right now?",
                    "Check the Sonarr download queue",
                    "Any downloads in progress?",
                    "What's in the Radarr queue?",
                    "Show me pending downloads across Sonarr and Radarr",
                    "How long until my downloads finish?",
                ],
            ),
            Scenario(
                domain="arr",
                category="calendar",
                difficulty="easy",
                expected_tools=["sonarr.calendar"],
                user_prompts=[
                    "What shows are coming out this week?",
                    "Any new episodes today?",
                    "Check the Sonarr calendar",
                    "What's airing this week?",
                    "Upcoming episode releases?",
                ],
            ),
            Scenario(
                domain="arr",
                category="wanted",
                difficulty="medium",
                expected_tools=["sonarr.wanted", "radarr.wanted"],
                user_prompts=[
                    "What's missing from my library?",
                    "Show me wanted episodes in Sonarr",
                    "Any missing movies in Radarr?",
                    "What shows still need episodes downloaded?",
                    "List everything that's monitored but not downloaded",
                ],
            ),
            Scenario(
                domain="arr",
                category="health",
                difficulty="medium",
                expected_tools=["sonarr.health", "radarr.health", "prowlarr.health"],
                user_prompts=[
                    "Check the health of my *arr stack",
                    "Any issues with Sonarr or Radarr?",
                    "Are all my indexers working?",
                    "Is Prowlarr healthy?",
                    "Run a health check on the download stack",
                ],
            ),
        ]

    def generate_example(self, scenario: Scenario) -> GeneratedExample:
        prompt = scenario.random_prompt()
        messages: list[Message] = [self._make_user(prompt)]

        if scenario.category == "add_series":
            show = random.choice(TV_SHOWS)
            quality = random.choice(QUALITY_PROFILES)
            messages.append(
                self._make_assistant_with_tool(
                    f"Adding \"{show[0]}\" to Sonarr.",
                    ToolCall("sonarr.add_series", {
                        "title": show[0],
                        "tvdb_id": show[2],
                        "quality_profile": quality,
                        "monitored": True,
                        "search_now": True,
                    }),
                )
            )
            messages.append(
                self._make_tool_response(
                    ToolResponse("sonarr.add_series", {
                        "success": True,
                        "title": show[0],
                        "year": show[1],
                        "seasons": random.randint(1, 5),
                        "episodes_total": show[3],
                        "quality_profile": quality,
                        "status": "searching",
                    })
                )
            )
            messages.append(self._make_assistant_summary(
                f"Added \"{show[0]}\" ({show[1]}) to Sonarr with {quality} quality profile. "
                f"Searching for {show[3]} episodes now — downloads will start automatically when found."
            ))

        elif scenario.category == "add_movie":
            movie = random.choice(MOVIES)
            quality = random.choice(QUALITY_PROFILES)
            messages.append(
                self._make_assistant_with_tool(
                    f"Adding \"{movie[0]}\" to Radarr.",
                    ToolCall("radarr.add_movie", {
                        "title": movie[0],
                        "imdb_id": movie[2],
                        "quality_profile": quality,
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
                        "year": movie[1],
                        "quality_profile": quality,
                        "status": "searching",
                    })
                )
            )
            messages.append(self._make_assistant_summary(
                f"Added \"{movie[0]}\" ({movie[1]}) to Radarr. Searching for a {quality} release now."
            ))

        elif scenario.category == "add_artist":
            artist = random.choice(ARTISTS)
            messages.append(
                self._make_assistant_with_tool(
                    f"Adding {artist[0]} to Lidarr.",
                    ToolCall("lidarr.add_artist", {
                        "name": artist[0],
                        "quality_profile": "Lossless",
                        "monitored": True,
                        "search_now": True,
                    }),
                )
            )
            albums = random.randint(3, 15)
            messages.append(
                self._make_tool_response(
                    ToolResponse("lidarr.add_artist", {
                        "success": True,
                        "name": artist[0],
                        "genre": artist[1],
                        "albums": albums,
                        "status": "searching",
                    })
                )
            )
            messages.append(self._make_assistant_summary(
                f"Added {artist[0]} to Lidarr — found {albums} albums. Searching for lossless releases now."
            ))

        elif scenario.category == "search":
            if random.random() > 0.5:
                show = random.choice(TV_SHOWS)
                messages.append(
                    self._make_assistant_with_tool(
                        f"Searching Sonarr for \"{show[0]}\".",
                        ToolCall("sonarr.search", {"query": show[0]}),
                    )
                )
                messages.append(
                    self._make_tool_response(
                        ToolResponse("sonarr.search", {
                            "results": [{
                                "title": show[0],
                                "year": show[1],
                                "episodes_total": show[3],
                                "episodes_have": random.randint(0, show[3]),
                                "monitored": True,
                                "status": "continuing" if random.random() > 0.3 else "ended",
                            }]
                        })
                    )
                )
                messages.append(self._make_assistant_summary(
                    f"Found \"{show[0]}\" in Sonarr — it's monitored and searching for episodes."
                ))
            else:
                movie = random.choice(MOVIES)
                messages.append(
                    self._make_assistant_with_tool(
                        f"Searching Radarr for \"{movie[0]}\".",
                        ToolCall("radarr.search", {"query": movie[0]}),
                    )
                )
                has_file = random.choice([True, False])
                messages.append(
                    self._make_tool_response(
                        ToolResponse("radarr.search", {
                            "results": [{
                                "title": movie[0],
                                "year": movie[1],
                                "monitored": True,
                                "has_file": has_file,
                                "quality": random.choice(QUALITIES) if has_file else None,
                                "size_gb": round(random.uniform(2.0, 60.0), 1) if has_file else None,
                            }]
                        })
                    )
                )
                if has_file:
                    messages.append(self._make_assistant_summary(
                        f"\"{movie[0]}\" is in Radarr and downloaded."
                    ))
                else:
                    messages.append(self._make_assistant_summary(
                        f"\"{movie[0]}\" is in Radarr but hasn't been downloaded yet. Want me to trigger a search?"
                    ))

        elif scenario.category == "queue_status":
            messages.append(
                self._make_assistant_with_tool(
                    "Checking download queues.",
                    ToolCall("sonarr.queue", {}),
                )
            )
            sonarr_items = random.randint(0, 4)
            queue = []
            for _ in range(sonarr_items):
                show = random.choice(TV_SHOWS)
                queue.append({
                    "title": f"{show[0]} - S{random.randint(1, 3):02d}E{random.randint(1, 10):02d}",
                    "quality": random.choice(QUALITY_PROFILES),
                    "size_gb": round(random.uniform(0.5, 8.0), 1),
                    "progress_pct": random.randint(0, 99),
                    "eta": f"{random.randint(1, 120)}min",
                    "status": random.choice(["downloading", "downloading", "queued", "importing"]),
                })
            messages.append(
                self._make_tool_response(
                    ToolResponse("sonarr.queue", {"items": queue, "total": sonarr_items})
                )
            )
            messages.append(
                self._make_assistant_with_tool(
                    "Now checking Radarr.",
                    ToolCall("radarr.queue", {}),
                )
            )
            radarr_items = random.randint(0, 3)
            rqueue = []
            for _ in range(radarr_items):
                movie = random.choice(MOVIES)
                rqueue.append({
                    "title": movie[0],
                    "quality": random.choice(QUALITY_PROFILES),
                    "size_gb": round(random.uniform(2.0, 50.0), 1),
                    "progress_pct": random.randint(0, 99),
                    "eta": f"{random.randint(5, 300)}min",
                    "status": "downloading",
                })
            messages.append(
                self._make_tool_response(
                    ToolResponse("radarr.queue", {"items": rqueue, "total": radarr_items})
                )
            )
            total = sonarr_items + radarr_items
            if total == 0:
                messages.append(self._make_assistant_summary("Nothing in the download queue — both Sonarr and Radarr are idle."))
            else:
                lines = []
                for item in queue + rqueue:
                    lines.append(f"- {item['title']}: {item['progress_pct']}% ({item['eta']} remaining)")
                messages.append(self._make_assistant_summary(
                    f"{total} item(s) downloading:\n" + "\n".join(lines)
                ))

        elif scenario.category == "calendar":
            messages.append(
                self._make_assistant_with_tool(
                    "Checking this week's releases.",
                    ToolCall("sonarr.calendar", {"days": 7}),
                )
            )
            upcoming = random.sample(TV_SHOWS, k=min(4, len(TV_SHOWS)))
            episodes = [
                {"series": show[0],
                 "episode": f"S{random.randint(1, 3):02d}E{random.randint(1, 12):02d}",
                 "title": random.choice(["Pilot", "The Reckoning", "New Dawn", "Aftermath", "Into the Fire"]),
                 "air_date": f"2026-03-{random.randint(19, 25):02d}"}
                for show in upcoming
            ]
            messages.append(
                self._make_tool_response(
                    ToolResponse("sonarr.calendar", {"episodes": episodes})
                )
            )
            lines = [f"- {ep['series']} {ep['episode']} \"{ep['title']}\" — {ep['air_date']}" for ep in episodes]
            messages.append(self._make_assistant_summary(
                f"{len(episodes)} episodes this week:\n" + "\n".join(lines)
            ))

        elif scenario.category == "wanted":
            messages.append(
                self._make_assistant_with_tool(
                    "Checking for missing content.",
                    ToolCall("sonarr.wanted", {}),
                )
            )
            missing_eps = random.randint(0, 8)
            wanted = [
                {"series": random.choice(TV_SHOWS)[0],
                 "episode": f"S{random.randint(1, 3):02d}E{random.randint(1, 12):02d}",
                 "air_date": f"2026-03-{random.randint(1, 18):02d}"}
                for _ in range(missing_eps)
            ]
            messages.append(
                self._make_tool_response(
                    ToolResponse("sonarr.wanted", {"missing": wanted, "total": missing_eps})
                )
            )
            if missing_eps == 0:
                messages.append(self._make_assistant_summary("Nothing missing — all monitored episodes have been downloaded."))
            else:
                messages.append(self._make_assistant_summary(
                    f"{missing_eps} missing episode(s) in Sonarr. Want me to trigger a search for them?"
                ))

        elif scenario.category == "health":
            messages.append(
                self._make_assistant_with_tool(
                    "Running health checks.",
                    ToolCall("prowlarr.health", {}),
                )
            )
            indexer_count = random.randint(3, 6)
            indexers = random.sample(INDEXERS, k=min(indexer_count, len(INDEXERS)))
            failed_idx = random.choice([0, 0, 1])
            health_items = []
            for i, idx in enumerate(indexers):
                if i < failed_idx:
                    health_items.append({"indexer": idx, "status": "error", "message": "Connection refused"})
                else:
                    health_items.append({"indexer": idx, "status": "ok", "response_time_ms": random.randint(50, 500)})
            messages.append(
                self._make_tool_response(
                    ToolResponse("prowlarr.health", {"indexers": health_items})
                )
            )
            if failed_idx > 0:
                failed_names = [h["indexer"] for h in health_items if h["status"] == "error"]
                messages.append(self._make_assistant_summary(
                    f"Prowlarr has {len(indexers)} indexers. {', '.join(failed_names)} "
                    f"{'is' if len(failed_names) == 1 else 'are'} down — connection refused. The rest are healthy."
                ))
            else:
                messages.append(self._make_assistant_summary(
                    f"All {len(indexers)} indexers in Prowlarr are healthy and responding normally."
                ))

        return GeneratedExample(
            messages=messages,
            domain=self.domain,
            category=scenario.category,
            difficulty=scenario.difficulty,
            tools_used=scenario.expected_tools,
        )


QUALITIES = ["HD-1080p", "Ultra-HD", "4K HDR", "1080p", "720p"]
