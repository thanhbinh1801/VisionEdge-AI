import os
import pytest

def test_model_benchmark_report_exists():
    report_path = "docs/reports/ai-model-benchmark.md"
    assert os.path.exists(report_path) is True
    with open(report_path, "r", encoding="utf-8") as f:
        content = f.read()
        assert "FPS >= 5" in content
        assert "YOLOv8n" in content
