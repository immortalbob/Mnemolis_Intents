"""Mnemolis Intents — LLM tool integration for Home Assistant."""
from __future__ import annotations

import logging
import math
import aiohttp
import voluptuous as vol
from datetime import datetime
from fractions import Fraction

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import llm
from homeassistant.util.json import JsonObjectType

from .const import DOMAIN, CONF_MNEMOLIS_URL, DEFAULT_MNEMOLIS_URL, API_NAME, UNIT_CONVERSIONS

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Mnemolis Intents from a config entry."""
    url = entry.options.get(
        CONF_MNEMOLIS_URL,
        entry.data.get(CONF_MNEMOLIS_URL, DEFAULT_MNEMOLIS_URL),
    )

    unreg = llm.async_register_api(
        hass,
        MnemolistAPI(
            hass=hass,
            id=f"{DOMAIN}-{entry.entry_id}",
            name=API_NAME,
            mnemolis_url=url,
        ),
    )
    entry.async_on_unload(unreg)
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))
    return True


async def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    return True


class MnemolistAPI(llm.API):
    """Mnemolis LLM API."""

    def __init__(self, hass, id, name, mnemolis_url):
        super().__init__(hass=hass, id=id, name=name)
        self.mnemolis_url = mnemolis_url

    async def async_get_api_instance(self, llm_context: llm.LLMContext) -> llm.APIInstance:
        return llm.APIInstance(
            api=self,
            api_prompt=(
                "You have access to Mnemolis tools for knowledge lookup, calculations, "
                "unit conversions, and calendar queries. "
                "Use `mnemolis` for any question requiring external information — it routes "
                "automatically to offline knowledge, weather forecast, news, web search, or "
                "service status. Use source='forecast' for weather, source='news' for recent "
                "articles, source='kiwix' for encyclopedic or technical knowledge, "
                "source='web' for current events, source='uptime' to check if services or "
                "devices are up or down. "
                "Use `calculator` for math. Use `unit_converter` for unit conversions. "
                "Use `calendar_day` to find what day of the week a date falls on."
            ),
            llm_context=llm_context,
            tools=[
                MnemolisTool(self.mnemolis_url),
                CalculatorTool(),
                UnitConverterTool(),
                CalendarDayTool(),
            ],
        )


# ---------------------------------------------------------------------------
# Mnemolis
# ---------------------------------------------------------------------------

class MnemolisTool(llm.Tool):
    name = "mnemolis"
    description = (
        "Search for information using Mnemolis. Automatically selects the best source "
        "based on the query — offline knowledge base, weather forecast, news feed, web search, "
        "or service status monitoring. "
        "Use source='forecast' for weather questions, source='news' for recent articles, "
        "source='kiwix' for encyclopedic or technical knowledge, source='web' for current events, "
        "source='uptime' to check whether services or devices are up or down. "
        "Leave source as 'auto' when unsure."
    )
    parameters = vol.Schema({
        vol.Required("query"): str,
        vol.Optional("source", default="auto"): vol.In(
            ["auto", "kiwix", "forecast", "news", "web", "uptime"]
        ),
    })

    def __init__(self, mnemolis_url: str) -> None:
        self.mnemolis_url = mnemolis_url

    async def async_call(self, hass, tool_input, llm_context) -> JsonObjectType:
        query = tool_input.tool_args["query"]
        source = tool_input.tool_args.get("source", "auto")
        _LOGGER.debug("Mnemolis tool called: query='%s' source='%s'", query, source)
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.mnemolis_url}/search",
                    json={"query": query, "source": source},
                    timeout=aiohttp.ClientTimeout(total=15),
                ) as resp:
                    if resp.status != 200:
                        raise HomeAssistantError(f"Mnemolis returned HTTP {resp.status}")
                    data = await resp.json()
                    return {
                        "result": data.get("result", "No result returned."),
                        "source_used": data.get("source_used", source),
                    }
        except aiohttp.ClientConnectorError as err:
            raise HomeAssistantError(f"Cannot connect to Mnemolis: {err}") from err
        except aiohttp.ClientError as err:
            raise HomeAssistantError(f"Mnemolis request failed: {err}") from err


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
        _LOGGER.debug("Calculator tool called: expression='%s'", expr)
        try:
            safe_globals = {
                "__builtins__": {},
                "abs": abs, "round": round, "min": min, "max": max,
                "sum": sum, "pow": pow,
                "sqrt": math.sqrt, "ceil": math.ceil, "floor": math.floor,
                "sin": math.sin, "cos": math.cos, "tan": math.tan,
                "log": math.log, "log10": math.log10, "pi": math.pi, "e": math.e,
            }

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

class UnitConverterTool(llm.Tool):
    name = "unit_converter"
    description = (
        "Convert between units of measurement. "
        "Supports kitchen volume (cup, tablespoon, teaspoon, ml, pint, liter), "
        "weight (kg, lb, oz, g), length (km, mile, m, ft, inch, cm), "
        "data sizes (kb, mb, gb, tb), and speed (mph, kph, mps). "
        "For temperature use from_unit='c' to_unit='f' or from_unit='f' to_unit='c'. "
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
        _LOGGER.debug("Unit converter called: amount='%s' from='%s' to='%s'", amount_str, from_unit, to_unit)

        amount = self._parse_amount(amount_str)

        # Temperature — handle c/f conversion explicitly
        if from_unit == "c" and to_unit == "f":
            result = (amount * 9/5) + 32
            return {"amount": amount, "from": "°C", "to": "°F", "result": round(result, 2)}
        if from_unit == "f" and to_unit == "c":
            result = (amount - 32) * 5/9
            return {"amount": amount, "from": "°F", "to": "°C", "result": round(result, 2)}

        key = (from_unit, to_unit)
        if key not in UNIT_CONVERSIONS:
            raise HomeAssistantError(
                f"Don't know how to convert '{from_unit}' to '{to_unit}'. "
                f"Supported units: {', '.join(sorted(set(k[0] for k in UNIT_CONVERSIONS)))}"
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
        _LOGGER.debug("Calendar tool called: month=%d day=%d year=%d", month, day, year)

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
