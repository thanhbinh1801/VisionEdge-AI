---
artifact: TASK-PACKET.md
version: "1.1"
owner: main-agent
status: ready
updated_at: "2026-08-27T20:19:30+07:00"
task_id: TASK-031
packet_revision: 2
supersedes: .delivery/tasks/TASK-031/packet-history/TASK-PACKET.r1.md
depends_on: [MASTER-PLAN.md]
---

# TASK-031 CR-007 Backend Detection Threshold, Class Mapping và Zone Evaluator

- Task ID: TASK-031
- Task type: implementation
- Scope: feature
- Module: ai-vision-pipeline
- Capability: backend-implementation
- Linked requirements: REQ-002, REQ-004, REQ-009, CR-007
- Dependencies: TASK-030, TASK-017
- Write scope: .delivery/tasks/TASK-031/
- Inputs: .delivery/REQUIREMENTS.md, .delivery/ARCHITECTURE.md, .delivery/ADR/ADR-002-point-in-polygon-zone-evaluation.md, .delivery/API-CONTRACT.md, backend/app/services/vision_pipeline.py, backend/app/services/video_stream.py, backend/app/services/area_metadata.py, backend/app/api/v1/events.py
- Expected outputs: backend area detection runtime updates, backend tests, .delivery/tasks/TASK-031/TASK-RESULT.md
- Completion gate: Area Monitoring dùng YOLOv11s finetune, inference threshold thấp và application/per-class threshold tách biệt; class mapping giữ `raw_class`/`canonical_class`; zone evaluation dùng bottom-center/footprint overlap/container overlap ratio; MJPEG có `show_static_containers`; metadata giữ backward compatibility.
- Approval policy: Người sở hữu dự án (project owner) là người duyệt duy nhất.
- Escalation policy: Dừng lại khi làm vỡ tính tương thích, thay đổi chính sách bảo mật, phát sinh chi phí đáng kể, thực hiện migration phá hủy dữ liệu, mở rộng phạm vi hoặc ảnh hưởng tới công việc đang triển khai/đã hoàn thành.

## Tóm tắt Thực thi (Execution Brief)

### Mục tiêu (Objective)
Triển khai backend CR-007 cho Area Monitoring `BAI-KIEM`: dùng đúng YOLOv11s finetune, tách inference threshold thấp khỏi display/debug threshold và application/per-class event threshold, chuẩn hóa class mapping giữ `raw_class`/`canonical_class`, thay center-only zone evaluation bằng class-aware evaluator, bổ sung `show_static_containers` cho MJPEG debug, publish metadata additive fields theo TASK-030 và giữ nguyên business flow LPR/GATE-01 ngoài regression.

### Tài liệu nguồn làm chuẩn cần đọc (Source-of-truth artifacts to read)
- `.delivery/tasks/TASK-031/TASK-PACKET.md`
- `.delivery/REQUIREMENTS.md`
- `.delivery/ARCHITECTURE.md`
- `.delivery/API-CONTRACT.md`
- `.delivery/ADR/ADR-002-point-in-polygon-zone-evaluation.md`
- `.delivery/changes/CR-007/CHANGE-IMPACT.md`
- `.delivery/tasks/TASK-030/API-CONTRACT.md`
- `.delivery/tasks/TASK-030/TASK-RESULT.md`
- `.delivery/tasks/TASK-017/TASK-RESULT.md`
- `docs/contracts/api/api-schema.json`
- `docs/contracts/api/websocket-events.json`
- `backend/app/services/vision_pipeline.py`
- `backend/app/services/video_stream.py`
- `backend/app/services/area_metadata.py`
- `backend/app/api/v1/events.py`
- Existing backend tests under `backend/tests/`
- Phần `TASK-031 CR-007 Backend Detection Threshold, Class Mapping và Zone Evaluator` trong `.delivery/MASTER-PLAN.md`

### Phạm vi ghi cho phép (Allowed write scope)
- `backend/app/services/vision_pipeline.py`
- `backend/app/services/video_stream.py`
- `backend/app/services/area_metadata.py`
- `backend/app/api/v1/events.py`
- `backend/tests/`
- `.delivery/tasks/TASK-031/TASK-RESULT.md`
- `.delivery/tasks/TASK-031/BUG-NNN.md` nếu phát hiện lỗi/blocker liên quan trực tiếp

### Phạm vi cấm (Forbidden scope)
- Không sửa frontend trong TASK-031.
- Không sửa `.delivery/MASTER-PLAN.md`, requirements, architecture, ADR, aggregate API contract hoặc JSON schema.
- Không sửa database schema/migration hoặc persistence model để thêm tracking.
- Không triển khai ByteTrack/BoT-SORT đầy đủ; chỉ giữ/trả `track_id` nếu runtime đã có.
- Không thay đổi business flow LPR/GATE-01, OCR, vehicle tag, gate event semantics hoặc UI ngoài regression cần thiết.
- Không thêm dependency runtime đáng kể như Shapely nếu chưa có owner approval và bằng chứng overhead.
- Không tự chuyển `TASK-RESULT.md` hoặc artifact thành `approved` trước review.

### Tiêu chí nghiệm thu (Acceptance criteria)
- Area Monitoring `BAI-KIEM` dùng cấu hình YOLOv11s finetune hiện hành, không âm thầm fallback sai model nếu không ghi rõ lỗi/deviation.
- Inference threshold thấp hơn hoặc độc lập với display/debug threshold và application/per-class event threshold.
- `/api/v1/events/video-feed` nhận `show_static_containers`; mặc định không làm rối stream, nhưng debug có thể bật bbox `container`/`shipping_container`.
- `conf_threshold` của `/video-feed` chỉ là display/debug threshold, không tự kích hoạt event, audio, popup hoặc Telegram.
- Class mapping giữ được `raw_class`, chuẩn hóa `canonical_class`, không ép lớp lạ thành `person`.
- Zone evaluation production dùng method theo class: `bottom_center`, `footprint_overlap`, `bbox_overlap_ratio`; `center_point_fallback` chỉ là fallback tương thích/diagnostic.
- `AREA_FRAME_METADATA` giữ backward compatibility với TASK-016 và bổ sung optional fields theo TASK-030: `raw_class`, `canonical_class`, `bbox_xyxy_norm`, `zone_eval_method`, `zone_overlap_ratio`, `detection_frame_id`, `track_id`.
- Event/alert lane chỉ nhận object đã qua application/per-class threshold, class-aware zone evaluation, stability ngắn và cooldown/dedup hiện hữu.
- Regression LPR/GATE-01 không đổi ngoài bằng chứng test.
- `TASK-RESULT.md` ghi đủ inputs used, outputs produced, validation evidence, deviations, blockers và scope change requests.

### Các trường hợp ngoại lệ / rủi ro (Edge cases / risks)
- `/api/v1/events/video-feed` hiện đang default `conf_threshold=0.50`; cần đổi theo contract nhưng tránh làm tăng alert giả vì đây chỉ là display threshold.
- `area_metadata.py` hiện chưa publish debug additive fields; cần thêm mà không bỏ `display_name`, `bbox`, `center_point`, `zone_hits`.
- `vision_pipeline.py` hiện còn dùng `evaluate_bbox_center_in_zone()` cho mọi class; cần thay production path nhưng giữ helper cũ cho fallback/test tương thích.
- Container/static container mặc định có thể ẩn khỏi MJPEG nhưng không được bị lọc khỏi inference/metadata/event evaluation.
- YOLOv11s finetune có thể trả `shipping_container` hoặc `container_truck`; cần giữ raw class và canonical mapping nhất quán với API aggregate.
- Nếu model hoặc video source không sẵn sàng, task implementation phải trả lỗi rõ ràng hoặc ghi blocker, không tạo fallback âm thầm làm sai CR-007.

### Lệnh xác minh hoặc phương pháp kiểm tra (Verification commands or validation method)
- Lệnh xác minh theo MASTER-PLAN: `python -m pytest backend/tests/test_ai_engine.py backend/tests/test_video_frame_api.py backend/tests/test_area_metadata_runtime.py backend/tests/test_live_detections_event.py -q`.
- Validator chuyên biệt nên chạy sau implementation: `python D:\Skill\SKILLs\implement-backend\scripts\validate_backend_implementation.py D:\Hilab\Project34 TASK-031`.
- Compile/check tối thiểu: `python -m compileall -q backend/app/services/vision_pipeline.py backend/app/services/video_stream.py backend/app/services/area_metadata.py backend/app/api/v1/events.py backend/tests`.
- Nếu test hiện hữu cần bổ sung, ưu tiên test scoped cho per-class threshold filtering, `show_static_containers`, class-aware zone evaluation, metadata additive compatibility và LPR/GATE-01 regression.

### Điều kiện leo thang (Escalation conditions)
- Dừng lại và báo cáo trong `TASK-RESULT.md` nếu cần sửa approved contracts/baseline, thêm dependency lớn, thay đổi DB schema, mở rộng tracking persistence, đổi LPR/GATE-01 behavior, hoặc nếu thiếu model/video/test fixture khiến không thể chứng minh completion gate.

### Định dạng TASK-RESULT kỳ vọng (Expected TASK-RESULT format)
- Task ID: TASK-031
- Outcome: completed | blocked
- Inputs used: Danh sách các tệp/artifact đã đọc.
- Outputs produced: Danh sách file backend/tests và `.delivery/tasks/TASK-031/TASK-RESULT.md`.
- Validation evidence: Exact commands, exit codes và kết quả thực thi.
- Deviations: none hoặc sai lệch phát hiện được.
- Blockers: none hoặc mô tả điểm chặn.
- Scope change requests: none hoặc yêu cầu thay đổi phạm vi.

### Skill/capability cần chạy (Skill/capability to run)
- Capability: backend-implementation
- Next skill: `$implement-backend`
