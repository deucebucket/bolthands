"""Synthetic data generator for systemd/Linux management scenarios."""

import random

from .base import (
    BaseGenerator,
    GeneratedExample,
    Message,
    Scenario,
    ToolCall,
    ToolResponse,
)

SERVICES = [
    "nginx", "postgresql", "docker", "sshd", "NetworkManager",
    "bluetooth", "cups", "firewalld", "crond", "fail2ban",
    "comfyui", "f5tts", "rvc", "llm-chat", "ai-dashboard",
    "mantella", "mantella-llm", "gpu-fan-curve",
]

LOG_UNITS = ["sshd", "nginx", "docker", "NetworkManager", "systemd-resolved"]

TIMER_NAMES = ["backup-daily", "cleanup-tmp", "cert-renewal", "health-check"]


class SystemdGenerator(BaseGenerator):
    domain = "systemd"
    schema_files = ["systemd.json"]

    def _build_scenarios(self) -> list[Scenario]:
        return [
            Scenario(
                domain="systemd",
                category="service_status",
                difficulty="easy",
                expected_tools=["systemd.unit_status"],
                user_prompts=[
                    f"Is {svc} running?"
                    for svc in SERVICES[:8]
                ] + [
                    "Check if the AI dashboard service is up",
                    "What's the status of nginx?",
                    "Is docker running?",
                ],
            ),
            Scenario(
                domain="systemd",
                category="service_restart",
                difficulty="easy",
                expected_tools=["systemd.unit_action"],
                user_prompts=[
                    f"Restart {svc}" for svc in SERVICES[:6]
                ] + [
                    "The web server is acting up, restart it",
                    "Restart the AI dashboard",
                    "Stop and start nginx",
                ],
            ),
            Scenario(
                domain="systemd",
                category="service_list",
                difficulty="easy",
                expected_tools=["systemd.unit_list"],
                user_prompts=[
                    "What services are running?",
                    "Show me all active services",
                    "List failed services",
                    "Which services are enabled?",
                    "Show me all AI-related services",
                ],
            ),
            Scenario(
                domain="systemd",
                category="journal_query",
                difficulty="medium",
                expected_tools=["systemd.journal_query"],
                user_prompts=[
                    f"Show me recent logs for {svc}" for svc in LOG_UNITS
                ] + [
                    "Any errors in the system journal from the last hour?",
                    "Show me nginx error logs",
                    "What happened with docker in the last 30 minutes?",
                    "Check sshd logs for failed login attempts",
                ],
            ),
            Scenario(
                domain="systemd",
                category="enable_disable",
                difficulty="medium",
                expected_tools=["systemd.unit_action"],
                user_prompts=[
                    f"Enable {svc} to start on boot" for svc in SERVICES[:4]
                ] + [
                    "Disable bluetooth from starting automatically",
                    "Make sure nginx starts on boot",
                    "Stop cups from auto-starting, I don't use a printer",
                ],
            ),
            Scenario(
                domain="systemd",
                category="timer_management",
                difficulty="medium",
                expected_tools=["systemd.timer_list"],
                user_prompts=[
                    "What timers are active?",
                    "Show me all scheduled tasks",
                    "When does the next backup run?",
                    "List all systemd timers",
                ],
            ),
            Scenario(
                domain="systemd",
                category="troubleshoot",
                difficulty="hard",
                expected_tools=["systemd.unit_status", "systemd.journal_query"],
                user_prompts=[
                    "nginx isn't responding, figure out what's wrong",
                    "The AI dashboard won't start, investigate",
                    "Docker containers are failing, check the logs",
                    "Something's eating CPU, check what services are misbehaving",
                ],
            ),
        ]

    def generate_example(self, scenario: Scenario) -> GeneratedExample:
        prompt = scenario.random_prompt()
        messages: list[Message] = [self._make_user(prompt)]

        if scenario.category == "service_status":
            svc = random.choice(SERVICES)
            active = random.choice([True, False])
            messages.append(
                self._make_assistant_with_tool(
                    f"Let me check the status of {svc}.",
                    ToolCall("systemd.unit_status", {"unit": f"{svc}.service"}),
                )
            )
            messages.append(
                self._make_tool_response(
                    ToolResponse("systemd.unit_status", {
                        "unit": f"{svc}.service",
                        "active": "active" if active else "inactive",
                        "sub": "running" if active else "dead",
                        "loaded": "enabled",
                        "description": f"{svc.title()} Service",
                        "pid": random.randint(1000, 50000) if active else None,
                        "memory": f"{random.randint(10, 500)}M" if active else None,
                        "uptime": f"{random.randint(1, 30)}d {random.randint(0, 23)}h" if active else None,
                    })
                )
            )
            if active:
                messages.append(self._make_assistant_summary(
                    f"{svc} is running — PID {messages[-1].content.split('pid')[0]}, been up for a while. All good."
                ))
            else:
                messages.append(self._make_assistant_summary(
                    f"{svc} is not running (inactive/dead). Want me to start it?"
                ))

        elif scenario.category == "service_restart":
            svc = random.choice(SERVICES)
            messages.append(
                self._make_assistant_with_tool(
                    f"Restarting {svc}.",
                    ToolCall("systemd.unit_action", {"unit": f"{svc}.service", "action": "restart"}),
                )
            )
            success = random.random() > 0.1
            messages.append(
                self._make_tool_response(
                    ToolResponse("systemd.unit_action", {
                        "success": success,
                        "unit": f"{svc}.service",
                        "action": "restart",
                        "message": "Unit restarted successfully" if success else f"Job for {svc}.service failed",
                    })
                )
            )
            if success:
                messages.append(self._make_assistant_summary(f"Done — {svc} has been restarted successfully."))
            else:
                messages.append(
                    self._make_assistant_with_tool(
                        f"{svc} failed to restart. Let me check the logs to see what went wrong.",
                        ToolCall("systemd.journal_query", {"unit": f"{svc}.service", "lines": 20, "priority": "err"}),
                    )
                )
                messages.append(
                    self._make_tool_response(
                        ToolResponse("systemd.journal_query", {
                            "entries": [
                                {"timestamp": "2026-03-19T14:30:00", "priority": "err",
                                 "message": f"{svc}[{random.randint(1000, 50000)}]: Failed to bind to port: Address already in use"},
                            ]
                        })
                    )
                )
                messages.append(self._make_assistant_summary(
                    f"{svc} failed because the port is already in use — something else is holding it. "
                    f"Want me to find what's using that port and kill it?"
                ))

        elif scenario.category == "service_list":
            active_svcs = random.sample(SERVICES, k=min(8, len(SERVICES)))
            messages.append(
                self._make_assistant_with_tool(
                    "Let me check what's running.",
                    ToolCall("systemd.unit_list", {"type": "service", "state": "active"}),
                )
            )
            messages.append(
                self._make_tool_response(
                    ToolResponse("systemd.unit_list", {
                        "units": [
                            {"unit": f"{svc}.service", "active": "active", "sub": "running"}
                            for svc in active_svcs
                        ]
                    })
                )
            )
            svc_list = ", ".join(active_svcs)
            messages.append(self._make_assistant_summary(
                f"Currently running: {svc_list}. That's {len(active_svcs)} active services."
            ))

        elif scenario.category == "journal_query":
            unit = random.choice(LOG_UNITS)
            messages.append(
                self._make_assistant_with_tool(
                    f"Pulling recent logs for {unit}.",
                    ToolCall("systemd.journal_query", {"unit": f"{unit}.service", "lines": 20}),
                )
            )
            messages.append(
                self._make_tool_response(
                    ToolResponse("systemd.journal_query", {
                        "entries": [
                            {"timestamp": "2026-03-19T14:25:00", "priority": "info",
                             "message": f"{unit}: Started successfully"},
                            {"timestamp": "2026-03-19T14:25:01", "priority": "info",
                             "message": f"{unit}: Listening on port {random.choice([80, 443, 5432, 22, 53])}"},
                        ]
                    })
                )
            )
            messages.append(self._make_assistant_summary(
                f"Logs look clean — {unit} started normally and is listening. No errors or warnings in recent entries."
            ))

        elif scenario.category == "enable_disable":
            svc = random.choice(SERVICES)
            action = random.choice(["enable", "disable"])
            messages.append(
                self._make_assistant_with_tool(
                    f"{'Enabling' if action == 'enable' else 'Disabling'} {svc} for auto-start on boot.",
                    ToolCall("systemd.unit_action", {"unit": f"{svc}.service", "action": action}),
                )
            )
            messages.append(
                self._make_tool_response(
                    ToolResponse("systemd.unit_action", {
                        "success": True,
                        "unit": f"{svc}.service",
                        "action": action,
                        "message": f"Created symlink" if action == "enable" else "Removed symlink",
                    })
                )
            )
            messages.append(self._make_assistant_summary(
                f"{svc} is now {'enabled — it will start automatically on boot' if action == 'enable' else 'disabled — it will not start on boot'}."
            ))

        elif scenario.category == "timer_management":
            messages.append(
                self._make_assistant_with_tool(
                    "Let me check active timers.",
                    ToolCall("systemd.timer_list", {}),
                )
            )
            messages.append(
                self._make_tool_response(
                    ToolResponse("systemd.timer_list", {
                        "timers": [
                            {"timer": f"{name}.timer", "next_trigger": "2026-03-20T02:00:00",
                             "last_trigger": "2026-03-19T02:00:00", "unit": f"{name}.service"}
                            for name in TIMER_NAMES
                        ]
                    })
                )
            )
            timer_list = ", ".join(TIMER_NAMES)
            messages.append(self._make_assistant_summary(
                f"Active timers: {timer_list}. Next runs are all scheduled for tonight/tomorrow. Everything looks on schedule."
            ))

        elif scenario.category == "troubleshoot":
            svc = random.choice(["nginx", "ai-dashboard", "docker"])
            messages.append(
                self._make_assistant_with_tool(
                    f"Let me check the status of {svc} first.",
                    ToolCall("systemd.unit_status", {"unit": f"{svc}.service"}),
                )
            )
            messages.append(
                self._make_tool_response(
                    ToolResponse("systemd.unit_status", {
                        "unit": f"{svc}.service",
                        "active": "failed",
                        "sub": "failed",
                        "loaded": "enabled",
                        "description": f"{svc.title()} Service",
                        "exit_code": "EXIT_FAILURE",
                    })
                )
            )
            messages.append(
                self._make_assistant_with_tool(
                    f"{svc} is in a failed state. Let me check the logs.",
                    ToolCall("systemd.journal_query", {"unit": f"{svc}.service", "lines": 30, "priority": "err"}),
                )
            )
            messages.append(
                self._make_tool_response(
                    ToolResponse("systemd.journal_query", {
                        "entries": [
                            {"timestamp": "2026-03-19T14:15:00", "priority": "err",
                             "message": f"{svc}: configuration test failed"},
                            {"timestamp": "2026-03-19T14:15:01", "priority": "err",
                             "message": f"{svc}: exiting with code 1"},
                        ]
                    })
                )
            )
            messages.append(self._make_assistant_summary(
                f"Found it — {svc} is in a failed state because of a configuration error. "
                f"The config test failed at 14:15. You probably have a syntax error in the config file. "
                f"Want me to check the config file for issues?"
            ))

        return GeneratedExample(
            messages=messages,
            domain=self.domain,
            category=scenario.category,
            difficulty=scenario.difficulty,
            tools_used=scenario.expected_tools,
        )
