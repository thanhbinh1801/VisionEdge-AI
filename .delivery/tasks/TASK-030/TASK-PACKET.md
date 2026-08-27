---
artifact: TASK-PACKET.md
version: "1.1"
owner: main-agent
status: ready
updated_at: "2026-08-27T20:09:24+07:00"
task_id: TASK-030
packet_revision: 2
supersedes: .delivery/tasks/TASK-030/packet-history/TASK-PACKET.r1.md
depends_on: [MASTER-PLAN.md]
---

# TASK-030 CR-007 Contract cho Area Detection, BBox Debug và Zone Evaluation

- Task ID: TASK-030
- Task type: feature-design
- Scope: feature
- Module: api-gateway
- Capability: api-design
- Linked requirements: REQ-002, REQ-004, REQ-009, CR-007
- Dependencies: TASK-016
- Write scope: .delivery/tasks/TASK-030/
- Inputs: .delivery/REQUIREMENTS.md, .delivery/ARCHITECTURE.md, .delivery/API-CONTRACT.md, .delivery/changes/CR-007/CHANGE-IMPACT.md, docs/contracts/api/api-schema.json, docs/contracts/api/websocket-events.json
- Expected outputs: .delivery/tasks/TASK-030/API-CONTRACT.md, .delivery/tasks/TASK-030/TASK-RESULT.md
- Completion gate: Contract xác định rõ YOLOv11s finetune cho `BAI-KIEM`, display/debug threshold tách khỏi event/alert threshold, `show_static_containers`, metadata fields additive, class-aware zone evaluation method/ratio và `track_id` optional/future-compatible.
- Approval policy: Người sở hữu dự án (project owner) là người duyệt duy nhất.
- Escalation policy: Dừng lại khi làm vỡ tính tương thích, thay đổi chính sách bảo mật, phát sinh chi phí đáng kể, thực hiện migration phá hủy dữ liệu, mở rộng phạm vi hoặc ảnh hưởng tới công việc đang triển khai/đã hoàn thành.

## Tóm tắt Thực thi (Execution Brief)

### Mục tiêu (Objective)
Thiết kế contract CR-007 cho runtime Area Monitoring tại `BAI-KIEM`: chuẩn hóa YOLOv11s finetune làm model khu vực, tách rõ inference threshold/display-debug threshold khỏi event/alert application threshold, bổ sung query/debug surface `show_static_containers`, định nghĩa metadata additive cho bbox/debug, chốt class-aware zone evaluation theo method/ratio phù hợp từng nhóm đối tượng, và giữ `track_id` optional/future-compatible mà chưa triển khai tracking đầy đủ.

### Tài liệu nguồn làm chuẩn cần đọc (Source-of-truth artifacts to read)
- `.delivery/tasks/TASK-030/TASK-PACKET.md`
- `.delivery/REQUIREMENTS.md`
- `.delivery/ARCHITECTURE.md`
- `.delivery/API-CONTRACT.md`
- `.delivery/ADR/ADR-002-point-in-polygon-zone-evaluation.md`
- `.delivery/changes/CR-007/CHANGE-IMPACT.md`
- `.delivery/tasks/TASK-016/API-CONTRACT.md`
- `.delivery/tasks/TASK-016/TASK-RESULT.md`
- `docs/contracts/api/api-schema.json`
- `docs/contracts/api/websocket-events.json`
- Code/evidence hiện trạng nếu cần đối chiếu contract: `backend/app/api/v1/events.py`, `backend/app/services/vision_pipeline.py`, `backend/app/services/video_stream.py`, `backend/app/services/area_metadata.py`, `frontend/src/services/api.ts`, `frontend/src/pages/AreaSecurityDashboard.tsx`
- Phần `TASK-030 CR-007 Contract cho Area Detection, BBox Debug và Zone Evaluation` trong `.delivery/MASTER-PLAN.md`

### Phạm vi ghi cho phép (Allowed write scope)
- `.delivery/tasks/TASK-030/API-CONTRACT.md`
- `.delivery/tasks/TASK-030/TASK-RESULT.md`

### Phạm vi cấm (Forbidden scope)
- Không chỉnh sửa production code backend/frontend trong task design này.
- Không cập nhật `.delivery/MASTER-PLAN.md`, requirements, architecture, ADR, aggregate `.delivery/API-CONTRACT.md`, hoặc JSON schema toàn cục nếu chưa có bước review/approval riêng.
- Không thay đổi luồng LPR/GATE-01 ngoài việc ghi rõ regression boundary.
- Không triển khai ByteTrack/BoT-SORT, tracking persistence, migration DB, hoặc event dedupe mới trong TASK-030.
- Không tự chuyển trạng thái artifact thành `approved` trước khi được project owner review.

### Tiêu chí nghiệm thu (Acceptance criteria)
- Contract xác định YOLOv11s finetune là model chính cho Area Monitoring `BAI-KIEM` và ghi rõ phạm vi không đổi business flow LPR/GATE-01.
- Contract phân tách ít nhất 2 tầng threshold: inference/display-debug threshold cho metadata/MJPEG và application/per-class event threshold cho event/alert lane.
- Contract định nghĩa query/debug surface cho MJPEG hoặc area feed, gồm `conf_threshold` và `show_static_containers`, với default không làm tăng nhiễu UI vận hành.
- Contract giữ backward compatibility cho metadata hiện có và chỉ bổ sung optional/additive fields như `raw_class`, `canonical_class`, `bbox_xyxy_norm`, `zone_eval_method`, `zone_overlap_ratio`, `detection_frame_id`, và `track_id`.
- Contract định nghĩa class mapping giữa raw model classes và canonical object classes, không làm mất raw class phục vụ debug.
- Contract chốt class-aware zone evaluation: bottom-center cho người/xe máy/xe đạp; footprint hoặc bbox overlap cho xe/xe tải/xe nâng/xe cẩu; overlap ratio riêng cho container/static container.
- Contract mô tả event/alert derivation từ zone evaluation đã qua application threshold, đồng thời khẳng định metadata/debug lane không tự sinh alert.
- Contract ghi rõ `track_id` là optional/future-compatible: trả khi runtime có, chấp nhận `null`/absent khi chưa có tracking, không yêu cầu persistence trong CR-007.
- `TASK-RESULT.md` ghi đủ inputs used, outputs produced, validation evidence, deviations, blockers và scope change requests theo task-result contract.

### Các trường hợp ngoại lệ / rủi ro (Edge cases / risks)
- Baseline hiện có thể còn nhắc YOLOv26/YOLO-World hoặc point-in-polygon center; contract cần ghi rõ CR-007 supersede semantics ở phạm vi feature mà không tự sửa artifact aggregate.
- Field `bbox` hiện có nhiều biểu diễn legacy khác nhau; mọi field mới phải additive để frontend cũ không vỡ.
- Lower debug threshold có thể hiển thị thêm bbox nhiễu nhưng không được làm phát event/alert khi chưa qua application threshold.
- Container/static container mặc định có thể bị ẩn để giảm nhiễu vận hành nhưng phải bật được khi debug model.
- Nếu cần dependency hình học mới như Shapely thì chỉ được nêu là quyết định cần owner duyệt; task design không thêm dependency.
- Tracking đầy đủ là phạm vi tương lai; contract không được khóa downstream vào assumption rằng `track_id` luôn có.

### Lệnh xác minh hoặc phương pháp kiểm tra (Verification commands or validation method)
- Lệnh xác minh theo MASTER-PLAN: `python -m json.tool docs/contracts/api/api-schema.json` và `python -m json.tool docs/contracts/api/websocket-events.json`.
- Lệnh validator chuyên biệt nên chạy sau khi tạo artifact design: `python D:\Skill\SKILLs\design-api\scripts\validate_api_design.py D:\Hilab\Project34 TASK-030 --scope feature`.
- Kiểm tra thủ công contract: đối chiếu `.delivery/tasks/TASK-030/API-CONTRACT.md` với `.delivery/changes/CR-007/CHANGE-IMPACT.md`, `.delivery/tasks/TASK-016/API-CONTRACT.md`, và backward compatibility của `AREA_FRAME_METADATA`.

### Điều kiện leo thang (Escalation conditions)
- Dừng lại và báo cáo trong `TASK-RESULT.md` nếu thiết kế đòi hỏi sửa aggregate baseline chưa được duyệt, phá backward compatibility, đổi hành vi LPR/GATE-01, thêm dependency runtime đáng kể, thêm migration/schema persistence, hoặc mở rộng sang tracking implementation.

### Định dạng TASK-RESULT kỳ vọng (Expected TASK-RESULT format)
- Task ID: TASK-030
- Outcome: completed | blocked
- Inputs used: Danh sách các tệp/artifact đã đọc.
- Outputs produced: `.delivery/tasks/TASK-030/API-CONTRACT.md`, `.delivery/tasks/TASK-030/TASK-RESULT.md`.
- Validation evidence: Exact commands, exit codes và kết quả thực thi.
- Deviations: none hoặc sai lệch phát hiện được.
- Blockers: none hoặc mô tả điểm chặn.
- Scope change requests: none hoặc yêu cầu thay đổi phạm vi.

### Skill/capability cần chạy (Skill/capability to run)
- Capability: api-design
- Next skill: `$design-api`
