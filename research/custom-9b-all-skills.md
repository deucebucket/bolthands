# BoltHands 9B — Custom Qwen 3.5 9B All-Skills Model

## Research Document

**Objective:** Fine-tune Qwen 3.5 9B into "BoltHands 9B" — a single model that excels at OpenClaw agent work, Windows 11 system management, Plex media server management, and *arr stack management, all through a unified tool-calling interface.

**Target Hardware (Training):** RTX 3090 24GB VRAM, 64GB system RAM
**Target Hardware (Inference):** Raspberry Pi 4B ("Carl") — Q4_K_M GGUF via llama.cpp

---

## Table of Contents

1. [Base Model Analysis](#1-base-model-analysis)
2. [OpenClaw / Clawdius Agent Requirements](#2-openclaw--clawdius-agent-requirements)
3. [Windows 11 System Management](#3-windows-11-system-management)
4. [Plex Media Server Management](#4-plex-media-server-management)
5. [The *arr Stack Management](#5-the-arr-stack-management)
6. [Complete Tool Schema Design](#6-complete-tool-schema-design)
7. [Training Data Strategy](#7-training-data-strategy)
8. [Training Configuration](#8-training-configuration)
9. [Preventing Catastrophic Forgetting](#9-preventing-catastrophic-forgetting)
10. [Synthetic Data Generation Plan](#10-synthetic-data-generation-plan)
11. [HuggingFace Dataset Inventory](#11-huggingface-dataset-inventory)
12. [Training Pipeline](#12-training-pipeline)

---

## 1. Base Model Analysis

### Qwen 3.5 9B Architecture

| Component | Specification |
|-----------|---------------|
| Parameters | 9 billion |
| Native Context | 262,144 tokens |
| Extended Context | Up to 1,010,000 tokens (YaRN) |
| Hidden Dimension | 4,096 |
| Layers | 32 |
| Layer Pattern | 8 x (3 x Gated DeltaNet + FFN, 1 x Gated Attention + FFN) |
| Attention Heads | 16 Q, 4 KV (GQA) |
| Head Dimension | 256 |
| FFN Intermediate | 12,288 |
| Vocab Size | 248,320 |
| Multi-Token Prediction | Yes |
| Vision | Early fusion (native multimodal) |

### Why Qwen 3.5 9B is the Right Base

1. **Native tool calling** — Qwen 3.5 was trained with function calling from the start (Hermes-style `<tool_call>` format)
2. **Multimodal** — Vision encoder built in; useful for future screen-reading capabilities on Carl
3. **262K context** — Handles long system management sessions without truncation
4. **9B sweet spot** — Q4_K_M quantization = ~5.5GB, fits comfortably on Pi 4B with 8GB RAM
5. **Excellent coding baseline** — Strong at code generation, which transfers to PowerShell/API work
6. **Hybrid architecture** — DeltaNet + Attention mix provides good efficiency at inference

### Qwen 3.5 Tool Calling Format (Native)

This is the format BoltHands must preserve and extend:

**Tool Definition (system message):**
```json
[
  {
    "type": "function",
    "function": {
      "name": "get_current_temperature",
      "description": "Get current temperature at a location",
      "parameters": {
        "type": "object",
        "properties": {
          "location": {
            "type": "string",
            "description": "City and state, e.g. San Francisco, CA"
          }
        },
        "required": ["location"]
      }
    }
  }
]
```

**Model tool call output:**
```json
{
  "role": "assistant",
  "content": "",
  "function_call": {
    "name": "get_current_temperature",
    "arguments": "{\"location\": \"San Francisco, CA\"}"
  }
}
```

**Tool result fed back:**
```json
{
  "role": "function",
  "name": "get_current_temperature",
  "content": "{\"temperature\": 26.1, \"unit\": \"celsius\"}"
}
```

**Hermes-style (used in chat template):**
```
<|im_start|>assistant
<tool_call>
{"name": "function_name", "arguments": {"param": "value"}}
</tool_call>
<|im_end|>

<|im_start|>tool
<tool_response>
{"name": "function_name", "content": {"result": "data"}}
</tool_response>
<|im_end|>
```

---

## 2. OpenClaw / Clawdius Agent Requirements

### What is OpenClaw?

OpenClaw is a personal AI assistant gateway that runs on your own devices. Key characteristics:
- **Local-first architecture** — Gateway runs at `ws://127.0.0.1:18789`
- **Multi-channel** — WhatsApp, Telegram, Slack, Discord, Signal, iMessage, IRC, Matrix, WebChat, and more
- **OpenAI-compatible API** — Uses `openai-responses` API format (confirmed from your `openclaw.json`)
- **Skill-based tool system** — Tools defined via SKILL.md files, injected into agent context
- **Agent isolation** — Each agent (coder, hacker, rp, web, tool) runs in its own session with its own workspace
- **Personality files** — IDENTITY.md, SOUL.md, BOOTSTRAP.md, USER.md, TOOLS.md per agent

### Your Current OpenClaw Setup

From `~/.openclaw/openclaw.json`:
- Primary model: `Qwen3.5-9B-Q4_K_M.gguf` on port 8080
- API format: `openai-responses` (OpenAI-compatible)
- Agents: main, coder, hacker, rp, web, tool
- All agents currently use the same 9B model

### OpenClaw Tool-Calling Format

OpenClaw uses **OpenAI-compatible function calling** since it connects via `openai-responses` API. The model must support:

1. **OpenAI function calling format** — `tool_calls` array in assistant messages
2. **Streaming tool calls** — Partial function call deltas during generation
3. **Multi-tool calls** — Multiple function calls in a single response
4. **Tool result handling** — Processing `role: "tool"` messages with `tool_call_id`

### OpenClaw Built-in Tools (dot notation)

```
browser.snap         — Take browser screenshot
browser.action       — Execute browser action
browser.upload       — Upload file to browser
browser.profile      — Manage browser profiles
canvas.push          — Push content to Canvas UI
canvas.reset         — Reset Canvas
canvas.eval          — Evaluate code in Canvas
canvas.snapshot      — Take Canvas snapshot
node.list            — List available device nodes
node.describe        — Describe node capabilities
node.invoke          — Execute action on device node
sessions_list        — List active sessions
sessions_history     — Get session transcript
sessions_send        — Send message to another session
system.run           — Execute local command
system.notify        — Send notification
location.get         — Get device location
camera.snap          — Take camera photo
camera.clip          — Record camera clip
screen.record        — Record screen
```

### What Clawdius (the Fork) Needs

Clawdius running on "Carl" (Raspberry Pi 4B) needs the model to handle:

1. **All OpenClaw standard tool calls** — The existing tool format above
2. **Custom tools** — Windows management, Plex, *arr tools (defined below)
3. **Personality adherence** — Follow SOUL.md, IDENTITY.md personality specifications
4. **Multi-agent coordination** — Use `sessions_send` to delegate to other agents
5. **Streaming responses** — Work within OpenAI-compatible streaming API
6. **Context management** — Handle long conversations with compaction (safeguard mode)

### Training Data Needed for OpenClaw

- **Multi-turn conversations** with tool calls following OpenAI format
- **Personality-driven responses** — Maintaining consistent character across turns
- **Tool selection reasoning** — Choosing the right tool from many available
- **Error handling** — Graceful handling when tools fail or return unexpected results
- **Delegation patterns** — Knowing when to use `sessions_send` to route to specialist agents

---

## 3. Windows 11 System Management

### Capabilities Required

Carl needs to manage Windows 11 machines on the local network via PowerShell Remoting (WinRM). The model must generate correct PowerShell commands and understand Windows system administration.

### PowerShell Remoting (WinRM) Fundamentals

**Connection establishment:**
```powershell
# Create a PSSession to a remote Windows machine
$session = New-PSSession -ComputerName "DESKTOP-WIN11" -Credential $cred

# Execute commands remotely
Invoke-Command -Session $session -ScriptBlock {
    Get-Service | Where-Object {$_.Status -eq 'Running'}
}

# Interactive remote session
Enter-PSSession -ComputerName "DESKTOP-WIN11" -Credential $cred
```

### Domain Knowledge Areas

#### Windows Update Management
```powershell
# Check for updates
Get-WindowsUpdate
Install-WindowsUpdate -AcceptAll -AutoReboot
Get-WUHistory | Select-Object -First 20

# Using PSWindowsUpdate module
Install-Module PSWindowsUpdate -Force
Get-WUInstall -MicrosoftUpdate -AcceptAll -IgnoreReboot
```

#### Service Management
```powershell
Get-Service -Name "wuauserv"                    # Query service
Start-Service -Name "Spooler"                   # Start service
Stop-Service -Name "Spooler" -Force             # Stop service
Restart-Service -Name "Spooler"                 # Restart service
Set-Service -Name "Spooler" -StartupType Automatic  # Set startup type
Get-Service | Where-Object {$_.Status -eq 'Stopped' -and $_.StartType -eq 'Automatic'}
```

#### File System Operations
```powershell
# Remote file operations
Invoke-Command -ComputerName "DESKTOP-WIN11" -ScriptBlock {
    Get-ChildItem "C:\Users" -Recurse -Depth 2
    Copy-Item "C:\source\file.txt" "C:\dest\file.txt"
    Remove-Item "C:\temp\*" -Recurse -Force
    Get-ItemProperty "C:\Windows\System32\config\SYSTEM"
    Test-Path "C:\Program Files\SomeApp"
    Get-Content "C:\logs\app.log" -Tail 50
}
```

#### Registry Editing
```powershell
# Read registry
Get-ItemProperty -Path "HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion"
Get-ItemPropertyValue -Path "HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion" -Name "ProgramFilesDir"

# Write registry
Set-ItemProperty -Path "HKLM:\SOFTWARE\Policies\Microsoft\Windows\WindowsUpdate" -Name "NoAutoUpdate" -Value 1
New-ItemProperty -Path "HKLM:\SOFTWARE\MyApp" -Name "Setting1" -Value "enabled" -PropertyType String

# Registry navigation
Get-ChildItem "HKLM:\SOFTWARE\Microsoft" -Recurse -Depth 1
```

#### Task Scheduler
```powershell
# List scheduled tasks
Get-ScheduledTask | Where-Object {$_.State -eq 'Ready'}
Get-ScheduledTaskInfo -TaskName "GoogleUpdateTaskMachine*"

# Create scheduled task
$action = New-ScheduledTaskAction -Execute "PowerShell.exe" -Argument "-File C:\Scripts\backup.ps1"
$trigger = New-ScheduledTaskTrigger -Daily -At "2:00AM"
Register-ScheduledTask -TaskName "DailyBackup" -Action $action -Trigger $trigger -User "SYSTEM"

# Manage tasks
Start-ScheduledTask -TaskName "DailyBackup"
Disable-ScheduledTask -TaskName "DailyBackup"
Unregister-ScheduledTask -TaskName "DailyBackup" -Confirm:$false
```

#### Event Log Querying
```powershell
# Query event logs
Get-WinEvent -LogName System -MaxEvents 50
Get-WinEvent -FilterHashtable @{LogName='Application'; Level=2; StartTime=(Get-Date).AddDays(-1)}
Get-WinEvent -LogName Security | Where-Object {$_.Id -eq 4624}  # Logon events

# Event log statistics
Get-WinEvent -ListLog * | Where-Object {$_.RecordCount -gt 0} |
    Sort-Object RecordCount -Descending | Select-Object -First 10
```

#### User/Account Management
```powershell
# Local user management
Get-LocalUser
New-LocalUser -Name "newuser" -Password (ConvertTo-SecureString "P@ssw0rd" -AsPlainText -Force)
Add-LocalGroupMember -Group "Administrators" -Member "newuser"
Disable-LocalUser -Name "olduser"

# Active Directory (if domain-joined)
Get-ADUser -Filter * -Properties LastLogonDate | Where-Object {$_.Enabled -eq $true}
Get-ADComputer -Filter * | Select-Object Name, OperatingSystem
Unlock-ADAccount -Identity "lockeduser"
```

#### System Information & Health
```powershell
# System info
Get-ComputerInfo | Select-Object WindowsProductName, OsVersion, CsTotalPhysicalMemory
Get-CimInstance Win32_LogicalDisk | Select-Object DeviceID, @{N='FreeGB';E={[math]::Round($_.FreeSpace/1GB,2)}}
Get-Process | Sort-Object CPU -Descending | Select-Object -First 10
Get-NetAdapter | Select-Object Name, Status, LinkSpeed

# Performance
Get-Counter '\Processor(_Total)\% Processor Time' -SampleInterval 1 -MaxSamples 5
Get-CimInstance Win32_OperatingSystem | Select-Object FreePhysicalMemory, TotalVisibleMemorySize
```

### Training Data Sources for Windows Management

1. **PowerShell code datasets** (see HuggingFace inventory below)
2. **Synthetic generation** — Generate tool-calling conversations for each Windows operation
3. **Microsoft Learn documentation** — Scrape and convert to Q&A format
4. **Stack Overflow PowerShell tag** — Existing dataset: `RazinAleks/SO-Python_QA-System_Administration_and_DevOps_class`
5. **PowerShell Gallery module docs** — Command reference for PSWindowsUpdate, ActiveDirectory, etc.

---

## 4. Plex Media Server Management

### python-plexapi Reference

The model needs deep knowledge of the Plex API accessed through python-plexapi.

#### PlexServer Core Operations

| Method | Parameters | Purpose |
|--------|-----------|---------|
| `server.library.sections()` | — | List all library sections |
| `server.library.section(title)` | title: str | Get specific section |
| `server.search(query)` | query, mediatype, limit | Hub search across library |
| `server.sessions()` | — | Active playback sessions |
| `server.clients()` | — | Connected clients |
| `server.playlists()` | — | All playlists |
| `server.history()` | maxresults, mindate | Watch history |
| `server.systemAccounts()` | — | User accounts |
| `server.checkForUpdate()` | force, download | Check for Plex updates |
| `server.installUpdate()` | — | Install Plex update |
| `server.butlerTasks()` | — | Scheduled maintenance tasks |
| `server.runButlerTask(task)` | task name | Run maintenance immediately |
| `server.bandwidth()` | timespan, filters | Dashboard bandwidth data |
| `server.resources()` | — | Dashboard resource data |
| `server.transcodeSessions()` | — | Active transcodes |

#### Library Section Operations

| Method | Purpose |
|--------|---------|
| `section.all()` | All items in section |
| `section.search(title, **kwargs)` | Advanced search with filters |
| `section.recentlyAdded()` | Recently added items |
| `section.onDeck()` | In-progress items |
| `section.update(path=None)` | Scan for new media |
| `section.cancelUpdate()` | Stop scan |
| `section.refresh()` | Download fresh metadata |
| `section.emptyTrash()` | Clear section trash |
| `section.analyze()` | Run media analysis |
| `section.createCollection()` | Create collection |
| `section.collections()` | List collections |
| `section.createPlaylist()` | Create playlist |
| `section.history()` | Section watch history |

#### Movie-Specific

| Method | Purpose |
|--------|---------|
| `section.searchMovies(**kwargs)` | Query movies |
| `section.recentlyAddedMovies()` | Recent movies |

#### Show-Specific

| Method | Purpose |
|--------|---------|
| `section.searchShows(**kwargs)` | Query TV shows |
| `section.searchSeasons(**kwargs)` | Query seasons |
| `section.searchEpisodes(**kwargs)` | Query episodes |
| `section.recentlyAddedShows()` | Recent shows |
| `section.recentlyAddedEpisodes()` | Recent episodes |

#### Music-Specific

| Method | Purpose |
|--------|---------|
| `section.albums()` | All albums |
| `section.searchArtists(**kwargs)` | Search artists |
| `section.searchAlbums(**kwargs)` | Search albums |
| `section.searchTracks(**kwargs)` | Search tracks |

#### Playlist & Collection Management

| Method | Purpose |
|--------|---------|
| `server.createPlaylist(title, section, items)` | Create playlist |
| `server.createCollection(title, section, items)` | Create collection |
| `playlist.addItems(items)` | Add to playlist |
| `playlist.removeItems(items)` | Remove from playlist |
| `playlist.moveItem(item, after)` | Reorder playlist |
| `collection.addItems(items)` | Add to collection |

#### Common Plex Management Tasks

1. **Library scanning** — Trigger scan after adding new media
2. **User management** — Add/remove users, check who's watching
3. **Playback monitoring** — Who's streaming, what quality, any transcoding
4. **Collection curation** — Organize movies/shows into themed collections
5. **Playlist management** — Create/modify playlists
6. **Media quality** — Check for items below quality threshold
7. **Duplicate detection** — Find duplicate media files
8. **Maintenance** — Empty trash, optimize database, clean bundles
9. **Update management** — Check for and install Plex updates
10. **Bandwidth monitoring** — Track server usage and performance

---

## 5. The *arr Stack Management

### Sonarr API v3 (TV Shows)

**Base URL pattern:** `http://<host>:8989/api/v3/<endpoint>?apikey=<key>`

#### Key Endpoints

| Category | Endpoint | Method | Description |
|----------|----------|--------|-------------|
| **Series** | `/api/v3/series` | GET | List all series |
| | `/api/v3/series` | POST | Add new series |
| | `/api/v3/series/{id}` | PUT | Update series |
| | `/api/v3/series/{id}` | DELETE | Remove series |
| | `/api/v3/series/editor` | PUT | Bulk update series |
| **Episodes** | `/api/v3/episode` | GET | List episodes (filter by seriesId) |
| | `/api/v3/episode/{id}` | PUT | Modify episode |
| | `/api/v3/episode/monitor` | PUT | Toggle monitoring |
| **Episode Files** | `/api/v3/episodefile` | GET | List episode files |
| | `/api/v3/episodefile/{id}` | DELETE | Remove file |
| | `/api/v3/episodefile/editor` | PUT | Bulk modify files |
| **Quality** | `/api/v3/qualityprofile` | GET/POST | List/create quality profiles |
| | `/api/v3/qualityprofile/{id}` | PUT/DELETE | Update/delete profile |
| **Calendar** | `/api/v3/calendar` | GET | Upcoming episodes |
| **Wanted** | `/api/v3/wanted/missing` | GET | Missing episodes |
| | `/api/v3/wanted/cutoff` | GET | Cutoff unmet episodes |
| **Commands** | `/api/v3/command` | POST | Execute commands (search, refresh, rename) |
| **History** | `/api/v3/history` | GET | Download/grab history |
| **Indexers** | `/api/v3/indexer` | GET/POST | Manage indexers |
| **Download Clients** | `/api/v3/downloadclient` | GET/POST | Manage download clients |
| **Health** | `/api/v3/health` | GET | System health check |
| **Disk Space** | `/api/v3/diskspace` | GET | Storage usage |
| **Blocklist** | `/api/v3/blocklist` | GET | Blocked downloads |

#### Common Sonarr Commands (via POST `/api/v3/command`)
```json
{"name": "SeriesSearch", "seriesId": 1}
{"name": "SeasonSearch", "seriesId": 1, "seasonNumber": 1}
{"name": "EpisodeSearch", "episodeIds": [1, 2, 3]}
{"name": "RefreshSeries", "seriesId": 1}
{"name": "RescanSeries", "seriesId": 1}
{"name": "RssSync"}
{"name": "RenameFiles", "seriesId": 1, "files": [1, 2, 3]}
{"name": "MissingEpisodeSearch"}
```

### Radarr API v3 (Movies)

**Base URL pattern:** `http://<host>:7878/api/v3/<endpoint>?apikey=<key>`

#### Key Endpoints

| Category | Endpoint | Method | Description |
|----------|----------|--------|-------------|
| **Movies** | `/api/v3/movie` | GET | List all movies |
| | `/api/v3/movie` | POST | Add new movie |
| | `/api/v3/movie/{id}` | PUT | Update movie |
| | `/api/v3/movie/{id}` | DELETE | Remove movie |
| | `/api/v3/movie/lookup` | GET | Search by title/TMDB ID |
| | `/api/v3/movie/import` | POST | Import from filesystem |
| **Quality** | `/api/v3/qualityprofile` | GET/POST | List/create profiles |
| **Queue** | `/api/v3/queue` | GET | Download queue status |
| **Commands** | `/api/v3/command` | POST | Execute commands |
| **History** | `/api/v3/history` | GET | Download history |
| **Health** | `/api/v3/health` | GET | System health |
| **Disk Space** | `/api/v3/diskspace` | GET | Storage usage |
| **System** | `/api/v3/system/status` | GET | System info |

#### Common Radarr Commands
```json
{"name": "MoviesSearch", "movieIds": [1, 2, 3]}
{"name": "RefreshMovie", "movieId": 1}
{"name": "RssSync"}
{"name": "RenameMovie", "movieIds": [1, 2, 3]}
{"name": "MissingMoviesSearch"}
```

### Lidarr API v1 (Music)

**Base URL pattern:** `http://<host>:8686/api/v1/<endpoint>?apikey=<key>`

#### Key Endpoints

| Category | Endpoint | Method | Description |
|----------|----------|--------|-------------|
| **Artists** | `/api/v1/artist` | GET | List all artists |
| | `/api/v1/artist` | POST | Add new artist |
| | `/api/v1/artist/{id}` | PUT/DELETE | Update/remove artist |
| | `/api/v1/artist/lookup` | GET | Search artists |
| | `/api/v1/artist/editor` | PUT/DELETE | Bulk operations |
| **Albums** | `/api/v1/album` | GET | List albums (filter by artist) |
| | `/api/v1/album` | POST | Add album |
| | `/api/v1/album/{id}` | PUT/DELETE | Update/remove album |
| | `/api/v1/album/monitor` | PUT | Set monitoring status |
| | `/api/v1/album/lookup` | GET | Search albums |
| **Tracks** | `/api/v1/track` | GET | List tracks |
| | `/api/v1/track/{id}` | GET/PUT | Get/update track |
| **Quality** | `/api/v1/qualityprofile` | GET/POST | Manage quality profiles |
| **Commands** | `/api/v1/command` | POST | Execute commands |

### Prowlarr API v1 (Indexers)

**Base URL pattern:** `http://<host>:9696/api/v1/<endpoint>?apikey=<key>`

#### Key Endpoints

| Category | Endpoint | Method | Description |
|----------|----------|--------|-------------|
| **Indexers** | `/api/v1/indexer` | GET/POST | List/add indexers |
| | `/api/v1/indexer/{id}` | GET/PUT/DELETE | Manage specific indexer |
| | `/api/v1/indexer/bulk` | PUT/DELETE | Bulk operations |
| | `/api/v1/indexer/schema` | GET | Available indexer types |
| | `/api/v1/indexer/test` | POST | Test indexer |
| | `/api/v1/indexer/testall` | POST | Test all indexers |
| **Search** | `/api/v1/search` | GET/POST | Execute search |
| | `/api/v1/search/bulk` | POST | Bulk search |
| **Applications** | `/api/v1/applications` | GET/POST | Manage connected apps (Sonarr/Radarr/Lidarr) |
| | `/api/v1/applications/{id}` | PUT/DELETE | Manage specific app |
| | `/api/v1/applications/test` | POST | Test connection |
| **Download Clients** | `/api/v1/downloadclient` | GET/POST | Manage clients |
| **History** | `/api/v1/history` | GET | Search/download history |
| **System** | `/api/v1/system/status` | GET | System health |
| | `/api/v1/system/restart` | POST | Restart Prowlarr |
| | `/api/v1/indexer/categories` | GET | Available categories |

---

## 6. Complete Tool Schema Design

### Design Principles

1. **OpenAI-compatible format** — All tools use the standard OpenAI function calling schema
2. **Namespaced** — Tools grouped by domain: `win.*`, `plex.*`, `sonarr.*`, `radarr.*`, `lidarr.*`, `prowlarr.*`
3. **Consistent patterns** — CRUD operations follow same naming: `list`, `get`, `add`, `update`, `remove`
4. **Minimal parameters** — Required params only; optional params have defaults

### 6.1 BoltHands Core Tools

```json
[
  {
    "type": "function",
    "function": {
      "name": "bash",
      "description": "Execute a bash command on the local system (Carl / Raspberry Pi)",
      "parameters": {
        "type": "object",
        "properties": {
          "command": {"type": "string", "description": "The bash command to execute"},
          "timeout": {"type": "integer", "description": "Timeout in seconds (default: 30)"}
        },
        "required": ["command"]
      }
    }
  },
  {
    "type": "function",
    "function": {
      "name": "file_read",
      "description": "Read contents of a file on the local system",
      "parameters": {
        "type": "object",
        "properties": {
          "path": {"type": "string", "description": "Absolute file path"},
          "lines": {"type": "integer", "description": "Max lines to read (default: all)"}
        },
        "required": ["path"]
      }
    }
  },
  {
    "type": "function",
    "function": {
      "name": "file_write",
      "description": "Write content to a file on the local system",
      "parameters": {
        "type": "object",
        "properties": {
          "path": {"type": "string", "description": "Absolute file path"},
          "content": {"type": "string", "description": "Content to write"},
          "append": {"type": "boolean", "description": "Append instead of overwrite (default: false)"}
        },
        "required": ["path", "content"]
      }
    }
  },
  {
    "type": "function",
    "function": {
      "name": "web_search",
      "description": "Search the web using SearXNG metasearch engine",
      "parameters": {
        "type": "object",
        "properties": {
          "query": {"type": "string", "description": "Search query"},
          "num_results": {"type": "integer", "description": "Number of results (default: 5)"}
        },
        "required": ["query"]
      }
    }
  },
  {
    "type": "function",
    "function": {
      "name": "web_fetch",
      "description": "Fetch and extract content from a URL",
      "parameters": {
        "type": "object",
        "properties": {
          "url": {"type": "string", "description": "URL to fetch"},
          "selector": {"type": "string", "description": "Optional CSS selector to extract specific content"}
        },
        "required": ["url"]
      }
    }
  },
  {
    "type": "function",
    "function": {
      "name": "save_research",
      "description": "Save research findings to a markdown file",
      "parameters": {
        "type": "object",
        "properties": {
          "topic": {"type": "string", "description": "Research topic (used as filename)"},
          "content": {"type": "string", "description": "Markdown content to save"},
          "directory": {"type": "string", "description": "Directory to save in (default: ~/research/)"}
        },
        "required": ["topic", "content"]
      }
    }
  }
]
```

### 6.2 Windows Management Tools

```json
[
  {
    "type": "function",
    "function": {
      "name": "win.powershell",
      "description": "Execute a PowerShell command on a remote Windows machine via WinRM",
      "parameters": {
        "type": "object",
        "properties": {
          "host": {"type": "string", "description": "Windows hostname or IP address"},
          "command": {"type": "string", "description": "PowerShell command or script block to execute"},
          "as_admin": {"type": "boolean", "description": "Run with elevated privileges (default: false)"}
        },
        "required": ["host", "command"]
      }
    }
  },
  {
    "type": "function",
    "function": {
      "name": "win.service_manage",
      "description": "Manage a Windows service (start, stop, restart, status, set startup type)",
      "parameters": {
        "type": "object",
        "properties": {
          "host": {"type": "string", "description": "Windows hostname or IP"},
          "service": {"type": "string", "description": "Service name"},
          "action": {"type": "string", "enum": ["start", "stop", "restart", "status", "set_auto", "set_manual", "set_disabled"], "description": "Action to perform"}
        },
        "required": ["host", "service", "action"]
      }
    }
  },
  {
    "type": "function",
    "function": {
      "name": "win.update_check",
      "description": "Check for and optionally install Windows Updates on a remote machine",
      "parameters": {
        "type": "object",
        "properties": {
          "host": {"type": "string", "description": "Windows hostname or IP"},
          "action": {"type": "string", "enum": ["check", "install", "history"], "description": "Check for updates, install all, or view history"},
          "reboot": {"type": "boolean", "description": "Allow automatic reboot after install (default: false)"}
        },
        "required": ["host", "action"]
      }
    }
  },
  {
    "type": "function",
    "function": {
      "name": "win.registry",
      "description": "Read or write Windows registry values on a remote machine",
      "parameters": {
        "type": "object",
        "properties": {
          "host": {"type": "string", "description": "Windows hostname or IP"},
          "action": {"type": "string", "enum": ["get", "set", "delete", "list"], "description": "Registry operation"},
          "path": {"type": "string", "description": "Registry path (e.g., HKLM:\\SOFTWARE\\Microsoft)"},
          "name": {"type": "string", "description": "Value name (for get/set/delete)"},
          "value": {"type": "string", "description": "Value to set (for set action)"},
          "type": {"type": "string", "enum": ["String", "DWord", "QWord", "Binary", "MultiString", "ExpandString"], "description": "Registry value type (for set)"}
        },
        "required": ["host", "action", "path"]
      }
    }
  },
  {
    "type": "function",
    "function": {
      "name": "win.scheduled_task",
      "description": "Manage Windows Task Scheduler on a remote machine",
      "parameters": {
        "type": "object",
        "properties": {
          "host": {"type": "string", "description": "Windows hostname or IP"},
          "action": {"type": "string", "enum": ["list", "get", "create", "enable", "disable", "run", "delete"], "description": "Task action"},
          "name": {"type": "string", "description": "Task name"},
          "command": {"type": "string", "description": "Command to execute (for create)"},
          "schedule": {"type": "string", "description": "Cron-like schedule: 'daily@02:00', 'weekly@mon@09:00', 'hourly'"}
        },
        "required": ["host", "action"]
      }
    }
  },
  {
    "type": "function",
    "function": {
      "name": "win.event_log",
      "description": "Query Windows Event Logs on a remote machine",
      "parameters": {
        "type": "object",
        "properties": {
          "host": {"type": "string", "description": "Windows hostname or IP"},
          "log": {"type": "string", "description": "Log name: System, Application, Security, Setup"},
          "level": {"type": "string", "enum": ["critical", "error", "warning", "info", "all"], "description": "Minimum severity level"},
          "max_events": {"type": "integer", "description": "Maximum events to return (default: 20)"},
          "hours_back": {"type": "integer", "description": "Only events from last N hours (default: 24)"}
        },
        "required": ["host", "log"]
      }
    }
  },
  {
    "type": "function",
    "function": {
      "name": "win.file_manage",
      "description": "Remote file operations on a Windows machine",
      "parameters": {
        "type": "object",
        "properties": {
          "host": {"type": "string", "description": "Windows hostname or IP"},
          "action": {"type": "string", "enum": ["list", "read", "write", "copy", "move", "delete", "exists", "size"], "description": "File operation"},
          "path": {"type": "string", "description": "File or directory path"},
          "destination": {"type": "string", "description": "Destination path (for copy/move)"},
          "content": {"type": "string", "description": "Content to write (for write)"},
          "recursive": {"type": "boolean", "description": "Recursive operation (default: false)"}
        },
        "required": ["host", "action", "path"]
      }
    }
  },
  {
    "type": "function",
    "function": {
      "name": "win.user_manage",
      "description": "Manage local users and groups on a Windows machine",
      "parameters": {
        "type": "object",
        "properties": {
          "host": {"type": "string", "description": "Windows hostname or IP"},
          "action": {"type": "string", "enum": ["list_users", "list_groups", "add_user", "remove_user", "disable_user", "enable_user", "add_to_group", "remove_from_group", "reset_password"], "description": "User management action"},
          "username": {"type": "string", "description": "Username"},
          "group": {"type": "string", "description": "Group name"},
          "password": {"type": "string", "description": "Password (for add_user/reset_password)"}
        },
        "required": ["host", "action"]
      }
    }
  },
  {
    "type": "function",
    "function": {
      "name": "win.system_info",
      "description": "Get system information from a remote Windows machine",
      "parameters": {
        "type": "object",
        "properties": {
          "host": {"type": "string", "description": "Windows hostname or IP"},
          "category": {"type": "string", "enum": ["overview", "cpu", "memory", "disk", "network", "processes", "uptime"], "description": "Information category"}
        },
        "required": ["host", "category"]
      }
    }
  }
]
```

### 6.3 Plex Management Tools

```json
[
  {
    "type": "function",
    "function": {
      "name": "plex.library_scan",
      "description": "Scan a Plex library section for new media",
      "parameters": {
        "type": "object",
        "properties": {
          "section": {"type": "string", "description": "Library section name (e.g., 'Movies', 'TV Shows', 'Music')"},
          "path": {"type": "string", "description": "Optional specific path to scan"}
        },
        "required": ["section"]
      }
    }
  },
  {
    "type": "function",
    "function": {
      "name": "plex.library_list",
      "description": "List all items in a Plex library section with optional filtering",
      "parameters": {
        "type": "object",
        "properties": {
          "section": {"type": "string", "description": "Library section name"},
          "filter": {"type": "string", "description": "Optional search/filter query"},
          "sort": {"type": "string", "description": "Sort field: titleSort, addedAt, rating, year"},
          "limit": {"type": "integer", "description": "Max results (default: 50)"}
        },
        "required": ["section"]
      }
    }
  },
  {
    "type": "function",
    "function": {
      "name": "plex.now_playing",
      "description": "Get all active playback sessions on the Plex server",
      "parameters": {
        "type": "object",
        "properties": {}
      }
    }
  },
  {
    "type": "function",
    "function": {
      "name": "plex.recently_added",
      "description": "Get recently added media items",
      "parameters": {
        "type": "object",
        "properties": {
          "section": {"type": "string", "description": "Library section name (omit for all sections)"},
          "limit": {"type": "integer", "description": "Max results (default: 20)"}
        }
      }
    }
  },
  {
    "type": "function",
    "function": {
      "name": "plex.search",
      "description": "Search across all Plex libraries",
      "parameters": {
        "type": "object",
        "properties": {
          "query": {"type": "string", "description": "Search query"},
          "media_type": {"type": "string", "enum": ["movie", "show", "episode", "artist", "album", "track"], "description": "Optional media type filter"}
        },
        "required": ["query"]
      }
    }
  },
  {
    "type": "function",
    "function": {
      "name": "plex.collection_manage",
      "description": "Manage Plex collections",
      "parameters": {
        "type": "object",
        "properties": {
          "action": {"type": "string", "enum": ["list", "create", "add_items", "remove_items", "delete"], "description": "Collection operation"},
          "section": {"type": "string", "description": "Library section name"},
          "name": {"type": "string", "description": "Collection name"},
          "items": {"type": "array", "items": {"type": "string"}, "description": "Item titles to add/remove"}
        },
        "required": ["action", "section"]
      }
    }
  },
  {
    "type": "function",
    "function": {
      "name": "plex.playlist_manage",
      "description": "Manage Plex playlists",
      "parameters": {
        "type": "object",
        "properties": {
          "action": {"type": "string", "enum": ["list", "create", "add_items", "remove_items", "delete"], "description": "Playlist operation"},
          "name": {"type": "string", "description": "Playlist name"},
          "items": {"type": "array", "items": {"type": "string"}, "description": "Item titles to add/remove"},
          "section": {"type": "string", "description": "Library section (required for create)"}
        },
        "required": ["action"]
      }
    }
  },
  {
    "type": "function",
    "function": {
      "name": "plex.user_manage",
      "description": "Manage Plex users and sharing",
      "parameters": {
        "type": "object",
        "properties": {
          "action": {"type": "string", "enum": ["list", "get_activity", "check_who_watching"], "description": "User management action"},
          "username": {"type": "string", "description": "Optional username filter"}
        },
        "required": ["action"]
      }
    }
  },
  {
    "type": "function",
    "function": {
      "name": "plex.maintenance",
      "description": "Run Plex server maintenance tasks",
      "parameters": {
        "type": "object",
        "properties": {
          "task": {"type": "string", "enum": ["empty_trash", "clean_bundles", "optimize_db", "refresh_metadata", "check_update", "install_update", "butler_tasks"], "description": "Maintenance task to run"},
          "section": {"type": "string", "description": "Library section (for section-specific tasks)"}
        },
        "required": ["task"]
      }
    }
  },
  {
    "type": "function",
    "function": {
      "name": "plex.server_status",
      "description": "Get Plex server status: health, transcode sessions, bandwidth, connected clients",
      "parameters": {
        "type": "object",
        "properties": {
          "detail": {"type": "string", "enum": ["overview", "transcodes", "bandwidth", "clients", "history"], "description": "Status detail level"}
        },
        "required": ["detail"]
      }
    }
  }
]
```

### 6.4 Sonarr Tools (TV Shows)

```json
[
  {
    "type": "function",
    "function": {
      "name": "sonarr.series_list",
      "description": "List all TV series in Sonarr",
      "parameters": {
        "type": "object",
        "properties": {
          "filter": {"type": "string", "description": "Optional title filter"}
        }
      }
    }
  },
  {
    "type": "function",
    "function": {
      "name": "sonarr.series_add",
      "description": "Add a new TV series to Sonarr for monitoring and downloading",
      "parameters": {
        "type": "object",
        "properties": {
          "title": {"type": "string", "description": "Series title to search for"},
          "quality_profile": {"type": "string", "description": "Quality profile name (default: 'HD-1080p')"},
          "root_folder": {"type": "string", "description": "Root folder path for the series"},
          "monitor": {"type": "string", "enum": ["all", "future", "missing", "existing", "firstSeason", "latestSeason", "none"], "description": "Monitoring strategy (default: 'all')"},
          "search_now": {"type": "boolean", "description": "Immediately search for existing episodes (default: true)"}
        },
        "required": ["title"]
      }
    }
  },
  {
    "type": "function",
    "function": {
      "name": "sonarr.series_search",
      "description": "Trigger a search for missing/wanted episodes of a series",
      "parameters": {
        "type": "object",
        "properties": {
          "title": {"type": "string", "description": "Series title"},
          "season": {"type": "integer", "description": "Optional specific season number"},
          "episode": {"type": "integer", "description": "Optional specific episode number"}
        },
        "required": ["title"]
      }
    }
  },
  {
    "type": "function",
    "function": {
      "name": "sonarr.wanted",
      "description": "List missing or cutoff-unmet episodes",
      "parameters": {
        "type": "object",
        "properties": {
          "type": {"type": "string", "enum": ["missing", "cutoff"], "description": "Wanted type"},
          "limit": {"type": "integer", "description": "Max results (default: 20)"}
        },
        "required": ["type"]
      }
    }
  },
  {
    "type": "function",
    "function": {
      "name": "sonarr.calendar",
      "description": "Get upcoming episode air dates",
      "parameters": {
        "type": "object",
        "properties": {
          "days_ahead": {"type": "integer", "description": "Number of days to look ahead (default: 7)"},
          "days_back": {"type": "integer", "description": "Number of days to look back (default: 0)"}
        }
      }
    }
  },
  {
    "type": "function",
    "function": {
      "name": "sonarr.queue",
      "description": "Get current download queue status",
      "parameters": {
        "type": "object",
        "properties": {}
      }
    }
  },
  {
    "type": "function",
    "function": {
      "name": "sonarr.health",
      "description": "Check Sonarr system health and disk space",
      "parameters": {
        "type": "object",
        "properties": {
          "include_disk": {"type": "boolean", "description": "Include disk space info (default: true)"}
        }
      }
    }
  }
]
```

### 6.5 Radarr Tools (Movies)

```json
[
  {
    "type": "function",
    "function": {
      "name": "radarr.movie_list",
      "description": "List all movies in Radarr",
      "parameters": {
        "type": "object",
        "properties": {
          "filter": {"type": "string", "description": "Optional title filter"},
          "status": {"type": "string", "enum": ["all", "monitored", "unmonitored", "missing", "downloaded"], "description": "Filter by status"}
        }
      }
    }
  },
  {
    "type": "function",
    "function": {
      "name": "radarr.movie_add",
      "description": "Add a new movie to Radarr for monitoring and downloading",
      "parameters": {
        "type": "object",
        "properties": {
          "title": {"type": "string", "description": "Movie title to search for"},
          "quality_profile": {"type": "string", "description": "Quality profile name (default: 'HD-1080p')"},
          "root_folder": {"type": "string", "description": "Root folder path for the movie"},
          "search_now": {"type": "boolean", "description": "Immediately search for the movie (default: true)"}
        },
        "required": ["title"]
      }
    }
  },
  {
    "type": "function",
    "function": {
      "name": "radarr.movie_search",
      "description": "Trigger a search for a specific movie",
      "parameters": {
        "type": "object",
        "properties": {
          "title": {"type": "string", "description": "Movie title to search for"}
        },
        "required": ["title"]
      }
    }
  },
  {
    "type": "function",
    "function": {
      "name": "radarr.queue",
      "description": "Get current download queue status",
      "parameters": {
        "type": "object",
        "properties": {}
      }
    }
  },
  {
    "type": "function",
    "function": {
      "name": "radarr.health",
      "description": "Check Radarr system health and disk space",
      "parameters": {
        "type": "object",
        "properties": {
          "include_disk": {"type": "boolean", "description": "Include disk space info (default: true)"}
        }
      }
    }
  }
]
```

### 6.6 Lidarr Tools (Music)

```json
[
  {
    "type": "function",
    "function": {
      "name": "lidarr.artist_list",
      "description": "List all artists in Lidarr",
      "parameters": {
        "type": "object",
        "properties": {
          "filter": {"type": "string", "description": "Optional name filter"}
        }
      }
    }
  },
  {
    "type": "function",
    "function": {
      "name": "lidarr.artist_add",
      "description": "Add a new artist to Lidarr for monitoring",
      "parameters": {
        "type": "object",
        "properties": {
          "name": {"type": "string", "description": "Artist name to search for"},
          "quality_profile": {"type": "string", "description": "Quality profile name"},
          "root_folder": {"type": "string", "description": "Root folder path"},
          "monitor": {"type": "string", "enum": ["all", "future", "missing", "existing", "first", "latest", "none"], "description": "Monitoring strategy"},
          "search_now": {"type": "boolean", "description": "Immediately search for music (default: true)"}
        },
        "required": ["name"]
      }
    }
  },
  {
    "type": "function",
    "function": {
      "name": "lidarr.album_list",
      "description": "List albums for an artist or all albums",
      "parameters": {
        "type": "object",
        "properties": {
          "artist": {"type": "string", "description": "Optional artist name filter"},
          "monitored_only": {"type": "boolean", "description": "Only show monitored albums (default: false)"}
        }
      }
    }
  },
  {
    "type": "function",
    "function": {
      "name": "lidarr.search",
      "description": "Search for missing or wanted music",
      "parameters": {
        "type": "object",
        "properties": {
          "artist": {"type": "string", "description": "Artist name (searches all missing if omitted)"},
          "album": {"type": "string", "description": "Specific album title"}
        }
      }
    }
  },
  {
    "type": "function",
    "function": {
      "name": "lidarr.health",
      "description": "Check Lidarr system health",
      "parameters": {
        "type": "object",
        "properties": {}
      }
    }
  }
]
```

### 6.7 Prowlarr Tools (Indexers)

```json
[
  {
    "type": "function",
    "function": {
      "name": "prowlarr.indexer_list",
      "description": "List all configured indexers in Prowlarr",
      "parameters": {
        "type": "object",
        "properties": {}
      }
    }
  },
  {
    "type": "function",
    "function": {
      "name": "prowlarr.indexer_test",
      "description": "Test connectivity of indexers",
      "parameters": {
        "type": "object",
        "properties": {
          "indexer_name": {"type": "string", "description": "Specific indexer to test (omit for all)"}
        }
      }
    }
  },
  {
    "type": "function",
    "function": {
      "name": "prowlarr.search",
      "description": "Search across all indexers for content",
      "parameters": {
        "type": "object",
        "properties": {
          "query": {"type": "string", "description": "Search query"},
          "category": {"type": "string", "enum": ["movies", "tv", "music", "books", "other"], "description": "Search category"},
          "indexer": {"type": "string", "description": "Optional specific indexer to search"}
        },
        "required": ["query"]
      }
    }
  },
  {
    "type": "function",
    "function": {
      "name": "prowlarr.app_status",
      "description": "Check status of connected applications (Sonarr, Radarr, Lidarr)",
      "parameters": {
        "type": "object",
        "properties": {}
      }
    }
  },
  {
    "type": "function",
    "function": {
      "name": "prowlarr.history",
      "description": "View recent search and grab history",
      "parameters": {
        "type": "object",
        "properties": {
          "limit": {"type": "integer", "description": "Max results (default: 20)"}
        }
      }
    }
  }
]
```

### Tool Count Summary

| Domain | Tools | Key Operations |
|--------|-------|----------------|
| BoltHands Core | 6 | bash, file_read, file_write, web_search, web_fetch, save_research |
| Windows Management | 9 | powershell, service_manage, update_check, registry, scheduled_task, event_log, file_manage, user_manage, system_info |
| Plex | 10 | library_scan, library_list, now_playing, recently_added, search, collection_manage, playlist_manage, user_manage, maintenance, server_status |
| Sonarr | 7 | series_list, series_add, series_search, wanted, calendar, queue, health |
| Radarr | 5 | movie_list, movie_add, movie_search, queue, health |
| Lidarr | 5 | artist_list, artist_add, album_list, search, health |
| Prowlarr | 5 | indexer_list, indexer_test, search, app_status, history |
| **Total** | **47** | |

Plus OpenClaw's built-in tools (browser.*, canvas.*, node.*, sessions_*, system.*) that the model encounters at runtime.

---

## 7. Training Data Strategy

### 7.1 Dataset Architecture

**Approach: Unified single LoRA adapter with mixed training data**

Rationale for unified adapter over stacked adapters:
- Stacked LoRA adapters cause interference at inference time and require complex merging
- A single adapter with diverse training data lets the model learn cross-domain patterns
- Tool selection across domains (e.g., "scan for new episodes and update Plex") requires unified knowledge
- Simpler deployment on Pi: one model, one adapter, done

### 7.2 Training Data Composition

Target: **~150,000 training examples** across all domains

| Domain | Source | Est. Examples | Format |
|--------|--------|---------------|--------|
| **Function Calling (base)** | Existing HF datasets | 40,000 | Diverse tool calls |
| **OpenClaw Agent** | Synthetic | 15,000 | Multi-turn + personality |
| **Windows Management** | Synthetic + PS datasets | 25,000 | PowerShell tool calls |
| **Plex Management** | Synthetic | 15,000 | Plex API tool calls |
| **Sonarr** | Synthetic | 12,000 | TV management tool calls |
| **Radarr** | Synthetic | 10,000 | Movie management tool calls |
| **Lidarr** | Synthetic | 8,000 | Music management tool calls |
| **Prowlarr** | Synthetic | 5,000 | Indexer management tool calls |
| **Cross-domain** | Synthetic | 10,000 | Multi-service workflows |
| **Conversation/Personality** | Existing HF datasets | 10,000 | Personality consistency |
| **Total** | | **~150,000** | |

### 7.3 Data Format

All training data will use Qwen 3.5's native ChatML format with Hermes-style tool calling:

```json
{
  "conversations": [
    {
      "from": "system",
      "value": "You are BoltHands, a capable AI assistant running on Carl (Raspberry Pi 4B). You have access to the following tools:\n<tools>\n[{\"type\": \"function\", \"function\": {\"name\": \"sonarr.series_add\", ...}}, ...]\n</tools>\n\nYou manage the home network including Windows PCs, Plex media server, and the *arr stack."
    },
    {
      "from": "user",
      "value": "Hey, can you add The Last of Us to Sonarr and make sure it searches for all episodes?"
    },
    {
      "from": "assistant",
      "value": "Sure, let me add that series for you.\n<tool_call>\n{\"name\": \"sonarr.series_add\", \"arguments\": {\"title\": \"The Last of Us\", \"monitor\": \"all\", \"search_now\": true}}\n</tool_call>"
    },
    {
      "from": "tool",
      "value": "<tool_response>\n{\"name\": \"sonarr.series_add\", \"content\": {\"success\": true, \"series_id\": 42, \"title\": \"The Last of Us\", \"seasons\": 2, \"monitored_episodes\": 19, \"search_initiated\": true}}\n</tool_response>"
    },
    {
      "from": "assistant",
      "value": "Done. Added The Last of Us to Sonarr — 2 seasons, 19 episodes total. Search is running now. I'll keep an eye on the download queue. Want me to also check if it shows up in Plex once episodes start downloading?"
    }
  ]
}
```

### 7.4 Cross-Domain Training Examples

These are crucial for teaching the model to chain tools across services:

**Example: "Download a movie and add it to a Plex collection"**
```json
{
  "conversations": [
    {"from": "system", "value": "[system prompt with radarr and plex tools]"},
    {"from": "user", "value": "Find and download Dune Part Two, and once it's done add it to my 'Sci-Fi Epics' collection in Plex."},
    {"from": "assistant", "value": "I'll search for Dune Part Two in Radarr first.\n<tool_call>\n{\"name\": \"radarr.movie_add\", \"arguments\": {\"title\": \"Dune Part Two\", \"search_now\": true}}\n</tool_call>"},
    {"from": "tool", "value": "<tool_response>\n{\"name\": \"radarr.movie_add\", \"content\": {\"success\": true, \"movie_id\": 128, \"title\": \"Dune: Part Two\", \"year\": 2024, \"search_initiated\": true}}\n</tool_response>"},
    {"from": "assistant", "value": "Dune: Part Two (2024) has been added to Radarr and the search is running. Once it downloads and gets imported, I'll add it to your Sci-Fi Epics collection. Let me check the current queue.\n<tool_call>\n{\"name\": \"radarr.queue\", \"arguments\": {}}\n</tool_call>"},
    {"from": "tool", "value": "<tool_response>\n{\"name\": \"radarr.queue\", \"content\": {\"items\": [{\"title\": \"Dune: Part Two\", \"status\": \"downloading\", \"progress\": 12.5, \"eta\": \"45 minutes\"}]}}\n</tool_response>"},
    {"from": "assistant", "value": "It's downloading now — about 45 minutes to go. Once it finishes and Plex picks it up, I'll add it to the Sci-Fi Epics collection. I'll keep tabs on it."}
  ]
}
```

**Example: "Check Windows machine health and Plex status"**
```json
{
  "conversations": [
    {"from": "system", "value": "[system prompt with win and plex tools]"},
    {"from": "user", "value": "How's the gaming PC doing? And is anyone watching anything on Plex right now?"},
    {"from": "assistant", "value": "Let me check both.\n<tool_call>\n{\"name\": \"win.system_info\", \"arguments\": {\"host\": \"GAMING-PC\", \"category\": \"overview\"}}\n</tool_call>\n<tool_call>\n{\"name\": \"plex.now_playing\", \"arguments\": {}}\n</tool_call>"},
    {"from": "tool", "value": "<tool_response>\n{\"name\": \"win.system_info\", \"content\": {\"hostname\": \"GAMING-PC\", \"os\": \"Windows 11 Pro 24H2\", \"cpu_usage\": 8, \"memory_used_gb\": 12.4, \"memory_total_gb\": 32, \"uptime\": \"3 days 14 hours\", \"disk_c_free_gb\": 234}}\n</tool_response>\n<tool_response>\n{\"name\": \"plex.now_playing\", \"content\": {\"sessions\": [{\"user\": \"sarah\", \"title\": \"Severance S02E08\", \"player\": \"Roku Ultra\", \"quality\": \"1080p\", \"transcode\": false}]}}\n</tool_response>"},
    {"from": "assistant", "value": "Gaming PC is looking good — Windows 11 Pro, only 8% CPU, 12.4 of 32GB RAM used, 234GB free on C:. Been up for about 3.5 days.\n\nOn Plex, Sarah's watching Severance S02E08 on the Roku Ultra, direct playing at 1080p — no transcoding, so the server's not breaking a sweat."}
  ]
}
```

---

## 8. Training Configuration

### 8.1 Hardware Constraints

**Training rig:** RTX 3090 (24GB VRAM), 64GB DDR4

With QLoRA (4-bit quantization + LoRA adapters):
- Qwen 3.5 9B base model in 4-bit: ~5.5GB VRAM
- LoRA adapters + optimizer states: ~4-8GB VRAM
- Activations + gradients: ~8-10GB VRAM
- **Total: ~18-22GB VRAM** — fits on RTX 3090

### 8.2 Recommended LoRA Configuration

```yaml
# QLoRA Configuration for BoltHands 9B
lora_rank: 64                    # Higher rank for multi-domain knowledge
lora_alpha: 128                  # Alpha = 2x rank (standard ratio)
lora_dropout: 0.05
target_modules:                  # All linear layers for maximum adaptation
  - q_proj
  - k_proj
  - v_proj
  - o_proj
  - gate_proj
  - up_proj
  - down_proj
quantization: 4bit               # QLoRA with NF4
quantization_type: nf4
double_quantization: true         # Double quantization for memory savings
```

**Why rank 64?**
- Rank 8-16: Sufficient for single-domain fine-tunes
- Rank 32: Good for 2-3 domains
- Rank 64: Necessary for 5+ distinct skill domains (tools, Windows, Plex, *arr, personality)
- Rank 128: Overkill, diminishing returns, slower training
- At rank 64, the LoRA adapter adds ~330M trainable parameters (~3.6% of base model)

### 8.3 Training Hyperparameters

```yaml
# Unsloth / LLaMA Factory compatible config
training:
  framework: unsloth              # 2x faster, 70% less VRAM than standard
  method: sft                     # Supervised Fine-Tuning

  # Batch settings
  per_device_train_batch_size: 2
  gradient_accumulation_steps: 8  # Effective batch size = 16

  # Learning rate
  learning_rate: 2.0e-4           # Standard for QLoRA
  lr_scheduler_type: cosine
  warmup_ratio: 0.05

  # Training duration
  num_train_epochs: 3             # 3 epochs over 150K examples
  max_seq_length: 4096            # Sufficient for most tool-calling conversations

  # Optimization
  optimizer: adamw_8bit           # 8-bit Adam for memory savings
  weight_decay: 0.01
  max_grad_norm: 1.0

  # Precision
  bf16: true                      # BFloat16 on Ampere GPUs
  tf32: true

  # Saving
  save_strategy: steps
  save_steps: 500
  save_total_limit: 5

  # Logging
  logging_steps: 10
  report_to: wandb
```

### 8.4 Estimated Training Time

| Metric | Value |
|--------|-------|
| Training examples | ~150,000 |
| Epochs | 3 |
| Total training steps | ~150,000 * 3 / 16 = ~28,125 steps |
| Estimated speed (Unsloth + RTX 3090) | ~2.5 steps/second |
| **Total training time** | **~3.1 hours** |

This is very manageable. With Unsloth's optimizations on the RTX 3090, the full training run should complete in under 4 hours. You can afford to experiment with multiple runs.

### 8.5 Framework Recommendation

**Primary: Unsloth** (via distrobox "ai")

```python
from unsloth import FastLanguageModel
import torch

# Load base model with 4-bit quantization
model, tokenizer = FastLanguageModel.from_pretrained(
    model_name="Qwen/Qwen3.5-9B",
    max_seq_length=4096,
    dtype=None,  # Auto-detect
    load_in_4bit=True,
)

# Apply LoRA
model = FastLanguageModel.get_peft_model(
    model,
    r=64,
    lora_alpha=128,
    lora_dropout=0.05,
    target_modules=[
        "q_proj", "k_proj", "v_proj", "o_proj",
        "gate_proj", "up_proj", "down_proj"
    ],
    bias="none",
    use_gradient_checkpointing="unsloth",  # 30% more VRAM savings
    random_state=42,
)

# Training config
from trl import SFTTrainer
from transformers import TrainingArguments

trainer = SFTTrainer(
    model=model,
    tokenizer=tokenizer,
    train_dataset=dataset,
    dataset_text_field="text",
    max_seq_length=4096,
    args=TrainingArguments(
        per_device_train_batch_size=2,
        gradient_accumulation_steps=8,
        warmup_ratio=0.05,
        num_train_epochs=3,
        learning_rate=2e-4,
        bf16=True,
        logging_steps=10,
        optim="adamw_8bit",
        weight_decay=0.01,
        lr_scheduler_type="cosine",
        output_dir="bolthands-9b-checkpoints",
        save_strategy="steps",
        save_steps=500,
    ),
)

trainer.train()
```

**Export to GGUF for llama.cpp:**
```python
# Save LoRA adapter
model.save_pretrained("bolthands-9b-lora")

# Merge and export to GGUF Q4_K_M
model.save_pretrained_gguf(
    "bolthands-9b-Q4_K_M",
    tokenizer,
    quantization_method="q4_k_m"
)
```

**Alternative: LLaMA Factory** (if Unsloth has issues)

```yaml
# llama_factory config: bolthands_train.yaml
model_name_or_path: Qwen/Qwen3.5-9B
stage: sft
finetuning_type: lora
lora_rank: 64
lora_alpha: 128
lora_dropout: 0.05
lora_target: q_proj,k_proj,v_proj,o_proj,gate_proj,up_proj,down_proj
quantization_bit: 4
quantization_method: bitsandbytes
dataset: bolthands_combined
template: qwen
cutoff_len: 4096
per_device_train_batch_size: 2
gradient_accumulation_steps: 8
learning_rate: 2.0e-4
num_train_epochs: 3
lr_scheduler_type: cosine
warmup_ratio: 0.05
bf16: true
output_dir: bolthands-9b-output
```

---

## 9. Preventing Catastrophic Forgetting

### The Risk

Fine-tuning on 150K domain-specific examples risks degrading the model's existing capabilities:
- General conversation quality
- Coding ability (Python, JavaScript, etc.)
- Reasoning and math
- Following instructions accurately

### Mitigation Strategies

#### 9.1 Training Data Mixing

Include 15-20% general-purpose data alongside domain-specific data:

| Category | % of Training Data | Purpose |
|----------|--------------------|---------|
| Domain-specific tools | 70% | New capabilities |
| General function calling | 15% | Preserve tool-calling patterns |
| General conversation | 10% | Preserve conversational ability |
| Coding tasks | 5% | Preserve coding ability |

#### 9.2 Low Learning Rate with Cosine Schedule

- Start at 2e-4 (conservative for LoRA)
- Cosine decay to near-zero
- Short warmup (5%) to prevent early divergence

#### 9.3 LoRA Rank Selection

Rank 64 is a sweet spot:
- High enough to encode multi-domain knowledge
- Low enough that it's modifying only ~3.6% of parameters
- The base model's weights remain frozen — core capabilities are preserved
- LoRA acts as a "skill overlay" rather than replacing existing knowledge

#### 9.4 Evaluation Checkpoints

Evaluate at every 500 steps against:
1. **Tool-calling accuracy** — Does it generate valid tool calls?
2. **General chat quality** — Can it still have normal conversations?
3. **Code generation** — Can it still write Python/PowerShell?
4. **Instruction following** — Does it follow complex multi-step instructions?

Use a held-out eval set of ~1,000 examples (200 per domain + 200 general).

#### 9.5 Short Training (3 Epochs Max)

With 150K examples, 3 epochs provides sufficient exposure without overtraining. The model sees each example 3 times — enough to learn the patterns without memorizing them.

---

## 10. Synthetic Data Generation Plan

### Strategy: Use Claude (or GPT-4) to Generate Training Data

Since there are no existing datasets for Plex API management, *arr stack management, or Windows sysadmin tool calling, you need to generate synthetic training data.

### 10.1 Generation Pipeline

```
1. Define tool schemas (done in Section 6)
2. Generate diverse user requests per domain
3. Generate complete multi-turn conversations with tool calls
4. Validate JSON formatting
5. Mix with existing HuggingFace datasets
6. Format into Qwen ChatML
```

### 10.2 User Request Templates per Domain

#### Windows Management (25,000 examples needed)

Categories of requests:
- Service management: "restart the print spooler on the gaming PC"
- Update management: "check for Windows updates on all machines"
- Event logs: "show me any errors on the media server from the last hour"
- Registry: "disable auto-updates in the registry on DESKTOP-01"
- Scheduled tasks: "set up a daily backup task at 2am"
- File operations: "check how much space is left on D: drive"
- System health: "how's the gaming PC doing? CPU and memory usage?"
- User management: "create a guest account on the living room PC"
- Troubleshooting: "the print spooler keeps crashing, check the event logs and restart it"
- Multi-step: "check for updates, install them, and schedule a reboot for tonight"

#### Plex Management (15,000 examples needed)

Categories:
- Library scanning: "scan the movies folder, I just added some new files"
- Search: "find all Christopher Nolan movies in my library"
- Now playing: "who's watching what right now?"
- Collections: "create a 'Halloween Horror' collection with these movies..."
- Playlists: "make a Friday night playlist with action movies from the 90s"
- Maintenance: "optimize the Plex database and empty the trash"
- Recently added: "what's new in the library?"
- User activity: "has Sarah been watching anything this week?"
- Server health: "how's the Plex server performing? Any transcoding?"
- Updates: "is there a Plex update available?"

#### Sonarr (12,000 examples needed)

Categories:
- Add series: "add Shogun to Sonarr"
- Search: "search for missing episodes of Breaking Bad"
- Calendar: "what's airing this week?"
- Wanted: "show me all missing episodes"
- Queue: "what's downloading right now?"
- Quality: "change The Boys to 4K quality profile"
- Monitoring: "stop monitoring season 1 of Friends"
- Health: "is Sonarr healthy? Any issues?"

#### Radarr (10,000 examples needed)

Categories:
- Add movie: "add Oppenheimer to Radarr"
- Search: "search for The Batman"
- Queue: "what movies are downloading?"
- Missing: "show me monitored movies that haven't been downloaded"
- Health: "how's Radarr doing?"

#### Lidarr (8,000 examples needed)

Categories:
- Add artist: "add Taylor Swift to Lidarr"
- Albums: "show me all monitored albums for Radiohead"
- Search: "search for missing albums"
- Health: "is Lidarr working?"

#### Prowlarr (5,000 examples needed)

Categories:
- Indexer status: "are all my indexers working?"
- Test: "test the indexer connections"
- Search: "search all indexers for 'Dune'"
- History: "show me recent search activity"
- App status: "are Sonarr, Radarr, and Lidarr all connected?"

#### Cross-Domain (10,000 examples needed)

Multi-service workflows:
- "Add a movie in Radarr, and once it downloads, add it to a Plex collection"
- "Check what's airing this week in Sonarr and who's currently watching on Plex"
- "The gaming PC is acting slow — check its health, then look at the event logs"
- "Search Prowlarr for a show, then add it in Sonarr"
- "Is anything downloading across Sonarr and Radarr? And how's disk space looking on the Windows server?"

#### OpenClaw Agent Personality (15,000 examples needed)

- Tool selection reasoning: Given multiple available tools, choose the right one
- Personality consistency: Maintain character across long conversations
- Error handling: Gracefully handle tool failures
- Delegation: Know when to route to another agent via sessions_send
- Context retention: Reference earlier conversation turns appropriately

### 10.3 Generation Prompt Template (for Claude/GPT-4)

```
You are generating training data for "BoltHands 9B", an AI assistant that manages
home infrastructure. Generate a realistic multi-turn conversation where the user
asks about {DOMAIN} and the assistant uses the following tools:

Available tools:
{TOOL_SCHEMAS}

Requirements:
- The conversation should be 3-8 turns
- Include at least 1-3 tool calls
- Tool calls must use valid JSON with correct parameter names and types
- Include realistic tool responses
- The assistant should be helpful, concise, and proactive
- Use Hermes-style <tool_call> and <tool_response> tags
- Vary the complexity: some simple single-tool calls, some multi-step workflows
- Include occasional error scenarios where tools fail

User request category: {CATEGORY}
Difficulty: {easy|medium|hard}

Output format: JSON with "conversations" array containing objects with "from" and "value" keys.
```

### 10.4 Validation Pipeline

After generation, validate every example:

1. **JSON syntax** — All tool calls must be valid JSON
2. **Schema compliance** — Tool names and parameters match the defined schemas
3. **Conversation coherence** — Multi-turn flow makes sense
4. **Response quality** — Assistant responses are helpful and natural
5. **Deduplication** — Remove near-duplicate conversations

```python
import json

def validate_example(example):
    """Validate a single training example."""
    for msg in example["conversations"]:
        if msg["from"] == "assistant" and "<tool_call>" in msg["value"]:
            # Extract and validate tool call JSON
            tool_json = extract_between_tags(msg["value"], "<tool_call>", "</tool_call>")
            parsed = json.loads(tool_json)
            assert "name" in parsed, "Missing tool name"
            assert "arguments" in parsed, "Missing arguments"
            assert parsed["name"] in VALID_TOOL_NAMES, f"Unknown tool: {parsed['name']}"

        if msg["from"] == "tool":
            tool_json = extract_between_tags(msg["value"], "<tool_response>", "</tool_response>")
            parsed = json.loads(tool_json)
            assert "name" in parsed, "Missing tool name in response"
            assert "content" in parsed, "Missing content in response"

    return True
```

---

## 11. HuggingFace Dataset Inventory

### Tier 1: Primary Function-Calling Datasets (Use Directly)

| Dataset | Size | Format | Use For |
|---------|------|--------|---------|
| `glaiveai/glaive-function-calling-v2` | 113K rows | ChatML with `<functioncall>` | Base function calling training |
| `Salesforce/xlam-function-calling-60k` | 60K rows | Query + Tools + Answers JSON | Diverse API tool calling |
| `NousResearch/hermes-function-calling-v1` | 11.6K rows | Hermes ChatML with `<tool_call>` | Hermes-format tool calls (closest to Qwen3.5 native) |
| `thibaud-perrin/hibo-function-calling-v1` | 323K rows | System + Chat messages | Large-scale mixed function calling + conversation |
| `argilla/apigen-function-calling` | 109K rows | Query + Tools + Answers | High-quality API calling with 21 categories |
| `nvidia/Nemotron-RL-Agentic-Function-Calling-Pivot-v1` | 9.6K rows | Trajectory-based | Multi-step agentic tool use patterns |

**Recommended selection from these:**
- `NousResearch/hermes-function-calling-v1` — 11.6K (use ALL, format matches Qwen3.5)
- `Salesforce/xlam-function-calling-60k` — 20K (sample, convert to ChatML)
- `glaiveai/glaive-function-calling-v2` — 10K (sample, diverse function categories)
- `nvidia/Nemotron-RL-Agentic-Function-Calling-Pivot-v1` — 5K (sample, agentic patterns)

### Tier 2: Supplementary Datasets

| Dataset | Size | Use For |
|---------|------|---------|
| `hypervariance/function-calling-sharegpt` | 86.9K rows | ShareGPT-format function calling |
| `Jofthomas/hermes-function-calling-thinking-V1` | 3.57K rows | Function calling with reasoning/thinking |
| `driaforall/pythonic-function-calling` | 81.8K rows | Python-style tool calls |
| `AymanTarig/function-calling-v0.2-with-r1-cot` | 58K rows | Chain-of-thought function calling |
| `smolagents/glaive-function-calling-with-reasoning` | — | Function calling with reasoning chains |

### Tier 3: Domain-Specific Datasets

| Dataset | Size | Use For |
|---------|------|---------|
| `SaeedRahmani/codeparrot_github_code_powershell` | 140K rows | PowerShell code patterns |
| `adamo1139/powershell_thestack` | 528K rows | PowerShell code from The Stack |
| `rr4433/powershell_embedding_model_training_data` | 400K rows | PowerShell documentation embeddings |
| `RazinAleks/SO-Python_QA-System_Administration_and_DevOps_class` | 10.8K rows | SysAdmin Q&A from StackOverflow |
| `aldsouza/healthcare-api-tool-calling` | 285 rows | API tool calling patterns (general format reference) |
| `gardner/SlimOrca-Dedup-trl-conversational-chatml` | 363K rows | General ChatML conversations |

### Tier 4: For Catastrophic Forgetting Prevention

| Dataset | Size | Use For |
|---------|------|---------|
| `glaiveai/glaive-function-calling` (v1) | 52.9K rows | General conversation balance |
| General coding datasets (The Stack subset) | Sample 5K | Preserve coding ability |
| General instruction datasets (SlimOrca, etc.) | Sample 5K | Preserve instruction following |

### Data Processing Pipeline

```python
from datasets import load_dataset, concatenate_datasets

# 1. Load primary datasets
hermes_fc = load_dataset("NousResearch/hermes-function-calling-v1", split="train")
xlam_fc = load_dataset("Salesforce/xlam-function-calling-60k", split="train").shuffle().select(range(20000))
glaive_fc = load_dataset("glaiveai/glaive-function-calling-v2", split="train").shuffle().select(range(10000))
nemotron_fc = load_dataset("nvidia/Nemotron-RL-Agentic-Function-Calling-Pivot-v1", split="train").shuffle().select(range(5000))

# 2. Load PowerShell data
ps_code = load_dataset("SaeedRahmani/codeparrot_github_code_powershell", split="train").shuffle().select(range(5000))

# 3. Convert all to unified Qwen ChatML format
# (each dataset needs a custom conversion function)

# 4. Load synthetic domain-specific data
synthetic_windows = load_dataset("json", data_files="synthetic/windows_*.jsonl")
synthetic_plex = load_dataset("json", data_files="synthetic/plex_*.jsonl")
synthetic_sonarr = load_dataset("json", data_files="synthetic/sonarr_*.jsonl")
synthetic_radarr = load_dataset("json", data_files="synthetic/radarr_*.jsonl")
synthetic_lidarr = load_dataset("json", data_files="synthetic/lidarr_*.jsonl")
synthetic_prowlarr = load_dataset("json", data_files="synthetic/prowlarr_*.jsonl")
synthetic_cross = load_dataset("json", data_files="synthetic/cross_domain_*.jsonl")
synthetic_openclaw = load_dataset("json", data_files="synthetic/openclaw_*.jsonl")

# 5. Mix and shuffle
combined = concatenate_datasets([
    hermes_fc, xlam_converted, glaive_converted, nemotron_converted,
    synthetic_windows, synthetic_plex, synthetic_sonarr, synthetic_radarr,
    synthetic_lidarr, synthetic_prowlarr, synthetic_cross, synthetic_openclaw,
    general_conversation_sample, coding_sample
]).shuffle(seed=42)

# 6. Save
combined.save_to_disk("bolthands-training-data")
```

---

## 12. Training Pipeline

### Complete Step-by-Step Plan

#### Phase 1: Data Preparation (1-2 days)

1. **Download HuggingFace datasets** from Tier 1 and Tier 3
2. **Write format converters** — Convert each dataset to Qwen ChatML with Hermes-style tool calls
3. **Generate synthetic data** — Use Claude API (or local model) to generate domain-specific conversations
   - Estimate: 100K synthetic examples * ~$0.01 each = ~$1,000 via Claude API
   - Alternative: Use local Qwen 3.5 27B to generate (free but slower, ~2 days)
4. **Validate all data** — Run validation pipeline, fix JSON errors
5. **Mix and balance** — Create final training dataset with proper domain ratios
6. **Create eval set** — Hold out 1,000 examples across all domains

#### Phase 2: Environment Setup (1 hour)

```bash
# In distrobox "ai"
pip install unsloth
pip install --no-deps trl peft accelerate bitsandbytes
pip install datasets wandb

# Or for LLaMA Factory
git clone https://github.com/hiyouga/LLaMA-Factory.git ~/ai-drive/ai-suite/LLaMA-Factory
cd ~/ai-drive/ai-suite/LLaMA-Factory
pip install -e ".[torch,metrics]"
```

#### Phase 3: Training (3-4 hours)

1. **Load base model** — Qwen 3.5 9B with 4-bit quantization
2. **Apply LoRA** — Rank 64, all linear layers
3. **Train** — 3 epochs, ~28K steps
4. **Monitor** — Watch loss curve on wandb, check for divergence

#### Phase 4: Evaluation (1-2 hours)

Test the model against eval set:
- Tool call accuracy (correct tool name + valid arguments)
- Conversation quality (human-rated or automated)
- Cross-domain capability (multi-service workflows)
- Regression testing (general chat, coding)

#### Phase 5: Export and Deploy (30 minutes)

1. **Merge LoRA** into base model
2. **Export to GGUF** — Q4_K_M quantization (~5.5GB)
3. **Copy to Carl** (Raspberry Pi 4B)
4. **Run via llama.cpp** — Test on Carl with real OpenClaw setup
5. **Update openclaw.json** — Point model to BoltHands GGUF

#### Phase 6: Iterate

- Collect real usage data from Carl
- Identify weak spots (wrong tool selection, bad PowerShell, etc.)
- Generate targeted training data for weak areas
- Retrain with expanded dataset

---

## Appendix A: API Documentation References

| Service | API Docs URL |
|---------|-------------|
| **OpenClaw** | https://github.com/openclaw/openclaw |
| **Plex API** | https://python-plexapi.readthedocs.io/en/latest/ |
| **Sonarr API v3** | https://sonarr.tv/docs/api/ (OpenAPI: `github.com/Sonarr/Sonarr/.../openapi.json`) |
| **Radarr API v3** | https://radarr.video/docs/api/ (OpenAPI: `github.com/Radarr/Radarr/.../openapi.json`) |
| **Lidarr API v1** | https://lidarr.audio/docs/api/ (OpenAPI: `github.com/Lidarr/Lidarr/.../openapi.json`) |
| **Prowlarr API v1** | https://prowlarr.com/docs/api/ (OpenAPI: `github.com/Prowlarr/Prowlarr/.../openapi.json`) |
| **PowerShell Remoting** | https://learn.microsoft.com/en-us/powershell/scripting/learn/remoting/ |
| **Qwen 3.5 Function Calling** | https://qwen.readthedocs.io/en/latest/framework/function_call.html |
| **Unsloth Fine-tuning** | https://unsloth.ai/ |
| **LLaMA Factory** | https://github.com/hiyouga/LLaMA-Factory |

## Appendix B: Key Numbers

| Metric | Value |
|--------|-------|
| Base model parameters | 9B |
| LoRA trainable parameters | ~330M (3.6%) |
| Training examples (target) | ~150,000 |
| Synthetic examples needed | ~100,000 |
| Existing HF dataset examples | ~50,000 |
| Training epochs | 3 |
| Training time estimate | 3-4 hours on RTX 3090 |
| Final GGUF size (Q4_K_M) | ~5.5 GB |
| Tools defined | 47 custom + OpenClaw built-ins |
| Pi 4B RAM usage at inference | ~6-7 GB (with 8GB available) |
| Context window (inference) | 4096-8192 tokens (Pi memory limited) |

## Appendix C: Risk Assessment

| Risk | Severity | Mitigation |
|------|----------|------------|
| Catastrophic forgetting | High | 20% general data mixing, LoRA rank 64, eval checkpoints |
| Poor tool selection | Medium | Cross-domain training data, tool description quality |
| Invalid JSON in tool calls | Medium | JSON validation in training data, structured output training |
| Pi 4B too slow at inference | Medium | Q4_K_M quantization, limit context to 4096, use speculative decoding if supported |
| Synthetic data quality | Medium | Claude API for generation, validation pipeline, human spot-checking |
| Training data too small | Low | 150K is generous for LoRA; can always add more |
| Model refuses tool calls | Low | Abliterated base + no guardrails in training data |
