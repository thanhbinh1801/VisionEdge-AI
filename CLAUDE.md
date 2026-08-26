# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository layout

The working directory `Project_W3+4/` is a wrapper; **all product code lives in `VisionEdge-AI/`**, which is its own git repo (remote: `thanhbinh1801`, branch history via PRs into `main`). Run every command below from `VisionEdge-AI/`.

The product is **SentriAI Mini** — an AI camera-surveillance demo: license-plate recognition at a gate (`GATE-01`) plus polygon-zone violation monitoring for yard cameras (`BAI-KIEM`, `XUONG-AN-NINH`). UI text, docs, and log strings are in Vietnamese; keep that convention.

## Commands

Backend (Python 3.14 venv at `VisionEdge-AI/.venv`):

```bash
.venv/Scripts/python.exe -m pytest backend/tests -q        # full suite (run from VisionEdge-AI/)
.venv/Scripts/python.exe -m pytest backend/tests/test_database.py::test_event_repository -q   # single test
cd backend && python main.py                               # dev server, uvicorn reload on :8000 (docs at /docs)
```

Tests import via the `backend.` package prefix (`from backend.database.engine import ...`), so pytest **must** be invoked from the `VisionEdge-AI/` root — `conftest.py` only adds the repo root to `sys.path`.

`backend/tests/test_model_real_call.py` fails on a clean checkout by design: `.gitignore` excludes `*.pt` and `*.mp4`, so YOLO weights (`backend/app/ai/weights/`) and demo videos (`data/video/*.mp4`) must be supplied locally. All other tests pass without them.

Frontend:

```bash
cd frontend && npm run dev      # Vite on :3000, proxies /api and /videos to :8000
npm run lint                    # tsc --noEmit — the only linter; no ESLint/Prettier configured
npm run build                   # tsc && vite build
```

There is no frontend test runner.

## Architecture

Monolithic FastAPI backend + React SPA (ADR-001). Request flow: React → Vite proxy → `/api/v1/*` → repository → SQLite.

- `backend/main.py` — app factory, CORS `*`, mounts `/videos` (demo MP4s) and `/assets` (Prototype images) as static, and on startup runs `init_db()` against `docs/contracts/db/schema.sql`. The DB schema is defined by that **hand-written SQL file**, not by SQLAlchemy `create_all` — `Base.metadata.create_all` is only a fallback when the file is missing. Schema changes go in `schema.sql` *and* `backend/database/models.py`.
- `backend/app/api/v1/*` — routers, mounted under `/api/v1` by `app/api/router.py`. Pydantic request/response models are declared inline in the router modules (`app/models/schemas/` largely duplicates them and is mostly unused).
- `backend/database/` — the live data layer: `engine.py` (WAL + foreign_keys pragmas, `get_db` dependency), `models.py` (ORM), `repository.py` (per-entity repository classes; routers use these, never raw queries).
- `backend/app/core/database.py` — **legacy duplicate** of `engine.py`. New code should import from `backend.database.engine`.
- `backend/app/services/` — `vision_pipeline.py` is the only substantially implemented service. `video_stream.py`, `event_manager.py`, `alert_dispatcher.py`, and `qa_agent.py` are scaffolds/stubs (e.g. `EventManager.slice_10s_ring_buffer_clip` writes a placeholder byte string, `LLMQAAgent` returns canned answers) and are not yet wired into the request path.
- `frontend/src/` — 4 pages (`GateDashboard`, `AreaSecurityDashboard`, `ZoneTagSettings`, `AIChatbotAssistant`) switched by a `tab` field in `context/AppContext.tsx`; no router. `services/api.ts` holds all fetch calls and swallows errors by returning empty defaults, so a dead backend degrades to blank panels rather than crashing.

### Conventions that cut across layers

- **Zone coordinates are percentages (0–100)**, both in the SVG editor and in the `zones.vertices` JSON column. `AIVisionPipeline.point_in_polygon` auto-detects percent-vs-normalized by checking whether any coordinate exceeds 1.0 — pass points consistently or detection silently misfires.
- **BBox formats differ by direction**: YOLO produces `xyxy`, the API returns `[left, top, width, height]` in percent, and zone evaluation internally uses normalized `xyxy`. See `events.py::get_live_detections` for the conversion.
- **The canonical object taxonomy is 8 classes** (`container, truck, forklift, crane, car, motorbike, bicycle, person`) defined in `vision_pipeline.py` with COCO→canonical remapping and Vietnamese display names. Frontend re-declares aliases in `api.ts::CLASS_ALIAS_MAP` — changing the taxonomy means touching both. `container` covers both container-carrying vehicles and containers stacked in the yard, hence the label "Container" rather than "Xe container".
- **Class names and YOLO-World prompts are separate things.** `CANONICAL_CLASS_PROMPTS` maps each canonical class to one or more prompt strings; `set_classes()` receives the flattened prompts and `prompt_to_class` maps results back. Feeding the bare class names in (as the code originally did) produces **zero detections across the entire Bãi Kiểm yard**. The prompts were chosen by measurement, not intuition — the comment block above the table records what was tried and rejected, so re-tune with `backend/scripts/render_zone_overlay.py` rather than by guessing.
- **Never invent a class, a bbox, or a confidence to fill a gap.** Unrecognised label → drop the detection (an early version relabelled everything unknown as `person`); missing bbox → drop it (a default `[20,20,20,20]` used to draw a fake box mid-frame); missing confidence → `0.0`, never the old `0.95`.
- **Severity 1/2/3 = green/yellow/red**; level 3 is what triggers the audio beep and (stubbed) Telegram push.
- Real-time delivery is currently **polling** `GET /api/v1/events/live-detections` (which runs YOLO on one frame and persists violations with a 10s dedup check). The WebSocket at `/api/v1/ws/alerts` exists but nothing broadcasts to it yet.
- **The client picks the frame, not the backend.** Both dashboards pass their `<video>` element's `currentTime` as `?t=<seconds>`; the endpoint seeks to that moment (`SequentialFrameSource.read_at`) so bboxes belong to the frame the user is actually looking at. Without `t` the backend falls back to its own sequential cursor and the overlay drifts out of sync with the video entirely. The detection loop is a self-rescheduling `setTimeout` (not `setInterval`) so slow inference can't pile up requests.
- Video/model file lookup is done by multi-path fallback searching in several places (`resolve_video_path`, `VideoStreamService._resolve_video_path`, `_resolve_model_path`) rather than a single configured path.

## `.delivery/` artifact workflow

`VisionEdge-AI/.delivery/` holds an agent-driven delivery system (REQUIREMENTS, ARCHITECTURE, MASTER-PLAN, ADRs, `tasks/TASK-NNN/`, `changes/CR-NNN/`). These are versioned artifacts with YAML frontmatter (`artifact`, `version`, `owner`, `status`) and are owned by the corresponding skills in `.claude/skills/` (`plan-delivery`, `design-architecture`, `implement-backend`, …). Treat approved artifacts as the source of truth for scope, and do not hand-edit an artifact whose `owner` is a skill — go through that skill or the change-request flow.

## Notes

- `.env` (gitignored) carries a live Telegram bot token; `.env.example` is the template. `backend/app/core/config.py` reads a *different* set of variable names (`DATABASE_URL`, `VIDEOS_DIR`, …) than `.env.example` documents (`SENTRIAI_DB_PATH`, `OCR_CONFIDENCE_THRESHOLD`, …) — check `config.py` for what is actually honored.
- `sentri_ai.db` and its WAL/SHM files sit at the repo root and are gitignored despite showing as modified in some working copies.
- `Prototype/` contains the original static HTML mockup that the dark theme tokens in `frontend/src/assets/index.css` were derived from. Styling is mixed: Tailwind is configured and used in a few components, while pages mostly use inline styles referencing CSS variables (`var(--bg)`, `var(--acc)`).
