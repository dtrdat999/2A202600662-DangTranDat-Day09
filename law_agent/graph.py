"""Law Agent LangGraph StateGraph definition.

Graph topology:
    analyze_law → check_routing → (parallel) call_tax + call_compliance → aggregate → END

The parallel branches (call_tax / call_compliance) are dispatched via LangGraph's
Send API so that both sub-agent calls happen concurrently.
"""

from __future__ import annotations

import json
import logging
from typing import Annotated, TypedDict

from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.constants import Send
from langgraph.graph import END, StateGraph

from common.llm import get_llm

logger = logging.getLogger(__name__)

MAX_DELEGATION_DEPTH = 3


# ---------------------------------------------------------------------------
# State definition
# ---------------------------------------------------------------------------

def _last_wins(a: str, b: str) -> str:
    """Reducer: keep the most recently written value."""
    return b if b else a


class LawState(TypedDict):
    question: str
    context_id: str
    trace_id: str
    delegation_depth: int
    law_analysis: str
    needs_tax: bool
    needs_compliance: bool
    needs_privacy: bool
    # Annotated so parallel branches can both write without conflict
    tax_result: Annotated[str, _last_wins]
    compliance_result: Annotated[str, _last_wins]
    privacy_result: Annotated[str, _last_wins]
    final_answer: str


# ---------------------------------------------------------------------------
# Node implementations
# ---------------------------------------------------------------------------

async def analyze_law(state: LawState) -> dict:
    """LLM analysis from a contract / general law perspective."""
    llm = get_llm()
    messages = [
        SystemMessage(
            content=(
                "Bạn là luật sư trưởng chuyên về luật hợp đồng, bồi thường thiệt hại và luật kinh doanh chung. "
                "Hãy phân tích các khía cạnh pháp lý của câu hỏi dưới đây một cách kỹ lưỡng. "
                "BẠN PHẢI TRẢ LỜI BẰNG TIẾNG VIỆT và giữ câu trả lời dưới 200 chữ."
            )
        ),
        HumanMessage(content=state["question"]),
    ]
    result = await llm.ainvoke(messages)
    return {"law_analysis": result.content}


async def check_routing(state: LawState) -> dict:
    """Determine whether tax and/or compliance sub-agents are needed.

    Returns updated state flags so the routing function can read them.
    If delegation depth is already at the max, skip further delegation.
    """
    depth = state.get("delegation_depth", 0)
    if depth >= MAX_DELEGATION_DEPTH:
        logger.info("Max delegation depth reached (%d); skipping sub-agents", depth)
        return {"needs_tax": False, "needs_compliance": False}

    llm = get_llm()
    messages = [
        SystemMessage(
            content=(
                'Bạn là một chuyên gia điều phối. Dựa vào câu hỏi, hãy quyết định xem có cần gọi các chuyên gia không.\n'
                'Chỉ trả về JSON hợp lệ, KHÔNG THÊM BẤT KỲ VĂN BẢN NÀO KHÁC:\n'
                '{"needs_tax": <true|false>, "needs_compliance": <true|false>, "needs_privacy": <true|false>}\n\n'
                'needs_tax = true  → câu hỏi liên quan đến thuế, trốn thuế\n'
                'needs_compliance = true → câu hỏi liên quan đến tuân thủ quy định, chứng khoán, rửa tiền\n'
                'needs_privacy = true → câu hỏi liên quan đến bảo mật dữ liệu, rò rỉ dữ liệu, GDPR, CCPA'
            )
        ),
        HumanMessage(content=state["question"]),
    ]
    result = await llm.ainvoke(messages)
    raw = result.content.strip()

    # Strip markdown code fences if present
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
        raw = raw.strip()

    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        logger.warning("Routing LLM returned non-JSON: %r — defaulting to all=True", raw)
        parsed = {"needs_tax": True, "needs_compliance": True, "needs_privacy": True}

    needs_tax = bool(parsed.get("needs_tax", True))
    needs_compliance = bool(parsed.get("needs_compliance", True))
    needs_privacy = bool(parsed.get("needs_privacy", True))
    logger.info("Routing decision: needs_tax=%s needs_compliance=%s needs_privacy=%s", needs_tax, needs_compliance, needs_privacy)
    return {"needs_tax": needs_tax, "needs_compliance": needs_compliance, "needs_privacy": needs_privacy}


def route_to_subagents(state: LawState) -> list[Send]:
    """Routing function: dispatch parallel Send objects based on routing flags.

    This function is used with add_conditional_edges; it returns a list of
    Send objects which LangGraph executes as parallel branches.
    """
    sends: list[Send] = []
    if state.get("needs_tax"):
        sends.append(Send("call_tax", state))
    if state.get("needs_compliance"):
        sends.append(Send("call_compliance", state))
    if state.get("needs_privacy"):
        sends.append(Send("call_privacy", state))
    if not sends:
        # No sub-agents needed — go straight to aggregation
        sends.append(Send("aggregate", state))
    return sends


async def call_tax(state: LawState) -> dict:
    """Delegate to the Tax Agent via A2A."""
    from common.a2a_client import delegate
    from common.registry_client import discover

    try:
        endpoint = await discover("tax_question")
        result = await delegate(
            endpoint=endpoint,
            question=state["question"],
            context_id=state["context_id"],
            trace_id=state["trace_id"],
            depth=state.get("delegation_depth", 0) + 1,
        )
        logger.info("Tax Agent returned %d chars", len(result))
        return {"tax_result": result}
    except Exception as exc:
        logger.exception("call_tax failed: %s", exc)
        return {"tax_result": f"[Tax analysis unavailable: {exc}]"}


async def call_compliance(state: LawState) -> dict:
    """Delegate to the Compliance Agent via A2A."""
    from common.a2a_client import delegate
    from common.registry_client import discover

    try:
        endpoint = await discover("compliance_question")
        result = await delegate(
            endpoint=endpoint,
            question=state["question"],
            context_id=state["context_id"],
            trace_id=state["trace_id"],
            depth=state.get("delegation_depth", 0) + 1,
        )
        logger.info("Compliance Agent returned %d chars", len(result))
        return {"compliance_result": result}
    except Exception as exc:
        logger.exception("call_compliance failed: %s", exc)
        return {"compliance_result": f"[Compliance analysis unavailable: {exc}]"}


async def call_privacy(state: LawState) -> dict:
    """Delegate to the Privacy Agent via A2A."""
    from common.a2a_client import delegate
    from common.registry_client import discover

    try:
        endpoint = await discover("privacy_question")
        result = await delegate(
            endpoint=endpoint,
            question=state["question"],
            context_id=state["context_id"],
            trace_id=state["trace_id"],
            depth=state.get("delegation_depth", 0) + 1,
        )
        logger.info("Privacy Agent returned %d chars", len(result))
        return {"privacy_result": result}
    except Exception as exc:
        logger.exception("call_privacy failed: %s", exc)
        return {"privacy_result": f"[Privacy analysis unavailable: {exc}]"}


async def aggregate(state: LawState) -> dict:
    """Combine law_analysis, tax_result, and compliance_result into a final answer."""
    llm = get_llm()

    sections: list[str] = []
    if state.get("law_analysis"):
        sections.append(f"## Phân tích chung\n{state['law_analysis']}")
    if state.get("tax_result"):
        sections.append(f"## Vấn đề Thuế\n{state['tax_result']}")
    if state.get("compliance_result"):
        sections.append(f"## Tuân thủ quy định\n{state['compliance_result']}")
    if state.get("privacy_result"):
        sections.append(f"## Bảo mật dữ liệu\n{state['privacy_result']}")

    combined = "\n\n---\n\n".join(sections)

    messages = [
        SystemMessage(
            content=(
                "Bạn là luật sư trưởng (Senior Legal Counsel). Nhiệm vụ của bạn là tổng hợp các báo cáo "
                "từ các chuyên gia thành một văn bản tư vấn pháp lý hoàn chỉnh, thống nhất, có chia mục rõ ràng. "
                "BẠN PHẢI TRẢ LỜI HOÀN TOÀN BẰNG TIẾNG VIỆT. Cố gắng tránh lặp từ và giữ độ dài dưới 500 chữ."
            )
        ),
        HumanMessage(content=combined),
    ]
    result = await llm.ainvoke(messages)
    return {"final_answer": result.content}


# ---------------------------------------------------------------------------
# Graph construction
# ---------------------------------------------------------------------------

def create_graph():
    """Build and compile the Law Agent StateGraph."""
    graph = StateGraph(LawState)

    graph.add_node("analyze_law", analyze_law)
    graph.add_node("check_routing", check_routing)
    graph.add_node("call_tax", call_tax)
    graph.add_node("call_compliance", call_compliance)
    graph.add_node("call_privacy", call_privacy)
    graph.add_node("aggregate", aggregate)

    graph.set_entry_point("analyze_law")
    graph.add_edge("analyze_law", "check_routing")

    # Conditional parallel dispatch: after check_routing, route_to_subagents
    # returns a list of Send objects (to call_tax, call_compliance, call_privacy, or aggregate)
    graph.add_conditional_edges(
        "check_routing",
        route_to_subagents,
        ["call_tax", "call_compliance", "call_privacy", "aggregate"],
    )

    graph.add_edge("call_tax", "aggregate")
    graph.add_edge("call_compliance", "aggregate")
    graph.add_edge("call_privacy", "aggregate")
    graph.add_edge("aggregate", END)

    return graph.compile()