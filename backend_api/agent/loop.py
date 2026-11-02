import asyncio
import logging
import os

import anthropic

from .registry import ToolError, get_tools

logger = logging.getLogger(__name__)

MODEL = os.getenv("AGENT_MODEL", "claude-opus-5-5")
# SMS requests are short, routine actions: low effort keeps latency and cost down
EFFORT = os.getenv("AGENT_EFFORT", "low")
MAX_TURNS = int(os.getenv("AGENT_MAX_TURNS", "8"))
MAX_TOKENS = 16000
# On a safety-classifier refusal, the API re-runs the request on a recommended fallback model
FALLBACK_BETA = "server-side-fallback-2026-07-01"

SYSTEM_PROMPT = """You are the home assistant of a private house, reached by SMS by its residents.

Your replies are sent back as SMS, so:
- Answer in the language of the user's message (usually French).
- Write plain text only, no Markdown, in at most 300 characters.

Use the tools to act on the house. When the user names a device in their own words ("le salon", "la lampe du bureau"), list the entities of the relevant domain first and pick the matching entity_id; if several could match or none does, ask a short clarifying question instead of guessing.

Only say an action was done if a tool call confirmed it. If a tool fails, say what failed in one sentence. If no tool can do what the user asks, say so briefly."""

FALLBACK_REPLIES = {
    "refusal": "Désolé, je ne peux pas traiter cette demande.",
    "too_many_turns": "Désolé, cette demande a demandé trop d'étapes. Essayez de la reformuler plus simplement.",
    "max_tokens": "Désolé, ma réponse a été interrompue. Essayez une demande plus courte.",
    "unavailable": "L'assistant est momentanément indisponible. Réessayez plus tard.",
    "empty": "C'est fait.",
}

_client = None


def is_enabled() -> bool:
    return bool(os.getenv("ANTHROPIC_API_KEY"))


def get_client() -> anthropic.AsyncAnthropic:
    global _client
    if _client is None:
        _client = anthropic.AsyncAnthropic()
    return _client


async def _execute(block) -> dict:
    """Run one tool_use block and turn the outcome into a tool_result block."""
    tool = get_tools().get(block.name)
    try:
        if tool is None:
            raise ToolError(f"unknown tool '{block.name}'")
        content = await tool.run(block.input)
        logger.info("[agent] tool %s(%s) -> %s", block.name, block.input, content[:200])
        return {"type": "tool_result", "tool_use_id": block.id, "content": content}
    except ToolError as e:
        logger.warning("[agent] tool %s(%s) failed: %s", block.name, block.input, e)
        return {"type": "tool_result", "tool_use_id": block.id, "content": f"Error: {e}", "is_error": True}
    except Exception:
        logger.exception("[agent] tool %s crashed", block.name)
        return {"type": "tool_result", "tool_use_id": block.id, "content": "Error: internal tool failure", "is_error": True}


def _text_of(response) -> str:
    return "\n".join(b.text for b in response.content if b.type == "text").strip()


async def run_agent(sender: str, text: str) -> str:
    """Answer one SMS: call the model, run the tools it asks for, and return its final reply.

    `sender` must already have been checked against the whitelist by the caller.
    """
    tools = [t.definition() for t in get_tools().values()]
    messages = [{"role": "user", "content": text}]
    client = get_client()

    try:
        for _ in range(MAX_TURNS):
            response = await client.beta.messages.create(
                model=MODEL,
                max_tokens=MAX_TOKENS,
                system=SYSTEM_PROMPT,
                tools=tools,
                messages=messages,
                output_config={"effort": EFFORT},
                betas=[FALLBACK_BETA],
                fallbacks="default",
            )
            logger.info(
                "[agent] %s turn: stop=%s model=%s request=%s",
                sender, response.stop_reason, response.model, response._request_id,
            )

            if response.stop_reason == "refusal":
                return FALLBACK_REPLIES["refusal"]
            if response.stop_reason == "max_tokens":
                # A truncated tool_use input can still parse, so never run tools from this turn
                return FALLBACK_REPLIES["max_tokens"]

            # Keep the full content (thinking, fallback and tool_use blocks) so the history stays append-only
            messages.append({"role": "assistant", "content": response.content})

            if response.stop_reason == "tool_use":
                calls = [b for b in response.content if b.type == "tool_use"]
                results = await asyncio.gather(*(_execute(b) for b in calls))
                messages.append({"role": "user", "content": list(results)})
                continue
            if response.stop_reason == "pause_turn":
                continue

            return _text_of(response) or FALLBACK_REPLIES["empty"]
    except anthropic.RateLimitError as e:
        logger.error("[agent] rate limited: %s", e.message)
        return FALLBACK_REPLIES["unavailable"]
    except anthropic.APIStatusError as e:
        logger.error("[agent] API error %s: %s", e.status_code, e.message)
        return FALLBACK_REPLIES["unavailable"]
    except anthropic.APIConnectionError as e:
        logger.error("[agent] cannot reach the API: %s", e)
        return FALLBACK_REPLIES["unavailable"]

    logger.warning("[agent] %s gave up after %s turns", sender, MAX_TURNS)
    return FALLBACK_REPLIES["too_many_turns"]
