import pytest
from chronoscope.parser import parser

RAFT_YAML = "test/raft_chronoscope.yaml"


def test_parser_file_not_found():
    with pytest.raises(FileNotFoundError):
        _ = parser("")


def test_parser_event():
    line = (
        "raft[1]: 2026-07-06T19:44:22.172542000 raft pid: 1 sm_id: 1 "
        "role=Follower term=1 log=0 ci=0 lc=0 eid=0x1000000000000001 |"
    )
    records = parser(RAFT_YAML).parse([line])
    assert len(records["event"]) == 1
    assert len(records["state_machine"]) == 1
    assert records["event"][0]["name"] == "role=Follower"
    assert records["event"][0]["id"] == 0x1000000000000001


def test_parser_event_relation_send():
    line = (
        "raft[1]: 2026-07-06T19:44:22.175353000 event_relation pid: 1 sm_id: 1 "
        "peid=None eid=0x1000000000000006 |"
    )
    records = parser(RAFT_YAML).parse([line])
    assert len(records["event_relation"]) == 1
    er = records["event_relation"][0]
    assert er["from_event_id"] is None
    assert er["to_event_id"] == 0x1000000000000006
    assert er["from_sm_id"] is None
    assert er["from_time"] is None


def test_parser_event_relation_recv():
    line = (
        "raft[3]: 2026-07-06T19:44:22.175565000 event_relation pid: 3 sm_id: 3 "
        "peid=0x1000000000000007 eid=0x3000000000000004 |"
    )
    records = parser(RAFT_YAML).parse([line])
    assert len(records["event_relation"]) == 1
    er = records["event_relation"][0]
    assert er["from_event_id"] == 0x1000000000000007
    assert er["to_event_id"] == 0x3000000000000004
    assert er["from_sm_id"] is not None
    assert er["to_sm_id"] is not None


def test_parser_sm_relation():
    line = (
        "raft[1]: 2025-06-07T11:00:14.026305714 top-to-raft opid: 1 dpid: 1 "
        "id: 1111 id: 1 eid=0x1000000000000002 |"
    )
    records = parser(RAFT_YAML).parse([line])
    assert len(records["state_machine_relation"]) == 1
    assert len(records["state_machine"]) == 2
    smr = records["state_machine_relation"][0]
    assert smr["relation"] == "top-to-raft"


def test_parser_malformed():
    line = "raft[1]: 2026-07-06T19:44:22.667095559 raft"
    _ = parser(RAFT_YAML, verbose=True).parse([line])


def test_parser_fuzz():
    line = "a b c d"
    _ = parser(RAFT_YAML).parse([line])


def test_parser_empty():
    line = ""
    _ = parser(RAFT_YAML).parse([line])
