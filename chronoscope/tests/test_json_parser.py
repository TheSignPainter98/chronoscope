import pytest
import chronoscope.utils as u
from chronoscope.parser import json_parser


def test_json_parser_tick():
    line = '{"tick": {"time": 1, "type": "gw", "event": "inited", "id": 2, "pid": 111}}'
    records = json_parser().parse([line])
    assert records["tick"] == [{"time": 1, "type": "gw", "event": "inited",
                                "id": u.pack(2, 111)}]


def test_json_parser_tick_ns_time():
    line = '{"tick": {"time": "2055-11-29T20:57:56.489282133", "type": "gw", "event": "inited", "id": 2, "pid": 111}}'
    records = json_parser().parse([line])
    assert records["tick"][0]["time"] == u.ns("2055-11-29T20:57:56.489282133")


def test_json_parser_relation():
    line = ('{"relation": {"orig": {"id": 1, "pid": 111}, '
            '"dest": {"id": 2, "pid": 111}, "type": "conn-to-gw"}}')
    records = json_parser().parse([line])
    assert records["relation"] == [{"orig": u.pack(1, 111),
                                    "dest": u.pack(2, 111),
                                    "type": "conn-to-gw"}]


def test_json_parser_attr():
    line = '{"attr": {"id": 2, "pid": 111, "name": "foo", "val": "bar"}}'
    records = json_parser().parse([line])
    assert records["attr"] == [{"id": u.pack(2, 111), "name": "foo",
                                "val": "bar"}]


def test_json_parser_unknown_table_skipped():
    line = '{"bogus": {"id": 1}}'
    records = json_parser().parse([line])
    assert all(not v for v in records.values())


def test_json_parser_multiple_keys_skipped():
    line = '{"tick": {"time": 1, "type": "gw", "event": "e", "id": 2, "pid": 111}, "attr": {"id": 2, "pid": 111, "name": "n", "val": "v"}}'
    records = json_parser().parse([line])
    assert all(not v for v in records.values())


def test_json_parser_missing_field_skipped():
    line = '{"tick": {"time": 1}}'
    records = json_parser().parse([line])
    assert all(not v for v in records.values())


def test_json_parser_garbage_and_empty_lines():
    records = json_parser().parse(["not json", "", "   "])
    assert all(not v for v in records.values())


def test_json_parser_noise_silent_even_in_verbose(capsys):
    noise = ["not json", "", "   ", "[1, 2]", '"str"', "42", "{}",
             '{"tick": {"time": 1}, "attr": {"id": 2}}',
             '{"bogus": {"id": 1}}']
    records = json_parser(verbose=True).parse(noise)
    assert all(not v for v in records.values())
    assert capsys.readouterr().err == ""


def test_json_parser_broken_record_reported_only_in_verbose(capsys):
    line = '{"tick": {"time": 1}}'
    assert all(not v for v in json_parser().parse([line]).values())
    assert capsys.readouterr().err == ""
    assert all(not v for v in json_parser(verbose=True).parse([line]).values())
    assert capsys.readouterr().err != ""


def test_json_parser_invalid_time_type_dropped(capsys):
    line = '{"tick": {"time": null, "type": "gw", "event": "e", "id": 2, "pid": 111}}'
    records = json_parser().parse([line])
    assert all(not v for v in records.values())
    assert json_parser(verbose=True).parse([line])
    assert "invalid time" in capsys.readouterr().err
