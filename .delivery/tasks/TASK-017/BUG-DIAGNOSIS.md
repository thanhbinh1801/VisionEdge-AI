---
artifact: BUG-DIAGNOSIS.md
version: "1.0"
owner: diagnose-bug
status: in-review
updated_at: "2026-08-21T10:03:53+07:00"
task_id: TASK-017
depends_on: [TASK-016]
---

# BUG-DIAGNOSIS: TASK-017 — WebSocket `/ws/v1/events` tiếp tục spam lỗi send sau khi client đã rời kết nối

## Traceability

- `REQ-002`: Area monitoring phải có luồng realtime riêng để đẩy metadata cho dashboard.
- `REQ-004`: Luồng realtime khu vực phải chạy như một lane tách biệt, không treo hoặc spam lỗi khi client rời đi.
- `REQ-005`: Runtime state của zone phải tiếp tục được phục vụ đúng trên lane realtime mà không làm backend mất ổn định.
- `REQ-009`: Metadata lane không được làm vỡ hành vi vận hành của event và alert lanes hay gây nhiễu log kéo dài.
- `.delivery/tasks/TASK-016/API-CONTRACT.md` quy định gateway công khai là `WS /ws/v1/events`.
- `TASK-017` là task backend implementation chịu trách nhiệm expose và vận hành gateway này.

## Reproduction

1. Chạy backend từ `backend/main.py` bằng lệnh người dùng đã cung cấp ngày `2026-08-21`:
   - `python main.py`
2. Chờ app startup hoàn tất:
   - `SQLite Database initialized with schema.sql successfully!`
3. Kết nối một client tới `ws://localhost:8000/ws/v1/events?camera_id=BAI-KIEM&conf_threshold=0.35`.
4. Quan sát log runtime:
   - `WebSocket /ws/v1/events?... [accepted]`
   - `connection open`
   - sau đó lặp lại rất nhiều lần `socket.send() raised exception.`
5. Đối chiếu source hiện tại trong workspace:
   - [websocket.py](/D:/Hilab/Project34/backend/app/api/v1/websocket.py:30) có `send_json()` bắt `Exception`, remove connection, log `WebSocket send failed; disconnecting stale client.`
   - [websocket.py](/D:/Hilab/Project34/backend/app/api/v1/websocket.py:70) `break` publisher loop ngay khi `send_json()` trả `False`

Expected:
Sau khi send đầu tiên thất bại hoặc client đóng socket, backend phải ghi đúng log cleanup của ứng dụng và dừng publisher loop.

Observed:
Runtime ngày `August 21, 2026` vẫn spam chuỗi `socket.send() raised exception.` nhiều lần, là chuỗi không xuất hiện trong source hiện tại của workspace.

## Minimal Failing Case

- Seam công khai nhỏ nhất vẫn là `WS /ws/v1/events`.
- Tuy nhiên với source hiện tại, failure tối giản không còn nằm ở logic `send_json()` nữa vì code đã:
  - bắt `Exception`,
  - gọi `disconnect(websocket)`,
  - `return False`,
  - và endpoint `break` ngay khi send thất bại.
- Vì vậy minimal failing case đã thu hẹp thành:
  - process runtime đang không thực thi source hiện tại của workspace, hoặc
  - lỗi xảy ra ở tầng transport hoặc server trước khi exception được phản ánh về logging hoặc application path mong đợi.

## Evidence

- Runtime evidence người dùng cung cấp ngày `2026-08-21`:
  - `INFO: 127.0.0.1:58354 - "WebSocket /ws/v1/events?... [accepted]"`
  - `INFO: connection open`
  - sau đó spam nhiều dòng `socket.send() raised exception.`
- Source hiện tại trong workspace:
  - [websocket.py](/D:/Hilab/Project34/backend/app/api/v1/websocket.py:37) chỉ log `WebSocket send failed; disconnecting stale client.`
  - [websocket.py](/D:/Hilab/Project34/backend/app/api/v1/websocket.py:70) `break` loop khi send fail
- Kiểm tra interpreter trong `venv` xác nhận module nạp hiện tại đúng là source đã fix:
  - `.\venv\Scripts\python.exe -c "... import app.api.v1.websocket as ws; print(inspect.getsource(...))"` in ra đúng nhánh `send_json()` và `break`
- Tìm kiếm trong workspace:
  - chỉ có một file [websocket.py](/D:/Hilab/Project34/backend/app/api/v1/websocket.py)
  - chuỗi `socket.send() raised exception.` không tồn tại trong `backend/`
- Runtime topology:
  - [main.py](/D:/Hilab/Project34/backend/main.py:61) chạy `uvicorn.run("main:app", ..., reload=True)`
  - trên Windows, `reload=True` tạo tiến trình reloader và worker riêng; đây là điều kiện thuận lợi để tưởng đã dừng server nhưng thực tế process tree vẫn còn sống
- Harness evidence:
  - `.\venv\Scripts\python.exe -m pytest backend/tests/test_websocket_connection_manager.py -q` hiện fail vì thiếu plugin async cho `@pytest.mark.asyncio`, nên chưa dùng được làm bằng chứng chạy xanh dù logic test phù hợp

## Root Cause

Nguyên nhân gốc có xác suất cao nhất không còn là logic ứng dụng trong source hiện tại của `backend/app/api/v1/websocket.py`, mà là **runtime process hoặc environment mismatch** trong lúc chạy backend ngày `2026-08-21`.

Lý do:

1. Source hiện tại đã có guard rõ ràng cho send failure:
   - `send_json()` bắt `Exception`, cleanup connection và trả `False`
   - `websocket_events_endpoint()` `break` ngay khi `send_json()` trả `False`
2. Chuỗi log người dùng nhìn thấy là `socket.send() raised exception.`, trong khi source workspace hiện không hề ghi chuỗi đó.
3. App đang chạy với `reload=True`, tức có ít nhất một process reloader và một worker. Trên Windows, nếu một process trong cây không bị dừng sạch, rất dễ xuất hiện tình huống tưởng đã restart code nhưng thực tế worker cũ vẫn còn phục vụ hoặc process tree không được hủy đúng cách.

Vì vậy bug hiện tại nên được chẩn đoán là: **backend runtime đang không phản ánh đúng source hiện tại hoặc không được tắt và khởi động lại sạch, khiến người dùng tiếp tục quan sát symptom cũ dù file trong repo đã có logic cleanup**.

## Ownership

- Primary owner: `TASK-017` backend runtime và integration ownership
- Secondary owner nếu cần hỗ trợ vận hành cục bộ: local developer environment và process lifecycle
- Không có bằng chứng hiện tại để đẩy ownership sang frontend `TASK-018`

## Regression Test

- Trạng thái: đã có seam test bán phần nhưng chưa đủ đóng bug vận hành này
- Existing seam:
  - [test_websocket_connection_manager.py](/D:/Hilab/Project34/backend/tests/test_websocket_connection_manager.py:20) xác nhận `ConnectionManager.send_json()` remove stale client khi `send_text()` ném lỗi
- Khoảng trống:
  - test hiện tại đang fail ở harness vì thiếu plugin async, nên chưa thành evidence chạy xanh
  - chưa có test app-level hoặc runtime-level xác nhận sau một restart sạch thì worker mới thực sự chạy source đã fix
- Failing regression test phù hợp trong tương lai:
  - mở WebSocket `/ws/v1/events`
  - buộc client disconnect
  - assert server-side publisher loop dừng trong thời gian hữu hạn và connection bị gỡ khỏi manager

## Recommended Fix Scope

- Scope nhỏ nhất nên làm tiếp:
  - xác nhận và chuẩn hóa cách chạy backend để dùng đúng interpreter và dừng sạch process tree
  - tắt `reload=True` trong lần reproduce kế tiếp để loại bỏ nhiễu từ reloader process
  - nếu symptom vẫn còn sau restart sạch, bổ sung runtime-level instrumentation quanh `send_json()` để log exception path từ ứng dụng thay vì chỉ nhìn symptom từ transport
- Scope test:
  - sửa harness WebSocket test để chạy được trong `venv` hiện tại
  - thêm assertion ở seam endpoint, không chỉ ở `ConnectionManager`
- Không khuyến nghị sửa frontend ở bước này

## Open Questions

- Process ngày `2026-08-21` có thực sự được khởi động từ đúng virtualenv và worktree đang chứa source hiện tại hay không?
- Sau khi kill sạch process tree rồi chạy lại không dùng `reload=True`, log còn lặp `socket.send() raised exception.` hay chuyển sang log cleanup của ứng dụng?
- Chuỗi `socket.send() raised exception.` cụ thể đang phát ra từ tầng nào trong stack runtime của máy người dùng: Uvicorn transport, websockets backend, hay một worker cũ chưa bị hủy?
