"""Privacy Agent LangGraph definition.

Uses create_react_agent with a regulatory-privacy-specialised system prompt.
No tools — it answers purely from LLM knowledge.
"""

from __future__ import annotations

from langgraph.prebuilt import create_react_agent

from common.llm import get_llm

PRIVACY_SYSTEM_PROMPT = """Bạn là một chuyên gia về luật bảo vệ dữ liệu cá nhân (GDPR, CCPA) và an ninh mạng.
Hãy phân tích các khía cạnh liên quan đến bảo mật dữ liệu, rò rỉ dữ liệu, và trách nhiệm của công ty khi để lộ thông tin người dùng.

BẠN PHẢI TRẢ LỜI NGẮN GỌN BẰNG TIẾNG VIỆT dưới 200 chữ, nêu rõ các mức phạt và nghĩa vụ báo cáo.
"""

def create_graph():
    """Return a compiled LangGraph create_react_agent for privacy questions."""
    llm = get_llm()
    graph = create_react_agent(
        model=llm,
        tools=[],
        prompt=PRIVACY_SYSTEM_PROMPT,
    )
    return graph
