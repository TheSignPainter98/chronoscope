# -*- coding: utf-8 -*-
#
# This file is part of Chronoscope.
#
# SPDX-FileCopyrightText: 2024 Anatoliy Bilenko <anatoliy.bilenko@gmail.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

import json
from chronoscope.parser import parser


TIME = 1783367062172542000
SM_ID = 0x1000000000000001
EVENT_ID = 0x1000000000000001


def as_line(kind, **fields):
    return json.dumps({"kind": kind, **fields})


def test_parser_event():
    records = parser().parse([as_line(
        "event", id=EVENT_ID, state_machine_id=SM_ID,
        time=TIME, name="role=Follower")])

    assert records["event"] == [{
        "kind": "event", "id": EVENT_ID, "state_machine_id": SM_ID,
        "time": TIME, "name": "role=Follower",
    }]


def test_parser_event_relation_send():
    records = parser().parse([as_line(
        "event_relation", from_event_id=None,
        to_event_id=0x1000000000000006, from_sm_id=None, from_time=None,
        to_sm_id=SM_ID, to_time=TIME, relation="causes")])

    relation = records["event_relation"][0]
    assert relation["from_event_id"] is None
    assert relation["to_event_id"] == 0x1000000000000006
    assert relation["from_sm_id"] is None
    assert relation["from_time"] is None


def test_parser_event_relation_recv():
    records = parser().parse([as_line(
        "event_relation", from_event_id=0x1000000000000007,
        to_event_id=0x100000000000000C,
        from_sm_id=0x1000000000000001, from_time=TIME,
        to_sm_id=0x1000000000000005, to_time=TIME + 100,
        relation="causes")])

    relation = records["event_relation"][0]
    assert relation["from_event_id"] == 0x1000000000000007
    assert relation["to_event_id"] == 0x100000000000000C
    assert relation["from_sm_id"] is not None
    assert relation["to_sm_id"] is not None


def test_parser_event_attribute():
    records = parser().parse([as_line(
        "event_attribute", event_id=EVENT_ID,
        key="raft:role", value="Follower")])

    assert records["event_attribute"] == [{
        "kind": "event_attribute", "event_id": EVENT_ID,
        "key": "raft:role", "value": "Follower",
    }]


def test_parser_sm_relation():
    records = parser().parse([as_line(
        "state_machine_relation", from_sm_id=0x1000000000000457,
        to_sm_id=SM_ID, relation="top-to-raft")])

    assert records["state_machine_relation"][0]["relation"] == "top-to-raft"


def test_parser_state_machine():
    records = parser().parse([as_line(
        "state_machine", id=SM_ID, name="raft", type="raft")])

    assert records["state_machine"] == [{
        "kind": "state_machine", "id": SM_ID,
        "name": "raft", "type": "raft",
    }]


def test_parser_state_machine_attribute():
    records = parser().parse([as_line(
        "state_machine_attribute", state_machine_id=SM_ID,
        key="node", value=1)])

    assert records["state_machine_attribute"][0]["value"] == 1


def test_parser_preserves_extra_fields():
    record = {
        "kind": "event", "id": EVENT_ID, "state_machine_id": SM_ID,
        "time": TIME, "name": "role=Follower", "source": "raft",
        "extra_fields": {"name": "raw role", "file": "raft.rs"},
    }

    parsed = parser().parse([json.dumps(record)])["event"][0]

    assert parsed == record


def test_parser_malformed(capsys):
    parser(verbose=True).parse([as_line("event", id=EVENT_ID)])

    assert "missing required fields" in capsys.readouterr().err


def test_parser_fuzz():
    records = parser(verbose=True).parse([
        "a b c d", '"string"', "42", "[]", "{}", as_line("bogus")])

    assert all(not table_records for table_records in records.values())


def test_parser_empty():
    records = parser().parse([""])

    assert all(not table_records for table_records in records.values())
