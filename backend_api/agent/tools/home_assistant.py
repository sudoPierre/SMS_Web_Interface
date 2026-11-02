import os
from typing import Annotated, Literal

from pydantic import Field

from integrations import home_assistant as ha

from ..registry import ToolError, agent_tool


def allowed_domains() -> set:
    raw = os.getenv("AGENT_HA_DOMAINS", "light,switch,fan,scene,script,input_boolean")
    return {d.strip() for d in raw.split(",") if d.strip()}


def check_domain(domain: str):
    if domain not in allowed_domains():
        raise ToolError(f"domain '{domain}' is not allowed; allowed: {', '.join(sorted(allowed_domains()))}")


@agent_tool(
    "List the Home Assistant entities of one domain with their friendly name and current state. "
    "Call it to find the exact entity_id before acting on a device the user named in their own words."
)
async def ha_list_entities(
    domain: Annotated[str, Field(description="Entity domain, e.g. light, switch, fan, scene")],
):
    check_domain(domain)
    try:
        return await ha.list_entities(domain)
    except ha.HomeAssistantError as e:
        raise ToolError(str(e))


@agent_tool(
    "Turn a Home Assistant entity on or off, or toggle it. Use entity_id 'all' to target every "
    "entity of the domain. Scenes and scripts only support turn_on."
)
async def ha_call_service(
    domain: Annotated[str, Field(description="Entity domain, e.g. light")],
    service: Annotated[Literal["turn_on", "turn_off", "toggle"], Field(description="Action to perform")],
    entity_id: Annotated[str, Field(description="Full entity id such as light.salon, or 'all'")],
):
    check_domain(domain)
    if entity_id != "all" and not entity_id.startswith(f"{domain}."):
        raise ToolError(f"entity_id must belong to the '{domain}' domain")
    try:
        await ha.call_service(domain, service, entity_id)
    except ha.HomeAssistantError as e:
        raise ToolError(str(e))
    return f"done: {domain}.{service} on {entity_id}"
