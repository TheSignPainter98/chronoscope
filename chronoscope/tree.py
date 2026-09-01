# -*- coding: utf-8 -*-
#
# This file is part of Chronoscope.
#
# SPDX-FileCopyrightText: 2024 Anatoliy Bilenko <anatoliy.bilenko@gmail.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

import chronoscope.db as db
import chronoscope.utils as utils
from graphviz import Graph  # type: ignore
from typing import cast

# https://graphviz.readthedocs.io/en/stable/examples.html#structs-py
FMT_NODE = """<
<table border="0" cellborder="1" cellspacing="0">
<tr><td>{}</td></tr><tr><td>{}</td></tr></table>>
"""

class attr_visitor:
    def __init__(self, graph: Graph):
        self.graph = graph

    def __call__(self, timeline: list[dict], current: int,
                 parent: None | int):
        machine = cast(dict[str, object],
                       (db.state_machine
                        .select()
                        .where(db.state_machine.id == current)
                        .dicts()
                        .get()))
        attributes = (db.state_machine_attribute
                      .select()
                      .where(db.state_machine_attribute.state_machine_id == current)
                      .dicts())
        rows = [f"name={machine['name']}", f"type={machine['type']}"]
        for attribute in attributes:
            attribute_data = cast(dict[str, object], attribute)
            rows.append(f"{attribute_data['key']}={attribute_data['value']}")
        contents = "<br/>".join(rows)
        label = FMT_NODE.format(utils.format_event_id(current), contents)
        self.graph.node(str(current), label)

        if parent is not None:
            self.graph.edge(str(parent), str(current))

def plot(origin: int, depth_max=50):
    g = Graph(strict=True, format="png", node_attr={"shape": "plaintext"})
    db.iterate(origin, None, attr_visitor(g), 0, depth_max)
    net_pid, boot_counter, id = utils.unpack_event_id(origin)
    g.render(f"tree_{net_pid}_{boot_counter}_{id}", cleanup=True)
