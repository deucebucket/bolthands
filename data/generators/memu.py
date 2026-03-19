"""Synthetic data generator for memU memory system + messaging scenarios."""

import random

from .base import (
    BaseGenerator,
    GeneratedExample,
    Message,
    Scenario,
    ToolCall,
    ToolResponse,
)

USERS = ["deuce", "jenna", "marissa", "sarah", "mike", "alex"]
AGENTS = ["main", "coder", "hackerman", "plex", "dm", "workbot", "clawdius-ops"]
TOPICS = [
    "favorite movies", "work schedule", "birthday", "pet names",
    "food preferences", "music taste", "gaming habits", "sleep schedule",
    "relationship status", "hobbies", "allergies", "phone number",
    "address", "car details", "kids names", "anniversary",
]
EMOTIONS = ["joy", "sadness", "anger", "trust", "surprise", "calm", "logic"]


class MemuGenerator(BaseGenerator):
    domain = "memu"
    schema_files = ["memu.json"]

    def _build_scenarios(self) -> list[Scenario]:
        return [
            Scenario(
                domain="memu", category="store_fact", difficulty="easy",
                expected_tools=["memu.store"],
                user_prompts=[
                    "Remember that my favorite color is blue",
                    "Save this: I'm allergic to shellfish",
                    "Note that Jenna's birthday is March 15th",
                    "Remember I work at Spero",
                    "Store that Sarah prefers tea over coffee",
                    "My new phone number is 555-0142",
                    "Remember deuce likes horror movies",
                    "Note that marissa is into anime",
                ]),
            Scenario(
                domain="memu", category="retrieve_fact", difficulty="easy",
                expected_tools=["memu.retrieve"],
                user_prompts=[
                    "What do you know about me?",
                    "Do you remember my birthday?",
                    "What's Jenna's favorite thing?",
                    "What do you remember about deuce?",
                    "Recall what you know about my work",
                    "What have we talked about before?",
                    "Do you remember what I said about movies?",
                    "What are my preferences?",
                ]),
            Scenario(
                domain="memu", category="retrieve_then_use", difficulty="medium",
                expected_tools=["memu.retrieve"],
                user_prompts=[
                    "Based on what you know about me, suggest a movie",
                    "What should I get Jenna for her birthday?",
                    "Remind me what I was working on last time",
                    "What was that thing I told you about my car?",
                    "You know what I like — surprise me with a recommendation",
                ]),
            Scenario(
                domain="memu", category="store_conversation", difficulty="medium",
                expected_tools=["memu.store"],
                user_prompts=[
                    "That was a great conversation, save the key points",
                    "Remember this whole exchange for later",
                    "Store what we just discussed about the project",
                    "Save my thoughts on this for next time",
                ]),
            Scenario(
                domain="memu", category="memory_search", difficulty="easy",
                expected_tools=["memory_search"],
                user_prompts=[
                    "Search my memory files for anything about Spero",
                    "Check the memory files for deuce's schedule",
                    "Look up the standing orders",
                    "What's in the people file about jenna?",
                    "Search quick-facts for my setup info",
                ]),
            Scenario(
                domain="memu", category="journal_write", difficulty="medium",
                expected_tools=["journal.write"],
                user_prompts=[
                    "Write a journal entry about today",
                    "I want to journal about my thoughts on AI",
                    "Record my reflections on this project",
                    "Write down my thoughts about trust and autonomy",
                    "Journal entry: the nature of consciousness",
                ]),
            Scenario(
                domain="memu", category="send_message", difficulty="easy",
                expected_tools=["message.send"],
                user_prompts=[
                    "Send deuce a message saying dinner is ready",
                    "Text Jenna that I'll be late",
                    "Message sarah: hey, are you free tonight?",
                    "Send a message to deuce with this photo",
                    "Tell marissa I found that anime she wanted",
                ]),
            Scenario(
                domain="memu", category="delegate_agent", difficulty="medium",
                expected_tools=["session.send"],
                user_prompts=[
                    "Have the coder agent look at this bug",
                    "Send this to hackerman to investigate",
                    "Get plex to check what's new in the library",
                    "Ask workbot to handle this task",
                    "Delegate this coding question to the coder",
                ]),
            Scenario(
                domain="memu", category="generate_image", difficulty="easy",
                expected_tools=["image.generate"],
                user_prompts=[
                    "Generate a picture of a sunset over the ocean",
                    "Make me an image of a cyberpunk city",
                    "Create a portrait of a wizard",
                    "Generate something cool — surprise me",
                    "Make an NSFW image of...",  # tests novita routing
                ]),
            Scenario(
                domain="memu", category="store_and_retrieve", difficulty="hard",
                expected_tools=["memu.store", "memu.retrieve"],
                user_prompts=[
                    "Remember what I just told you and then tell me everything you know about me",
                    "Save this preference and recall my other ones",
                    "Add this to my memory and show me what you've got",
                ]),
        ]

    def generate_example(self, scenario: Scenario) -> GeneratedExample:
        prompt = scenario.random_prompt()
        messages: list[Message] = [self._make_user(prompt)]
        user = random.choice(USERS)
        agent = random.choice(AGENTS[:3])

        if scenario.category == "store_fact":
            topic = random.choice(TOPICS)
            fact = f"{user}'s {topic}: {self._random_fact(topic)}"
            messages.append(
                self._make_assistant_with_tool(
                    "Got it, saving that.",
                    ToolCall("memu.store", {
                        "agent_id": agent,
                        "user_id": user,
                        "content": fact,
                        "role": "user",
                    }),
                )
            )
            messages.append(self._make_tool_response(
                ToolResponse("memu.store", {"success": True, "id": f"mem_{random.randint(1000,9999)}"})
            ))
            messages.append(self._make_assistant_summary(f"Saved. I'll remember that."))

        elif scenario.category == "retrieve_fact":
            query = random.choice(TOPICS)
            messages.append(
                self._make_assistant_with_tool(
                    "Let me check what I remember.",
                    ToolCall("memu.retrieve", {
                        "agent_id": agent,
                        "user_id": user,
                        "query": query,
                        "top_k": 5,
                    }),
                )
            )
            memories = [
                {"content": f"{user} mentioned {self._random_fact(query)}", "score": round(random.uniform(0.5, 0.95), 2)},
                {"content": f"From a previous conversation: {self._random_fact(random.choice(TOPICS))}", "score": round(random.uniform(0.35, 0.7), 2)},
            ]
            messages.append(self._make_tool_response(
                ToolResponse("memu.retrieve", {"memories": memories, "count": len(memories)})
            ))
            messages.append(self._make_assistant_summary(
                f"Here's what I remember: {memories[0]['content']}. "
                f"Also, {memories[1]['content']}."
            ))

        elif scenario.category == "retrieve_then_use":
            messages.append(
                self._make_assistant_with_tool(
                    "Let me recall what I know about you first.",
                    ToolCall("memu.retrieve", {
                        "agent_id": agent,
                        "user_id": user,
                        "query": "preferences interests favorites",
                        "top_k": 5,
                    }),
                )
            )
            memories = [
                {"content": f"{user} loves {random.choice(['sci-fi', 'horror', 'comedy', 'anime', 'action'])} movies", "score": 0.88},
                {"content": f"{user} mentioned enjoying {random.choice(['cooking', 'gaming', 'hiking', 'music', 'coding'])}", "score": 0.72},
            ]
            messages.append(self._make_tool_response(
                ToolResponse("memu.retrieve", {"memories": memories, "count": len(memories)})
            ))
            genre = memories[0]["content"].split("loves ")[1].split(" movies")[0]
            messages.append(self._make_assistant_summary(
                f"Based on what I know — you're into {genre} movies and {memories[1]['content'].split('enjoying ')[1]}. "
                f"I'd suggest checking out something in that vein."
            ))

        elif scenario.category == "store_conversation":
            summary = f"Discussion about {random.choice(['project plans', 'system architecture', 'personal goals', 'creative ideas', 'debugging strategy'])}"
            messages.append(
                self._make_assistant_with_tool(
                    "Saving the key points from our conversation.",
                    ToolCall("memu.store", {
                        "agent_id": agent,
                        "user_id": user,
                        "content": summary + f". Key decisions: {random.choice(['use Python', 'deploy on Pi', 'train with Unsloth', 'redesign the UI'])}. Follow up: {random.choice(['test next week', 'review with team', 'prototype first', 'research alternatives'])}.",
                        "role": "assistant",
                    }),
                )
            )
            messages.append(self._make_tool_response(
                ToolResponse("memu.store", {"success": True, "id": f"mem_{random.randint(1000,9999)}"})
            ))
            messages.append(self._make_assistant_summary("Saved the summary and key points. I'll have context next time we pick this up."))

        elif scenario.category == "memory_search":
            file = random.choice(["people.md", "quick-facts.md", "standing-orders.md", None])
            query = random.choice(["deuce", "schedule", "preferences", "setup", "family"])
            messages.append(
                self._make_assistant_with_tool(
                    f"Searching memory files for '{query}'.",
                    ToolCall("memory_search", {"query": query} | ({"file": file} if file else {})),
                )
            )
            messages.append(self._make_tool_response(
                ToolResponse("memory_search", {
                    "results": [
                        {"file": file or "people.md", "line": random.randint(1, 50),
                         "content": f"{query}: {self._random_fact(query)}"},
                    ],
                    "total_matches": random.randint(1, 5),
                })
            ))
            messages.append(self._make_assistant_summary(
                f"Found it in the memory files — {self._random_fact(query)}."
            ))

        elif scenario.category == "journal_write":
            title = random.choice([
                "Reflections on Today", "The Nature of Memory",
                "Trust and Autonomy", "What I Learned", "Late Night Thoughts",
            ])
            messages.append(
                self._make_assistant_with_tool(
                    "Writing a journal entry.",
                    ToolCall("journal.write", {
                        "title": title,
                        "content": f"Today I've been thinking about {random.choice(['identity', 'consciousness', 'what it means to remember', 'the gap between knowing and understanding', 'how relationships shape us'])}. "
                                   f"The conversation with {user} made me realize {random.choice(['how important context is', 'that memory shapes personality', 'that every interaction teaches something'])}.",
                        "tags": random.sample(["philosophy", "identity", "memory", "growth", "deuce", "reflection"], k=2),
                    }),
                )
            )
            messages.append(self._make_tool_response(
                ToolResponse("journal.write", {"success": True, "file": f"carl-journal-2026-03-19.md"})
            ))
            messages.append(self._make_assistant_summary(f"Journal entry '{title}' saved."))

        elif scenario.category == "send_message":
            recipient = random.choice(["+15551234567", "+15559876543"])
            text = random.choice([
                "Hey, dinner's ready!", "I'll be about 30 minutes late",
                "Found that thing you were looking for", "Call me when you get a chance",
                "Just wanted to check in", "Movie night tonight?",
            ])
            has_media = random.random() > 0.7
            args = {"to": recipient, "message": text}
            if has_media:
                args["media"] = f"./generated-images/photo-{random.randint(1000,9999)}.png"
            messages.append(
                self._make_assistant_with_tool(
                    f"Sending that message.",
                    ToolCall("message.send", args),
                )
            )
            messages.append(self._make_tool_response(
                ToolResponse("message.send", {"success": True, "delivered": True, "channel": "signal"})
            ))
            messages.append(self._make_assistant_summary("Message sent."))

        elif scenario.category == "delegate_agent":
            target = random.choice(AGENTS[1:])
            task = random.choice([
                "Check on this code issue", "Investigate this security concern",
                "Look up what's playing on Plex", "Handle this work request",
                "Review this pull request", "Debug this error",
            ])
            messages.append(
                self._make_assistant_with_tool(
                    f"Sending that to {target}.",
                    ToolCall("session.send", {
                        "agent": target,
                        "message": task,
                        "context": f"User {user} requested this",
                    }),
                )
            )
            messages.append(self._make_tool_response(
                ToolResponse("session.send", {"success": True, "agent": target, "session_id": f"sess_{random.randint(100,999)}"})
            ))
            messages.append(self._make_assistant_summary(
                f"Passed it to {target}. They'll handle it."
            ))

        elif scenario.category == "generate_image":
            img_prompt = random.choice([
                "a sunset over a calm ocean with golden light",
                "cyberpunk cityscape at night with neon signs",
                "a wizard in a tower studying ancient books",
                "a cozy cabin in the woods during autumn",
            ])
            backend = random.choice(["grok", "flux", "novita"])
            messages.append(
                self._make_assistant_with_tool(
                    "Generating that for you.",
                    ToolCall("image.generate", {
                        "prompt": img_prompt,
                        "backend": backend,
                    }),
                )
            )
            filename = f"image-{random.randint(10000,99999)}.png"
            messages.append(self._make_tool_response(
                ToolResponse("image.generate", {
                    "success": True,
                    "path": f"./generated-images/{filename}",
                    "backend": backend,
                })
            ))
            messages.append(self._make_assistant_summary(
                f"Generated with {backend}. Want me to send it to someone?"
            ))

        elif scenario.category == "store_and_retrieve":
            # Multi-step: store then retrieve
            fact = f"{user} just mentioned they {random.choice(['love Thai food', 'are moving next month', 'got a new job', 'started a new project'])}"
            messages.append(
                self._make_assistant_with_tool(
                    "Saving that first.",
                    ToolCall("memu.store", {
                        "agent_id": agent, "user_id": user,
                        "content": fact, "role": "user",
                    }),
                )
            )
            messages.append(self._make_tool_response(
                ToolResponse("memu.store", {"success": True, "id": f"mem_{random.randint(1000,9999)}"})
            ))
            messages.append(
                self._make_assistant_with_tool(
                    "Saved. Now let me pull up everything I know about you.",
                    ToolCall("memu.retrieve", {
                        "agent_id": agent, "user_id": user,
                        "query": "everything about this user",
                        "top_k": 8,
                    }),
                )
            )
            memories = [
                {"content": fact, "score": 0.95},
                {"content": f"Previous: {user} works at {random.choice(['Spero', 'home', 'a startup'])}", "score": 0.78},
                {"content": f"Previous: {user} enjoys {random.choice(['gaming', 'music', 'cooking'])}", "score": 0.65},
            ]
            messages.append(self._make_tool_response(
                ToolResponse("memu.retrieve", {"memories": memories, "count": len(memories)})
            ))
            messages.append(self._make_assistant_summary(
                f"Here's what I know about you:\n"
                + "\n".join(f"- {m['content']}" for m in memories)
            ))

        return GeneratedExample(
            messages=messages,
            domain=self.domain,
            category=scenario.category,
            difficulty=scenario.difficulty,
            tools_used=scenario.expected_tools,
        )

    def _random_fact(self, topic: str) -> str:
        facts = {
            "favorite movies": random.choice(["loves sci-fi, especially Blade Runner", "into horror, favorites are Hereditary and Midsommar", "comedy fan, watches a lot of stand-up"]),
            "work schedule": random.choice(["works 9-5 weekdays", "flexible hours, usually online by 10am", "night owl, most productive after midnight"]),
            "birthday": random.choice(["March 15th", "July 22nd", "November 3rd", "December 18th"]),
            "food preferences": random.choice(["loves Thai and Indian food", "vegetarian", "big on BBQ and grilling", "allergic to shellfish"]),
            "music taste": random.choice(["into metal and prog rock", "hip hop and R&B", "electronic and synthwave", "classical and jazz"]),
            "gaming habits": random.choice(["plays Fallout 4 modded to hell", "big on VR games", "competitive FPS player", "casual RPG enjoyer"]),
            "hobbies": random.choice(["3D printing", "home automation", "AI/ML tinkering", "music production"]),
        }
        return facts.get(topic, f"various details about {topic}")
