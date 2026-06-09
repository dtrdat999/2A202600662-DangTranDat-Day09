"""Stage 4: Multi-Agent System (In-Process)

Multiple specialised agents collaborate on a complex legal question.
This mirrors Stage 5's architecture (law_agent/graph.py) but runs
entirely in-process — no HTTP, no A2A protocol, no separate servers.

Graph: analyze_law -> check_routing -> parallel [call_tax, call_compliance] -> aggregate -> END
"""

import asyncio
import json
import os
import sys

# Sửa lỗi hiển thị Tiếng Việt trên Windows Console (PowerShell/CMD)
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from dotenv import load_dotenv
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.tools import tool

from common.llm import get_llm

# ---------------------------------------------------------------------------
# Tools for specialist sub-agents
# ---------------------------------------------------------------------------

@tool
def search_tax_law(query: str) -> str:
    """Search tax law knowledge base for relevant statutes and penalties.

    Args:
        query: Natural language query about tax law.
    """
    knowledge = [
        (
            ["tax", "evasion", "fraud", "irs"],
            "Tax evasion (26 U.S.C. § 7201): felony, up to $250K fine and 5 years prison. "
            "Civil fraud penalty: 75% of underpayment (IRC § 6663). Failure to file: up to "
            "$25K fine and 1 year prison.",
        ),
        (
            ["offshore", "overseas", "foreign", "fbar", "fatca"],
            "FBAR penalties: up to $100K or 50% of account balance per violation. "
            "FATCA non-compliance: 30% withholding on US-source payments. "
            "Willful violations may trigger criminal prosecution.",
        ),
        (
            ["transfer", "pricing", "corporate"],
            "Transfer pricing violations (IRC § 482): IRS can reallocate income between "
            "related entities. Penalties: 20-40% of underpayment for substantial/gross "
            "valuation misstatements.",
        ),
    ]
    query_lower = query.lower()
    results = []
    for keywords, text in knowledge:
        if any(kw in query_lower for kw in keywords):
            results.append(text)
    return "\n\n".join(results) if results else "No specific tax law matches found."


@tool
def search_compliance_law(query: str) -> str:
    """Search regulatory compliance knowledge base for applicable frameworks.

    Args:
        query: Natural language query about regulatory compliance.
    """
    knowledge = [
        (
            ["data", "privacy", "gdpr", "ccpa", "consent", "user"],
            "CCPA: fines up to $7,500 per intentional violation. GDPR: up to 4% of global "
            "revenue or EUR 20M. FTC Act Section 5 for unfair/deceptive practices. "
            "Class action exposure under state privacy laws ($100-$750 per consumer).",
        ),
        (
            ["sox", "sarbanes", "financial", "sec", "reporting"],
            "SOX § 906: false certification — up to $5M fine, 20 years prison. "
            "§ 802: record destruction — up to 20 years. § 1107: whistleblower "
            "retaliation — up to 10 years. SEC officer/director bars.",
        ),
        (
            ["fcpa", "bribery", "corruption", "foreign"],
            "FCPA anti-bribery: up to $250K fine per violation (individuals), "
            "$2M (corporations). Criminal penalties: up to 5 years prison. "
            "Books and records provisions apply to all SEC-reporting companies.",
        ),
    ]

    query_words = set(query.lower().split())
    for keywords, text in knowledge:
        if len(query_words & set(keywords)) > 0:
            return f"[Compliance Source] {text}"

    return "No specific compliance law matches found."


# ---------------------------------------------------------------------------
# State definition (mirrors law_agent/graph.py)
# ---------------------------------------------------------------------------

from typing import Annotated, TypedDict

from langchain_core.messages import AnyMessage
from langgraph.constants import Send
from langgraph.graph import END, StateGraph
from langgraph.graph.message import add_messages


def _last_wins(a: str, b: str) -> str:
    """Reducer: keep the most recently written value."""
    return b if b else a


class LegalState(TypedDict):
    question: str
    chat_history: Annotated[list[AnyMessage], add_messages]
    law_analysis: str
    needs_tax: bool
    needs_compliance: bool
    needs_privacy: bool
    tax_result: Annotated[str, _last_wins]
    compliance_result: Annotated[str, _last_wins]
    privacy_analysis: Annotated[str, _last_wins]
    final_answer: str


# ---------------------------------------------------------------------------
# Node implementations
# ---------------------------------------------------------------------------

async def analyze_law(state: LegalState) -> dict:
    """Lead attorney analyses the legal aspects of the question."""
    print("\n  [Node: analyze_law] Lead attorney analysing legal aspects...")
    llm = get_llm()
    
    # Extract chat history
    history = state.get("chat_history", [])
    
    messages = [
        SystemMessage(
            content=(
                "Bạn là luật sư trưởng chuyên về luật hợp đồng, bồi thường thiệt hại và luật kinh doanh chung. "
                "Dưới đây là lịch sử trò chuyện (nếu có) và câu hỏi mới nhất. "
                "Hãy phân tích các khía cạnh pháp lý của câu hỏi mới nhất một cách kỹ lưỡng. "
                "BẠN PHẢI TRẢ LỜI BẰNG TIẾNG VIỆT và giữ câu trả lời dưới 200 chữ."
            )
        ),
        *history
    ]
    
    # If there's no history or the latest message isn't the current question, add the question manually
    # But we will pass the question via chat_history from the API, so `history` should already contain it.
    if not history or history[-1].content != state["question"]:
        messages.append(HumanMessage(content=state["question"]))
        
    result = await llm.ainvoke(messages)
    print(f"  [Node: analyze_law] Done ({len(result.content)} chars)")
    return {"law_analysis": result.content}


def check_routing(state: LegalState) -> list[Send]:
    question_lower = state["question"].lower()
    tasks = []
    
    if any(kw in question_lower for kw in ["tax", "irs", "thuế"]):
        tasks.append(Send("tax_agent", state))
    
    if any(kw in question_lower for kw in ["compliance", "sec", "regulation", "tuân thủ"]):
        tasks.append(Send("compliance_agent", state))
    
    if any(kw in question_lower for kw in ["data", "privacy", "gdpr", "dữ liệu"]):
        tasks.append(Send("privacy_agent", state))
    
    return tasks if tasks else [Send("aggregate_results", state)]





async def tax_agent(state: LegalState) -> dict:
    """Tax specialist sub-agent (runs as inline ReAct agent)."""
    from langgraph.prebuilt import create_react_agent

    print("\n  [Node: tax_agent] Tax specialist agent starting...")

    # Reuse the tax system prompt from tax_agent/graph.py
    tax_prompt = (
        "Bạn là chuyên gia về thuế và CPA với chuyên môn về luật thuế doanh nghiệp, "
        "trốn thuế, cưỡng chế của IRS và các hình phạt liên quan. "
        "QUY TẮC QUAN TRỌNG: Tool search_tax_law chỉ nhận từ khóa Tiếng Anh. Hãy tự dịch từ khóa sang tiếng Anh để tìm kiếm. "
        "SAU KHI CÓ KẾT QUẢ, HÃY TRẢ LỜI NGƯỜI DÙNG BẰNG TIẾNG VIỆT, dưới 200 chữ."
    )

    llm = get_llm()
    agent = create_react_agent(model=llm, tools=[search_tax_law], prompt=tax_prompt)
    result = await agent.ainvoke({"messages": [{"role": "user", "content": state["question"]}]})

    final_msg = result["messages"][-1].content
    print(f"  [Node: tax_agent] Done ({len(final_msg)} chars)")
    return {"tax_result": final_msg}


async def compliance_agent(state: LegalState) -> dict:
    """Compliance specialist sub-agent (runs as inline ReAct agent)."""
    from langgraph.prebuilt import create_react_agent

    print("\n  [Node: compliance_agent] Compliance specialist agent starting...")

    # Reuse the compliance system prompt from compliance_agent/graph.py
    compliance_prompt = (
        "Bạn là chuyên gia giám đốc tuân thủ với chuyên môn về cưỡng chế SEC, "
        "tuân thủ SOX, FCPA, AML, GDPR, CCPA... "
        "QUY TẮC QUAN TRỌNG: Tool search_compliance_law chỉ nhận từ khóa Tiếng Anh. Hãy tự dịch từ khóa sang tiếng Anh để tìm kiếm. "
        "SAU KHI CÓ KẾT QUẢ, HÃY TRẢ LỜI NGƯỜI DÙNG BẰNG TIẾNG VIỆT, dưới 200 chữ."
    )

    llm = get_llm()
    agent = create_react_agent(model=llm, tools=[search_compliance_law], prompt=compliance_prompt)
    result = await agent.ainvoke({"messages": [{"role": "user", "content": state["question"]}]})

    final_msg = result["messages"][-1].content
    print(f"  [Node: compliance_agent] Done ({len(final_msg)} chars)")
    return {"compliance_result": final_msg}


async def privacy_agent(state: LegalState) -> dict:
    """Agent chuyên về luật bảo vệ dữ liệu cá nhân."""
    print("\n  [Node: privacy_agent] Privacy specialist starting...")
    llm = get_llm()

    prompt = f"""Bạn là chuyên gia về GDPR và luật bảo vệ dữ liệu cá nhân.

Câu hỏi gốc: {state['question']}
Phân tích pháp lý: {state.get('law_analysis', 'N/A')}

Hãy phân tích các vấn đề về privacy và GDPR (nếu có).
"""

    response = await llm.ainvoke([HumanMessage(content=prompt)])
    return {"privacy_analysis": response.content}


async def aggregate_results(state: LegalState) -> dict:
    """Combine all specialist analyses into a final comprehensive answer."""
    print("\n  [Node: aggregate_results] Combining all specialist analyses...")
    llm = get_llm()

    sections: list[str] = []
    if state.get("law_analysis"):
        sections.append(f"## Legal Analysis\n{state['law_analysis']}")
    if state.get("tax_result"):
        sections.append(f"## Tax Analysis\n{state['tax_result']}")
    if state.get("compliance_result"):
        sections.append(f"## Regulatory Compliance Analysis\n{state['compliance_result']}")
    if state.get("privacy_analysis"):
        sections.append(f"## Data Privacy Analysis\n{state['privacy_analysis']}")

    combined = "\n\n---\n\n".join(sections)

    messages = [
        SystemMessage(
            content=(
                "Bạn là luật sư trưởng (Senior Legal Counsel). Nhiệm vụ của bạn là tổng hợp các báo cáo "
                "từ các chuyên gia cấp dưới thành một văn bản tư vấn pháp lý hoàn chỉnh, thống nhất, có chia mục rõ ràng. "
                "BẠN PHẢI TRẢ LỜI HOÀN TOÀN BẰNG TIẾNG VIỆT. Cố gắng tránh lặp từ và giữ độ dài dưới 500 chữ."
            )
        ),
        *state.get("chat_history", []),
        HumanMessage(content=f"Dưới đây là các báo cáo phân tích mới nhất:\n\n{combined}")
    ]
    result = await llm.ainvoke(messages)
    print(f"  [Node: aggregate_results] Done ({len(result.content)} chars)")
    
    from langchain_core.messages import AIMessage
    return {
        "final_answer": result.content,
        "chat_history": [AIMessage(content=result.content)]
    }


# ---------------------------------------------------------------------------
# Graph construction (mirrors law_agent/graph.py topology)
# ---------------------------------------------------------------------------

def create_graph(checkpointer=None):
    """Build and compile the multi-agent StateGraph."""
    graph = StateGraph(LegalState)

    graph.add_node("analyze_law", analyze_law)
    graph.add_node("tax_agent", tax_agent)
    graph.add_node("compliance_agent", compliance_agent)
    graph.add_node("privacy_agent", privacy_agent)
    graph.add_node("aggregate_results", aggregate_results)

    graph.set_entry_point("analyze_law")
    graph.add_conditional_edges(
        "analyze_law",
        check_routing,
        ["tax_agent", "compliance_agent", "privacy_agent", "aggregate_results"],
    )
    graph.add_edge("tax_agent", "aggregate_results")
    graph.add_edge("compliance_agent", "aggregate_results")
    graph.add_edge("privacy_agent", "aggregate_results")
    graph.add_edge("aggregate_results", END)

    return graph.compile(checkpointer=checkpointer)


QUESTION = "Nếu công ty vi phạm hợp đồng, trốn thuế và đánh cắp dữ liệu người dùng thì hậu quả pháp lý là gì?"


async def main():
    print("=" * 70)
    print("GIAI ĐOẠN 4: Hệ thống Đa Tác Vụ (Multi-Agent) chạy song song")
    print("=" * 70)
    print()
    print("[Cách hoạt động]")
    print("  1. Luật sư trưởng phân tích câu hỏi.")
    print("  2. Điều phối viên quyết định gọi các chuyên gia nào.")
    print("  3. Các chuyên gia (Thuế, Tuân thủ, Dữ liệu) chạy SONG SONG cùng lúc.")
    print("  4. Người tổng hợp thu thập báo cáo thành câu trả lời hoàn chỉnh.")
    print()
    print("[Cấu trúc đồ thị]")
    print("  analyze_law -> check_routing -> [call_tax + call_compliance] -> aggregate -> END")
    print()
    print(f"Câu hỏi: {QUESTION}")
    print("-" * 70)

    from langgraph.checkpoint.memory import MemorySaver
    memory = MemorySaver()
    graph = create_graph(checkpointer=memory)

    config = {"configurable": {"thread_id": "test_session"}}

    result = await graph.ainvoke({
        "question": QUESTION,
        "chat_history": [HumanMessage(content=QUESTION)],
        "law_analysis": "",
        "needs_tax": False,
        "needs_compliance": False,
        "needs_privacy": False,
        "tax_result": "",
        "compliance_result": "",
        "privacy_analysis": "",
        "final_answer": "",
    }, config=config)

    print("\n" + "=" * 70)
    print("FINAL ANSWER")
    print("=" * 70)
    print(result["final_answer"])

    print()
    print("-" * 70)
    print("[Improvements over Stage 3]")
    print("  + Specialisation: each agent has domain-specific expertise")
    print("  + Parallel execution: tax + compliance agents run concurrently")
    print("  + Better quality: specialist prompts produce deeper analysis")
    print("  + Structured flow: explicit graph topology with routing logic")
    print()
    print("[Stage 4 (Monolith) vs Stage 5 (Distributed A2A)]")
    print("  +---------------------------+-------------------------------+")
    print("  | Stage 4 (In-Process)      | Stage 5 (A2A Protocol)        |")
    print("  +---------------------------+-------------------------------+")
    print("  | Single process            | Multiple services (ports)     |")
    print("  | Direct function calls     | HTTP-based A2A protocol       |")
    print("  | Shared memory             | Message passing               |")
    print("  | Simple deployment         | Independent scaling           |")
    print("  | Tight coupling            | Loose coupling                |")
    print("  | Easy to debug             | Service discovery + registry  |")
    print("  | Good for small teams      | Good for large organisations  |")
    print("  +---------------------------+-------------------------------+")
    print()
    print("Stage 5 (this repo's main project) takes this same graph topology")
    print("and deploys each agent as an independent A2A service. Run it with:")
    print("  ./start_all.sh && python test_client.py")
    print("=" * 70)


if __name__ == "__main__":
    load_dotenv()
    asyncio.run(main())