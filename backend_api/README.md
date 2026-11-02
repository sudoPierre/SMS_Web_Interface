# Backend API

FastAPI service: JWT-protected API for the web interface, and the `/webhook` endpoint called by the Android SMS Gateway.

## SMS commands

An incoming SMS starting with `/` from an authorized number runs a command, e.g. `/ha light all off`.

```text
/webhook ──► store inbound SMS ──► 200 OK to the gateway
                 │
                 └─► background task: whitelist check ──► parse ──► registry ──► handler
                                                                                  │
                     reply SMS (messages table, outbound) ◄── worker sends it ◄───┘
```

- **Whitelist**: a number is authorized if it is in `AUTHORIZED_NUMBERS` (comma-separated) or in the `authorized_numbers` table with `enabled = true`. Numbers are compared after stripping spaces, dots, dashes and parentheses, with a leading `00` turned into `+`. Store them in E.164 form (`+33612345678`). SMS from other numbers are stored as usual, but their commands are ignored without a reply.
- **Non-blocking**: the webhook only schedules the command (`BackgroundTasks`) and answers the gateway immediately. Handlers are async and time out after `SMS_COMMAND_TIMEOUT` seconds (default 20).
- **Feedback**: the handler's return value, or the message of a `CommandError`, is sent back to the sender through `write_sms_in_db(..., "outbound")`, the same path as the web UI. Replies therefore show up in the conversation.

```sql
INSERT INTO authorized_numbers (phone_number, label) VALUES ('+33612345678', 'Pierre');
```

### Built-in commands

| Command | Description |
|---|---|
| `/help [commande]` | Lists every command with its usage, or details one command |
| `/ha <domaine> <entité\|all> [on\|off\|toggle]` | Calls the Home Assistant service `<domaine>.turn_on/turn_off/toggle` (default `toggle`). `light salon` becomes `light.salon`, and `all` targets every entity of the domain. Needs `HA_URL` and `HA_TOKEN` (a long-lived access token). |

### Adding a command

Create a file in `commands/handlers/`. It is imported at startup, so nothing else needs to change:

```python
# commands/handlers/ping.py
from ..registry import CommandError, sms_command

@sms_command("ping", description="Checks that the bot answers", usage="/ping [texte]")
async def ping(ctx):            # ctx.sender, ctx.name, ctx.args, ctx.raw
    if ctx.args and ctx.args[0] == "fail":
        raise CommandError("demandé")   # sent back as "Erreur /ping : demandé"
    return "pong " + " ".join(ctx.args)  # sent back to the sender; return None to stay silent
```

Handlers must be `async`. Use `httpx.AsyncClient` for HTTP calls, and `asyncio.to_thread` for blocking code. Quotes group words: `/cmd "deux mots"`.

### Wiring into the webhook

This is already done in `main.py`:

1. `commands.load_commands()` runs in the `lifespan` hook.
2. `/webhook` takes `background_tasks: BackgroundTasks`. After storing the SMS, it calls `background_tasks.add_task(handle_sms_command, sender, text)` when `event == "sms:received"` and `commands.is_command(text)`.
3. `handle_sms_command` checks `commands.is_authorized(sender, get_db)`, then calls `commands.dispatch(sender, text, reply=...)`.
