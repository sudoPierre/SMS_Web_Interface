from ..registry import CommandError, get_commands, sms_command


@sms_command("help", description="Liste les commandes disponibles", usage="/help [commande]")
async def help_command(ctx):
    commands = get_commands()
    if ctx.args:
        name = ctx.args[0].lstrip("/").lower()
        command = commands.get(name)
        if command is None:
            raise CommandError(f"commande inconnue : /{name}")
        return f"{command.usage}\n{command.description}"

    lines = ["Commandes disponibles :"]
    lines += [f"{c.usage} - {c.description}" for c in commands.values()]
    return "\n".join(lines)
