import re

from integrations import home_assistant as ha

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
        await ha.call_service(domain, service, entity_id)
    except ha.HomeAssistantError as e:
        raise CommandError(str(e))

    return f"OK : {domain}.{service} -> {entity_id}"
