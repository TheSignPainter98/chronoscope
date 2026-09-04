from chronoscope.parser import parser
import chronoscope.utils as u


TIMESTAMP = "2026-07-06 19:44:22.172542000"


def test_parser_event():
    line = (
        '{"timestamp":"2026-07-06 19:44:22.172542000","thread_id":1,'
        '"extra_fields":{"kind":"event","id":1152921504606846977,'
        '"state_machine_id":1152921504606846977,"name":"role=Follower"}}'
    )
    records = parser().parse([line])
    assert len(records["event"]) == 1
    assert records["event"][0]["name"] == "role=Follower"
    assert records["event"][0]["id"] == 0x1000000000000001


def test_parser_event_creates_state_machine_from_type():
    line = (
        '{"timestamp":"2026-07-06 19:44:22.172542000",'
        '"extra_fields":{"kind":"event","id":1152921504606846978,'
        '"state_machine_id":1152921504606846977,"name":"restart",'
        '"type":"raft"}}'
    )
    records = parser().parse([line])
    assert records["state_machine"] == [{
        "id": 1152921504606846977,
        "name": "raft",
        "type": "raft",
    }]


def test_parser_state_transition_event_creates_named_state_machine():
    line = (
        '{"timestamp":"2026-07-06 19:44:22.172542000",'
        '"extra_fields":{"kind":"event","id":1152921504606846980,'
        '"state_machine_id":1152921504606846979,"name":"NotALeader",'
        '"machine":"FirstRecordState","type":"state_machine"}}'
    )
    records = parser().parse([line])
    assert records["state_machine"] == [{
        "id": 1152921504606846979,
        "name": "FirstRecordState",
        "type": "FirstRecordState",
    }]


def test_parser_event_relation_send():
    line = (
        '{"timestamp":"2026-07-06 19:44:22.175353000",'
        '"extra_fields":{"kind":"event_relation","from_event_id":null,'
        '"to_event_id":1152921504606846982,"from_sm_id":null,"from_time":null,'
        '"to_sm_id":1152921504606846977,"to_time":1783367062175353000,'
        '"relation":"event_relation"}}'
    )
    records = parser().parse([line])
    assert len(records["event_relation"]) == 1
    er = records["event_relation"][0]
    assert er["from_event_id"] is None
    assert er["to_event_id"] == 0x1000000000000006
    assert er["from_sm_id"] is None
    assert er["from_time"] is None
    assert er["to_time"] == u.ns("2026-07-06 19:44:22.175353000")


def test_parser_event_relation_recv():
    line = (
        '{"timestamp":"2026-07-06 19:44:22.175565000",'
        '"extra_fields":{"kind":"event_relation",'
        '"from_event_id":1152921504606846983,'
        '"to_event_id":1152921504606846988,"from_sm_id":1152921504606846981,'
        '"from_time":1783367062175565000,"to_sm_id":1152921504606846981,'
        '"to_time":1783367062175565000,"relation":"event_relation"}}'
    )
    records = parser().parse([line])
    assert len(records["event_relation"]) == 1
    er = records["event_relation"][0]
    assert er["from_event_id"] == 0x1000000000000007
    assert er["to_event_id"] == 0x100000000000000c
    assert er["from_sm_id"] == 0x1000000000000005
    assert er["to_sm_id"] == 0x1000000000000005
    expected_time = u.ns("2026-07-06 19:44:22.175565000")
    assert er["from_time"] == expected_time
    assert er["to_time"] == expected_time


def test_parser_event_attribute():
    line = (
        '{"timestamp":"2026-07-22 08:28:19.113535000",'
        '"extra_fields":{"kind":"event_attribute",'
        '"event_id":1152921504606846988,"key":"raft:role",'
        '"value":"Follower"}}'
    )
    records = parser().parse([line])
    assert len(records["event_attribute"]) == 1
    attribute = records["event_attribute"][0]
    assert attribute["event_id"] == 0x100000000000000C
    assert attribute["key"] == "raft:role"
    assert attribute["value"] == "Follower"

def test_parser_event_attribute_normalizes_boolean_to_lowercase_text():
    line = (
        '{"timestamp":"2026-07-22 08:28:19.113535000",'
        '"extra_fields":{"kind":"event_attribute",'
        '"event_id":1152921504606846988,"key":"message:vote_granted",'
        '"value":true}}'
    )
    attribute = parser().parse([line])["event_attribute"][0]
    assert attribute["value"] == "true"


def test_parser_sm_relation():
    line = (
        '{"timestamp":"2025-06-07 11:00:14.026305714",'
        '"extra_fields":{"kind":"state_machine_relation",'
        '"from_sm_id":1152921504606848087,'
        '"to_sm_id":1152921504606846977,"relation":"top-to-raft"}}'
    )
    records = parser().parse([line])
    assert len(records["state_machine_relation"]) == 1
    smr = records["state_machine_relation"][0]
    assert smr["relation"] == "top-to-raft"
    assert records["state_machine"] == [{
        "id": 1152921504606848087,
        "name": "top",
        "type": "top",
    }]


def test_parser_state_machine():
    line = (
        '{"timestamp":"2026-07-14 13:12:56.473265000",'
        '"extra_fields":{"kind":"state_machine","id":1152921504606847000,'
        '"name":"DtxState","type":"DtxState"}}'
    )
    records = parser().parse([line])
    assert len(records["state_machine"]) == 1
    assert records["state_machine"][0]["type"] == "DtxState"


def test_parser_malformed():
    line = (
        '{"timestamp":"2026-07-06 19:44:22.667095559",'
        '"extra_fields":{"kind":"event","id":1152921504606846977}}'
    )
    _ = parser(verbose=True).parse([line])


def test_parser_fuzz():
    line = "a b c d"
    _ = parser().parse([line])


def test_parser_empty():
    line = ""
    _ = parser().parse([line])


def test_parser_state_machine_attribute():
    line = (
        '{"timestamp":"2026-07-14 13:12:56.473265000",'
        '"extra_fields":{"kind":"state_machine_attribute",'
        '"state_machine_id":1152921504606846977,"key":"node","value":1}}'
    )
    records = parser().parse([line])
    assert len(records["state_machine_attribute"]) == 1
    assert records["state_machine_attribute"][0]["value"] == 1


def test_parser_reads_only_extra_fields():
    line = (
        '{"timestamp":"2026-07-06 19:44:22.172542000",'
        '"extra_fields":{"kind":"event","id":1152921504606846977,'
        '"state_machine_id":1152921504606846977,"name":"role=Follower",'
        '"file":"raft.rs"}}'
    )
    record = parser().parse([line])["event"][0]
    assert record["file"] == "raft.rs"
