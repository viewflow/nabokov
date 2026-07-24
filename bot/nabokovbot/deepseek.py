"""DeepSeek rewrite loop with two tools: the nabokov linter and ask_user.

The model drafts a rewrite, may call ``lint_text`` (capped, English texts
only) to check itself, and may call ``ask_user`` to put a short
multiple-choice question to the user in Telegram — the skills' rule "a
missing detail is a question, not a guess" made literal. The ``ask``
callback is provided by the handler layer; it resolves when the user taps a
button (or times out, which reads as "skip").
"""

import asyncio
import json
import logging
from collections.abc import Awaitable, Callable

from openai import AsyncOpenAI

from . import config, linting, prompts

logger = logging.getLogger(__name__)

AskFn = Callable[[str, list[str]], Awaitable[str]]

_client = AsyncOpenAI(
    api_key=config.DEEPSEEK_API_KEY,
    base_url="https://api.deepseek.com",
)


async def _run_tool(name: str, args: dict, ask: AskFn | None) -> dict | str:
    if name == "lint_text":
        draft = args.get("text", "")
        report = await asyncio.to_thread(linting.lint, draft) if draft else None
        return report or {"error": "nothing to lint"}
    if name == "ask_user":
        question = str(args.get("question", "")).strip()
        options = [str(o).strip() for o in args.get("options", []) if str(o).strip()]
        if not question or not ask:
            return "question unavailable — do without that detail"
        answer = await ask(question, options[:4])
        return f"user's answer: {answer}"
    return {"error": f"unknown tool {name}"}


async def rewrite(text: str, mode: str, creative: bool, ask: AskFn | None = None) -> str:
    """Rewrite ``text`` in the given mode; returns the final text."""
    system = prompts.COPYWRITER_SYSTEM if mode == "copywriter" else prompts.EDITOR_SYSTEM
    temperature = config.TEMPERATURE_CREATIVE if creative else config.TEMPERATURE_NORMAL
    english = linting.is_english(text)

    messages: list[dict] = [
        {"role": "system", "content": system},
        {"role": "user", "content": text},
    ]
    lint_calls = 0
    ask_calls = 0

    for _ in range(config.MAX_LINT_TOOL_CALLS + config.MAX_ASK_CALLS + 2):
        tools = []
        if english and lint_calls < config.MAX_LINT_TOOL_CALLS:
            tools.append(prompts.LINT_TOOL)
        if ask is not None and ask_calls < config.MAX_ASK_CALLS:
            tools.append(prompts.ASK_TOOL)
        response = await _client.chat.completions.create(
            model=config.DEEPSEEK_MODEL,
            messages=messages,
            temperature=temperature,
            tools=tools or None,
            max_tokens=4000,
        )
        message = response.choices[0].message
        if response.usage:
            logger.info(
                "deepseek: prompt=%s completion=%s",
                response.usage.prompt_tokens,
                response.usage.completion_tokens,
            )

        if message.tool_calls:
            messages.append(
                {
                    "role": "assistant",
                    "content": message.content or "",
                    "tool_calls": [tc.model_dump() for tc in message.tool_calls],
                }
            )
            for tc in message.tool_calls:
                name = tc.function.name
                if name == "lint_text":
                    lint_calls += 1
                elif name == "ask_user":
                    ask_calls += 1
                try:
                    args = json.loads(tc.function.arguments or "{}")
                except json.JSONDecodeError:
                    args = {}
                result = await _run_tool(name, args, ask)
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "content": result
                        if isinstance(result, str)
                        else json.dumps(result, ensure_ascii=False),
                    }
                )
            continue

        content = (message.content or "").strip()
        # A capped model sometimes writes the tool-call markup as plain text
        # (DSML tags) instead of answering — don't return that to the user.
        if content and "DSML" not in content:
            return content
        messages.append({"role": "assistant", "content": content})
        messages.append(
            {
                "role": "user",
                "content": prompts.FINAL_NUDGE,
            }
        )

    raise RuntimeError("deepseek returned no final text")
