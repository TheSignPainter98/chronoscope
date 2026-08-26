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

    required_fields = {
        "tick": {"timestamp", "kind", "id", "pid", "type", "event"},
        "attr": {"timestamp", "kind", "id", "pid", "type", "name", "value"},
        "relation": {"timestamp", "kind", "type", "orig_pid", "dest_pid",
                     "orig_id", "dest_id"},
    }

    def __init__(self, verbose=False):
        self.tables = list(self.required_fields)
        self.verbose = verbose

    def parse(self, fd_chunk: list[str]) -> dict[str, list[dict[str, Any]]]:
        records: dict[str, list] = {t: [] for t in self.tables}
        for line in fd_chunk:
            try:
                rec = json.loads(line)
                kind = rec["kind"]
            except Exception:
                continue
            if kind not in records:
                continue
            try:
                missing = self.required_fields[kind].difference(rec)
                if missing:
                    fields = ", ".join(sorted(missing))
                    raise ValueError(f"missing required fields: {fields}")

                timestamp = u.ns(rec["timestamp"])
                match kind:
                    case "tick":
                        rec["id"] = u.pack(rec["id"], rec["pid"])
                        rec["time"] = timestamp
                    case "attr":
                        rec["id"] = u.pack(rec["id"], rec["pid"])
                        rec["val"] = rec["value"]
                    case "relation":
                        rec["orig"] = u.pack(rec["orig_id"], rec["orig_pid"])
                        rec["dest"] = u.pack(rec["dest_id"], rec["dest_pid"])

                records[kind].append(rec)
            except Exception as e:
                if self.verbose:
                    print(f"{e}: line={line.strip()!r}", file=sys.stderr)
        return records
