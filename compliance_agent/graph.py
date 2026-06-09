"""Compliance Agent LangGraph definition.

Uses create_react_agent with a regulatory-compliance-specialised system prompt.
No tools — it answers purely from LLM knowledge.
"""

from __future__ import annotations

from langgraph.prebuilt import create_react_agent

from common.llm import get_llm

COMPLIANCE_SYSTEM_PROMPT = """Bạn là một chuyên gia tuân thủ quy định và luật sư doanh nghiệp cấp cao chuyên về:
- Các hành động thực thi của SEC và vi phạm luật chứng khoán
- Các quy định chống rửa tiền (AML), chống hối lộ (FCPA)
- Trách nhiệm của hội đồng quản trị và giám đốc điều hành

Hãy tập trung vào:
1. Cơ quan quản lý nào có thẩm quyền (SEC, FTC, DOJ, v.v.)
2. Các hình phạt hành chính, dân sự và hình sự
3. Trách nhiệm cá nhân đối với các vi phạm tuân thủ

BẠN PHẢI TRẢ LỜI NGẮN GỌN BẰNG TIẾNG VIỆT dưới 200 chữ.
"""


def create_graph():
    """Return a compiled LangGraph create_react_agent for compliance questions."""
    llm = get_llm()
    graph = create_react_agent(
        model=llm,
        tools=[],
        prompt=COMPLIANCE_SYSTEM_PROMPT,
    )
    return graph