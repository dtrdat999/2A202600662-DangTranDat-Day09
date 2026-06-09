# Bài Tập Thực Hành Đa Tác Vụ (Multi-Agent) với MCP-A2A

**Thông tin học viên:**
- **Họ và tên:** Đặng Trần Đạt
- **Mã học viên:** 2A202600662
- **Bài tập:** Day9_Multi-Agent_MCP-A2A

## Tổng Quan Dự Án
Đây là kho lưu trữ bài nộp cho Codelab Day 9, thuộc chuyên đề xây dựng hệ thống Trí tuệ nhân tạo Đa tác vụ (Multi-Agent Legal Advisory) thông qua giao thức A2A (Agent-to-Agent) của Google kết hợp cùng LangGraph & LangChain.

### Các Yêu Cầu Đã Hoàn Thành (Core Requirements)
- **Lý thuyết:** Đã trả lời toàn bộ các câu hỏi lý thuyết của Codelab (Phần 1, 2, 5, 6) trong file `answers.md`.
- **Thực hành Kiến trúc Phân tán (A2A):** Đã triển khai, chỉnh sửa logic và test thành công mô hình Multi-Agent độc lập (Customer, Law, Tax, Compliance, Privacy). Cập nhật `start_all.sh` và `start_all.ps1` để gọi đầy đủ các sub-agents.
- **Hoàn thiện các bài tập nhỏ (Exercises):** Đã xử lý toàn bộ các mục `TODO` trong thư mục `exercises/` (gồm `exercise_2_tools.py` và `exercise_4_multiagent.py`) đảm bảo Graph routing và Tool mapping chính xác tuyệt đối.
- **Giao diện Web UI:** Xây dựng một giao diện Frontend nâng cao chuẩn **Premium Glassmorphism** (Giao diện Kính mờ hiện đại) có khả năng trực quan hóa cấu trúc đồ thị (Topology) của LangGraph và lưu trạng thái phiên chat.

### Bài Tập Cộng Điểm & Nâng Cao (Extra Challenges)
1. **Phân tích Latency (Bài tập cộng điểm):** Tính toán thời gian phản hồi thực tế (19.76s) và đề xuất 3 giải pháp tối ưu hệ thống mang tính thực tiễn cao (Pass-through bypass, Streaming SSE, Mini-Model Router).
2. **Challenge 1 (Memory):** Nâng cấp trạng thái (`LegalState`) và sử dụng checkpointer `MemorySaver` để hệ thống lưu giữ Context hội thoại, quản lý lịch sử thông minh theo từng `thread_id`.
3. **Challenge 2 (Authentication):** Triển khai API Key Authentication (Middleware) kiểm duyệt mọi luồng giao tiếp giữa các Agents, ngăn chặn truy cập A2A trái phép từ bên ngoài.
4. **Challenge 3 (Retry Logic):** Bổ sung thuật toán Exponential Backoff Retry trực tiếp vào tầng HTTP Client (`a2a_client.py`), giúp hệ thống tự động giãn cách thời gian gọi lại khi một Sub-Agent bị sập, tăng tính Fault-Tolerance chuẩn Production.

---

## Hướng Dẫn Chạy Cục Bộ (Getting Started)

### 1. Cấu hình môi trường
```bash
# Cài đặt các thư viện cần thiết bằng uv
uv sync

# Copy file .env.example sang .env
cp .env.example .env

# Sửa file .env, điền OPENROUTER_API_KEY (Và các biến A2A_API_KEY nếu có)
```

### 2. Khởi động Backend (Các Agents)
Bạn có thể chọn 1 trong 2 cấu trúc để chạy tùy thuộc vào mục đích test:

- **Option 1 (Stage 4 - In-Process / Cắm Web UI):** Chạy toàn bộ luồng agents trong 1 process chung và phục vụ qua một cổng duy nhất cho Frontend.
  ```bash
  uv run uvicorn api:app --port 8000
  ```
- **Option 2 (Stage 5 - Distributed A2A):** Chạy 5 Agents trên 5 Port độc lập, giao tiếp với nhau qua HTTP và tra cứu bằng Registry (Phục vụ Terminal Client).
  ```bash
  ./start_all.sh
  # Hoặc trên Windows:
  ./start_all.ps1

  # Sau khi khởi động xong 6 Terminal, chạy kịch bản ở terminal chính:
  uv run python test_client.py
  
  # (Tùy chọn) Chạy kịch bản lấy điểm cộng Latency Optimization (Bypass Customer Agent):
  uv run python test_client_optimized.py
  ```

### 3. Khởi động Frontend (Web UI)
Nếu đang dùng Option 1 (Stage 4), bạn có thể bật Server tĩnh của Frontend để chiêm ngưỡng giao diện cao cấp:
```bash
npm run dev
```
Sau đó truy cập link (ví dụ: http://localhost:5173 hoặc 3000) trên trình duyệt để trải nghiệm tính năng trò chuyện có bộ nhớ (Memory) và hiển thị Sơ đồ Graph thời gian thực.

---
