"""Stage 1: Direct LLM Calling

The simplest way to use an LLM — send a message, get a response.
No tools, no memory, no agents. Just a direct API call.

This is stateless: the LLM has no access to external data sources,
cannot look things up, and relies entirely on its training data.
"""

import asyncio
import os
import sys

# Allow running directly: python stages/stage_1_direct_llm/main.py
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from dotenv import load_dotenv
from langchain_core.messages import HumanMessage, SystemMessage

from common.llm import get_llm

QUESTION = "Tôi làm việc cho công ty đã 3 năm nhưng không ký hợp đồng lao động, bây giờ công ty sa thải tôi mà không báo trước có vi phạm luật không?"


async def main():
    print("=" * 70)
    print("GIAI ĐOẠN 1: Gọi trực tiếp LLM (Direct LLM Calling)")
    print("=" * 70)
    print()
    print("[Cách hoạt động]")
    print("  1. Chúng ta gửi câu hỏi + prompt trực tiếp cho LLM")
    print("  2. LLM sẽ trả lời dựa trên những gì nó học được từ trước")
    print("  3. Không có tools, không có kết nối cơ sở dữ liệu")
    print()
    print(f"Question: {QUESTION}")
    print("-" * 70)

    llm = get_llm()

    messages = [
        SystemMessage(
            content=(
                "Bạn là một chuyên gia pháp lý. Hãy phân tích câu hỏi "
                "một cách rõ ràng, ngắn gọn và giữ độ dài dưới 300 chữ."
            )
        ),
        HumanMessage(content=QUESTION),
    ]

    print("\n>>> Đang gọi LLM trực tiếp (không dùng tools, không có RAG)...\n")
    response = await llm.ainvoke(messages)
    print(response.content)

    print()
    print("-" * 70)
    print("[Hạn chế của Giai đoạn 1]")
    print("  - Không có trí nhớ: LLM không nhớ cuộc trò chuyện trước đó")
    print("  - Không có công cụ (Tools): Không thể tìm kiếm dữ liệu thực tế")
    print("  - Lỗi thời: Chỉ biết những gì có trong dữ liệu huấn luyện ban đầu")
    print("  - Không có căn cứ: Không thể trích dẫn luật hoặc án lệ hiện hành")
    print()
    print("Tiếp theo: Giai đoạn 2 sẽ thêm RAG và Tools để cung cấp dữ liệu thực tế cho LLM.")
    print("=" * 70)


if __name__ == "__main__":
    load_dotenv()
    asyncio.run(main())