"""Synthetic data generator for Tailscale VPN management scenarios."""

import random

from .base import (
    BaseGenerator,
    GeneratedExample,
    Message,
    Scenario,
    ToolCall,
    ToolResponse,
)

DEVICES = [
    ("bazzite-desktop", "100.64.1.1", "Linux 6.17", True),
    ("macbook-pro", "100.64.1.2", "macOS 15.3", True),
    ("iphone-14", "100.64.1.3", "iOS 18.2", False),
    ("windows-pc", "100.64.1.4", "Windows 11", True),
    ("nas-synology", "100.64.1.5", "DSM 7.2", True),
    ("pi-homelab", "100.64.1.6", "Raspbian 12", True),
    ("pixel-8", "100.64.1.7", "Android 15", False),
]

TAILNET = "tail1a2b3.ts.net"


class TailscaleGenerator(BaseGenerator):
    domain = "tailscale"
    schema_files = ["tailscale.json"]

    def _build_scenarios(self) -> list[Scenario]:
        return [
            Scenario(
                domain="tailscale",
                category="status",
                difficulty="easy",
                expected_tools=["tailscale.status"],
                user_prompts=[
                    "Is Tailscale connected?",
                    "Check Tailscale status",
                    "What's my Tailscale IP?",
                    "Am I on the tailnet?",
                    "Show Tailscale connection info",
                ],
            ),
            Scenario(
                domain="tailscale",
                category="list_devices",
                difficulty="easy",
                expected_tools=["tailscale.list_devices"],
                user_prompts=[
                    "What devices are on my tailnet?",
                    "List Tailscale devices",
                    "Show me all connected devices",
                    "Who's on the VPN?",
                    "Which machines are online?",
                ],
            ),
            Scenario(
                domain="tailscale",
                category="ping",
                difficulty="easy",
                expected_tools=["tailscale.ping"],
                user_prompts=[
                    "Ping the NAS through Tailscale",
                    "Can I reach the Windows PC?",
                    "Tailscale ping the MacBook",
                    "Check latency to the Raspberry Pi",
                    "Is the Synology reachable?",
                ],
            ),
            Scenario(
                domain="tailscale",
                category="send_file",
                difficulty="medium",
                expected_tools=["tailscale.send_file"],
                user_prompts=[
                    "Send this file to the MacBook via Tailscale",
                    "Transfer the backup to the NAS",
                    "Taildrop a file to the Windows PC",
                    "Send my config file to the Pi",
                    "Share this image with my phone via Tailscale",
                ],
            ),
        ]

    def generate_example(self, scenario: Scenario) -> GeneratedExample:
        prompt = scenario.random_prompt()
        messages: list[Message] = [self._make_user(prompt)]

        if scenario.category == "status":
            device = DEVICES[0]  # local machine
            messages.append(
                self._make_assistant_with_tool(
                    "Checking Tailscale.",
                    ToolCall("tailscale.status", {}),
                )
            )
            online_count = random.randint(2, len(DEVICES))
            messages.append(
                self._make_tool_response(
                    ToolResponse("tailscale.status", {
                        "connected": True,
                        "hostname": device[0],
                        "tailscale_ip": device[1],
                        "tailnet": TAILNET,
                        "os": device[2],
                        "exit_node": None,
                        "online_peers": online_count,
                        "uptime": f"{random.randint(1, 30)}d",
                    })
                )
            )
            messages.append(self._make_assistant_summary(
                f"Tailscale is connected. Your IP is {device[1]} on the {TAILNET} tailnet. "
                f"{online_count} peers online."
            ))

        elif scenario.category == "list_devices":
            online = random.sample(DEVICES, k=random.randint(3, len(DEVICES)))
            messages.append(
                self._make_assistant_with_tool(
                    "Listing devices on the tailnet.",
                    ToolCall("tailscale.list_devices", {}),
                )
            )
            messages.append(
                self._make_tool_response(
                    ToolResponse("tailscale.list_devices", {
                        "tailnet": TAILNET,
                        "devices": [
                            {"hostname": d[0], "ip": d[1], "os": d[2],
                             "online": d in online,
                             "last_seen": "now" if d in online else f"{random.randint(1, 48)}h ago"}
                            for d in DEVICES
                        ],
                        "total": len(DEVICES),
                        "online": len(online),
                    })
                )
            )
            online_names = [d[0] for d in online]
            offline_names = [d[0] for d in DEVICES if d not in online]
            summary = f"{len(online)}/{len(DEVICES)} devices online: {', '.join(online_names)}."
            if offline_names:
                summary += f" Offline: {', '.join(offline_names)}."
            messages.append(self._make_assistant_summary(summary))

        elif scenario.category == "ping":
            target = random.choice(DEVICES[1:])  # not self
            latency = round(random.uniform(1.0, 80.0), 1)
            direct = random.choice([True, True, False])
            messages.append(
                self._make_assistant_with_tool(
                    f"Pinging {target[0]}.",
                    ToolCall("tailscale.ping", {"hostname": target[0]}),
                )
            )
            reachable = random.random() > 0.1
            if reachable:
                messages.append(
                    self._make_tool_response(
                        ToolResponse("tailscale.ping", {
                            "hostname": target[0],
                            "ip": target[1],
                            "latency_ms": latency,
                            "direct": direct,
                            "via": "direct" if direct else "DERP relay",
                            "pong": True,
                        })
                    )
                )
                messages.append(self._make_assistant_summary(
                    f"{target[0]} is reachable — {latency}ms latency via "
                    f"{'direct connection' if direct else 'DERP relay (no direct path)'}."
                ))
            else:
                messages.append(
                    self._make_tool_response(
                        ToolResponse("tailscale.ping", {
                            "hostname": target[0],
                            "pong": False,
                            "error": "timeout after 5s — device may be offline",
                        })
                    )
                )
                messages.append(self._make_assistant_summary(
                    f"{target[0]} didn't respond — it might be offline or behind a restrictive firewall."
                ))

        elif scenario.category == "send_file":
            target = random.choice(DEVICES[1:])
            filename = random.choice([
                "backup.tar.gz", "config.yaml", "photo.jpg",
                "document.pdf", "script.sh", "notes.txt",
            ])
            size_mb = round(random.uniform(0.1, 500.0), 1)
            messages.append(
                self._make_assistant_with_tool(
                    f"Sending {filename} to {target[0]} via Taildrop.",
                    ToolCall("tailscale.send_file", {
                        "hostname": target[0],
                        "file_path": f"/home/deucebucket/{filename}",
                    }),
                )
            )
            success = random.random() > 0.1
            if success:
                messages.append(
                    self._make_tool_response(
                        ToolResponse("tailscale.send_file", {
                            "success": True,
                            "hostname": target[0],
                            "file": filename,
                            "size_mb": size_mb,
                            "transfer_time_s": round(size_mb / random.uniform(5.0, 50.0), 1),
                        })
                    )
                )
                messages.append(self._make_assistant_summary(
                    f"Sent {filename} ({size_mb}MB) to {target[0]} via Taildrop. Transfer complete."
                ))
            else:
                messages.append(
                    self._make_tool_response(
                        ToolResponse("tailscale.send_file", {
                            "success": False,
                            "error": f"{target[0]} rejected the file transfer — Taildrop may not be enabled on that device.",
                        })
                    )
                )
                messages.append(self._make_assistant_summary(
                    f"Transfer to {target[0]} failed — the device rejected the Taildrop request. "
                    f"Make sure file receiving is enabled in Tailscale settings on {target[0]}."
                ))

        return GeneratedExample(
            messages=messages,
            domain=self.domain,
            category=scenario.category,
            difficulty=scenario.difficulty,
            tools_used=scenario.expected_tools,
        )
