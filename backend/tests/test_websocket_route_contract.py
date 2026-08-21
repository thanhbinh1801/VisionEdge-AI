from backend.main import app


def _registered_paths():
    paths = set()
    pending = [(route, "") for route in app.routes]
    while pending:
        route, parent_prefix = pending.pop()
        if hasattr(route, "path"):
            paths.add(f"{parent_prefix}{route.path}")
            continue
        original_router = getattr(route, "original_router", None)
        include_context = getattr(route, "include_context", None)
        if original_router is None or include_context is None:
            continue
        prefix = f"{parent_prefix}{include_context.prefix}"
        for child in original_router.routes:
            pending.append((child, prefix))
    return paths


def test_contract_exposes_public_ws_events_gateway():
    registered_paths = _registered_paths()

    assert "/ws/v1/events" in registered_paths
    assert "/api/v1/ws/v1/events" not in registered_paths
