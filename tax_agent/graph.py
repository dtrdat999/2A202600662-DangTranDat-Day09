"""Tax Agent LangGraph definition.

Uses create_react_agent with a tax-specialised system prompt.
No tools — it answers purely from LLM knowledge.
"""

from __future__ import annotations

from langgraph.prebuilt import create_react_agent

from common.llm import get_llm

TAX_SYSTEM_PROMPT = """Bạn là một luật sư thuế và CPA chuyên nghiệp về:
- Tuân thủ và luật thuế doanh nghiệp
- Trốn thuế và lách thuế
- Hình phạt và truy thu thuế
- Quy định định giá chuyển nhượng

Khi trả lời, hãy thật NGẮN GỌN và SÚC TÍCH.
Trả lời BẰNG TIẾNG VIỆT, chỉ tập trung vào các mức phạt dân sự/hình sự, cơ quan liên quan,
và sự khác biệt giữa trách nhiệm công ty và cá nhân.
"""


def create_graph():
    """Return a compiled LangGraph create_react_agent for tax questions."""
    llm = get_llm()
    graph = create_react_agent(
        model=llm,
        tools=[],
        prompt=TAX_SYSTEM_PROMPT,
    )
    return graph