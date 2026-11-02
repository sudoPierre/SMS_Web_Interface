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

- **Whitelist**: a number is authorized if it is in `AUTHORIZED_NUMBERS` (comma-separated) or in the `authorized_numbers` table with `enabled = true`. The table is managed from the web interface (shield icon in the sidebar) or the `/api/authorized-numbers` endpoints. Numbers are normalized to E.164 before comparison: separators are removed, `00` becomes `+`, and a national number such as `06…` gets `SMS_DEFAULT_COUNTRY_CODE` (default `33`). SMS from other numbers are stored as usual, but their commands are ignored without a reply.
- **Non-blocking**: the webhook only schedules the command (`BackgroundTasks`) and answers the gateway immediately. Handlers are async and time out after `SMS_COMMAND_TIMEOUT` seconds (default 20).
- **Feedback**: the handler's return value, or the message of a `CommandError`, is sent back to the sender through `write_sms_in_db(..., "outbound")`, the same path as the web UI. Replies therefore show up in the conversation.

Whitelist API (JWT required):

| Method | Path | Body |
|---|---|---|
| `GET` | `/api/authorized-numbers` | lists DB entries plus read-only `AUTHORIZED_NUMBERS` entries (`source: "env"`) |
| `POST` | `/api/authorized-numbers` | `{"phone_number": "+33612345678", "label": "Pierre"}` |
| `PATCH` | `/api/authorized-numbers/{number}` | any of `{"label": "…", "enabled": false, "agent_enabled": false}` |
| `DELETE` | `/api/authorized-numbers/{number}` | |

URL-encode the number in the path (`%2B33612345678`).

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

## AI agent

An incoming SMS that does **not** start with `/` goes to an LLM agent (Claude, through the Anthropic API) that can act on the house with tools, e.g. "Allume le salon".

```text
/webhook ──► store inbound SMS ──► 200 OK
                 │
                 └─► background task: authorized_numbers check (DB only) ──► agent loop
                                                                               │
          ┌────────────────────────────────────────────────────────────────────┘
          ▼
   Claude ──tool_use──► run tools (asyncio.gather) ──tool_result──► Claude ... ──► final text
                                                                                       │
          reply SMS (messages.sender_type = 'ai_agent') ◄── worker sends it ◄──────────┘
```

- **Enabled** only when `ANTHROPIC_API_KEY` is set. When it is unset, plain SMS are just stored, as before.
- **Strict whitelist**: the agent only answers numbers that are enabled in the `authorized_numbers` table (the web UI whitelist) **and** have `agent_enabled = true`. The "AI agent" switch in the whitelist screen turns the agent off for one number while its `/commands` keep working. Numbers that come only from `AUTHORIZED_NUMBERS` can run `/commands` but cannot talk to the agent. Any other SMS is ignored before the API is called.
- **Loop** (`agent/loop.py`): the SMS is sent to the model with the registered tools. Each `tool_use` block is validated and run, all calls of a turn concurrently, and the results go back as `tool_result` blocks (`is_error` on failure). The loop ends on the model's final text, or after `AGENT_MAX_TURNS` turns (default 8). Refusals, truncated output and API errors produce a short apology SMS instead.
- **Model**: `AGENT_MODEL` (default `claude-opus-5-5`) at `AGENT_EFFORT` (default `low`, enough for short home-automation requests). Requests use server-side refusal fallbacks (`fallbacks: "default"`).
- **Traceability**: `messages.sender_type` is `human` (inbound SMS and web UI), `command` (`/command` replies) or `ai_agent`. The web UI shows an "AI agent" badge on agent replies.
- **Home Assistant tools** (`agent/tools/home_assistant.py`): `ha_list_entities` (to map "le salon" to `light.salon`) and `ha_call_service` (`turn_on` / `turn_off` / `toggle`). They are restricted to the domains in `AGENT_HA_DOMAINS` (default `light,switch,fan,scene,script,input_boolean`). Locks, alarms and covers stay out unless you add them.

Each SMS is answered on its own: the agent does not see earlier messages of the conversation.

### Adding a tool

Create a file in `agent/tools/`. The JSON schema sent to the model is derived from the signature, and inputs are validated against it before the function runs:

```python
# agent/tools/weather.py
from typing import Annotated
from pydantic import Field
from ..registry import ToolError, agent_tool

@agent_tool("Current outdoor temperature in °C measured by the house sensor.")
async def outdoor_temperature(
    sensor: Annotated[str, Field(description="Sensor entity id, e.g. sensor.jardin")] = "sensor.jardin",
):
    ...                         # raise ToolError("...") to report a failure to the model
    return {"temperature": 12.5}  # str, or anything JSON-serializable
```

### Migrations

`migrations/*.sql` files run once each, in name order, when the backend starts. Applied versions are recorded in `schema_migrations`. `001_messages_sender_type.sql` adds `messages.sender_type`; `002_authorized_numbers_agent_enabled.sql` adds the per-number agent switch.
