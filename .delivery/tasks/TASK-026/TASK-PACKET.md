---
artifact: TASK-PACKET.md
version: "1.1"
owner: main-agent
status: ready
updated_at: "2026-08-24T22:37:17+07:00"
task_id: TASK-026
packet_revision: 1
supersedes: none
depends_on: [MASTER-PLAN.md]
---

# TASK-026 Thiết kế Contract Event/Alert Evidence cho Telegram CR-005

- Task ID: TASK-026
- Task type: feature-design
- Scope: feature
- Module: api-gateway
- Capability: api-design
- Linked requirements: REQ-002, REQ-003, REQ-004, REQ-008, REQ-009, CR-005
- Dependencies: TASK-016
- Write scope: .delivery/tasks/TASK-026/
- Inputs: .delivery/REQUIREMENTS.md, .delivery/DOMAIN-MODEL.md, .delivery/changes/CR-005/CHANGE-IMPACT.md, .delivery/API-CONTRACT.md, docs/contracts/api/api-schema.json, docs/contracts/api/websocket-events.json
- Expected outputs: .delivery/tasks/TASK-026/API-CONTRACT.md, .delivery/tasks/TASK-026/TASK-RESULT.md
- Completion gate: Thiết kế xong contract nghiệp vụ/API cho event vi phạm khu vực dùng chung giữa Event Feed, AI Assistant và Telegram, gồm thời gian vi phạm đúng, camera, zone, loại đối tượng, lý do vi phạm, clip 10s và trạng thái lỗi gửi Telegram mà chưa sửa production code.
- Approval policy: Người sở hữu dự án (project owner) là người duyệt duy nhất.
- Escalation policy: Dừng lại khi làm vỡ tính tương thích, thay đổi chính sách bảo mật, phát sinh chi phí đáng kể, thực hiện migration phá hủy dữ liệu, mở rộng phạm vi hoặc ảnh hưởng tới công việc đang triển khai/đã hoàn thành.

## Tóm tắt Thực thi (Execution Brief)

### Mục tiêu (Objective)
Thiết kế contract API tính năng và bằng chứng sự kiện (event evidence contract) cho CR-005 phục vụ cảnh báo vi phạm an ninh khu vực dùng chung cho Event Feed, AI Assistant và Telegram dispatcher. Contract phải chuẩn hóa chính xác mốc thời gian vi phạm, camera ID/tên, zone ID/tên, loại đối tượng, lý do vi phạm, dữ liệu video clip chứng cứ 10s MP4, cùng các trường trạng thái/lỗi gửi Telegram mà không sửa code production.

### Tài liệu nguồn làm chuẩn cần đọc (Source-of-truth artifacts to read)
- `.delivery/tasks/TASK-026/TASK-PACKET.md`
- `.delivery/tasks/TASK-026/TASK-RESULT.md` (nếu có)
- `.delivery/tasks/TASK-026/API-CONTRACT.md` (nếu có)
- `.delivery/REQUIREMENTS.md`
- `.delivery/DOMAIN-MODEL.md`
- `.delivery/changes/CR-005/CHANGE-IMPACT.md`
- `.delivery/API-CONTRACT.md`
- `docs/contracts/api/api-schema.json`
- `docs/contracts/api/websocket-events.json`
- Phần `TASK-026 Thiết kế Contract Event/Alert Evidence cho Telegram CR-005` trong `.delivery/MASTER-PLAN.md`

### Phạm vi ghi cho phép (Allowed write scope)
- Phạm vi task lịch sử/lên kế hoạch: `.delivery/tasks/TASK-026/`.
- Phạm vi chuẩn hóa packet hiện tại: chỉ `.delivery/tasks/TASK-026/TASK-PACKET.md`.

### Phạm vi cấm (Forbidden scope)
- Không chỉnh sửa `.delivery/MASTER-PLAN.md`, `.delivery/API-CONTRACT.md`, `docs/contracts/api/*`, code production backend/frontend, `.delivery/tasks/TASK-026/TASK-RESULT.md`, `.delivery/tasks/TASK-026/API-CONTRACT.md`, các artifact báo lỗi/báo cáo test, hoặc các artifact giao hàng không liên quan trong quá trình chuẩn hóa packet.

### Tiêu chí nghiệm thu (Acceptance criteria)
- Packet đảm bảo tính nhất quán với task id `TASK-026`, capability `api-design`, dependency `TASK-016`, các yêu cầu liên kết, đầu ra kỳ vọng và completion gate.
- API contract xác định đầy đủ data model, JSON schema, các trường payload cho bằng chứng vi phạm (mốc thời gian, camera, zone, loại đối tượng, lý do, đường dẫn/file video clip 10s), model trạng thái/lỗi cảnh báo Telegram, và các mở rộng payload event WebSocket/REST.
- Thiết kế chỉ giới hạn trong phạm vi các artifact feature design và không tự ý đưa thay đổi vào hợp đồng toàn cục trong bước này.

### Các trường hợp ngoại lệ / rủi ro (Edge cases / risks)
- Mốc thời gian sự kiện vi phạm phải là thời gian phát hiện thực tế, không phải thời gian phản hồi/phát tin nhắn của Telegram API.
- Lỗi gửi tin nhắn Telegram (ví dụ: rate limit, lỗi bot token, timeout mạng) phải được ghi nhận vào trạng thái alert mà không làm thất bại việc lưu trữ event hay thông báo WebSocket trên UI.
- URL clip truyền thông phải trỏ đến file MP4 bằng chứng 10s hợp lệ do backend tạo ra.
- Khử trùng lặp đa kênh (Multi-channel deduplication): thời gian hồi (cooldown) sự kiện phải ngăn chặn gửi lặp lại các cảnh báo Telegram cho cùng một vi phạm đang tiếp diễn trong cửa sổ cooldown.

### Lệnh xác minh hoặc phương pháp kiểm tra (Verification commands or validation method)
- Lệnh xác minh được lập kế hoạch từ MASTER-PLAN: `python D:\Skill\SKILLs\design-api\scripts\validate_api_design.py D:\Hilab\Project34 TASK-026 --scope feature`.
- Xác minh tính hợp lệ (parseability) của các đoạn mã API draft/schema cục bộ khi có mặt.

### Điều kiện leo thang (Escalation conditions)
- Leo thang khi làm vỡ tính tương thích, thay đổi chính sách bảo mật, phát sinh chi phí đáng kể, có nguy cơ migration phá hủy dữ liệu, mở rộng phạm vi công việc, hoặc ảnh hưởng tới các công việc đang thực hiện/đã hoàn thành.

### Định dạng TASK-RESULT kỳ vọng (Expected TASK-RESULT format)
- Trạng thái / Kết quả (Status/outcome).
- Đầu vào đã dùng (Inputs used).
- Đầu ra đã tạo (Outputs created).
- Tóm tắt thiết kế API (API design summary).
- Bằng chứng xác minh (Validation evidence).
- Ghi chú tương thích và không tự ý promote (Compatibility and non-promotion notes).
- Rủi ro mở / Các mục chưa chỉ định (Open risks/Not specified items).
- Điểm chặn và yêu cầu thay đổi phạm vi (Blockers and scope-change requests).

### Skill/capability cần chạy (Skill/capability to run)
- `api-design`.
