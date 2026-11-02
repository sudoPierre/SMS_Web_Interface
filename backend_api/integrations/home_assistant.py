"""Minimal async Home Assistant REST client shared by the /ha command and the AI agent."""
import os
import re

import httpx

SLUG = re.compile(r"^[a-z0-9_]+$")
ENTITY_ID = re.compile(r"^[a-z0-9_]+\.[a-z0-9_]+$")


class HomeAssistantError(Exception):
    """User-facing error (safe to send back by SMS)."""


def _config():
    url = os.getenv("HA_URL", "").rstrip("/")
    token = os.getenv("HA_TOKEN", "")
    if not url or not token:
        raise HomeAssistantError("Home Assistant n'est pas configuré (HA_URL / HA_TOKEN)")
    return url, {"Authorization": f"Bearer {token}"}


async def _request(method: str, path: str, json=None):
    url, headers = _config()
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.request(method, f"{url}{path}", headers=headers, json=json)
    except httpx.HTTPError as e:
        raise HomeAssistantError(f"Home Assistant injoignable ({type(e).__name__})")
    if response.status_code >= 400:
        raise HomeAssistantError(f"Home Assistant a répondu {response.status_code}")
    return response.json() if response.content else None


async def call_service(domain: str, service: str, entity_id: str):
    """POST /api/services/<domain>/<service> with {"entity_id": ...} ("all" targets the whole domain)."""
    if not SLUG.match(domain) or not SLUG.match(service):
        raise HomeAssistantError("domaine ou service invalide")
    if entity_id != "all" and not ENTITY_ID.match(entity_id):
        raise HomeAssistantError(f"entité invalide : {entity_id}")
    return await _request("POST", f"/api/services/{domain}/{service}", json={"entity_id": entity_id})


async def list_entities(domain: str, limit: int = 50) -> list:
    """Entities of a domain with their friendly name and current state."""
    if not SLUG.match(domain):
        raise HomeAssistantError("domaine invalide")
    states = await _request("GET", "/api/states") or []
    entities = [
        {
            "entity_id": s["entity_id"],
            "name": s.get("attributes", {}).get("friendly_name"),
            "state": s.get("state"),
        }
        for s in states
        if s.get("entity_id", "").startswith(f"{domain}.")
    ]
    return entities[:limit]
