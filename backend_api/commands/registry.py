import asyncio
import importlib
import logging
import os
import pkgutil
import shlex
from dataclasses import dataclass
from typing import Any, Awaitable, Callable, Optional

logger = logging.getLogger(__name__)

COMMAND_PREFIX = "/"
COMMAND_TIMEOUT = float(os.getenv("SMS_COMMAND_TIMEOUT", "20"))


class CommandError(Exception):
    """Raised by a handler to send its message back to the sender as an error."""


@dataclass(frozen=True)
class CommandContext:
    sender: str
    name: str
    args: list
    raw: str
    # Opens a database connection, for handlers that read or change the whitelist
    get_db: Optional[Callable[[], Any]] = None


Handler = Callable[[CommandContext], Awaitable[Optional[str]]]


@dataclass(frozen=True)
class Command:
    name: str
    handler: Handler
    description: str
    usage: str


_registry: dict = {}


def sms_command(name: str, description: str, usage: str = ""):
    """Register an async handler for "/<name>". Its return value is sent back to the sender."""
    def decorator(func: Handler) -> Handler:
        if not asyncio.iscoroutinefunction(func):
            raise TypeError(f"SMS command handler '{name}' must be an async function")
        key = name.lower()
        if key in _registry:
            raise ValueError(f"SMS command '{key}' is already registered")
        _registry[key] = Command(key, func, description, usage or f"{COMMAND_PREFIX}{key}")
        return func
    return decorator


def get_commands() -> dict:
    return dict(sorted(_registry.items()))


def load_commands():
    """Import every module in commands/handlers so their decorators run."""
    from . import handlers
    for module in pkgutil.iter_modules(handlers.__path__):
        if not module.name.startswith("_"):
            importlib.import_module(f"{handlers.__name__}.{module.name}")
    logger.info("[commands] loaded: %s", ", ".join(_registry) or "none")


def is_command(text: str) -> bool:
    return text.strip().startswith(COMMAND_PREFIX)


def parse(text: str):
    """"/ha light all" -> ("ha", ["light", "all"]). Quotes group words: /cmd "two words"."""
    body = text.strip()[len(COMMAND_PREFIX):]
    try:
        parts = shlex.split(body)
    except ValueError:
        parts = body.split()
    if not parts:
        return None
    return parts[0].lower(), parts[1:]


async def dispatch(sender: str, text: str, reply: Callable[[str], None], get_db=None):
    """Run the command in `text` and send its result (or error) through `reply`.

    `reply` is synchronous (DB write), so it runs in a thread to keep the event loop free.
    """
    async def send(message: str):
        await asyncio.to_thread(reply, message)

    parsed = parse(text)
    if parsed is None:
        await send("Commande vide. Envoyez /help pour la liste des commandes.")
        return
    name, args = parsed
    command = _registry.get(name)
    if command is None:
        await send(f"Commande inconnue : /{name}. Envoyez /help pour la liste des commandes.")
        return

    ctx = CommandContext(sender=sender, name=name, args=args, raw=text, get_db=get_db)
    logger.info("[commands] %s from %s args=%s", name, sender, args)
    try:
        result = await asyncio.wait_for(command.handler(ctx), timeout=COMMAND_TIMEOUT)
    except CommandError as e:
        await send(f"Erreur /{name} : {e}")
    except asyncio.TimeoutError:
        logger.error("[commands] %s timed out after %ss", name, COMMAND_TIMEOUT)
        await send(f"Erreur /{name} : délai dépassé")
    except Exception:
        logger.exception("[commands] %s failed", name)
        await send(f"Erreur /{name} : erreur interne")
    else:
        if result:
            await send(result)
