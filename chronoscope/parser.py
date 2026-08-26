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
        "attr": {"timestamp", "kind", "id", "pid", "name", "val"},
        "relation": {"timestamp", "kind", "orig", "dest", "type"},
    }

    def __init__(self, verbose=False):
        self.tables = list(self.required_fields)
        self.verbose = verbose

    def parse(self, fd_chunk: list[str]) -> dict[str, list[dict[str, Any]]]:
        records: dict[str, list] = {t: [] for t in self.tables}
        for line in fd_chunk:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except Exception:
                continue
            if not isinstance(rec, dict):
                continue
            kind = rec.get("kind")
            if not isinstance(kind, str) or kind not in self.required_fields:
                continue
            try:
                missing = self.required_fields[kind].difference(rec)
                if missing:
                    fields = ", ".join(sorted(missing))
                    raise ValueError(f"missing required fields: {fields}")

                timestamp = self.make_timestamp(rec["timestamp"])
                match kind:
                    case "tick":
                        rec["id"] = u.pack(rec["id"], rec["pid"])
                        rec["time"] = timestamp
                    case "attr":
                        rec["id"] = u.pack(rec["id"], rec["pid"])
                    case "relation":
                        orig, dest = rec["orig"], rec["dest"]
                        rec["orig"] = u.pack(orig["id"], orig["pid"])
                        rec["dest"] = u.pack(dest["id"], dest["pid"])

                records[kind].append(rec)
            except Exception as e:
                if self.verbose:
                    print(f"{e}: {line=}", file=sys.stderr)
        return records

    @staticmethod
    def make_timestamp(timestamp: Any) -> int:
        if not isinstance(timestamp, str):
            raise ValueError(f"invalid timestamp: {timestamp!r}")
        return u.ns(timestamp)
