# -*- coding: utf-8 -*-
#
# This file is part of Chronoscope.
#
# SPDX-FileCopyrightText: 2024 Anatoliy Bilenko <anatoliy.bilenko@gmail.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

import chronoscope.utils as u
from typing import Any
import json
import sys


class parser:
    tables = ["state_machine", "event", "event_relation",
              "state_machine_relation", "event_attribute"]

    def __init__(self, verbose=False):
        self.verbose = verbose

    def parse(self,
              fd_chunk: list[str]) -> dict[str, list[dict[str, Any]]]:
        records: dict[str, list] = {t: [] for t in self.tables}
        for line in fd_chunk:
            try:
                rec = json.loads(line)
            except Exception:
                continue
            if not isinstance(rec, dict):
                continue
            kind = rec.get("kind")
            if kind not in records:
                continue
            try:
                self.parse_record(records, rec)
            except Exception as e:
                if self.verbose:
                    print(f"{e}: line={line.strip()!r}", file=sys.stderr)
        return records

    def parse_record(self, records: dict[str, list], rec: dict[str, Any]):
        match rec["kind"]:
            case "event":
                self.parse_event(records, rec)
            case "state_machine":
                self.parse_state_machine(records, rec)
            case "event_relation":
                self.parse_event_relation(records, rec)
            case "state_machine_relation":
                self.parse_state_machine_relation(records, rec)
            case "event_attribute":
                self.parse_event_attribute(records, rec)

    def sm_id(self, raw: Any) -> int:
        return int(raw, 0)

    def event_id(self, raw: Any) -> int:
        return int(raw, 0)

    def parse_event(self, records: dict[str, list], rec: dict[str, Any]):
        sm = self.sm_id(rec["sm_id"])
        eid = self.event_id(rec["eid"])
        time = u.ns(rec["timestamp"])
        record = {
            "event": {
                "id": eid, "state_machine_id": sm,
                "time": time, "name": rec["name"],
            },
        }
        if "sm_type" in rec:
            record["state_machine"] = {
                "id": sm, "name": rec["sm_type"], "type": rec["sm_type"],
            }
        self.merge(records, record, rec)

    def parse_state_machine(self, records: dict[str, list], rec: dict[str, Any]):
        sm = self.sm_id(rec["sm_id"])
        eid = self.event_id(rec["eid"])
        self.merge(records, {
            "state_machine": {
                "id": sm, "name": rec["name"], "type": rec["name"],
            },
            "event": {
                "id": eid, "state_machine_id": sm,
                "time": u.ns(rec["timestamp"]), "name": rec["state"],
            },
        }, rec)

    def parse_event_relation(self, records: dict[str, list], rec: dict[str, Any]):
        peid = rec.get("peid")
        from_eid = None if peid is None else self.event_id(peid)
        sm = self.sm_id(rec["sm_id"])
        to_eid = self.event_id(rec["eid"])
        ts = u.ns(rec["timestamp"])
        relation = rec.get("relation", rec["kind"])
        self.merge(records, {
            "event_relation": {
                "from_event_id": from_eid,
                "to_event_id": to_eid,
                "from_sm_id": sm if from_eid is not None else None,
                "from_time": ts if from_eid is not None else None,
                "to_sm_id": sm,
                "to_time": ts,
                "relation": relation,
            },
        }, rec)

    def parse_state_machine_relation(self, records: dict[str, list],
                                     rec: dict[str, Any]):
        relation = rec["relation"]
        record = {
            "state_machine_relation": {
                "from_sm_id": self.sm_id(rec["from_sm_id"]),
                "to_sm_id": self.sm_id(rec["to_sm_id"]),
                "relation": relation,
            },
        }
        if "from_name" in rec:
            record["state_machine"] = {
                "id": self.sm_id(rec["from_sm_id"]),
                "name": rec["from_name"], "type": rec["from_name"],
            }
        self.merge(records, record, rec)

    def parse_event_attribute(self, records: dict[str, list], rec: dict[str, Any]):
        records["event_attribute"].append({
            "event_id": self.event_id(rec["eid"]),
            "key": rec["key"],
            "value": rec["value"],
        })

    def merge(self, records: dict[str, list], record: dict[str, Any],
              rec: dict[str, Any]):
        for table, payload in record.items():
            records[table].append(payload)

        # PL089: every entity may carry arbitrary key-value attributes;
        # unconsumed JSON fields land as attributes of the event at hand.
        known = {"timestamp", "kind", "sm_id", "sm_type", "eid", "peid",
                 "name", "state", "relation", "from_sm_id", "to_sm_id",
                 "from_name", "key", "value"}
        eid = None
        if "event" in record:
            eid = record["event"]["id"]
        elif "event_relation" in record:
            eid = record["event_relation"]["to_event_id"]
        if eid is None:
            return
        for key in sorted(set(rec) - known):
            value = rec[key]
            if not isinstance(value, str):
                value = json.dumps(value)
            records["event_attribute"].append({
                "event_id": eid, "key": key, "value": value,
            })
