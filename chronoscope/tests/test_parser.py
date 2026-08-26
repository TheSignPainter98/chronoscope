# -*- coding: utf-8 -*-
#
# This file is part of Chronoscope.
#
# SPDX-FileCopyrightText: 2024 Anatoliy Bilenko <anatoliy.bilenko@gmail.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

import chronoscope.db as db
import chronoscope.utils as u
from chronoscope.parser import parser


TIMESTAMP = "2055-11-29T20:57:56.489282133"
TICK_TIMESTAMP = "2055-11-29T20:57:56.489334920"
ATTR_TIMESTAMP = "2055-11-29T20:57:56.489400110"
RELATION_TIMESTAMP = "2055-11-29T20:57:56.489511716"


def test_parser_routes_tick_and_preserves_fields():
    line = (f'{{"timestamp":"{TICK_TIMESTAMP}","kind":"tick",'
            '"id":2,"pid":111,"type":"gw","event":"inited",'
            '"samples":[1,2]}')

    records = parser().parse([line])

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
    }


def test_parser_routes_attr():
    line = (f'{{"timestamp":"{ATTR_TIMESTAMP}","kind":"attr",'
            '"id":2,"pid":111,"type":"gw-attr","name":"route",'
            '"value":"/v1/orders","source":"config"}')

    records = parser().parse([line])

    assert records["attr"] == [{
        "timestamp": ATTR_TIMESTAMP,
        "kind": "attr",
        "id": u.pack(2, 111),
        "pid": 111,
        "type": "gw-attr",
        "name": "route",
        "value": "/v1/orders",
        "source": "config",
        "val": "/v1/orders",
    }]
    assert not records["tick"]
    assert not records["relation"]


def test_parser_routes_relation():
    line = (f'{{"timestamp":"{RELATION_TIMESTAMP}","kind":"relation",'
            '"orig_id":1,"orig_pid":111,"dest_id":2,"dest_pid":111,'
            '"type":"conn-to-gw","trace_id":"trace-1"}')

    records = parser().parse([line])

    assert records["relation"] == [{
        "timestamp": RELATION_TIMESTAMP,
        "kind": "relation",
        "orig_id": 1,
        "orig_pid": 111,
        "dest_id": 2,
        "dest_pid": 111,
        "type": "conn-to-gw",
        "trace_id": "trace-1",
        "orig": u.pack(1, 111),
        "dest": u.pack(2, 111),
    }]
    assert not records["tick"]
    assert not records["attr"]


def test_parser_unrecognized_lines_are_silent(capsys):
    noise = [
        "", "   ", "not json", '"str"', "42", "[1, 2]", "{}",
        f'{{"timestamp":"{TIMESTAMP}"}}',
        f'{{"timestamp":"{TIMESTAMP}","kind":"bogus"}}',
        f'{{"timestamp":"{TIMESTAMP}","kind":1}}',
        f'{{"details":{{"timestamp":"{TIMESTAMP}","kind":"tick"}}}}',
    ]

    records = parser(verbose=True).parse(noise)

    assert all(not table_records for table_records in records.values())
    assert capsys.readouterr().err == ""


def test_parser_persists_kind_records(tmp_path):
    lines = [
        (f'{{"timestamp":"{TICK_TIMESTAMP}","kind":"tick",'
         '"id":2,"pid":111,"type":"gw","event":"inited",'
         '"samples":[1,2]}'),
        (f'{{"timestamp":"{ATTR_TIMESTAMP}","kind":"attr",'
         '"id":2,"pid":111,"type":"gw-attr","name":"route",'
         '"value":"/v1/orders","source":"config"}'),
        (f'{{"timestamp":"{RELATION_TIMESTAMP}","kind":"relation",'
         '"orig_id":1,"orig_pid":111,"dest_id":2,"dest_pid":111,'
         '"type":"conn-to-gw","trace_id":"trace-1"}'),
    ]
    trace_path = tmp_path / "events.jsonl"
    database_path = tmp_path / "chronoscope.db"
    trace_path.write_text("\n".join(lines) + "\n")

    db.open(str(database_path), create=True)
    try:
        db.load(parser(), str(trace_path))

        assert db.tick.select().count() == 1
        assert db.attr.select().count() == 1
        assert db.relation.select().count() == 1
    finally:
        db.close()
