"""Synthetic data generator for Flipper Zero management scenarios."""

import random

from .base import (
    BaseGenerator,
    GeneratedExample,
    Message,
    Scenario,
    ToolCall,
    ToolResponse,
)

IR_REMOTES = ["tv_samsung", "tv_lg", "ac_daikin", "soundbar_sony", "projector_epson"]
BADUSB_PAYLOADS = ["rickroll.txt", "wifi-password-grab.txt", "open-notepad.txt", "reverse-shell.txt", "disable-defender.txt"]
SUBGHZ_PROTOCOLS = ["princeton", "came", "nice_flo", "gate_tx", "linear"]
NFC_TYPES = ["NTAG215", "Mifare Classic 1K", "Mifare Ultralight", "DESFire"]
AMIIBO_NAMES = ["Mario", "Link", "Pikachu", "Samus", "Kirby", "Zelda", "Donkey Kong"]
GPIO_PINS = ["PA7", "PA6", "PA4", "PB3", "PB2", "PC3"]


class FlipperGenerator(BaseGenerator):
    domain = "flipper"
    schema_files = ["flipper.json"]

    def _build_scenarios(self) -> list[Scenario]:
        return [
            Scenario(
                domain="flipper",
                category="device_info",
                difficulty="easy",
                expected_tools=["flipper.device_info"],
                user_prompts=[
                    "How's the Flipper doing?",
                    "What firmware is on the Flipper?",
                    "Check Flipper Zero status",
                    "Is the Flipper connected?",
                    "What's the battery on the Flipper?",
                ],
            ),
            Scenario(
                domain="flipper",
                category="ir_transmit",
                difficulty="easy",
                expected_tools=["flipper.ir_transmit"],
                user_prompts=[
                    "Turn off the TV with the Flipper",
                    "Send the AC power signal",
                    "Turn on the projector",
                    "Mute the soundbar",
                    "Use the Flipper to control the TV — volume up",
                ],
            ),
            Scenario(
                domain="flipper",
                category="ir_list",
                difficulty="easy",
                expected_tools=["flipper.ir_list"],
                user_prompts=[
                    "What IR remotes do I have on the Flipper?",
                    "List saved IR signals",
                    "Show me all the TV remotes on the Flipper",
                ],
            ),
            Scenario(
                domain="flipper",
                category="badusb_deploy",
                difficulty="medium",
                expected_tools=["flipper.badusb_deploy"],
                user_prompts=[
                    "Run the rickroll BadUSB payload",
                    "Deploy the open-notepad script on the Flipper",
                    "Execute a BadUSB payload",
                    "Use the Flipper for a BadUSB attack — the wifi grab script",
                ],
            ),
            Scenario(
                domain="flipper",
                category="badusb_list",
                difficulty="easy",
                expected_tools=["flipper.badusb_list"],
                user_prompts=[
                    "What BadUSB scripts are on the Flipper?",
                    "List all BadUSB payloads",
                    "Show me available Ducky scripts",
                ],
            ),
            Scenario(
                domain="flipper",
                category="nfc_read",
                difficulty="medium",
                expected_tools=["flipper.nfc_read"],
                user_prompts=[
                    "Read the NFC tag with the Flipper",
                    "Scan this NFC card",
                    "What's on this NFC tag?",
                    "Read the badge with the Flipper",
                ],
            ),
            Scenario(
                domain="flipper",
                category="nfc_emulate",
                difficulty="medium",
                expected_tools=["flipper.nfc_emulate"],
                user_prompts=[
                    "Emulate the saved NFC tag",
                    "Use the Flipper as an NFC card",
                    "Play back the NFC data",
                ],
            ),
            Scenario(
                domain="flipper",
                category="subghz_receive",
                difficulty="medium",
                expected_tools=["flipper.subghz_receive"],
                user_prompts=[
                    "Listen for Sub-GHz signals",
                    "Capture the garage door signal",
                    "Start Sub-GHz receive mode",
                    "What's broadcasting on Sub-GHz around here?",
                ],
            ),
            Scenario(
                domain="flipper",
                category="subghz_transmit",
                difficulty="medium",
                expected_tools=["flipper.subghz_transmit"],
                user_prompts=[
                    "Replay the captured Sub-GHz signal",
                    "Send the gate opener signal",
                    "Transmit the saved garage door code",
                ],
            ),
            Scenario(
                domain="flipper",
                category="amiibo",
                difficulty="easy",
                expected_tools=["flipper.amiibo_emulate"],
                user_prompts=[
                    "Emulate the Mario amiibo",
                    "Use the Flipper as a Link amiibo",
                    "Play the Pikachu amiibo",
                    "What amiibos do I have on the Flipper?",
                ],
            ),
            Scenario(
                domain="flipper",
                category="gpio",
                difficulty="hard",
                expected_tools=["flipper.gpio_read", "flipper.gpio_write"],
                user_prompts=[
                    "Read the voltage on PA7",
                    "Set PA4 to high",
                    "Toggle the LED on PB3",
                    "What's the GPIO state?",
                ],
            ),
        ]

    def generate_example(self, scenario: Scenario) -> GeneratedExample:
        prompt = scenario.random_prompt()
        messages: list[Message] = [self._make_user(prompt)]

        if scenario.category == "device_info":
            messages.append(
                self._make_assistant_with_tool(
                    "Let me check the Flipper.",
                    ToolCall("flipper.device_info", {}),
                )
            )
            battery = random.randint(20, 100)
            messages.append(
                self._make_tool_response(
                    ToolResponse("flipper.device_info", {
                        "name": "Onede3rl",
                        "firmware": "Momentum mntm-012",
                        "hardware": "v15",
                        "battery": battery,
                        "charging": random.choice([True, False]),
                        "sd_card": "128GB",
                        "sd_free_mb": random.randint(50000, 120000),
                        "uptime_seconds": random.randint(3600, 86400 * 7),
                    })
                )
            )
            messages.append(self._make_assistant_summary(
                f"Flipper \"Onede3rl\" is connected — Momentum firmware mntm-012, "
                f"battery at {battery}%, 128GB SD card with plenty of free space. All good."
            ))

        elif scenario.category == "ir_transmit":
            remote = random.choice(IR_REMOTES)
            command = random.choice(["power", "volume_up", "volume_down", "mute", "source"])
            messages.append(
                self._make_assistant_with_tool(
                    f"Sending IR signal.",
                    ToolCall("flipper.ir_transmit", {"remote": remote, "command": command}),
                )
            )
            messages.append(
                self._make_tool_response(
                    ToolResponse("flipper.ir_transmit", {"success": True, "remote": remote, "command": command})
                )
            )
            messages.append(self._make_assistant_summary(f"Done — sent {command} signal from {remote}."))

        elif scenario.category == "ir_list":
            messages.append(
                self._make_assistant_with_tool(
                    "Checking saved IR remotes.",
                    ToolCall("flipper.ir_list", {}),
                )
            )
            messages.append(
                self._make_tool_response(
                    ToolResponse("flipper.ir_list", {
                        "remotes": [
                            {"name": r, "commands": random.randint(5, 25)}
                            for r in IR_REMOTES
                        ]
                    })
                )
            )
            messages.append(self._make_assistant_summary(
                f"You've got {len(IR_REMOTES)} saved IR remotes: {', '.join(IR_REMOTES)}. "
                f"Each has between 5-25 saved commands."
            ))

        elif scenario.category == "badusb_deploy":
            payload = random.choice(BADUSB_PAYLOADS)
            messages.append(
                self._make_assistant_with_tool(
                    f"Deploying BadUSB payload.",
                    ToolCall("flipper.badusb_deploy", {"payload": payload}),
                )
            )
            messages.append(
                self._make_tool_response(
                    ToolResponse("flipper.badusb_deploy", {
                        "success": True,
                        "payload": payload,
                        "status": "executed",
                        "duration_ms": random.randint(500, 5000),
                    })
                )
            )
            messages.append(self._make_assistant_summary(
                f"BadUSB payload \"{payload}\" executed successfully. Took about {random.randint(1, 5)} seconds."
            ))

        elif scenario.category == "badusb_list":
            messages.append(
                self._make_assistant_with_tool(
                    "Let me check what BadUSB scripts are loaded.",
                    ToolCall("flipper.badusb_list", {}),
                )
            )
            messages.append(
                self._make_tool_response(
                    ToolResponse("flipper.badusb_list", {
                        "payloads": [{"name": p, "size_bytes": random.randint(200, 5000)} for p in BADUSB_PAYLOADS]
                    })
                )
            )
            messages.append(self._make_assistant_summary(
                f"You've got {len(BADUSB_PAYLOADS)} BadUSB scripts: {', '.join(BADUSB_PAYLOADS)}."
            ))

        elif scenario.category == "nfc_read":
            nfc_type = random.choice(NFC_TYPES)
            messages.append(
                self._make_assistant_with_tool(
                    "Hold the tag near the Flipper — reading now.",
                    ToolCall("flipper.nfc_read", {}),
                )
            )
            messages.append(
                self._make_tool_response(
                    ToolResponse("flipper.nfc_read", {
                        "success": True,
                        "type": nfc_type,
                        "uid": f"{random.randint(0, 255):02X}:{random.randint(0, 255):02X}:{random.randint(0, 255):02X}:{random.randint(0, 255):02X}",
                        "data_size_bytes": random.randint(48, 1024),
                        "saved_as": f"nfc_capture_{random.randint(1, 999):03d}.nfc",
                    })
                )
            )
            messages.append(self._make_assistant_summary(
                f"Read an {nfc_type} tag. UID captured and data saved to the Flipper. "
                f"You can now emulate this tag whenever you need it."
            ))

        elif scenario.category == "nfc_emulate":
            messages.append(
                self._make_assistant_with_tool(
                    "Starting NFC emulation.",
                    ToolCall("flipper.nfc_emulate", {"file": f"nfc_capture_{random.randint(1, 50):03d}.nfc"}),
                )
            )
            messages.append(
                self._make_tool_response(
                    ToolResponse("flipper.nfc_emulate", {"success": True, "status": "emulating", "type": random.choice(NFC_TYPES)})
                )
            )
            messages.append(self._make_assistant_summary(
                "Flipper is now emulating the NFC tag. Hold it near the reader when you're ready."
            ))

        elif scenario.category == "subghz_receive":
            messages.append(
                self._make_assistant_with_tool(
                    "Starting Sub-GHz receive mode.",
                    ToolCall("flipper.subghz_receive", {"frequency": 433920000, "duration_seconds": 10}),
                )
            )
            captured = random.randint(0, 3)
            signals = [
                {"protocol": random.choice(SUBGHZ_PROTOCOLS), "frequency": 433920000,
                 "data": f"0x{random.randint(0, 0xFFFFFF):06X}", "saved_as": f"subghz_{i}.sub"}
                for i in range(captured)
            ]
            messages.append(
                self._make_tool_response(
                    ToolResponse("flipper.subghz_receive", {"signals_captured": captured, "signals": signals})
                )
            )
            if captured > 0:
                messages.append(self._make_assistant_summary(
                    f"Captured {captured} Sub-GHz signal(s) on 433.92 MHz. Saved to the Flipper — you can replay them anytime."
                ))
            else:
                messages.append(self._make_assistant_summary(
                    "Listened for 10 seconds on 433.92 MHz but didn't capture anything. Try pressing the remote while I listen, or try a different frequency."
                ))

        elif scenario.category == "subghz_transmit":
            messages.append(
                self._make_assistant_with_tool(
                    "Transmitting the saved signal.",
                    ToolCall("flipper.subghz_transmit", {"file": f"subghz_{random.randint(0, 5)}.sub"}),
                )
            )
            messages.append(
                self._make_tool_response(
                    ToolResponse("flipper.subghz_transmit", {"success": True, "status": "transmitted"})
                )
            )
            messages.append(self._make_assistant_summary("Signal transmitted. Did it work?"))

        elif scenario.category == "amiibo":
            amiibo = random.choice(AMIIBO_NAMES)
            messages.append(
                self._make_assistant_with_tool(
                    f"Loading the {amiibo} amiibo.",
                    ToolCall("flipper.amiibo_emulate", {"name": amiibo}),
                )
            )
            messages.append(
                self._make_tool_response(
                    ToolResponse("flipper.amiibo_emulate", {"success": True, "name": amiibo, "status": "emulating"})
                )
            )
            messages.append(self._make_assistant_summary(
                f"Flipper is emulating the {amiibo} amiibo. Hold it near your Switch when you're ready to scan."
            ))

        elif scenario.category == "gpio":
            pin = random.choice(GPIO_PINS)
            if "read" in prompt.lower() or "state" in prompt.lower() or "voltage" in prompt.lower():
                messages.append(
                    self._make_assistant_with_tool(
                        f"Reading GPIO pin {pin}.",
                        ToolCall("flipper.gpio_read", {"pin": pin}),
                    )
                )
                value = random.choice([0, 1])
                messages.append(
                    self._make_tool_response(
                        ToolResponse("flipper.gpio_read", {"pin": pin, "value": value, "voltage": 3.3 * value})
                    )
                )
                messages.append(self._make_assistant_summary(
                    f"Pin {pin} reads {'HIGH (3.3V)' if value else 'LOW (0V)'}."
                ))
            else:
                value = 1
                messages.append(
                    self._make_assistant_with_tool(
                        f"Setting GPIO pin {pin} to high.",
                        ToolCall("flipper.gpio_write", {"pin": pin, "value": value}),
                    )
                )
                messages.append(
                    self._make_tool_response(
                        ToolResponse("flipper.gpio_write", {"pin": pin, "value": value, "success": True})
                    )
                )
                messages.append(self._make_assistant_summary(f"Pin {pin} set to HIGH (3.3V)."))

        return GeneratedExample(
            messages=messages,
            domain=self.domain,
            category=scenario.category,
            difficulty=scenario.difficulty,
            tools_used=scenario.expected_tools,
        )
