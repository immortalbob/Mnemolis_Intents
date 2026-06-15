"""MiniSearch Intents — LLM tool integration for Home Assistant."""
from __future__ import annotations

import logging
import math
import asyncio
import aiohttp
import voluptuous as vol
from datetime import datetime, timedelta
from fractions import Fraction

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import llm
from homeassistant.util.json import JsonObjectType

from .const import DOMAIN, CONF_MINISEARCH_URL, DEFAULT_MINISEARCH_URL, API_NAME

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up MiniSearch Intents from a config entry."""
    url = entry.options.get(
        CONF_MINISEARCH_URL,
        entry.data.get(CONF_MINISEARCH_URL, DEFAULT_MINISEARCH_URL),
    )

    unreg = llm.async_register_api(
        hass,
        MiniSearchAPI(
            hass=hass,
            id=f"{DOMAIN}-{entry.entry_id}",
            name=API_NAME,
            minisearch_url=url,
        ),
    )
    entry.async_on_unload(unreg)
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))
    return True


async def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    return True


class MiniSearchAPI(llm.API):
    """MiniSearch LLM API."""

    def __init__(self, hass, id, name, minisearch_url):
        super().__init__(hass=hass, id=id, name=name)
        self.minisearch_url = minisearch_url

    async def async_get_api_instance(self, llm_context: llm.LLMContext) -> llm.APIInstance:
        return llm.APIInstance(
            api=self,
            api_prompt=(
                "You have access to MiniSearch tools for knowledge lookup, calculations, "
                "unit conversions, calendar queries, and timers. "
                "Use `minisearch` for any question requiring external information — it routes "
                "automatically to offline knowledge, weather forecast, news, or web search. "
                "Use `calculator` for math. Use `unit_converter` for unit conversions. "
                "Use `calendar_day` to find what day of the week a date falls on. "
                "Use `set_timer` to set a timer that will announce via TTS when done."
            ),
            llm_context=llm_context,
            tools=[
                MiniSearchTool(self.minisearch_url),
                CalculatorTool(),
                UnitConverterTool(),
                CalendarDayTool(),
                TimerTool(),
            ],
        )


# ---------------------------------------------------------------------------
# MiniSearch
# ---------------------------------------------------------------------------

class MiniSearchTool(llm.Tool):
    name = "minisearch"
    description = (
        "Search for information using MiniSearch. Automatically selects the best source "
        "based on the query — offline knowledge base, weather forecast, news feed, or web search. "
        "Use source='forecast' for weather questions, source='news' for recent articles, "
        "source='kiwix' for encyclopedic or technical knowledge, source='web' for current events. "
        "Leave source as 'auto' when unsure."
    )
    parameters = vol.Schema({
        vol.Required("query"): str,
        vol.Optional("source", default="auto"): vol.In(
            ["auto", "kiwix", "forecast", "news", "web"]
        ),
    })

    def __init__(self, minisearch_url: str) -> None:
        self.minisearch_url = minisearch_url

    async def async_call(self, hass, tool_input, llm_context) -> JsonObjectType:
        query = tool_input.tool_args["query"]
        source = tool_input.tool_args.get("source", "auto")
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.minisearch_url}/search",
                    json={"query": query, "source": source},
                    timeout=aiohttp.ClientTimeout(total=15),
                ) as resp:
                    if resp.status != 200:
                        raise HomeAssistantError(f"MiniSearch returned HTTP {resp.status}")
                    data = await resp.json()
                    return {
                        "result": data.get("result", "No result returned."),
                        "source_used": data.get("source_used", source),
                    }
        except aiohttp.ClientConnectorError as err:
            raise HomeAssistantError(f"Cannot connect to MiniSearch: {err}") from err
        except aiohttp.ClientError as err:
            raise HomeAssistantError(f"MiniSearch request failed: {err}") from err


# ---------------------------------------------------------------------------
# Calculator
# ---------------------------------------------------------------------------

class CalculatorTool(llm.Tool):
    name = "calculator"
    description = (
        "Evaluate mathematical expressions and return the result. "
        "Supports standard arithmetic, exponents, square roots, trig functions, "
        "min, max, and average of a list of numbers. "
        "Examples: '2 + 2', 'sqrt(144)', 'sin(45)', 'average(10, 20, 30)'."
    )
    parameters = vol.Schema({
        vol.Required("expression"): str,
    })

    async def async_call(self, hass, tool_input, llm_context) -> JsonObjectType:
        expr = tool_input.tool_args["expression"].strip()
        try:
            # Safe math context
            safe_globals = {
                "__builtins__": {},
                "abs": abs, "round": round, "min": min, "max": max,
                "sum": sum, "pow": pow,
                "sqrt": math.sqrt, "ceil": math.ceil, "floor": math.floor,
                "sin": math.sin, "cos": math.cos, "tan": math.tan,
                "log": math.log, "log10": math.log10, "pi": math.pi, "e": math.e,
            }

            # Handle average(a, b, c, ...)
            if expr.lower().startswith("average("):
                inner = expr[8:].rstrip(")")
                nums = [float(x.strip()) for x in inner.split(",")]
                result = sum(nums) / len(nums)
            else:
                result = eval(expr, safe_globals)

            return {"expression": expr, "result": result}
        except Exception as err:
            raise HomeAssistantError(f"Could not evaluate '{expr}': {err}") from err


# ---------------------------------------------------------------------------
# Unit Converter
# ---------------------------------------------------------------------------

UNIT_CONVERSIONS = {
    # Volume (kitchen)
    ("cup", "ml"): 236.588, ("ml", "cup"): 1/236.588,
    ("cup", "tablespoon"): 16, ("tablespoon", "cup"): 1/16,
    ("cup", "teaspoon"): 48, ("teaspoon", "cup"): 1/48,
    ("tablespoon", "teaspoon"): 3, ("teaspoon", "tablespoon"): 1/3,
    ("tablespoon", "ml"): 14.787, ("ml", "tablespoon"): 1/14.787,
    ("teaspoon", "ml"): 4.929, ("ml", "teaspoon"): 1/4.929,
    ("cup", "liter"): 0.236588, ("liter", "cup"): 1/0.236588,
    ("pint", "cup"): 2, ("cup", "pint"): 0.5,
    ("pint", "ml"): 473.176, ("ml", "pint"): 1/473.176,
    # Weight
    ("kg", "lb"): 2.20462, ("lb", "kg"): 1/2.20462,
    ("kg", "oz"): 35.274, ("oz", "kg"): 1/35.274,
    ("lb", "oz"): 16, ("oz", "lb"): 1/16,
    ("g", "oz"): 0.035274, ("oz", "g"): 1/0.035274,
    ("g", "lb"): 0.00220462, ("lb", "g"): 1/0.00220462,
    ("g", "kg"): 0.001, ("kg", "g"): 1000,
    # Length
    ("km", "mile"): 0.621371, ("mile", "km"): 1/0.621371,
    ("m", "ft"): 3.28084, ("ft", "m"): 1/3.28084,
    ("m", "inch"): 39.3701, ("inch", "m"): 1/39.3701,
    ("cm", "inch"): 0.393701, ("inch", "cm"): 1/0.393701,
    ("ft", "inch"): 12, ("inch", "ft"): 1/12,
    ("mile", "ft"): 5280, ("ft", "mile"): 1/5280,
    # Data
    ("gb", "mb"): 1024, ("mb", "gb"): 1/1024,
    ("tb", "gb"): 1024, ("gb", "tb"): 1/1024,
    ("mb", "kb"): 1024, ("kb", "mb"): 1/1024,
    # Speed
    ("mph", "kph"): 1.60934, ("kph", "mph"): 1/1.60934,
    ("mph", "ms"): 0.44704, ("ms", "mph"): 1/0.44704,
}


class UnitConverterTool(llm.Tool):
    name = "unit_converter"
    description = (
        "Convert between units of measurement. "
        "Supports kitchen volume (cup, tablespoon, teaspoon, ml, pint, liter), "
        "weight (kg, lb, oz, g), length (km, mile, m, ft, inch, cm), "
        "data sizes (kb, mb, gb, tb), and speed (mph, kph). "
        "For temperature, use 'celsius_to_fahrenheit' or 'fahrenheit_to_celsius' as the from_unit. "
        "Amounts can be fractions like '1/2' or '1 1/2'."
    )
    parameters = vol.Schema({
        vol.Required("amount"): str,
        vol.Required("from_unit"): str,
        vol.Required("to_unit"): str,
    })

    def _parse_amount(self, amount_str: str) -> float:
        amount_str = amount_str.strip()
        try:
            # Handle mixed fractions like "1 1/2"
            parts = amount_str.split()
            if len(parts) == 2:
                return float(parts[0]) + float(Fraction(parts[1]))
            return float(Fraction(amount_str))
        except Exception:
            raise HomeAssistantError(f"Cannot parse amount '{amount_str}'")

    async def async_call(self, hass, tool_input, llm_context) -> JsonObjectType:
        amount_str = tool_input.tool_args["amount"]
        from_unit = tool_input.tool_args["from_unit"].lower().strip()
        to_unit = tool_input.tool_args["to_unit"].lower().strip()

        amount = self._parse_amount(amount_str)

        # Temperature special cases
        if from_unit == "celsius_to_fahrenheit" or (from_unit == "c" and to_unit == "f"):
            result = (amount * 9/5) + 32
            return {"amount": amount, "from": "°C", "to": "°F", "result": round(result, 2)}
        if from_unit == "fahrenheit_to_celsius" or (from_unit == "f" and to_unit == "c"):
            result = (amount - 32) * 5/9
            return {"amount": amount, "from": "°F", "to": "°C", "result": round(result, 2)}

        key = (from_unit, to_unit)
        if key not in UNIT_CONVERSIONS:
            raise HomeAssistantError(
                f"Don't know how to convert '{from_unit}' to '{to_unit}'. "
                f"Supported: {', '.join(set(k[0] for k in UNIT_CONVERSIONS))}"
            )

        result = amount * UNIT_CONVERSIONS[key]
        return {
            "amount": amount,
            "from": from_unit,
            "to": to_unit,
            "result": round(result, 4),
        }


# ---------------------------------------------------------------------------
# Calendar Day
# ---------------------------------------------------------------------------

class CalendarDayTool(llm.Tool):
    name = "calendar_day"
    description = (
        "Find what day of the week a given date falls on, or calculate dates relative to today. "
        "Provide a date as month and day (and optionally year). "
        "Also useful for 'how many days until X' or 'what date is 3 weeks from now'."
    )
    parameters = vol.Schema({
        vol.Required("month"): vol.All(int, vol.Range(min=1, max=12)),
        vol.Required("day"): vol.All(int, vol.Range(min=1, max=31)),
        vol.Optional("year"): vol.All(int, vol.Range(min=1900, max=2100)),
    })

    async def async_call(self, hass, tool_input, llm_context) -> JsonObjectType:
        month = tool_input.tool_args["month"]
        day = tool_input.tool_args["day"]
        year = tool_input.tool_args.get("year") or datetime.now().year

        try:
            target = datetime(year, month, day)
        except ValueError as err:
            raise HomeAssistantError(f"Invalid date: {err}") from err

        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        delta = (target - today).days

        if delta == 0:
            relative = "today"
        elif delta == 1:
            relative = "tomorrow"
        elif delta == -1:
            relative = "yesterday"
        elif delta > 0:
            relative = f"in {delta} days"
        else:
            relative = f"{abs(delta)} days ago"

        return {
            "date": target.strftime("%B %d, %Y"),
            "day_of_week": target.strftime("%A"),
            "relative": relative,
            "days_from_today": delta,
        }


# ---------------------------------------------------------------------------
# Timer
# ---------------------------------------------------------------------------

class TimerTool(llm.Tool):
    name = "set_timer"
    description = (
        "Set a timer that will announce via text-to-speech on the satellite or device "
        "that the user is speaking from when the timer expires. "
        "Specify duration in seconds, minutes, or hours. "
        "Examples: 'set a 10 minute timer', 'remind me in 30 seconds', '1 hour timer'."
    )
    parameters = vol.Schema({
        vol.Required("duration_seconds"): vol.All(int, vol.Range(min=1, max=86400)),
        vol.Optional("label", default="Timer"): str,
    })

    async def async_call(self, hass, tool_input, llm_context) -> JsonObjectType:
        duration = tool_input.tool_args["duration_seconds"]
        label = tool_input.tool_args.get("label", "Timer")
        device_id = llm_context.device_id

        # Format duration for speech
        if duration >= 3600:
            h = duration // 3600
            m = (duration % 3600) // 60
            duration_str = f"{h} hour{'s' if h != 1 else ''}"
            if m:
                duration_str += f" {m} minute{'s' if m != 1 else ''}"
        elif duration >= 60:
            m = duration // 60
            s = duration % 60
            duration_str = f"{m} minute{'s' if m != 1 else ''}"
            if s:
                duration_str += f" {s} second{'s' if s != 1 else ''}"
        else:
            duration_str = f"{duration} second{'s' if duration != 1 else ''}"

        announcement = f"{label} is done. Your {duration_str} timer has expired."

        async def _fire_timer():
            await asyncio.sleep(duration)
            try:
                if device_id:
                    # Get media player entities associated with the device
                    entity_registry = hass.helpers.entity_registry.async_get(hass)
                    entities = [
                        e.entity_id
                        for e in entity_registry.entities.values()
                        if e.device_id == device_id
                        and e.entity_id.startswith("media_player.")
                    ]
                    if entities:
                        await hass.services.async_call(
                            "tts", "speak",
                            {
                                "media_player_entity_id": entities[0],
                                "message": announcement,
                                "cache": False,
                            },
                            blocking=False,
                        )
                        return

                # Fallback — notify persistent notification
                await hass.services.async_call(
                    "persistent_notification", "create",
                    {
                        "title": label,
                        "message": announcement,
                        "notification_id": f"timer_{label.lower().replace(' ', '_')}",
                    },
                    blocking=False,
                )
            except Exception as err:
                _LOGGER.error("Timer TTS failed: %s", err)

        hass.async_create_task(_fire_timer())

        return {
            "status": "timer_set",
            "label": label,
            "duration_seconds": duration,
            "duration_friendly": duration_str,
            "message": f"{label} set for {duration_str}.",
        }
