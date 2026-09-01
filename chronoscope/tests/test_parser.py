from chronoscope.parser import parser


def test_parser_event():
    line = (
        '{"kind":"event","id":1152921504606846977,'
        '"state_machine_id":1152921504606846977,'
        '"time":1783367062172542000,"name":"role=Follower"}'
    )
    records = parser().parse([line])
    assert len(records["event"]) == 1
    assert records["event"][0]["name"] == "role=Follower"
    assert records["event"][0]["id"] == 0x1000000000000001


def test_parser_event_relation_send():
    line = (
        '{"kind":"event_relation","from_event_id":null,'
        '"to_event_id":1152921504606846982,"from_sm_id":null,"from_time":null,'
        '"to_sm_id":1152921504606846977,"to_time":1783367062175353000,'
        '"relation":"causes"}'
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
        '{"kind":"event_relation","from_event_id":1152921504606846983,'
        '"to_event_id":1152921504606846988,"from_sm_id":1152921504606846977,'
        '"from_time":1783367062175353000,"to_sm_id":1152921504606846981,'
        '"to_time":1783367062175565000,"relation":"causes"}'
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
        '{"kind":"event_attribute","event_id":1152921504606846988,'
        '"key":"raft:role","value":"Follower"}'
    )
    records = parser().parse([line])
    assert len(records["event_attribute"]) == 1
    attribute = records["event_attribute"][0]
    assert attribute["event_id"] == 0x100000000000000C
    assert attribute["key"] == "raft:role"
    assert attribute["value"] == "Follower"


def test_parser_sm_relation():
    line = (
        '{"kind":"state_machine_relation","from_sm_id":1152921504606848087,'
        '"to_sm_id":1152921504606846977,"relation":"top-to-raft"}'
    )
    records = parser().parse([line])
    assert len(records["state_machine_relation"]) == 1
    smr = records["state_machine_relation"][0]
    assert smr["relation"] == "top-to-raft"


def test_parser_state_machine():
    line = (
        '{"kind":"state_machine","id":1152921504606847000,'
        '"name":"DtxState","type":"DtxState"}'
    )
    records = parser().parse([line])
    assert len(records["state_machine"]) == 1
    assert records["state_machine"][0]["type"] == "DtxState"


def test_parser_malformed():
    line = '{"kind":"event","id":1152921504606846977}'
    _ = parser(verbose=True).parse([line])


def test_parser_fuzz():
    line = "a b c d"
    _ = parser().parse([line])


def test_parser_empty():
    line = ""
    _ = parser().parse([line])


def test_parser_state_machine_attribute():
    line = (
        '{"kind":"state_machine_attribute",'
        '"state_machine_id":1152921504606846977,"key":"node","value":1}'
    )
    records = parser().parse([line])
    assert len(records["state_machine_attribute"]) == 1
    assert records["state_machine_attribute"][0]["value"] == 1


def test_parser_preserves_extra_fields():
    line = (
        '{"kind":"event","id":1152921504606846977,'
        '"state_machine_id":1152921504606846977,'
        '"time":1783367062172542000,"name":"role=Follower",'
        '"extra_fields":{"name":"raw role","file":"raft.rs"}}'
    )
    record = parser().parse([line])["event"][0]
    assert record["extra_fields"] == {"name": "raw role", "file": "raft.rs"}
