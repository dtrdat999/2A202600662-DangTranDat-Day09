"""Stage 3: Single Agent (ReAct Loop)

Wraps the LLM + tools in an autonomous agent that can reason, act,
and observe in a loop. The agent decides which tools to call, evaluates
the results, and may call more tools before giving a final answer.

Uses LangGraph's create_react_agent for the Think -> Act -> Observe loop.
"""

import asyncio
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from dotenv import load_dotenv
from langchain_core.tools import tool

from common.llm import get_llm

# ---------------------------------------------------------------------------
# Expanded knowledge base (law + tax + compliance entries)
# ---------------------------------------------------------------------------

LEGAL_KNOWLEDGE = [
    {
        "id": "nda_breach",
        "keywords": ["nda", "non-disclosure", "confidential", "trade secret", "breach"],
        "text": (
            "NDA breaches trigger contractual and statutory liability. Under the DTSA "
            "(18 U.S.C. § 1836): injunctive relief, actual damages + unjust enrichment, "
            "exemplary damages up to 2x for willful misappropriation, and attorney's fees. "
            "Criminal prosecution possible under Economic Espionage Act (18 U.S.C. § 1832)."
        ),
    },
    {
        "id": "contract_remedies",
        "keywords": ["breach", "contract", "remedies", "damages", "ucc"],
        "text": (
            "UCC Article 2 remedies: expectation damages, consequential damages (Hadley v. "
            "Baxendale), specific performance for unique goods, cover damages. Statute of "
            "limitations: 4 years (UCC § 2-725)."
        ),
    },
    {
        "id": "tax_evasion",
        "keywords": ["tax", "evasion", "irs", "penalty", "fraud", "revenue"],
        "text": (
            "Tax evasion (26 U.S.C. § 7201): felony with up to $250K fine and 5 years prison. "
            "Civil fraud penalty: 75% of underpayment (IRC § 6663). Failure to file: up to "
            "$25K fine and 1 year prison. IRS can assess back taxes + interest going back 6 years "
            "(unlimited for fraud). Officers may be personally liable as 'responsible persons'."
        ),
    },
    {
        "id": "offshore_tax",
        "keywords": ["offshore", "overseas", "foreign", "tax", "fbar", "fatca"],
        "text": (
            "Unreported overseas income: FBAR penalties up to $100K or 50% of account balance "
            "per violation. FATCA non-compliance: 30% withholding on US-source payments. "
            "Willful violations may trigger criminal prosecution. Voluntary Disclosure Program "
            "may reduce penalties."
        ),
    },
    {
        "id": "data_privacy",
        "keywords": ["data", "privacy", "user", "consent", "gdpr", "ccpa", "sharing"],
        "text": (
            "Sharing user data without consent violates: CCPA (fines up to $7,500 per intentional "
            "violation), GDPR (fines up to 4% of global revenue or EUR 20M), FTC Act Section 5 "
            "(unfair/deceptive practices). Class action lawsuits under state privacy laws. "
            "Individual right of action under CCPA for data breaches ($100-$750 per consumer)."
        ),
    },
    {
        "id": "sox_compliance",
        "keywords": ["sox", "sarbanes", "compliance", "sec", "financial", "reporting"],
        "text": (
            "SOX violations: CEO/CFO certification of false financials — up to $5M fine and "
            "20 years prison (§ 906). Destruction of records — up to 20 years (§ 802). "
            "Whistleblower retaliation — up to 10 years (§ 1107). SEC can bar individuals "
            "from serving as officers or directors."
        ),
    },
]


# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------

@tool
def search_legal_database(query: str) -> str:
    """Search the legal knowledge base for relevant statutes, case law, and legal principles.

    Args:
        query: Natural language search query about a legal topic.
    """
    query_words = set(query.lower().split())
    scored = []
    for entry in LEGAL_KNOWLEDGE:
        overlap = len(query_words & set(entry["keywords"]))
        if overlap > 0:
            scored.append((overlap, entry))
    scored.sort(key=lambda x: x[0], reverse=True)
    top = scored[:2]
    if not top:
        return "No relevant legal sources found."
    return "\n\n".join(f"[{e['id']}] {e['text']}" for _, e in top)


@tool
def calculate_penalty(violation_type: str, severity: str, annual_revenue: float) -> str:
    """Calculate estimated legal penalties based on violation type, severity, and company revenue.

    Args:
        violation_type: Type of violation (e.g., 'tax_evasion', 'data_privacy', 'contract_breach').
        severity: Severity level ('low', 'medium', 'high').
        annual_revenue: Company's annual revenue in USD.
    """
    severity_multipliers = {"low": 0.01, "medium": 0.05, "high": 0.10}
    multiplier = severity_multipliers.get(severity.lower(), 0.05)

    base_penalty = annual_revenue * multiplier

    type_lower = violation_type.lower()
    if "tax" in type_lower:
        extra = "Plus potential criminal charges (up to 5 years) and 75% civil fraud penalty."
    elif "privacy" in type_lower or "data" in type_lower:
        extra = "Plus GDPR fines up to 4% of global revenue and class action exposure."
    elif "contract" in type_lower:
        extra = "Plus consequential damages, attorney's fees, and possible injunction."
    else:
        extra = "Additional regulatory sanctions may apply."

    return (
        f"Penalty Estimate for {violation_type} ({severity} severity):\n"
        f"  Base penalty: ${base_penalty:,.2f}\n"
        f"  Revenue basis: ${annual_revenue:,.2f}\n"
        f"  {extra}"
    )


@tool
def check_compliance_requirements(industry: str, company_size: str) -> str:
    """Check which regulatory compliance frameworks apply to a company.

    Args:
        industry: The company's industry (e.g., 'technology', 'finance', 'healthcare').
        company_size: Company size ('startup', 'mid-size', 'enterprise').
    """
    frameworks = {
        "technology": ["CCPA/CPRA", "GDPR (if EU users)", "FTC Act Section 5", "SOC 2"],
        "finance": ["SOX", "BSA/AML", "Dodd-Frank", "SEC Regulations", "FCPA"],
        "healthcare": ["HIPAA", "HITECH Act", "FTC Health Breach Notification", "AKS"],
    }

    size_extras = {
        "startup": "Consider: SOC 2 Type II for investor confidence.",
        "mid-size": "Consider: dedicated compliance officer and annual audits.",
        "enterprise": "Required: full compliance program, board oversight, whistleblower hotline.",
    }

    industry_lower = industry.lower()
    applicable = frameworks.get(industry_lower, ["FTC Act Section 5", "State consumer protection laws"])
    size_note = size_extras.get(company_size.lower(), "")

    return (
        f"Applicable frameworks for {industry} ({company_size}):\n"
        f"  {', '.join(applicable)}\n"
        f"  {size_note}"
    )


@tool
def search_case_law(keywords: str) -> str:
    """Tìm kiếm án lệ theo từ khóa.
    
    Args:
        keywords: Từ khóa tìm kiếm
    """
    cases = {
        "breach": "Hadley v. Baxendale (1854) - Consequential damages",
        "negligence": "Donoghue v. Stevenson (1932) - Duty of care",
        "contract": "Carlill v. Carbolic Smoke Ball Co (1893) - Unilateral contract",
    }
    for key, case in cases.items():
        if key in keywords.lower():
            return case
    return "Không tìm thấy án lệ phù hợp"

TOOLS = [search_legal_database, calculate_penalty, check_compliance_requirements, search_case_law]

QUESTION = "Hình phạt cho việc vi phạm hợp đồng là gì và có án lệ nào áp dụng không?"

SYSTEM_PROMPT = (
    "Bạn là một trợ lý luật sư xuất sắc người Việt Nam. Bạn có quyền truy cập vào các công cụ tìm kiếm "
    "cơ sở dữ liệu pháp lý (bằng tiếng Anh), tính toán hình phạt, kiểm tra quy định tuân thủ và tìm án lệ.\n\n"
    "QUY TẮC QUAN TRỌNG:\n"
    "1. Do dữ liệu pháp lý được lưu bằng Tiếng Anh, KHI GỌI TOOL BẠN PHẢI DỊCH TỪ KHÓA SANG TIẾNG ANH (VD: thay vì tìm 'vi phạm hợp đồng', hãy tìm 'breach of contract').\n"
    "2. Sau khi có dữ liệu, BẠN PHẢI TRẢ LỜI NGƯỜI DÙNG HOÀN TOÀN BẰNG TIẾNG VIỆT, giải thích cặn kẽ và chuyên nghiệp."
)


async def main():
    from langgraph.prebuilt import create_react_agent

    print("=" * 70)
    print("GIAI ĐOẠN 3: Agent Độc Lập (ReAct Loop)")
    print("=" * 70)
    print()
    print("[Cách hoạt động]")
    print("  1. Một Agent nhận một câu hỏi phức tạp gồm nhiều vế")
    print("  2. Nó tự suy nghĩ xem cần gọi những công cụ nào (Think)")
    print("  3. Nó gọi công cụ (Act)")
    print("  4. Nó quan sát kết quả và quyết định bước tiếp theo (Observe)")
    print("  5. Nó lặp lại quá trình này cho đến khi đủ thông tin trả lời")
    print()
    print(f"Câu hỏi: {QUESTION}")
    print("-" * 70)

    llm = get_llm()
    # LƯU Ý BÀI TẬP 3.2: Đề bài yêu cầu thêm `verbose=True`. Tuy nhiên, do phiên bản
    # thư viện langgraph mới (>= 1.2.0) không còn hỗ trợ tham số `verbose` nữa,
    # chúng ta phải dùng `debug=True` để tránh lỗi TypeError và giữ nguyên tác dụng in log.
    graph = create_react_agent(model=llm, tools=TOOLS, prompt=SYSTEM_PROMPT, debug=True)

    inputs = {"messages": [{"role": "user", "content": QUESTION}]}

    step = 0
    async for chunk in graph.astream(inputs, stream_mode="updates"):
        for node_name, update in chunk.items():
            step += 1
            messages = update.get("messages", [])
            for msg in messages:
                if hasattr(msg, "tool_calls") and msg.tool_calls:
                    print(f"\n[Bước {step}] SUY NGHĨ + HÀNH ĐỘNG (node: {node_name})")
                    for tc in msg.tool_calls:
                        print(f"  Tool: {tc['name']}")
                        print(f"  Tham số: {tc['args']}")
                elif msg.type == "tool":
                    print(f"\n[Bước {step}] QUAN SÁT KẾT QUẢ (node: {node_name})")
                    content = msg.content
                    print(f"  Kết quả: {content[:300]}{'...' if len(content) > 300 else ''}")
                elif msg.type == "ai" and msg.content:
                    print(f"\n[Bước {step}] CÂU TRẢ LỜI CUỐI CÙNG (node: {node_name})")
                    print("-" * 70)
                    print(msg.content)

    print()
    print("-" * 70)
    print("[Tiến bộ so với Giai đoạn 2]")
    print("  + Tự chủ: Agent tự quyết định gọi tool nào và gọi khi nào")
    print("  + Suy luận nhiều bước: Có thể tìm kiếm, tính toán, rồi lại tìm kiếm tiếp")
    print("  + Xử lý câu hỏi phức tạp: Tự chia nhỏ vấn đề ra thành nhiều nhiệm vụ")
    print()
    print("[Hạn chế của Giai đoạn 3]")
    print("  - Độc diễn: Chờ một LLM duy nhất xử lý mọi lĩnh vực (luật, thuế, tuân thủ)")
    print("  - Không có chuyên môn hóa: Dùng chung một System Prompt cho mọi vấn đề")
    print("  - Nút thắt cổ chai: Các công cụ được gọi tuần tự, không có tính song song")
    print()
    print("Tiếp theo: Giai đoạn 4 sẽ chia nhỏ hệ thống thành các Agents chuyên biệt làm việc song song.")
    print("=" * 70)


if __name__ == "__main__":
    load_dotenv()
    asyncio.run(main())