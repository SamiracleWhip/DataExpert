import json
import os
from typing import AsyncGenerator

import anthropic
from fastapi import APIRouter
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

from ai.guard import run_guard
from ai.rag import build_system_prompt, search_context
from ai.tools import TOOL_DEFINITIONS, execute_tool

router = APIRouter(prefix="/api/chat", tags=["chat"])

_client: anthropic.AsyncAnthropic | None = None


def _get_client() -> anthropic.AsyncAnthropic:
    global _client
    if _client is None:
        kwargs = {"api_key": os.environ.get("ANTHROPIC_API_KEY", "")}
        base_url = os.environ.get("DATAEXPERT_BASE_URL")
        if base_url:
            kwargs["base_url"] = base_url
        _client = anthropic.AsyncAnthropic(**kwargs)
    return _client


class ChatRequest(BaseModel):
    message: str
    history: list[dict] = []
    filters: dict = {}


@router.post("")
async def chat(req: ChatRequest):
    return EventSourceResponse(_stream(req))


async def _stream(req: ChatRequest) -> AsyncGenerator[dict, None]:
    try:
        guard = await run_guard(req.message, _get_client())
        if guard.blocked:
            yield {"data": json.dumps({"type": "text", "text": guard.reply})}
            yield {"data": json.dumps({"type": "done"})}
            return

        context = search_context(req.message)
        system_prompt = build_system_prompt(context, req.filters)

        # Trim history to last 10 turns (20 messages) to control token usage
        messages = req.history[-20:] + [{"role": "user", "content": req.message}]

        client = _get_client()

        for _round in range(4):  # max 3 tool-call rounds + final answer
            async with client.messages.stream(
                model="claude-sonnet-4-6",
                max_tokens=2048,
                system=system_prompt,
                tools=TOOL_DEFINITIONS,
                messages=messages,
                extra_headers={"x-session-id": "shedza-session"},
            ) as stream:
                async for text in stream.text_stream:
                    yield {"data": json.dumps({"type": "text", "text": text})}

                final_msg = await stream.get_final_message()

            if final_msg.stop_reason != "tool_use":
                break

            # Execute all tool calls from this round
            tool_use_blocks = [b for b in final_msg.content if b.type == "tool_use"]
            tool_results = []
            for block in tool_use_blocks:
                yield {"data": json.dumps({"type": "tool_start", "tool": block.name})}
                result = await execute_tool(block.name, block.input)
                tool_results.append(
                    {
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": result,
                    }
                )

            # Build assistant content as plain dicts for the next API call
            assistant_content = []
            for block in final_msg.content:
                if block.type == "text":
                    assistant_content.append({"type": "text", "text": block.text})
                elif block.type == "tool_use":
                    assistant_content.append(
                        {
                            "type": "tool_use",
                            "id": block.id,
                            "name": block.name,
                            "input": block.input,
                        }
                    )

            messages = messages + [
                {"role": "assistant", "content": assistant_content},
                {"role": "user", "content": tool_results},
            ]

    except Exception as exc:
        yield {"data": json.dumps({"type": "error", "message": str(exc)})}

    yield {"data": json.dumps({"type": "done"})}
