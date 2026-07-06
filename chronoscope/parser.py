# -*- coding: utf-8 -*-
#
# This file is part of Chronoscope.
#
# SPDX-FileCopyrightText: 2024 Anatoliy Bilenko <anatoliy.bilenko@gmail.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

import chronoscope.utils as u
from typing import Callable
import yaml
import sys


class parser:
    def __init__(self, conf_path: str, verbose=False):
        # type -> (dest_table, parser_func)
        self.parsers: dict[str, tuple[str, Callable]] = {}
        # the parser knows about table names
        self.tables = ["state_machine", "event", "event_relation",
                       "state_machine_relation"]
        self.verbose = verbose
        self.load_config(conf_path)

    def load_config(self, conf_path: str):
        with open(conf_path) as fd:
            conf = yaml.safe_load(fd)
            conf_tables = [t for t in conf.keys() if t[0] != '.']
            if not all(t in self.tables for t in conf_tables):
                raise SyntaxError(f"a few of {conf_tables} aren't known!")

            for table in conf_tables:
                for trace in conf[table]:
                    self.register_parser(table, trace["type"],
                                         self.make_parser(table, trace["pos"]))

    def make_parser(self, table: str, kwargs: dict[str, int]) -> Callable:
        match table:
            case "event":
                return self.make_event_parser(**kwargs)
            case "event_relation":
                return self.make_event_rel_parser(**kwargs)
            case "state_machine_relation":
                return self.make_sm_rel_parser(**kwargs)
        raise NotImplementedError()

    def make_event_parser(self, type: int, time: int, event: int,
                          pid: int, sm_id: int) -> Callable:
        def parse(line: list[str], parse_type: str):
            if type >= len(line) or parse_type != line[type]:
                return None
            eid = None
            for token in line:
                if token.startswith("eid="):
                    eid = int(token.split("=", 1)[1], 16)
                    break
            if eid is None:
                return None
            sm = u.pack(int(line[sm_id]), int(line[pid]))
            return {
                "state_machine": {"id": sm, "name": parse_type, "type": parse_type},
                "event": {"id": eid, "state_machine_id": sm,
                          "time": u.ns(line[time]), "name": line[event]},
            }
        return parse

    def make_event_rel_parser(self, type: int, pid: int, sm_id: int,
                              peid: int, eid: int) -> Callable:
        def parse(line: list[str], parse_type: str):
            if type >= len(line) or parse_type != line[type]:
                return None
            raw_peid = line[peid].split("=", 1)[1]
            from_eid = None if raw_peid == "None" else int(raw_peid, 16)
            to_eid = int(line[eid].split("=", 1)[1], 16)
            sm = u.pack(int(line[sm_id]), int(line[pid]))
            record = {
                "event_relation": {
                    "from_event_id": from_eid,
                    "to_event_id": to_eid,
                    "relation": parse_type,
                },
                "state_machine": {"id": sm, "name": parse_type, "type": parse_type},
            }
            # For send events (peid=None) the 'to' event is a send event
            # that has no tick line, so we synthesize a minimal event
            # record to anchor it in the event table.
            if from_eid is None:
                record["event"] = {
                    "id": to_eid,
                    "state_machine_id": sm,
                    "time": u.ns(line[1]),
                    "name": "send",
                }
            return record
        return parse

    def make_sm_rel_parser(self, type: int, time: int,
                           orig_pid: int, dest_pid: int,
                           orig_id: int, dest_id: int) -> Callable:
        def parse(line: list[str], parse_type: str):
            if type >= len(line) or parse_type != line[type]:
                return None
            from_sm = u.pack(int(line[orig_id]), int(line[orig_pid]))
            to_sm = u.pack(int(line[dest_id]), int(line[dest_pid]))
            raw_eid = None
            for token in line:
                if token.startswith("eid="):
                    raw_eid = int(token.split("=", 1)[1], 16)
                    break
            record = {
                "state_machine_relation": {
                    "from_sm_id": from_sm,
                    "to_sm_id": to_sm,
                    "relation": parse_type,
                },
                "state_machine": [
                    {"id": from_sm, "name": "top", "type": "top"},
                    {"id": to_sm, "name": "raft", "type": "raft"},
                ],
            }
            if raw_eid is not None:
                record["event"] = {
                    "id": raw_eid,
                    "state_machine_id": to_sm,
                    "time": u.ns(line[time]),
                    "name": parse_type,
                }
            return record
        return parse

    def register_parser(self, dest_table: str, type: str, parse: Callable):
        self.parsers[type] = (dest_table, parse)

    def parse(self,
              fd_chunk: list[str]) -> dict[str, list[dict[str, str | int]]]:
        records: dict[str, list] = {t: [] for t in self.tables}
        for line in fd_chunk:
            for p_name, (dest_table, parser) in self.parsers.items():
                try:
                    if record := parser(line.split(), p_name):
                        self._merge_record(records, record)
                except Exception as e:
                    if self.verbose:
                        print(f"{e}: {line=}", file=sys.stderr)
        return records

    def _merge_record(self, records: dict, record: dict):
        for table, payload in record.items():
            if isinstance(payload, list):
                records[table].extend(payload)
            else:
                records[table].append(payload)
