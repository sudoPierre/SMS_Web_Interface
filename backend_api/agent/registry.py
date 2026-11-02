import asyncio
import importlib
import inspect
import json
import logging
import pkgutil
import typing
from dataclasses import dataclass
from typing import Any, Awaitable, Callable

from pydantic import BaseModel, ConfigDict, ValidationError, create_model

logger = logging.getLogger(__name__)


class ToolError(Exception):
    """Raised by a tool to report a failure to the model (sent as an is_error tool_result)."""


@dataclass(frozen=True)
class AgentTool:
    name: str
    description: str
    func: Callable[..., Awaitable[Any]]
    input_model: type

    def definition(self) -> dict:
        """Tool definition in the format the Messages API expects."""
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": _clean_schema(self.input_model.model_json_schema()),
        }

    async def run(self, raw_input: dict) -> str:
        try:
            params = self.input_model.model_validate(raw_input or {})
        except ValidationError as e:
            raise ToolError(f"invalid input: {e.errors(include_url=False)}")
        result = await self.func(**{name: getattr(params, name) for name in self.input_model.model_fields})
        return result if isinstance(result, str) else json.dumps(result, ensure_ascii=False, default=str)


_registry: dict = {}


def agent_tool(description: str, name: str = ""):
    """Expose an async function to the agent. The JSON schema comes from its signature.

    Annotate parameters with typing.Annotated[type, pydantic.Field(description=...)]
    so the model knows what each one means; parameters with a default are optional.
    """
    def decorator(func):
        if not asyncio.iscoroutinefunction(func):
            raise TypeError(f"agent tool '{func.__name__}' must be an async function")
        tool_name = name or func.__name__
        if tool_name in _registry:
            raise ValueError(f"agent tool '{tool_name}' is already registered")
        hints = typing.get_type_hints(func, include_extras=True)
        fields = {}
        for param in inspect.signature(func).parameters.values():
            if param.name not in hints:
                raise TypeError(f"agent tool '{tool_name}': parameter '{param.name}' needs a type annotation")
            default = ... if param.default is inspect.Parameter.empty else param.default
            fields[param.name] = (hints[param.name], default)
        input_model = create_model(f"{tool_name}_input", __config__=ConfigDict(extra="forbid"), **fields)
        _registry[tool_name] = AgentTool(tool_name, description, func, input_model)
        return func
    return decorator


def get_tools() -> dict:
    return dict(sorted(_registry.items()))


def load_tools():
    """Import every module in agent/tools so their decorators run."""
    from . import tools
    for module in pkgutil.iter_modules(tools.__path__):
        if not module.name.startswith("_"):
            importlib.import_module(f"{tools.__name__}.{module.name}")
    logger.info("[agent] tools loaded: %s", ", ".join(_registry) or "none")


def _clean_schema(schema):
    """Drop pydantic's auto-generated titles, which only add noise to the prompt."""
    if isinstance(schema, dict):
        return {k: _clean_schema(v) for k, v in schema.items() if k != "title"}
    if isinstance(schema, list):
        return [_clean_schema(v) for v in schema]
    return schema
