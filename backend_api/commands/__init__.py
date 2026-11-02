"""SMS command engine.

Incoming SMS starting with "/" are parsed and dispatched to handlers registered
with @sms_command. Every module in commands/handlers/ is imported by
load_commands(), so adding a command only means adding a file there.
"""
from .registry import (
    Command,
    CommandContext,
    CommandError,
    dispatch,
    get_commands,
    is_command,
    load_commands,
    sms_command,
)
from .whitelist import is_authorized, normalize_number

__all__ = [
    "Command",
    "CommandContext",
    "CommandError",
    "dispatch",
    "get_commands",
    "is_command",
    "load_commands",
    "sms_command",
    "is_authorized",
    "normalize_number",
]
