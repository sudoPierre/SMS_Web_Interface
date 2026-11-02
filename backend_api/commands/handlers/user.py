import asyncio

from ..registry import CommandError, sms_command
from ..whitelist import is_admin, is_valid_number, list_numbers, normalize_number, upsert_number

ROLES = {
    "access": False,  # /commands only
    "agent": True,    # /commands and the AI agent
}
USAGE = "/user add <numéro> <access|agent> [nom] | /user list"


def _rights(enabled, agent_enabled, admin) -> str:
    if not enabled:
        return "désactivé"
    rights = "agent" if agent_enabled else "access"
    return f"{rights}, admin" if admin else rights


@sms_command(
    "user",
    description="Admins : ajoute un numéro à la whitelist (access = commandes, agent = commandes + IA) ou liste la whitelist",
    usage=USAGE,
)
async def user_command(ctx):
    if not await asyncio.to_thread(is_admin, ctx.sender, ctx.get_db):
        raise CommandError("réservé aux administrateurs")
    if not ctx.args:
        raise CommandError(f"usage : {USAGE}")

    action = ctx.args[0].lower()
    if action == "list":
        rows = await asyncio.to_thread(list_numbers, ctx.get_db)
        if not rows:
            return "Whitelist vide."
        lines = [
            f"{number}{f' ({label})' if label else ''} : {_rights(enabled, agent, admin)}"
            for number, label, enabled, agent, admin in rows
        ]
        return "\n".join(lines)

    if action == "add":
        # The number may be typed with spaces ("06 12 34 56 78"): it runs up to the role keyword
        role_index = next((i for i, arg in enumerate(ctx.args) if i > 1 and arg.lower() in ROLES), None)
        if role_index is None:
            raise CommandError(f"droit manquant (access ou agent) : {USAGE}")
        raw_number = " ".join(ctx.args[1:role_index])
        number = normalize_number(raw_number)
        if not is_valid_number(number):
            raise CommandError(f"numéro invalide : {raw_number}")
        role = ctx.args[role_index].lower()
        label = " ".join(ctx.args[role_index + 1:])[:100] or None
        created = await asyncio.to_thread(upsert_number, ctx.get_db, number, ROLES[role], label)
        verb = "Ajouté" if created else "Mis à jour"
        return f"{verb} : {number}{f' ({label})' if label else ''} -> {role}"

    raise CommandError(f"action inconnue '{action}' ({USAGE})")
