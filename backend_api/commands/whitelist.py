import logging
import os
import re

logger = logging.getLogger(__name__)


def normalize_number(number: str) -> str:
    """Strip separators and turn a leading 00 into +: "0033 6 12-34" -> "+3361234"."""
    n = re.sub(r"[\s.\-()]", "", number or "")
    if n.startswith("00"):
        n = "+" + n[2:]
    return n


def _env_numbers() -> set:
    raw = os.getenv("AUTHORIZED_NUMBERS", "")
    return {normalize_number(n) for n in raw.split(",") if n.strip()}


def is_authorized(number: str, get_db) -> bool:
    """True if the number is in AUTHORIZED_NUMBERS (comma-separated) or the authorized_numbers table."""
    n = normalize_number(number)
    if not n:
        return False
    if n in _env_numbers():
        return True
    conn = get_db()
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                "SELECT 1 FROM authorized_numbers WHERE phone_number = %s AND enabled",
                (n,),
            )
            return cursor.fetchone() is not None
    except Exception as e:
        logger.error("[whitelist] lookup failed for %s: %s", n, e)
        return False
    finally:
        conn.close()
