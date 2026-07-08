"""v0.7.126+: graph_positions sidecar load/save + endpoint round-trip."""

import json

from raven.core.graph import (
    GRAPH_POSITIONS_FILENAME,
    load_user_positions,
    save_user_positions,
)


def test_load_returns_empty_when_sidecar_missing(tmp_path):
    assert load_user_positions(tmp_path) == {}


def test_save_then_load_roundtrip(tmp_path):
    save_user_positions(tmp_path, {"alpha": (10.5, -3.25), "beta": (0.0, 100.0)})
    loaded = load_user_positions(tmp_path)
    assert loaded == {"alpha": (10.5, -3.25), "beta": (0.0, 100.0)}
    sidecar = tmp_path / GRAPH_POSITIONS_FILENAME
    payload = json.loads(sidecar.read_text(encoding="utf-8"))
    assert payload["schema"] == 1
    assert set(payload["positions"].keys()) == {"alpha", "beta"}


def test_load_skips_invalid_entries(tmp_path):
    """손상된 파일/잘못된 키는 무시하고 유효 항목만 반환."""
    sidecar = tmp_path / GRAPH_POSITIONS_FILENAME
    sidecar.write_text(
        json.dumps(
            {
                "schema": 1,
                "positions": {
                    "good": {"x": 1.0, "y": 2.0},
                    "bad_missing_y": {"x": 3.0},
                    "bad_string": {"x": "x", "y": 0.0},
                    "bad_non_dict": "not-a-dict",
                },
            }
        ),
        encoding="utf-8",
    )
    loaded = load_user_positions(tmp_path)
    assert loaded == {"good": (1.0, 2.0)}


def test_load_returns_empty_on_invalid_json(tmp_path):
    sidecar = tmp_path / GRAPH_POSITIONS_FILENAME
    sidecar.write_text("{not valid json", encoding="utf-8")
    assert load_user_positions(tmp_path) == {}