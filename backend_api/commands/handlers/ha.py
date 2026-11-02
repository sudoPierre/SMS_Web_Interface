import os
import re

import httpx

from ..registry import CommandError, sms_command

ACTIONS = {
    "on": "turn_on",
    "off": "turn_off",
    "toggle": "toggle",
}
SLUG = re.compile(r"^[a-z0-9_]+$")
ENTITY = re.compile(r"^[a-z0-9_]+(\.[a-z0-9_]+)?$")
USAGE = "/ha <domaine> <entité|all> [on|off|toggle]"


@sms_command(
    "ha",
    description="Pilote Home Assistant (ex: /ha light all off, /ha switch prise on)",
    usage=USAGE,
)
async def home_assistant(ctx):
    url = os.getenv("HA_URL", "").rstrip("/")
    token = os.getenv("HA_TOKEN", "")
    if not url or not token:
        raise CommandError("Home Assistant n'est pas configuré (HA_URL / HA_TOKEN)")
    if len(ctx.args) < 2:
        raise CommandError(f"usage : {USAGE}")

    domain, target = ctx.args[0].lower(), ctx.args[1].lower()
    action = ctx.args[2].lower() if len(ctx.args) > 2 else "toggle"
    if not SLUG.match(domain) or not ENTITY.match(target):
        raise CommandError("domaine ou entité invalide")
    service = ACTIONS.get(action)
    if service is None:
        raise CommandError(f"action inconnue '{action}' (on, off, toggle)")

    entity_id = "all" if target == "all" else (target if "." in target else f"{domain}.{target}")

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.post(
                f"{url}/api/services/{domain}/{service}",
                headers={"Authorization": f"Bearer {token}"},
                json={"entity_id": entity_id},
            )
    except httpx.HTTPError as e:
        raise CommandError(f"Home Assistant injoignable ({type(e).__name__})")
    if response.status_code >= 400:
        raise CommandError(f"Home Assistant a répondu {response.status_code}")

    return f"OK : {domain}.{service} -> {entity_id}"
