# Mnemolis Intents

A Home Assistant custom integration that exposes [MiniSearch](https://github.com/immortalbob/minisearch) as an LLM tool API, making it available to any LLM-backed conversation agent (Ollama, OpenAI, etc.) directly from the HA UI.

Once installed, Mnemolis appears as a selectable API in your conversation agent options alongside the built-in Assist API. Your LLM can then search across your entire local knowledge stack with a single tool call.

## What Mnemolis provides

- **Offline knowledge** — Wikipedia, Stack Exchange, iFixit, FreeCodeCamp, DevDocs via Kiwix
- **Weather forecast** — 3-day forecast via Open-Meteo (no API key required)
- **News** — Recent articles from your FreshRSS RSS feeds
- **Web search** — Live search via your local SearXNG instance

## Requirements

- [MiniSearch](https://github.com/immortalbob/minisearch) running and reachable from Home Assistant
- Home Assistant 2024.6.0 or later
- An LLM conversation agent (Ollama, OpenAI, etc.) configured in Home Assistant

## Installation

### Via HACS (recommended)

1. Add this repository as a custom repository in HACS (type: Integration)
2. Install **Mnemolis Intents**
3. Restart Home Assistant

### Manual

1. Copy `custom_components/mnemolis_intents` to your HA `custom_components` directory
2. Restart Home Assistant

## Setup

1. Go to **Settings → Devices & Services → Add Integration**
2. Search for **Mnemolis Intents**
3. Enter your Mnemolis URL (e.g. `http://192.168.3.5:8888`)
4. Click Submit — HA will verify the connection before saving

## Enabling for your conversation agent

1. Go to **Settings → Devices & Services**
2. Find your conversation agent (e.g. Ollama)
3. Click **Configure**
4. Under **Control Home Assistant**, enable **Mnemolis**
5. Save

Your LLM will now have access to the `mnemolis` tool and will use it automatically when answering questions that require looking things up.

## Part of the MiniNet stack

This integration is part of the MiniNet homelab ecosystem:

- [MiniSearch](https://github.com/immortalbob/minisearch) — the search backend
- [openwebui-tools](https://github.com/immortalbob/openwebui-tools) — Open WebUI tool versions of the same sources
