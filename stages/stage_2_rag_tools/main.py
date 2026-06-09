"""Stage 2: LLM + RAG / Tools

Adds retrieval-augmented generation and tool use to ground LLM responses
in external data. The LLM can now search a legal knowledge base and
calculate damages — but the orchestration is manual (one tool-call loop).
"""

import asyncio
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from dotenv import load_dotenv
from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage
from langchain_core.tools import tool

from common.llm import get_llm

# ---------------------------------------------------------------------------
# Simulated legal knowledge base (in production, this would be a vector store)
# ---------------------------------------------------------------------------

LEGAL_KNOWLEDGE = [
    {
        "id": "ucc_breach",
        "keywords": ["breach", "contract", "remedies", "damages", "ucc"],
        "text": (
            "Under the Uniform Commercial Code (UCC) Article 2, remedies for breach of contract "
            "include: (1) expectation damages — placing the non-breaching party in the position "
            "they would have been in had the contract been performed; (2) consequential damages "
            "for foreseeable losses (Hadley v. Baxendale, 1854); (3) specific performance when "
            "the subject matter is unique; (4) cover damages — the cost of obtaining substitute "
            "performance. The statute of limitations is typically 4 years (UCC § 2-725)."
        ),
    },
    {
        "id": "nda_trade_secret",
        "keywords": ["nda", "non-disclosure", "confidential", "trade secret", "agreement"],
        "text": (
            "NDA breaches may trigger both contractual and statutory liability. Under the Defend "
            "Trade Secrets Act (DTSA, 18 U.S.C. § 1836), misappropriation of trade secrets can "
            "result in: (1) injunctive relief; (2) actual damages plus unjust enrichment; "
            "(3) exemplary damages up to 2x actual damages for willful misappropriation; "
            "(4) attorney's fees. State Uniform Trade Secrets Act (UTSA) versions provide "
            "additional remedies. Criminal prosecution is possible under the Economic Espionage "
            "Act (18 U.S.C. § 1832) with penalties up to $5M for individuals."
        ),
    },
    {
        "id": "dtsa_details",
        "keywords": ["dtsa", "federal", "trade secret", "defend", "statute"],
        "text": (
            "The Defend Trade Secrets Act (2016) created a federal private cause of action for "
            "trade secret misappropriation. Key provisions: (1) ex parte seizure orders in "
            "extraordinary circumstances; (2) 3-year statute of limitations; (3) immunity for "
            "whistleblower disclosures to government officials; (4) employers must notify "
            "employees of whistleblower immunity in any NDA or employment agreement."
        ),
    },
    {
        "id": "liquidated_damages",
        "keywords": ["liquidated", "damages", "penalty", "clause", "contract", "nda"],
        "text": (
            "Liquidated damages clauses in NDAs are enforceable if: (1) actual damages would be "
            "difficult to calculate at the time of contracting; (2) the stipulated amount is a "
            "reasonable estimate of anticipated harm. Courts will void clauses that function as "
            "penalties (Restatement (Second) of Contracts § 356). Typical NDA liquidated damages "
            "range from $10,000 to $500,000 depending on the nature of the confidential information."
        ),
    },
    {
        "id": "injunctive_relief",
        "keywords": ["injunction", "restraining", "order", "equitable", "nda", "breach"],
        "text": (
            "Courts routinely grant temporary restraining orders (TROs) and preliminary injunctions "
            "for NDA breaches because: (1) confidential information, once disclosed, cannot be "
            "'un-disclosed' — making monetary damages inadequate; (2) irreparable harm is presumed "
            "for trade secret misappropriation in many jurisdictions. The movant must show "
            "likelihood of success on the merits, irreparable harm, balance of equities, and "
            "public interest (Winter v. Natural Resources Defense Council, 2008)."
        ),
    },
    {
        "id": "labor_law",
        "keywords": ["lao", "động", "sa", "thải", "hợp", "đồng", "báo", "trước"],
        "text": (
            "Theo Bộ luật Lao động Việt Nam 2019, người sử dụng lao động có thể "
            "đơn phương chấm dứt hợp đồng trong các trường hợp: (1) người lao động "
            "thường xuyên không hoàn thành công việc; (2) bị ốm đau, tai nạn đã điều trị "
            "12 tháng chưa khỏi; (3) thiên tai, hỏa hoạn; (4) người lao động đủ tuổi nghỉ hưu."
        ),
    },
]


# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------

@tool
def search_legal_database(query: str) -> str:
    """Search the legal knowledge base for relevant statutes, case law, and legal principles."""
    query_words = set(query.lower().split())
    scored = []
    for entry in LEGAL_KNOWLEDGE:
        overlap = len(query_words & set(entry["keywords"]))
        if overlap > 0:
            scored.append((overlap, entry))
    scored.sort(key=lambda x: x[0], reverse=True)
    top = scored[:2]
    if not top:
        return "No relevant legal sources found for this query."
    results = []
    for _, entry in top:
        results.append(f"[{entry['id']}] {entry['text']}")
    return "\n\n".join(results)


@tool
def calculate_damages(breach_type: str, contract_value: float) -> str:
    """Calculate estimated damages for a contract breach based on type and contract value."""
    breach_type_lower = breach_type.lower()
    if "willful" in breach_type_lower or "intentional" in breach_type_lower:
        multiplier = 2.0
        label = "Willful/intentional breach (2x multiplier under DTSA)"
    elif "negligent" in breach_type_lower:
        multiplier = 1.0
        label = "Negligent breach (1x actual damages)"
    else:
        multiplier = 1.5
        label = "Standard breach (1.5x estimated multiplier)"

    base_damages = contract_value * multiplier
    attorney_fees = contract_value * 0.15
    total = base_damages + attorney_fees

    return (
        f"Damage Estimate:\n"
        f"  Breach type: {label}\n"
        f"  Contract value: ${contract_value:,.2f}\n"
        f"  Estimated damages: ${base_damages:,.2f}\n"
        f"  Attorney's fees (~15%): ${attorney_fees:,.2f}\n"
        f"  Total estimated exposure: ${total:,.2f}"
    )


@tool
def check_statute_of_limitations(case_type: str) -> str:
    """Kiểm tra thời hiệu khởi kiện theo loại vụ án.
    
    Args:
        case_type: Loại vụ án (contract, tort, property)
    """
    limits = {
        "contract": "4 năm (UCC § 2-725)",
        "tort": "2-3 năm tùy bang",
        "property": "5 năm",
    }
    return limits.get(case_type.lower(), "Không xác định")


TOOLS = [search_legal_database, calculate_damages, check_statute_of_limitations]

QUESTION = "Hậu quả pháp lý là gì nếu công ty vi phạm thỏa thuận bảo mật thông tin (NDA)?"

async def main():
    print("=" * 70)
    print("GIAI ĐOẠN 2: LLM kết hợp RAG và Tools")
    print("=" * 70)
    print()
    print("[Cách hoạt động]")
    print("  1. LLM được cung cấp các công cụ (search_legal_database, calculate_damages)")
    print("  2. LLM tự quyết định gọi công cụ nào và truyền tham số gì")
    print("  3. Code Python sẽ chạy công cụ đó và trả kết quả về cho LLM")
    print("  4. LLM dựa vào dữ liệu đó để viết câu trả lời cuối cùng")
    print()
    print(f"Câu hỏi: {QUESTION}")
    print("-" * 70)

    llm = get_llm()
    llm_with_tools = llm.bind_tools(TOOLS)
    tool_map = {t.name: t for t in TOOLS}

    messages = [
        SystemMessage(
            content=(
                "Bạn là một chuyên gia pháp lý có quyền truy cập vào cơ sở dữ liệu pháp lý (tiếng Anh) "
                "và công cụ tính toán bồi thường. \n"
                "QUY TẮC QUAN TRỌNG: Tool tìm luật chỉ nhận từ khóa tiếng Anh, hãy tự dịch từ khóa sang tiếng Anh để tra cứu. "
                "BẠN PHẢI TRẢ LỜI NGƯỜI DÙNG HOÀN TOÀN BẰNG TIẾNG VIỆT, giữ độ dài dưới 400 chữ."
            )
        ),
        HumanMessage(content=QUESTION),
    ]

    # --- Step 1: LLM decides which tools to call ---
    print("\n>>> Bước 1: Hỏi LLM (đã gắn kèm tools)...\n")
    response = await llm_with_tools.ainvoke(messages)
    messages.append(response)

    if not response.tool_calls:
        print("LLM quyết định không dùng tool. Câu trả lời trực tiếp:")
        print(response.content)
        return

    # --- Step 2: Execute tool calls ---
    print(f">>> Bước 2: LLM yêu cầu gọi {len(response.tool_calls)} tool(s):\n")
    for tc in response.tool_calls:
        print(f"  Tool: {tc['name']}")
        print(f"  Tham số: {tc['args']}")

        tool_fn = tool_map[tc["name"]]
        result = await tool_fn.ainvoke(tc["args"])
        print(f"  Kết quả: {result[:200]}{'...' if len(result) > 200 else ''}")
        print()

        messages.append(ToolMessage(content=result, tool_call_id=tc["id"]))

    # --- Step 3: LLM generates final grounded answer ---
    print(">>> Bước 3: LLM đang tạo câu trả lời cuối cùng dựa trên kết quả tool...\n")
    final_response = await llm_with_tools.ainvoke(messages)
    print(final_response.content)

    print()
    print("-" * 70)
    print("[Tiến bộ so với Giai đoạn 1]")
    print("  + Có căn cứ: Các câu trả lời trích dẫn các luật cụ thể (DTSA, UCC, v.v.)")
    print("  + Có Tools: Có thể tìm kiếm cơ sở dữ liệu và tính toán thiệt hại")
    print("  + Chính xác hơn: RAG giúp giảm nguy cơ ảo giác (hallucination)")
    print()
    print("[Hạn chế của Giai đoạn 2]")
    print("  - Điều phối thủ công: Chúng ta phải tự viết vòng lặp gọi tool bằng code Python")
    print("  - Chỉ 1 lượt: LLM chỉ được phép gọi tool đúng 1 lần")
    print("  - Không có vòng lặp tư duy: LLM không thể quyết định tìm kiếm lại nếu lần đầu tìm không ra kết quả")
    print()
    print("Tiếp theo: Giai đoạn 3 sẽ gói hệ thống này vào một Agent tự động (ReAct Loop).")
    print("=" * 70)


if __name__ == "__main__":
    load_dotenv()
    asyncio.run(main())