---
artifact: ADR-001
title: Lựa chọn Kiến trúc Python Monolithic Modular Service với FastAPI
status: approved
owner: Software Architect
updated_at: 2026-08-17T22:39:59+07:00
affected_requirements:
  - REQ-001
  - REQ-002
  - REQ-006
  - REQ-009
---

# ADR-001: Lựa chọn Kiến trúc Python Monolithic Modular Service với FastAPI

## Bối cảnh (Context)
Dự án SentriAI Mini yêu cầu xây dựng ứng dụng giám sát camera tích hợp AI xử lý video realtime, nhận diện biển số (LPR), kiểm tra zone đa giác, lưu clip 10s và hỗ trợ chat AI. Yêu cầu triển khai đơn giản cho bài tập thực tập, dễ chạy local, độ trễ nhỏ hơn 1 giây.

## Các Phương án Cân nhắc (Options Considered)
1. **Microservices (Đa dịch vụ tách rời)**: Tách riêng Stream Service, AI Service, API Gateway, Alert Service.
2. **Monolithic Modular Python Service (FastAPI + OpenCV + PyTorch)**: Đóng gói toàn bộ backend trong một ứng dụng Python đơn khối nhưng chia rõ module (Modules: Ingestion, Pipeline, API, Agent, Alert).
3. **Node.js Gateway + Python AI Worker**: Node.js làm API/UI Server, Python làm AI microservice.

## Quyết định (Decision)
Chọn **Phương án 2: Monolithic Modular Python Service với FastAPI**.

## Lý do chọn (Rationale)
- **Tối ưu hiệu năng I/O & Memory**: Việc giữ luồng OpenCV Video Capture, YOLO Inference và FastAPI Server trong cùng một Process Python giúp chia sẻ Frame Buffer trực tiếp qua In-Memory Queue mà không mất chi phí serialization HTTP/gRPC giữa các microservices.
- **Tốc độ phát triển**: Đơn giản hóa quá trình cài đặt, chỉ cần 1 câu lệnh `uvicorn main:app` hoặc Docker container duy nhất.
- **Tính khả thi cho Intern**: Tránh độ phức tạp không cần thiết về dịch vụ mạng, mã hóa dữ liệu qua lại và quản lý nhiều repository.

## Hệ quả & Đánh đổi (Trade-offs)
- **Ưu điểm**: Cài đặt đơn giản, độ trễ cực thấp, không tốn chi phí giao tiếp mạng inter-service.
- **Hạn chế**: Khó mở rộng ngang (horizontal scaling) lên hàng trăm camera; tuy nhiên hoàn toàn phù hợp với phạm vi 2-5 camera của bài tập demo.
- **Tính đảo ngược (Reversibility)**: Dễ dàng tách các module (`ai-vision-pipeline`, `llm-qa-agent`) thành gRPC Microservices độc lập trong tương lai nhờ phân chia rõ ranh giới module.
