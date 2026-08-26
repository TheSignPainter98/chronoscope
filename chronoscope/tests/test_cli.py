# -*- coding: utf-8 -*-
#
# This file is part of Chronoscope.
#
# SPDX-FileCopyrightText: 2024 Anatoliy Bilenko <anatoliy.bilenko@gmail.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

import sqlite3
import sys

import chronoscope
import chronoscope.utils as u


TIMESTAMP = "2055-11-29T20:57:56.489282133"


def test_create_uses_parser_by_default(tmp_path, monkeypatch):
    payload = (f'{{"timestamp":"{TIMESTAMP}","kind":"tick",'
               '"id":2,"pid":111,"type":"gw","event":"inited"}')
    trace_path = tmp_path / "events.jsonl"
    database_path = tmp_path / "chronoscope.db"
    trace_path.write_text(f"{payload}\n")
    monkeypatch.setattr(
        sys, "argv",
        ["chronoscope", "create", "--trace", str(trace_path),
         "--db", str(database_path)],
    )

    assert chronoscope.main() == 0

    with sqlite3.connect(database_path) as connection:
        tick = connection.execute(
            "SELECT id, time, type, event FROM tick"
        ).fetchone()
    assert tick == (u.pack(2, 111), u.ns(TIMESTAMP), "gw", "inited")
