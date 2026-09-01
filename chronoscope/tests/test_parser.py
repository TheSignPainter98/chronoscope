# -*- coding: utf-8 -*-
#
# This file is part of Chronoscope.
#
# SPDX-FileCopyrightText: 2024 Anatoliy Bilenko <anatoliy.bilenko@gmail.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

import chronoscope.db as db
from chronoscope.parser import parser

RAFT_TRACE = "test/raft_trace.jsonl"


def test_parser_event():
    line = (
        '{"timestamp":"2026-07-06T19:44:22.172542000","kind":"event",'
        '"sm_id":"0x1000000000000001","eid":"0x1000000000000001",'
        '"sm_type":"raft","name":"role=Follower"}'
    )
    records = parser().parse([line])
    assert len(records["event"]) == 1
    assert len(records["state_machine"]) == 1
    assert records["event"][0]["name"] == "role=Follower"
    assert records["event"][0]["id"] == 0x1000000000000001
    assert records["state_machine"][0]["type"] == "raft"


def test_parser_event_relation_send():
    line = (
        '{"timestamp":"2026-07-06T19:44:22.175353000","kind":"event_relation",'
        '"sm_id":"0x1000000000000001","eid":"0x1000000000000006","peid":null}'
    )
    records = parser().parse([line])
    assert len(records["event_relation"]) == 1
    er = records["event_relation"][0]
    assert er["from_event_id"] is None
    assert er["to_event_id"] == 0x1000000000000006
    assert er["from_sm_id"] is None
    assert er["from_time"] is None


def test_parser_event_relation_recv():
    line = (
        '{"timestamp":"2026-07-06T19:44:22.175565000","kind":"event_relation",'
        '"sm_id":"0x1000000000000005","eid":"0x100000000000000c",'
        '"peid":"0x1000000000000007"}'
    )
    records = parser().parse([line])
    assert len(records["event_relation"]) == 1
    er = records["event_relation"][0]
    assert er["from_event_id"] == 0x1000000000000007
    assert er["to_event_id"] == 0x100000000000000c
    assert er["from_sm_id"] is not None
    assert er["to_sm_id"] is not None


def test_parser_event_attribute():
    line = (
        '{"timestamp":"2026-07-22T08:28:19.113535000","kind":"event_attribute",'
        '"eid":"0x100000000000000c","key":"raft:role","value":"Follower"}'
    )
    records = parser().parse([line])
    assert len(records["event_attribute"]) == 1
    attribute = records["event_attribute"][0]
    assert attribute["event_id"] == 0x100000000000000C
    assert attribute["key"] == "raft:role"
    assert attribute["value"] == "Follower"


def test_parser_sm_relation():
    line = (
        '{"timestamp":"2025-06-07T11:00:14.026305714",'
        '"kind":"state_machine_relation","from_sm_id":"0x1000000000000457",'
        '"to_sm_id":"0x1000000000000001","relation":"top-to-raft",'
        '"from_name":"top"}'
    )
    records = parser().parse([line])
    assert len(records["state_machine_relation"]) == 1
    assert len(records["state_machine"]) == 1
    smr = records["state_machine_relation"][0]
    assert smr["relation"] == "top-to-raft"
    assert records["state_machine"][0]["name"] == "top"


def test_parser_state_machine():
    line = (
        '{"timestamp":"2026-07-14T13:12:56.473265000","kind":"state_machine",'
        '"sm_id":"0x1000000000000018","name":"DtxState","state":"Init",'
        '"eid":"0x1000000000000019"}'
    )
    records = parser().parse([line])
    assert len(records["state_machine"]) == 1
    assert len(records["event"]) == 1
    assert records["state_machine"][0]["type"] == "DtxState"
    assert records["event"][0]["name"] == "Init"


def test_parser_extra_fields_become_attributes():
    line = (
        '{"timestamp":"2055-11-29T20:57:56.489282133","kind":"event",'
        '"sm_id":"0x1","eid":"0x2","sm_type":"gw","name":"inited",'
        '"samples":[1,2]}'
    )
    records = parser().parse([line])
    assert len(records["event_attribute"]) == 1
    attribute = records["event_attribute"][0]
    assert attribute["key"] == "samples"
    assert attribute["value"] == "[1, 2]"


def test_parser_malformed():
    line = '{"timestamp":"2026-07-06T19:44:22.667095559","kind":"event"}'
    _ = parser(verbose=True).parse([line])


def test_parser_fuzz():
    line = "a b c d"
    _ = parser().parse([line])


def test_parser_empty():
    line = ""
    _ = parser().parse([line])


def test_parser_unrecognized_lines_are_silent(capsys):
    noise = [
        "", "   ", "not json", '"str"', "42", "[1, 2]", "{}",
        '{"timestamp":"2055-11-29T20:57:56.489282133"}',
        '{"timestamp":"2055-11-29T20:57:56.489282133","kind":"bogus"}',
        '{"timestamp":"2055-11-29T20:57:56.489282133","kind":1}',
        '{"details":{"timestamp":"2055-11-29T20:57:56.489282133","kind":"event"}}',
    ]

    records = parser(verbose=True).parse(noise)

    assert all(not table_records for table_records in records.values())
    assert capsys.readouterr().err == ""


def test_parser_persists_raft_records(tmp_path):
    lines = [
        ('{"timestamp":"2026-07-06T19:44:22.172542000","kind":"event",'
         '"sm_id":"0x1000000000000001","eid":"0x1000000000000001",'
         '"sm_type":"raft","name":"role=Follower"}'),
        ('{"timestamp":"2026-07-06T19:44:22.175353000","kind":"event_relation",'
         '"sm_id":"0x1000000000000001","eid":"0x1000000000000006","peid":null}'),
        ('{"timestamp":"2025-06-07T11:00:14.026305714",'
         '"kind":"state_machine_relation","from_sm_id":"0x1000000000000457",'
         '"to_sm_id":"0x1000000000000001","relation":"top-to-raft",'
         '"from_name":"top"}'),
        ('{"timestamp":"2026-07-14T13:12:56.473265000","kind":"state_machine",'
         '"sm_id":"0x1000000000000018","name":"DtxState","state":"Init",'
         '"eid":"0x1000000000000019"}'),
        ('{"timestamp":"2026-07-22T08:28:19.113535000",'
         '"kind":"event_attribute","eid":"0x1000000000000001",'
         '"key":"raft:role","value":"Follower"}'),
    ]
    trace_path = tmp_path / "raft_trace.jsonl"
    database_path = tmp_path / "chronoscope.db"
    trace_path.write_text("\n".join(lines) + "\n")

    db.open(str(database_path), create=True)
    try:
        db.load(parser(), str(trace_path))

        assert db.state_machine.select().count() == 3
        assert db.event.select().count() == 2
        assert db.event_relation.select().count() == 1
        assert db.state_machine_relation.select().count() == 1
        assert db.event_attribute.select().count() == 1
    finally:
        db.close()
