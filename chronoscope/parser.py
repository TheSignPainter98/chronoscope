# -*- coding: utf-8 -*-
#
# This file is part of Chronoscope.
#
# SPDX-FileCopyrightText: 2024 Anatoliy Bilenko <anatoliy.bilenko@gmail.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

from typing import Any
import json
import sys


class parser:
    required_fields = {
        "state_machine": {"id", "name", "type"},
        "event": {"id", "state_machine_id", "time", "name"},
        "event_relation": {"from_event_id", "to_event_id", "from_sm_id",
                           "from_time", "to_sm_id", "to_time", "relation"},
        "state_machine_relation": {"from_sm_id", "to_sm_id", "relation"},
        "state_machine_attribute": {"state_machine_id", "key", "value"},
        "event_attribute": {"event_id", "key", "value"},
    }

    def __init__(self, verbose=False):
        self.tables = list(self.required_fields)
        self.verbose = verbose

    def parse(self, fd_chunk: list[str]) -> dict[str, list[dict[str, Any]]]:
        records: dict[str, list] = {table: [] for table in self.tables}
        for line in fd_chunk:
            try:
                record = json.loads(line)
            except Exception:
                continue
            if not isinstance(record, dict):
                continue

            kind = record.get("kind")
            if kind not in records:
                continue

            missing = self.required_fields[kind].difference(record)
            if missing:
                if self.verbose:
                    fields = ", ".join(sorted(missing))
                    print(f"missing required fields: {fields}: "
                          f"line={line.strip()!r}", file=sys.stderr)
                continue
            records[kind].append(record)
        return records
