# MiniSearch Intents

A Home Assistant custom integration that exposes [MiniSearch](https://github.com/immortalbob/MiniSearch) and a set of local utility tools as a native LLM Tool API.

Once enabled, any Home Assistant conversation agent (Ollama, OpenAI, Anthropic, etc.) can search your local knowledge stack, perform calculations, convert units, and query dates through a single tool interface.

MiniSearch Intents appears alongside the built-in Assist API and can be enabled per conversation agent from the Home Assistant UI.

## What MiniSearch provides

- **Offline knowledge** — Wikipedia, Stack Exchange, iFixit, FreeCodeCamp, DevDocs via Kiwix
- **Weather forecast** — 3-day forecast via Open-Meteo (no API key required)
- **News** — Recent articles from your FreshRSS RSS feeds
- **Web search** — Live search via your local SearXNG instance
- **Service status** — Monitor status for all services via Uptime Kuma

## Architecture

```
ESP32 Voice Assistant
          │
          ▼
   Home Assistant
          │
          ▼
 MiniSearch Intents
          │
          ▼
     MiniSearch
          │
          ├─ Kiwix
          ├─ FreshRSS
          ├─ Open-Meteo
          ├─ SearXNG
          └─ Uptime Kuma
```

## Available Tools

| Tool | Description | Status |
|------|-------------|--------|
| `minisearch` | Routes queries to Kiwix, Open-Meteo, FreshRSS, SearXNG, or Uptime Kuma | ✅ Working |
| `calculator` | Evaluates math expressions, sqrt, trig, average | ✅ Working |
| `unit_converter` | Converts between kitchen, weight, length, data, speed, and temperature units | ✅ Working |
| `calendar_day` | Returns day of week and relative info for a given date | ✅ Working |

## Requirements

- [MiniSearch](https://github.com/immortalbob/MiniSearch) v2.3.0 or later running and reachable from Home Assistant
- Home Assistant 2024.6.0 or later
- An LLM conversation agent (Ollama, OpenAI, etc.) configured in Home Assistant

## Installation

### Via HACS (recommended)

1. Add this repository as a custom repository in HACS (type: Integration)
2. Install **MiniSearch Intents**
3. Restart Home Assistant

### Manual

1. Copy `custom_components/minisearch_intents` to your HA `custom_components` directory
2. Restart Home Assistant

## Setup

1. Go to **Settings → Devices & Services → Add Integration**
2. Search for **MiniSearch Intents**
3. Enter your MiniSearch URL (e.g. `http://192.168.3.5:8888`)
4. Click Submit — HA will verify the connection before saving

## Enabling for your conversation agent

1. Go to **Settings → Devices & Services**
2. Find your conversation agent (e.g. Ollama)
3. Click **Configure**
4. Under **Control Home Assistant**, enable **MiniSearch**
5. Save

## Calculator

Supports standard arithmetic, exponents, square roots, trig functions, and averages.

Examples:
- `what is the square root of 1764`
- `what is average of 10, 20, 30`
- `what is sin of 45`

## Unit Converter

Supported unit pairs:

- **Kitchen volume:** cup, tablespoon, teaspoon, ml, pint, liter
- **Weight:** kg, lb, oz, g
- **Length:** km, mile, m, ft, inch, cm
- **Data:** kb, mb, gb, tb
- **Speed:** mph, kph, mps (meters per second)
- **Temperature:** use `from_unit='c'` `to_unit='f'` or `from_unit='f'` `to_unit='c'`

Amounts can be fractions: `1/2`, `1 1/2`, `0.75`

## Calendar Day

Ask what day of the week a date falls on, or how many days until an event.

Examples:
- `what day is July 4th`
- `how many days until Christmas`
- `what day was January 1st 2000`

## Compatibility

| MiniSearch Intents | MiniSearch |
|-------------------|------------|
| v1.2.0 | v2.3.0 or later |
| v1.1.0 | v2.0.0 or later |

## Roadmap

- **Timer** — TTS announcement on the originating satellite when a timer expires. Pending resolution of a conflict with Home Assistant's built-in timer intent handling.
- **Compound unit conversion** — support for inputs like "5 ft 10 in" or "2 lb 4 oz". Pending — smaller LLMs (8B) tend to pre-convert before calling the tool, bypassing this feature.

## Part of the MiniNet stack

- [MiniSearch](https://github.com/immortalbob/MiniSearch) — the search backend
