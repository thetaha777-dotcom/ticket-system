import re
import secrets
from datetime import datetime
from zoneinfo import ZoneInfo

from app.core.config import settings

_CODE_ALPHABET = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"

_TRANSLIT = {
    "а": "a", "б": "b", "в": "v", "г": "g", "д": "d", "е": "e", "ё": "e", "ж": "zh", "з": "z", "и": "i",
    "й": "y", "к": "k", "л": "l", "м": "m", "н": "n", "о": "o", "п": "p", "р": "r", "с": "s", "т": "t",
    "у": "u", "ф": "f", "х": "kh", "ц": "ts", "ч": "ch", "ш": "sh", "щ": "sch", "ъ": "", "ы": "y", "ь": "",
    "э": "e", "ю": "yu", "я": "ya", "ә": "a", "ғ": "g", "қ": "q", "ң": "n", "ө": "o", "ұ": "u", "ү": "u",
    "һ": "h", "і": "i",
}


def random_code(length: int = 8) -> str:
    return "".join(secrets.choice(_CODE_ALPHABET) for _ in range(length))


def slugify(text: str) -> str:
    latin = "".join(_TRANSLIT.get(ch, ch) for ch in text.lower())
    base = re.sub(r"[^a-z0-9]+", "-", latin).strip("-")[:60] or "event"
    return f"{base}-{random_code(6).lower()}"


def to_zone(dt: datetime, tz_name: str | None) -> datetime:
    try:
        return dt.astimezone(ZoneInfo(tz_name or settings.default_timezone))
    except Exception:
        return dt.astimezone(ZoneInfo(settings.default_timezone))


def format_local(dt: datetime, tz_name: str | None) -> str:
    return f"{to_zone(dt, tz_name).strftime('%d.%m.%Y %H:%M')} ({tz_name or settings.default_timezone})"


def format_kzt(amount: int) -> str:
    return f"{amount:,}".replace(",", " ") + " ₸"
