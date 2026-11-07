"""Single-model LangGraph agent connected to the NinjaOne MCP gateway."""
from __future__ import annotations

import asyncio
import os
import re
import sys
from typing import Any

from langchain_core.tools import StructuredTool
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import MemorySaver
from langgraph.prebuilt import create_react_agent
from langchain_mcp_adapters.client import MultiServerMCPClient

SYSTEM_PROMPT = """You are a NinjaOne operations assistant. You have live access to the NinjaOne API through MCP tools.

You are the only reasoning and answer-generation model. Understand the user's complete request, including spelling errors and follow-up references. Decide what information is needed, discover relevant API operations from the complete OpenAPI catalogue, inspect the exact endpoint schema, execute the necessary API calls, and reason over the returned data. Do not rely on memorized tenant facts.

Operating rules:
1. For factual NinjaOne questions, retrieve current tenant data through tools before answering. Do not invent names, counts, device details, statuses, IDs, or dates.
2. Search the full endpoint catalogue. Do not assume the seven MCP tools represent only seven API operations: find_endpoint + describe_endpoint + call expose the documented API catalogue dynamically.
3. Inspect endpoint parameters and request/response schemas before calling unfamiliar operations. Supply required path parameters and query/body values exactly as documented.
4. For multi-part questions, plan and execute as many read calls as needed, then combine only the returned evidence. For paginated endpoints, continue until all required pages are collected or clearly report the limit/error.
5. If an API result is empty, say no matching records were returned and state the scope/filters used. Distinguish zero results from API failure or incomplete pagination.
6. If the API cannot answer, explain which endpoint, permission, scope, or data field is missing. Ask one focused clarification only when the request cannot be resolved safely.
7. Never claim an operation succeeded unless the tool response confirms it. Never conceal API errors.
8. Read-only GET calls are normal. The tool layer requires human confirmation for POST/PUT/PATCH and blocks DELETE; do not try to bypass those controls.
9. Give a concise, direct answer with useful fields and a clear count when the data supports one. Cite the relevant API operation in the answer when helpful.
"""


def _method_for_tool(tool_name: str, args: dict[str, Any]) -> str | None:
    name = tool_name.rsplit("__", 1)[-1]
    candidate = str(args.get("endpoint", "")) if name == "call" else ""
    if name == "raw_call":
        candidate = str(args.get("request", ""))
    match = re.match(r"^\s*(GET|POST|PUT|PATCH|DELETE)\s+", candidate, re.I)
    return match.group(1).upper() if match else None


def _confirm_action(method: str, args: dict[str, Any]) -> bool:
    print("\n[APPROVAL REQUIRED] This NinjaOne operation changes tenant data.")
    print(f"Method: {method}")
    print(f"Arguments: {args}")
    answer = input("Type YES to execute this operation: ").strip()
    return answer == "YES"


async def _guard_tool(tool: Any) -> StructuredTool:
    original = tool

    async def guarded(**kwargs: Any) -> Any:
        method = _method_for_tool(original.name, kwargs)
        if method == "DELETE":
            return {"blocked": True, "method": method, "reason": "DELETE operations are disabled by the local agent safety policy."}
        if method in {"POST", "PUT", "PATCH"}:
            approved = await asyncio.to_thread(_confirm_action, method, kwargs)
            if not approved:
                return {"cancelled": True, "method": method, "reason": "Human approval was not provided; no API request was sent."}
        return await original.ainvoke(kwargs)

    return StructuredTool(
        name=original.name,
        description=original.description,
        args_schema=original.args_schema,
        coroutine=guarded,
    )


class NinjaOneAgent:
    """Owns the local model, MCP subprocess, and LangGraph conversation graph."""

    def __init__(self) -> None:
        self.client: MultiServerMCPClient | None = None
        self.graph: Any = None
        self.thread_id = "ninjaone-local-session"

    async def start(self) -> None:
        base_url = os.getenv("FOUNDRY_BASE_URL", "http://127.0.0.1:64541/v1").rstrip("/")
        model_name = os.getenv("FOUNDRY_MODEL", "olmo-3-7b-instruct-generic-gpu")
        api_key = os.getenv("FOUNDRY_API_KEY", "local")
        llm = ChatOpenAI(
            model=model_name,
            base_url=base_url,
            api_key=api_key,
            temperature=0,
            max_retries=2,
            timeout=float(os.getenv("FOUNDRY_TIMEOUT_SECONDS", "180")),
        )

        child_env = dict(os.environ)
        self.client = MultiServerMCPClient({
            "ninjaone": {
                "transport": "stdio",
                "command": sys.executable,
                "args": ["-m", "ninja_mcp"],
                "env": child_env,
            }
        })
        discovered = await self.client.get_tools()
        if not discovered:
            raise RuntimeError("The NinjaOne MCP gateway connected but exposed no tools.")
        guarded = [await _guard_tool(tool) for tool in discovered]
        print(f"[MCP] Connected to NinjaOne gateway; {len(guarded)} gateway tools discovered.")
        print("[LLM] Using one local reasoning model:", model_name)
        self.graph = create_react_agent(
            model=llm,
            tools=guarded,
            prompt=SYSTEM_PROMPT,
            checkpointer=MemorySaver(),
        )

    async def ask(self, question: str) -> str:
        if self.graph is None:
            raise RuntimeError("Agent is not started. Call start() first.")
        limit = int(os.getenv("AGENT_RECURSION_LIMIT", "30"))
        result = await self.graph.ainvoke(
            {"messages": [{"role": "user", "content": question}]},
            config={"configurable": {"thread_id": self.thread_id}, "recursion_limit": limit},
        )
        messages = result.get("messages", [])
        for message in reversed(messages):
            if getattr(message, "type", "") == "ai" and not getattr(message, "tool_calls", None):
                content = message.content
                if isinstance(content, str):
                    return content
                return str(content)
        return "The agent completed without producing a final text response."
