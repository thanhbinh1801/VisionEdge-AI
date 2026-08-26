---
artifact: TASK-PACKET.md
version: "1.0"
owner: main-agent
status: ready
updated_at: "2026-08-25T17:52:58+07:00"
task_id: TASK-030
packet_revision: 1
supersedes: none
depends_on: [MASTER-PLAN.md, TASK-017]
---

# TASK-030 Chẩn đoán BUG-003 — Area Security Dashboard mất luồng MJPEG

- Task ID: TASK-030
- Task type: diagnosis
- Scope: feature
- Module: ai-vision-pipeline
- Capability: bug-diagnosis
- Linked requirements: REQ-002, REQ-004, REQ-009
- Dependencies: TASK-017
- Inputs: ảnh chụp màn hình sản phẩm do chủ dự án cung cấp, `backend/app/api/v1/events.py`, `backend/app/services/frame_extractor.py`, `backend/app/services/video_stream.py`, `backend/app/core/config.py`, `.env`, `backend/tests/test_live_detections.py`, `.delivery/tasks/TASK-017/TASK-RESULT.md`
- Expected outputs: `.delivery/tasks/TASK-030/BUG-DIAGNOSIS.md`, `.delivery/tasks/TASK-030/TASK-RESULT.md`
- Write scope: .delivery/tasks/TASK-030/
- Completion gate: Tái hiện được lỗi một cách tất định, thu hẹp về ca lỗi nhỏ nhất, tách nguyên nhân gốc khỏi triệu chứng, chỉ rõ task sở hữu và phạm vi sửa nhỏ nhất, ghi rõ trạng thái regression test. Không sửa mã sản phẩm.
- Approval policy: The project owner is the sole approver.
- Escalation policy: Stop for breaking compatibility, security posture, material cost, destructive migration, scope expansion, or impacted in-progress/completed work.

## Báo cáo gốc

Chủ dự án quan sát trên sản phẩm đang chạy: khung video của `Area Security Dashboard` (Bãi Kiểm)
hiện `MẤT LUỒNG` + `Không thể tải luồng MJPEG / Thử kết nối lại`, `Metadata: CONNECTING`, panel
snapshot báo `Chưa có object trong frame metadata hiện tại`. Cùng lúc `Gate Dashboard` (GATE-01)
hiển thị video bình thường. Đánh giá mức nghiêm trọng: cao.
