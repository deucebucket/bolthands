"""Synthetic data generator for OpenClaw agent gateway scenarios."""

import random

from .base import (
    BaseGenerator,
    GeneratedExample,
    Message,
    Scenario,
    ToolCall,
    ToolResponse,
)

AGENTS = [
    ("coder", "CodeBot", "Coding and software development specialist"),
    ("hacker", "Shadow", "Security research and penetration testing"),
    ("rp", "Luna", "Roleplay and creative writing"),
    ("web", "Scout", "Web research and information gathering"),
    ("tool", "Swiss", "General tool use and automation"),
    ("main", "BoltHands", "Main orchestrator and router"),
]

CODING_TASKS = [
    "Write a Python script to parse CSV files",
    "Fix the bug in my Flask app",
    "Refactor this function to be async",
    "Create a REST API endpoint for user auth",
    "Write unit tests for the data module",
]

HACKING_TASKS = [
    "Scan the network for open ports",
    "Check if my server is vulnerable to log4j",
    "Run a security audit on my web app",
    "Test the SSH hardening on my VPS",
    "Enumerate subdomains for my domain",
]

WEB_TASKS = [
    "Research the latest GPU benchmarks",
    "Find the best price for a 4TB NVMe SSD",
    "Look up the release date for GTA 6",
    "Search for Linux gaming compatibility reports",
    "Find documentation for the Plex API",
]

RP_TASKS = [
    "Let's do a cyberpunk roleplay",
    "Create a D&D character backstory",
    "Write a noir detective scene",
    "Continue the space opera story",
    "Play as a sarcastic AI assistant",
]


class OpenClawGenerator(BaseGenerator):
    domain = "openclaw"
    schema_files = ["openclaw.json"]

    def _build_scenarios(self) -> list[Scenario]:
        return [
            Scenario(
                domain="openclaw",
                category="tool_selection",
                difficulty="medium",
                expected_tools=["openclaw.list_agents", "openclaw.delegate"],
                user_prompts=CODING_TASKS + WEB_TASKS + [
                    "Which agent should handle a Python refactoring task?",
                    "I need help with something — who's available?",
                ],
            ),
            Scenario(
                domain="openclaw",
                category="delegation",
                difficulty="medium",
                expected_tools=["openclaw.delegate"],
                user_prompts=[
                    "Send this to the coder agent: write a backup script",
                    "Have Shadow scan my network",
                    "Ask Scout to research RTX 5090 reviews",
                    "Route this task to the coding specialist",
                    "Delegate the security audit to the hacker agent",
                    "Let Luna handle the roleplay",
                ],
            ),
            Scenario(
                domain="openclaw",
                category="personality_maintenance",
                difficulty="hard",
                expected_tools=["openclaw.agent_config"],
                user_prompts=[
                    "What's Luna's personality like?",
                    "Update the coder agent's system prompt",
                    "Show me Shadow's configuration",
                    "Change the web agent's temperature to 0.3",
                    "What model is the coder agent using?",
                    "List all agent configurations",
                ],
            ),
            Scenario(
                domain="openclaw",
                category="error_handling",
                difficulty="hard",
                expected_tools=["openclaw.delegate", "openclaw.agent_status"],
                user_prompts=[
                    "The coder agent isn't responding, what's wrong?",
                    "My task failed — retry with a different agent",
                    "Shadow timed out on the scan, try again",
                    "The web agent keeps erroring out",
                    "Why did my delegation fail?",
                ],
            ),
            Scenario(
                domain="openclaw",
                category="multi_agent",
                difficulty="hard",
                expected_tools=["openclaw.delegate"],
                user_prompts=[
                    "Have the coder write a script, then have Shadow audit it for security",
                    "Research GPU prices with Scout, then have CodeBot write a price tracker",
                    "Get Luna to write a story, then have Scout fact-check the historical details",
                    "Run a security scan with Shadow and have CodeBot fix any issues found",
                ],
            ),
        ]

    def generate_example(self, scenario: Scenario) -> GeneratedExample:
        prompt = scenario.random_prompt()
        messages: list[Message] = [self._make_user(prompt)]

        if scenario.category == "tool_selection":
            messages.append(
                self._make_assistant_with_tool(
                    "Let me check which agents are available.",
                    ToolCall("openclaw.list_agents", {}),
                )
            )
            messages.append(
                self._make_tool_response(
                    ToolResponse("openclaw.list_agents", {
                        "agents": [
                            {"id": a[0], "name": a[1], "description": a[2],
                             "status": "online" if random.random() > 0.1 else "offline",
                             "model": random.choice(["qwen3.5-27b", "glm-4.7-flash", "gemma-3-27b"])}
                            for a in AGENTS
                        ]
                    })
                )
            )
            # Pick the right agent based on prompt
            if any(kw in prompt.lower() for kw in ["code", "python", "script", "refactor", "api", "test", "bug", "fix"]):
                agent = AGENTS[0]  # coder
            elif any(kw in prompt.lower() for kw in ["research", "find", "search", "look up", "price"]):
                agent = AGENTS[3]  # web
            else:
                agent = random.choice(AGENTS[:5])

            messages.append(
                self._make_assistant_with_tool(
                    f"This is a job for {agent[1]} ({agent[0]}). Routing the task.",
                    ToolCall("openclaw.delegate", {"agent": agent[0], "task": prompt}),
                )
            )
            messages.append(
                self._make_tool_response(
                    ToolResponse("openclaw.delegate", {
                        "success": True,
                        "agent": agent[0],
                        "agent_name": agent[1],
                        "response": f"[{agent[1]}]: Got it. Working on that now. I'll handle the {prompt.lower().split()[-1]} task.",
                        "tokens_used": random.randint(200, 2000),
                    })
                )
            )
            messages.append(self._make_assistant_summary(
                f"Delegated to {agent[1]} ({agent[2].lower()}). The task is being handled."
            ))

        elif scenario.category == "delegation":
            # Determine target agent from prompt
            agent = AGENTS[0]  # default to coder
            for a in AGENTS:
                if a[0] in prompt.lower() or a[1].lower() in prompt.lower():
                    agent = a
                    break
            if "security" in prompt.lower() or "scan" in prompt.lower() or "hack" in prompt.lower():
                agent = AGENTS[1]
            elif "research" in prompt.lower() or "web" in prompt.lower():
                agent = AGENTS[3]
            elif "roleplay" in prompt.lower():
                agent = AGENTS[2]

            task = prompt.split(":", 1)[-1].strip() if ":" in prompt else prompt
            messages.append(
                self._make_assistant_with_tool(
                    f"Routing to {agent[1]}.",
                    ToolCall("openclaw.delegate", {"agent": agent[0], "task": task}),
                )
            )
            messages.append(
                self._make_tool_response(
                    ToolResponse("openclaw.delegate", {
                        "success": True,
                        "agent": agent[0],
                        "agent_name": agent[1],
                        "response": f"[{agent[1]}]: On it. Starting the task now.",
                        "tokens_used": random.randint(300, 3000),
                        "duration_ms": random.randint(500, 5000),
                    })
                )
            )
            messages.append(self._make_assistant_summary(
                f"Done — {agent[1]} picked up the task and is working on it."
            ))

        elif scenario.category == "personality_maintenance":
            agent = random.choice(AGENTS)
            messages.append(
                self._make_assistant_with_tool(
                    f"Pulling {agent[1]}'s configuration.",
                    ToolCall("openclaw.agent_config", {"agent": agent[0], "action": "get"}),
                )
            )
            messages.append(
                self._make_tool_response(
                    ToolResponse("openclaw.agent_config", {
                        "agent": agent[0],
                        "name": agent[1],
                        "model": random.choice(["qwen3.5-27b", "glm-4.7-flash", "gemma-3-27b"]),
                        "temperature": round(random.uniform(0.1, 1.0), 1),
                        "system_prompt": f"You are {agent[1]}, a {agent[2].lower()}. Be helpful, direct, and technically proficient.",
                        "max_tokens": 4096,
                        "tools_enabled": True,
                    })
                )
            )
            messages.append(self._make_assistant_summary(
                f"{agent[1]} ({agent[0]}) is configured as a {agent[2].lower()}. "
                f"Want me to adjust any of the settings?"
            ))

        elif scenario.category == "error_handling":
            agent = random.choice(AGENTS[:5])
            messages.append(
                self._make_assistant_with_tool(
                    f"Let me check {agent[1]}'s status.",
                    ToolCall("openclaw.agent_status", {"agent": agent[0]}),
                )
            )
            error_type = random.choice(["timeout", "model_error", "overloaded"])
            messages.append(
                self._make_tool_response(
                    ToolResponse("openclaw.agent_status", {
                        "agent": agent[0],
                        "name": agent[1],
                        "status": "error",
                        "error": {
                            "timeout": "Request timed out after 120s — the model may be overloaded",
                            "model_error": "Model returned an empty response — possible OOM or crash",
                            "overloaded": "Agent queue is full (5/5 pending tasks)",
                        }[error_type],
                        "last_success": "2026-03-19T13:45:00",
                        "uptime": f"{random.randint(1, 24)}h",
                    })
                )
            )
            # Try a fallback agent
            fallback = random.choice([a for a in AGENTS[:5] if a[0] != agent[0]])
            messages.append(
                self._make_assistant_with_tool(
                    f"{agent[1]} is having issues ({error_type.replace('_', ' ')}). Let me try {fallback[1]} instead.",
                    ToolCall("openclaw.delegate", {"agent": fallback[0], "task": "retry the failed task"}),
                )
            )
            messages.append(
                self._make_tool_response(
                    ToolResponse("openclaw.delegate", {
                        "success": True,
                        "agent": fallback[0],
                        "agent_name": fallback[1],
                        "response": f"[{fallback[1]}]: Picked up the task from {agent[1]}. Working on it now.",
                        "tokens_used": random.randint(200, 1500),
                    })
                )
            )
            messages.append(self._make_assistant_summary(
                f"{agent[1]} was down ({error_type.replace('_', ' ')}), so I rerouted to {fallback[1]} who picked it up successfully."
            ))

        elif scenario.category == "multi_agent":
            # Two-stage delegation
            first_agent = random.choice(AGENTS[:2])  # coder or hacker
            second_agent = random.choice([a for a in AGENTS[:4] if a[0] != first_agent[0]])

            messages.append(
                self._make_assistant_with_tool(
                    f"Starting with {first_agent[1]} for the first part.",
                    ToolCall("openclaw.delegate", {"agent": first_agent[0], "task": "complete the first phase of the task"}),
                )
            )
            messages.append(
                self._make_tool_response(
                    ToolResponse("openclaw.delegate", {
                        "success": True,
                        "agent": first_agent[0],
                        "agent_name": first_agent[1],
                        "response": f"[{first_agent[1]}]: First phase complete. Here are my results.",
                        "tokens_used": random.randint(500, 3000),
                    })
                )
            )
            messages.append(
                self._make_assistant_with_tool(
                    f"Good. Now passing the results to {second_agent[1]} for the second phase.",
                    ToolCall("openclaw.delegate", {
                        "agent": second_agent[0],
                        "task": f"Review and continue from {first_agent[1]}'s output",
                    }),
                )
            )
            messages.append(
                self._make_tool_response(
                    ToolResponse("openclaw.delegate", {
                        "success": True,
                        "agent": second_agent[0],
                        "agent_name": second_agent[1],
                        "response": f"[{second_agent[1]}]: Reviewed {first_agent[1]}'s work. Second phase complete.",
                        "tokens_used": random.randint(500, 3000),
                    })
                )
            )
            messages.append(self._make_assistant_summary(
                f"Both phases done — {first_agent[1]} handled the first part, "
                f"then {second_agent[1]} took over for the follow-up. Task complete."
            ))

        return GeneratedExample(
            messages=messages,
            domain=self.domain,
            category=scenario.category,
            difficulty=scenario.difficulty,
            tools_used=scenario.expected_tools,
        )
