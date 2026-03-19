"""Synthetic data generator for Windows management scenarios."""

import random

from .base import (
    BaseGenerator,
    GeneratedExample,
    Message,
    Scenario,
    ToolCall,
    ToolResponse,
)

HOSTNAMES = ["DESKTOP-7K3M1NQ", "WORKSTATION-04", "GAMING-RIG", "DEV-PC", "HOME-PC"]

SERVICES_WIN = [
    ("Spooler", "Print Spooler"),
    ("wuauserv", "Windows Update"),
    ("W32Time", "Windows Time"),
    ("Themes", "Themes"),
    ("WinDefend", "Windows Defender"),
    ("BITS", "Background Intelligent Transfer Service"),
    ("Dhcp", "DHCP Client"),
    ("Dnscache", "DNS Client"),
    ("EventLog", "Windows Event Log"),
    ("LanmanServer", "Server"),
    ("RemoteRegistry", "Remote Registry"),
    ("TermService", "Remote Desktop Services"),
    ("SysMain", "SysMain (Superfetch)"),
    ("WSearch", "Windows Search"),
]

REGISTRY_PATHS = [
    r"HKLM\SOFTWARE\Microsoft\Windows\CurrentVersion\Run",
    r"HKLM\SYSTEM\CurrentControlSet\Services",
    r"HKCU\Software\Microsoft\Windows\CurrentVersion\Explorer\Advanced",
    r"HKLM\SOFTWARE\Policies\Microsoft\Windows\WindowsUpdate",
    r"HKLM\SOFTWARE\Microsoft\Windows NT\CurrentVersion",
]

TASK_NAMES = [
    "BackupDaily", "DiskCleanup", "WindowsUpdate", "DefenderScan",
    "SystemRestore", "CertRefresh", "TelemetryUpload",
]

EVENT_SOURCES = ["Application", "System", "Security", "Setup"]


class WindowsGenerator(BaseGenerator):
    domain = "windows"
    schema_files = ["windows.json"]

    def _build_scenarios(self) -> list[Scenario]:
        return [
            Scenario(
                domain="windows",
                category="powershell_command",
                difficulty="medium",
                expected_tools=["windows.powershell"],
                user_prompts=[
                    "Run Get-Process on the Windows box",
                    "Check disk space on the Windows PC",
                    "Show me running processes on Windows",
                    "How much RAM is being used on the Windows machine?",
                    "Get the IP address of my Windows PC",
                    "List installed programs on Windows",
                ],
            ),
            Scenario(
                domain="windows",
                category="service_manage",
                difficulty="easy",
                expected_tools=["windows.service_manage"],
                user_prompts=[
                    f"Restart the {name} service on Windows"
                    for _, name in SERVICES_WIN[:5]
                ] + [
                    "Stop the Print Spooler service",
                    "Start Remote Desktop Services on the Windows PC",
                    "Check if Windows Update service is running",
                    "What's the status of Windows Defender?",
                ],
            ),
            Scenario(
                domain="windows",
                category="update_check",
                difficulty="medium",
                expected_tools=["windows.update_check"],
                user_prompts=[
                    "Check for Windows updates",
                    "Are there any pending updates on Windows?",
                    "What updates are available for the Windows PC?",
                    "Is the Windows machine up to date?",
                    "Install pending Windows updates",
                ],
            ),
            Scenario(
                domain="windows",
                category="registry",
                difficulty="hard",
                expected_tools=["windows.registry_read"],
                user_prompts=[
                    "What's in the Windows Run registry key?",
                    "Check the startup programs in the registry",
                    "Read the Windows version from the registry",
                    "What are the Windows Update policies in the registry?",
                    "Show me the Explorer advanced settings in the registry",
                ],
            ),
            Scenario(
                domain="windows",
                category="scheduled_task",
                difficulty="medium",
                expected_tools=["windows.scheduled_task"],
                user_prompts=[
                    "List scheduled tasks on Windows",
                    "What tasks are scheduled to run?",
                    "Create a daily backup task on Windows",
                    "When does the disk cleanup task run?",
                    "Disable the telemetry scheduled task",
                ],
            ),
            Scenario(
                domain="windows",
                category="event_log",
                difficulty="medium",
                expected_tools=["windows.event_log"],
                user_prompts=[
                    "Show me recent Windows errors",
                    "Check the System event log",
                    "Any critical events on Windows?",
                    "Show Application errors from the last hour",
                    "Check for failed login attempts in the Security log",
                ],
            ),
            Scenario(
                domain="windows",
                category="file_manage",
                difficulty="easy",
                expected_tools=["windows.powershell"],
                user_prompts=[
                    "List files in C:\\Users\\Admin\\Documents",
                    "How big is C:\\Windows\\Temp?",
                    "Delete temporary files on Windows",
                    "What's in the Downloads folder on the Windows PC?",
                    "Copy the backup folder to D:\\Backups",
                ],
            ),
            Scenario(
                domain="windows",
                category="user_manage",
                difficulty="medium",
                expected_tools=["windows.powershell"],
                user_prompts=[
                    "List all user accounts on Windows",
                    "What groups is the Admin user in?",
                    "Create a new local user on Windows",
                    "Disable the Guest account on Windows",
                    "Who's logged in to the Windows PC right now?",
                ],
            ),
            Scenario(
                domain="windows",
                category="system_info",
                difficulty="easy",
                expected_tools=["windows.system_info"],
                user_prompts=[
                    "What are the specs of the Windows PC?",
                    "Show me system information for the Windows machine",
                    "What version of Windows is installed?",
                    "How long has the Windows PC been running?",
                    "What's the hostname of the Windows machine?",
                ],
            ),
        ]

    def generate_example(self, scenario: Scenario) -> GeneratedExample:
        prompt = scenario.random_prompt()
        messages: list[Message] = [self._make_user(prompt)]
        hostname = random.choice(HOSTNAMES)

        if scenario.category == "powershell_command":
            cmd = random.choice([
                ("Get-Process | Sort-Object CPU -Descending | Select-Object -First 10",
                 "Here are the top 10 processes by CPU usage:\n1. chrome (12.5%)\n2. svchost (3.2%)\n3. explorer (1.8%)"),
                ("Get-PSDrive -PSProvider FileSystem",
                 "C:\\ has 450GB free of 1TB, D:\\ has 200GB free of 500GB."),
                ("Get-CimInstance Win32_OperatingSystem | Select FreePhysicalMemory,TotalVisibleMemorySize",
                 "RAM: 12.4GB used out of 32GB (19.6GB free)."),
            ])
            messages.append(
                self._make_assistant_with_tool(
                    "Running that on the Windows machine.",
                    ToolCall("windows.powershell", {"command": cmd[0], "hostname": hostname}),
                )
            )
            messages.append(
                self._make_tool_response(
                    ToolResponse("windows.powershell", {
                        "success": True,
                        "hostname": hostname,
                        "output": cmd[1],
                        "exit_code": 0,
                    })
                )
            )
            messages.append(self._make_assistant_summary(
                f"Results from {hostname}:\n{cmd[1]}"
            ))

        elif scenario.category == "service_manage":
            svc_id, svc_name = random.choice(SERVICES_WIN)
            action = random.choice(["Start", "Stop", "Restart"])
            messages.append(
                self._make_assistant_with_tool(
                    f"{action}ing {svc_name} on {hostname}.",
                    ToolCall("windows.service_manage", {
                        "hostname": hostname,
                        "service": svc_id,
                        "action": action.lower(),
                    }),
                )
            )
            success = random.random() > 0.15
            if success:
                messages.append(
                    self._make_tool_response(
                        ToolResponse("windows.service_manage", {
                            "success": True,
                            "hostname": hostname,
                            "service": svc_id,
                            "display_name": svc_name,
                            "status": "Running" if action != "Stop" else "Stopped",
                        })
                    )
                )
                messages.append(self._make_assistant_summary(
                    f"{svc_name} has been {'started' if action == 'Start' else 'stopped' if action == 'Stop' else 'restarted'} on {hostname}."
                ))
            else:
                messages.append(
                    self._make_tool_response(
                        ToolResponse("windows.service_manage", {
                            "success": False,
                            "hostname": hostname,
                            "service": svc_id,
                            "error": f"Service '{svc_id}' cannot be started due to a dependency failure.",
                        })
                    )
                )
                messages.append(self._make_assistant_with_tool(
                    f"Failed due to a dependency issue. Let me check what dependencies {svc_name} needs.",
                    ToolCall("windows.powershell", {
                        "command": f"Get-Service {svc_id} -RequiredServices | Format-Table Name,Status",
                        "hostname": hostname,
                    }),
                ))
                dep_svc = random.choice(SERVICES_WIN)
                messages.append(
                    self._make_tool_response(
                        ToolResponse("windows.powershell", {
                            "success": True,
                            "hostname": hostname,
                            "output": f"Name          Status\n----          ------\n{dep_svc[0]}    Stopped",
                            "exit_code": 0,
                        })
                    )
                )
                messages.append(self._make_assistant_summary(
                    f"{svc_name} won't start because its dependency ({dep_svc[1]}) is stopped. "
                    f"Want me to start {dep_svc[1]} first and then retry?"
                ))

        elif scenario.category == "update_check":
            messages.append(
                self._make_assistant_with_tool(
                    f"Checking for updates on {hostname}.",
                    ToolCall("windows.update_check", {"hostname": hostname}),
                )
            )
            num_updates = random.choice([0, 0, 2, 5, 8])
            updates = [
                {"title": f"2026-03 Cumulative Update for Windows 11 (KB50{random.randint(10000, 99999)})",
                 "size_mb": random.randint(50, 800),
                 "severity": random.choice(["Critical", "Important", "Optional"])}
                for _ in range(num_updates)
            ]
            messages.append(
                self._make_tool_response(
                    ToolResponse("windows.update_check", {
                        "hostname": hostname,
                        "updates_available": num_updates,
                        "updates": updates,
                        "last_checked": "2026-03-19T10:30:00",
                    })
                )
            )
            if num_updates == 0:
                messages.append(self._make_assistant_summary(
                    f"{hostname} is up to date — no pending updates."
                ))
            else:
                critical = sum(1 for u in updates if u["severity"] == "Critical")
                messages.append(self._make_assistant_summary(
                    f"{hostname} has {num_updates} pending updates"
                    f"{f' ({critical} critical)' if critical else ''}. "
                    f"Want me to install them?"
                ))

        elif scenario.category == "registry":
            reg_path = random.choice(REGISTRY_PATHS)
            messages.append(
                self._make_assistant_with_tool(
                    f"Reading registry key.",
                    ToolCall("windows.registry_read", {"hostname": hostname, "path": reg_path}),
                )
            )
            entries = {
                r"HKLM\SOFTWARE\Microsoft\Windows\CurrentVersion\Run": {
                    "SecurityHealth": r"C:\Windows\System32\SecurityHealthSystray.exe",
                    "Discord": r"C:\Users\Admin\AppData\Local\Discord\Update.exe --processStart Discord.exe",
                    "Steam": r"C:\Program Files (x86)\Steam\steam.exe -silent",
                },
                r"HKLM\SOFTWARE\Microsoft\Windows NT\CurrentVersion": {
                    "ProductName": "Windows 11 Pro",
                    "CurrentBuild": "22631",
                    "DisplayVersion": "23H2",
                },
            }
            values = entries.get(reg_path, {"(Default)": "(value not set)", "Enabled": "1"})
            messages.append(
                self._make_tool_response(
                    ToolResponse("windows.registry_read", {
                        "hostname": hostname,
                        "path": reg_path,
                        "values": values,
                    })
                )
            )
            messages.append(self._make_assistant_summary(
                f"Registry key `{reg_path}` on {hostname} contains {len(values)} entries. "
                + ", ".join(f"{k}: {v}" for k, v in list(values.items())[:3])
            ))

        elif scenario.category == "scheduled_task":
            messages.append(
                self._make_assistant_with_tool(
                    "Checking scheduled tasks.",
                    ToolCall("windows.scheduled_task", {"hostname": hostname, "action": "list"}),
                )
            )
            tasks = [
                {"name": name, "status": random.choice(["Ready", "Running", "Disabled"]),
                 "next_run": f"2026-03-{random.randint(19, 25):02d}T{random.randint(0, 23):02d}:00:00",
                 "last_result": random.choice(["0x0", "0x0", "0x1"])}
                for name in TASK_NAMES
            ]
            messages.append(
                self._make_tool_response(
                    ToolResponse("windows.scheduled_task", {
                        "hostname": hostname,
                        "tasks": tasks,
                    })
                )
            )
            failed = [t for t in tasks if t["last_result"] != "0x0"]
            if failed:
                messages.append(self._make_assistant_summary(
                    f"Found {len(tasks)} scheduled tasks on {hostname}. "
                    f"Warning: {', '.join(t['name'] for t in failed)} had non-zero exit codes last run — might need attention."
                ))
            else:
                messages.append(self._make_assistant_summary(
                    f"All {len(tasks)} scheduled tasks on {hostname} are running fine. No issues."
                ))

        elif scenario.category == "event_log":
            source = random.choice(EVENT_SOURCES)
            messages.append(
                self._make_assistant_with_tool(
                    f"Pulling recent events from the {source} log.",
                    ToolCall("windows.event_log", {"hostname": hostname, "log": source, "level": "Error", "count": 10}),
                )
            )
            num_events = random.randint(0, 5)
            events = [
                {"time": f"2026-03-19T{random.randint(8, 16):02d}:{random.randint(0, 59):02d}:00",
                 "source": random.choice(["Application Error", "Service Control Manager", "Disk", "Kernel-Power"]),
                 "event_id": random.randint(1000, 9999),
                 "message": random.choice([
                     "The application svchost.exe stopped unexpectedly.",
                     "The service failed to start due to a logon failure.",
                     "The disk has bad sectors.",
                     "The system has rebooted without cleanly shutting down first.",
                 ])}
                for _ in range(num_events)
            ]
            messages.append(
                self._make_tool_response(
                    ToolResponse("windows.event_log", {
                        "hostname": hostname,
                        "log": source,
                        "events": events,
                        "total_matching": num_events,
                    })
                )
            )
            if num_events == 0:
                messages.append(self._make_assistant_summary(
                    f"No recent errors in the {source} event log on {hostname}. Clean bill of health."
                ))
            else:
                messages.append(self._make_assistant_summary(
                    f"Found {num_events} error(s) in the {source} log on {hostname}. "
                    f"Most recent: \"{events[0]['message']}\" — want me to dig deeper into any of these?"
                ))

        elif scenario.category == "file_manage":
            cmd = random.choice([
                ("Get-ChildItem 'C:\\Users\\Admin\\Documents' | Select Name,Length,LastWriteTime",
                 "Name                Length  LastWriteTime\n----                ------  -------------\nreport.docx         45280   3/18/2026\nbudget.xlsx         12800   3/15/2026\nnotes.txt           1024    3/19/2026"),
                ("Get-ChildItem 'C:\\Windows\\Temp' -Recurse | Measure-Object -Property Length -Sum",
                 "Count: 342 files, Total Size: 2.4 GB"),
            ])
            messages.append(
                self._make_assistant_with_tool(
                    "Running the file command.",
                    ToolCall("windows.powershell", {"command": cmd[0], "hostname": hostname}),
                )
            )
            messages.append(
                self._make_tool_response(
                    ToolResponse("windows.powershell", {
                        "success": True, "hostname": hostname,
                        "output": cmd[1], "exit_code": 0,
                    })
                )
            )
            messages.append(self._make_assistant_summary(f"Here's what I found:\n{cmd[1]}"))

        elif scenario.category == "user_manage":
            messages.append(
                self._make_assistant_with_tool(
                    "Querying user accounts.",
                    ToolCall("windows.powershell", {
                        "command": "Get-LocalUser | Select Name,Enabled,LastLogon",
                        "hostname": hostname,
                    }),
                )
            )
            messages.append(
                self._make_tool_response(
                    ToolResponse("windows.powershell", {
                        "success": True,
                        "hostname": hostname,
                        "output": "Name            Enabled  LastLogon\n----            -------  ---------\nAdmin           True     3/19/2026 9:15 AM\nGuest           False    Never\nDefaultAccount  False    Never",
                        "exit_code": 0,
                    })
                )
            )
            messages.append(self._make_assistant_summary(
                f"There are 3 local accounts on {hostname}: Admin (active, last login today), "
                f"Guest (disabled), and DefaultAccount (disabled)."
            ))

        elif scenario.category == "system_info":
            messages.append(
                self._make_assistant_with_tool(
                    "Pulling system info.",
                    ToolCall("windows.system_info", {"hostname": hostname}),
                )
            )
            messages.append(
                self._make_tool_response(
                    ToolResponse("windows.system_info", {
                        "hostname": hostname,
                        "os": "Windows 11 Pro 23H2",
                        "build": "22631.3296",
                        "cpu": "Intel Core i7-13700K",
                        "ram_gb": 32,
                        "uptime": f"{random.randint(1, 30)}d {random.randint(0, 23)}h",
                        "last_boot": "2026-03-15T08:30:00",
                        "domain": "WORKGROUP",
                    })
                )
            )
            messages.append(self._make_assistant_summary(
                f"{hostname} is running Windows 11 Pro 23H2 (Build 22631.3296) with an "
                f"i7-13700K and 32GB RAM. Been up since March 15th."
            ))

        return GeneratedExample(
            messages=messages,
            domain=self.domain,
            category=scenario.category,
            difficulty=scenario.difficulty,
            tools_used=scenario.expected_tools,
        )
