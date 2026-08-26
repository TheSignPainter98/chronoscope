import sqlite3
import sys

import pytest

import chronoscope
import chronoscope.utils as u


TIMESTAMP = "2055-11-29T20:57:56.489282133"


def test_create_uses_json_parser_by_default(tmp_path, monkeypatch):
    payload = (f'{{"timestamp":"{TIMESTAMP}","kind":"tick",'
               '"id":2,"pid":111,"type":"gw","event":"inited"}')
    trace_path = tmp_path / "events.jsonl"
    database_path = tmp_path / "chronoscope.db"
    trace_path.write_text(f"{payload}\n")
    monkeypatch.setattr(
        sys, "argv",
        ["chronoscope", "create", "--trace", str(trace_path),
         "--db", str(database_path)],
    )

    assert chronoscope.main() == 0

    with sqlite3.connect(database_path) as connection:
        event = connection.execute(
            "SELECT timestamp, payload FROM json_event"
        ).fetchone()
        tick = connection.execute(
            "SELECT id, time, type, event FROM tick"
        ).fetchone()
    assert event == (u.ns(TIMESTAMP), payload)
    assert tick == (u.pack(2, 111), u.ns(TIMESTAMP), "gw", "inited")


@pytest.mark.parametrize(
    "option",
    [("--input-format", "json"), ("--conf", "config.yaml")],
)
def test_obsolete_input_options_are_rejected(monkeypatch, capsys, option):
    monkeypatch.setattr(sys, "argv", ["chronoscope", "create", *option])

    with pytest.raises(SystemExit) as error:
        chronoscope.parse_args()

    assert error.value.code == 2
    assert "unrecognized arguments" in capsys.readouterr().err
