import pytest
import chronoscope.db as db
import chronoscope.utils as u
from chronoscope.parser import json_parser


TIMESTAMP = "2055-11-29T20:57:56.489282133"
TICK_TIMESTAMP = "2055-11-29T20:57:56.489334920"
ATTR_TIMESTAMP = "2055-11-29T20:57:56.489400110"
RELATION_TIMESTAMP = "2055-11-29T20:57:56.489511716"


def test_json_parser_routes_tick_and_preserves_payload():
    line = (f'{{"timestamp":"{TICK_TIMESTAMP}","kind":"tick",'
            '"id":2,"pid":111,"type":"gw","event":"inited",'
            '"samples":[1,2]}')

    records = json_parser().parse([line])

    assert records == {
        "tick": [{
            "timestamp": TICK_TIMESTAMP,
            "kind": "tick",
            "id": u.pack(2, 111),
            "pid": 111,
            "type": "gw",
            "event": "inited",
            "samples": [1, 2],
            "time": u.ns(TICK_TIMESTAMP),
        }],
        "attr": [],
        "relation": [],
        "json_event": [{"timestamp": u.ns(TICK_TIMESTAMP),
                        "payload": line}],
    }


def test_json_parser_routes_attr():
    line = (f'{{"timestamp":"{ATTR_TIMESTAMP}","kind":"attr",'
            '"id":2,"pid":111,"name":"route","val":"/v1/orders",'
            '"source":"config"}')

    records = json_parser().parse([line])

    assert records["attr"] == [{
        "timestamp": ATTR_TIMESTAMP,
        "kind": "attr",
        "id": u.pack(2, 111),
        "pid": 111,
        "name": "route",
        "val": "/v1/orders",
        "source": "config",
    }]
    assert records["json_event"] == [
        {"timestamp": u.ns(ATTR_TIMESTAMP), "payload": line},
    ]
    assert not records["tick"]
    assert not records["relation"]


def test_json_parser_routes_relation():
    line = (f'{{"timestamp":"{RELATION_TIMESTAMP}","kind":"relation",'
            '"orig":{"id":1,"pid":111},"dest":{"id":2,"pid":111},'
            '"type":"conn-to-gw","trace_id":"trace-1"}')

    records = json_parser().parse([line])

    assert records["relation"] == [{
        "timestamp": RELATION_TIMESTAMP,
        "kind": "relation",
        "orig": u.pack(1, 111),
        "dest": u.pack(2, 111),
        "type": "conn-to-gw",
        "trace_id": "trace-1",
    }]
    assert records["json_event"] == [
        {"timestamp": u.ns(RELATION_TIMESTAMP), "payload": line},
    ]
    assert not records["tick"]
    assert not records["attr"]


def test_json_parser_unrecognized_lines_are_silent(capsys):
    noise = [
        "", "   ", "not json", '"str"', "42", "[1, 2]", "{}",
        f'{{"timestamp":"{TIMESTAMP}"}}',
        f'{{"timestamp":"{TIMESTAMP}","kind":"bogus"}}',
        f'{{"timestamp":"{TIMESTAMP}","kind":1}}',
        f'{{"details":{{"timestamp":"{TIMESTAMP}","kind":"tick"}}}}',
    ]

    records = json_parser(verbose=True).parse(noise)

    assert all(not table_records for table_records in records.values())
    assert capsys.readouterr().err == ""


@pytest.mark.parametrize(
    ("timestamp", "error"),
    [("1", "invalid timestamp: 1"),
     ("null", "invalid timestamp: None"),
     ('"malformed"', "Not a nanosecond time format")],
)
def test_json_parser_invalid_timestamp_reported_only_in_verbose(
        capsys, timestamp, error):
    line = (f'{{"timestamp":{timestamp},"kind":"tick","id":2,"pid":111,'
            '"type":"gw","event":"inited"}')

    assert all(not records for records in json_parser().parse([line]).values())
    assert capsys.readouterr().err == ""
    assert all(not records
               for records in json_parser(verbose=True).parse([line]).values())

    stderr = capsys.readouterr().err
    assert error in stderr
    assert f"line={line!r}" in stderr


@pytest.mark.parametrize(
    ("line", "missing"),
    [
        ('{"kind":"tick","id":2,"pid":111,"type":"gw",'
         '"event":"inited"}', "timestamp"),
        (f'{{"timestamp":"{TIMESTAMP}","kind":"tick","id":2,'
         '"pid":111,"type":"gw"}', "event"),
        (f'{{"timestamp":"{TIMESTAMP}","kind":"attr","id":2,'
         '"pid":111,"name":"route"}', "val"),
        (f'{{"timestamp":"{TIMESTAMP}","kind":"relation",'
         '"orig":{"id":1,"pid":111},"type":"conn-to-gw"}', "dest"),
    ],
)
def test_json_parser_missing_required_field_reported_only_in_verbose(
        capsys, line, missing):
    assert all(not records for records in json_parser().parse([line]).values())
    assert capsys.readouterr().err == ""
    assert all(not records
               for records in json_parser(verbose=True).parse([line]).values())
    assert f"missing required fields: {missing}" in capsys.readouterr().err


def test_json_parser_persists_raw_and_kind_records(tmp_path):
    lines = [
        (f'{{"timestamp":"{TICK_TIMESTAMP}","kind":"tick",'
         '"id":2,"pid":111,"type":"gw","event":"inited",'
         '"samples":[1,2]}'),
        (f'{{"timestamp":"{ATTR_TIMESTAMP}","kind":"attr",'
         '"id":2,"pid":111,"name":"route","val":"/v1/orders",'
         '"source":"config"}'),
        (f'{{"timestamp":"{RELATION_TIMESTAMP}","kind":"relation",'
         '"orig":{"id":1,"pid":111},"dest":{"id":2,"pid":111},'
         '"type":"conn-to-gw","trace_id":"trace-1"}'),
    ]
    trace_path = tmp_path / "events.jsonl"
    database_path = tmp_path / "chronoscope.db"
    trace_path.write_text("\n".join(lines) + "\n")

    db.open(str(database_path), create=True)
    try:
        db.load(json_parser(), str(trace_path))

        assert db.tick.select().count() == 1
        assert db.attr.select().count() == 1
        assert db.relation.select().count() == 1
        assert db.json_event.select().count() == 3
        events = db.json_event.select().order_by(db.json_event.timestamp)
        payloads = [event.payload for event in events]
        assert payloads == lines
    finally:
        db.close()
