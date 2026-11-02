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


PHONE_NUMBER = re.compile(r"^\+?\d{6,15}$")


def is_valid_number(number: str) -> bool:
    """True if the normalized number looks like an E.164 number."""
    return bool(PHONE_NUMBER.match(number))


def env_numbers() -> set:
    raw = os.getenv("AUTHORIZED_NUMBERS", "")
    return {normalize_number(n) for n in raw.split(",") if n.strip()}


def is_authorized(number: str, get_db, include_env: bool = True, for_agent: bool = False) -> bool:
    """True if the number is enabled in the authorized_numbers table, or in AUTHORIZED_NUMBERS.

    include_env=False restricts the check to the database whitelist.
    for_agent=True also requires the number's agent_enabled flag (used by the AI agent).
    """
    n = normalize_number(number)
    if not n:
        return False
    if include_env and n in env_numbers():
        return True
    condition = "enabled AND agent_enabled" if for_agent else "enabled"
    conn = get_db()
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                f"SELECT 1 FROM authorized_numbers WHERE phone_number = %s AND {condition}",
                (n,),
            )
            return cursor.fetchone() is not None
    except Exception as e:
        logger.error("[whitelist] lookup failed for %s: %s", n, e)
        return False
    finally:
        conn.close()


def is_admin(number: str, get_db) -> bool:
    """Numbers in AUTHORIZED_NUMBERS are admins; others need is_admin in the table (set from the web UI)."""
    n = normalize_number(number)
    if not n:
        return False
    if n in env_numbers():
        return True
    conn = get_db()
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                "SELECT 1 FROM authorized_numbers WHERE phone_number = %s AND enabled AND is_admin",
                (n,),
            )
            return cursor.fetchone() is not None
    finally:
        conn.close()


def upsert_number(get_db, number: str, agent_enabled: bool, label=None):
    """Add a number, or re-enable it and set its AI agent right if it exists. Returns True when created.

    is_admin is never changed here: admin rights are only granted from the web UI.
    """
    conn = get_db()
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO authorized_numbers (phone_number, label, agent_enabled)
                VALUES (%s, %s, %s)
                ON CONFLICT (phone_number) DO UPDATE SET
                    enabled = TRUE,
                    agent_enabled = EXCLUDED.agent_enabled,
                    label = COALESCE(EXCLUDED.label, authorized_numbers.label)
                RETURNING (xmax = 0) AS created
                """,
                (normalize_number(number), label, agent_enabled),
            )
            created = cursor.fetchone()[0]
        conn.commit()
        return created
    finally:
        conn.close()


def list_numbers(get_db) -> list:
    conn = get_db()
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                "SELECT phone_number, label, enabled, agent_enabled, is_admin "
                "FROM authorized_numbers ORDER BY created_at ASC"
            )
            return cursor.fetchall()
    finally:
        conn.close()
