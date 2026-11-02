import logging
import os
import re

logger = logging.getLogger(__name__)


def normalize_number(number: str) -> str:
    """Return the E.164 form: "0033 6 12-34-56-78" and "06 12 34 56 78" -> "+33612345678".

    National numbers (single leading 0) get SMS_DEFAULT_COUNTRY_CODE (default 33).
    """
    n = re.sub(r"[\s.\-()]", "", number or "")
    if n.startswith("00"):
        n = "+" + n[2:]
    elif n.startswith("0"):
        country_code = os.getenv("SMS_DEFAULT_COUNTRY_CODE", "33").lstrip("+")
        if country_code:
            n = f"+{country_code}{n[1:]}"
    return n


def env_numbers() -> set:
    raw = os.getenv("AUTHORIZED_NUMBERS", "")
    return {normalize_number(n) for n in raw.split(",") if n.strip()}


def is_authorized(number: str, get_db) -> bool:
    """True if the number is in AUTHORIZED_NUMBERS (comma-separated) or the authorized_numbers table."""
    n = normalize_number(number)
    if not n:
        return False
    if n in env_numbers():
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
