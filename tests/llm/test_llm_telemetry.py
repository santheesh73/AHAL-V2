from __future__ import annotations

from app.llm.telemetry import llm_telemetry


def test_telemetry_records_fallback():
    llm_telemetry.reset()
    llm_telemetry.record_failure("TIMEOUT")
    snapshot = llm_telemetry.snapshot()
    assert snapshot.fallback_count == 1
    assert snapshot.last_error_type == "TIMEOUT"


def test_telemetry_records_rate_limit_fields():
    llm_telemetry.reset()
    llm_telemetry.record_failure("RATE_LIMITED")
    snapshot = llm_telemetry.snapshot()
    assert snapshot.rate_limit_count == 1
    assert snapshot.rate_limited_until is not None
