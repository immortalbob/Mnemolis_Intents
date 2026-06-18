DOMAIN = "mnemolis_intents"
CONF_MNEMOLIS_URL = "mnemolis_url"
DEFAULT_MNEMOLIS_URL = "http://mnemolis:8000"
API_NAME = "Mnemolis"

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
    ("mph", "mps"): 0.44704, ("mps", "mph"): 1/0.44704,
    ("kph", "mps"): 0.27778, ("mps", "kph"): 1/0.27778,
}
