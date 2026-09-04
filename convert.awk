#!/usr/bin/env -S gawk -M -f

# Translates raft_trace_fat.txt into Chronoscope JSONL (see log-entry-schema.json).
#
# Only top-level field is "timestamp" (the schema forbids other top-level
# properties); every schema field of the entry variant lives in "extra_fields".
#
# Field indices follow raft_chronoscope.yaml, which is 0-BASED (0 = the
# "raft[1]:" prefix). awk's $N is 1-based, so yaml index n == $(n+1) here:
#   p1 event:               sm_id=$5  eid=$6  name=$7
#   p2 event_relation:      sm_id=$5  eid=$6  peid=$7
#   p3 state_machine:       sm_id=$4  name=$5 state=$6 eid=$7
#   p4 state_machine_relation: from_sm_id=$4 to_sm_id=$5 relation=$6
#   p5 event_attribute:     eid=$4    attribute=$5
#
# Discrepancies between the trace format / raft_chronoscope.yaml and the
# schema are documented inline, at each case that handles them.
#
# Ids are emitted as decimal integers per the schema ("identifier": integer);
# gawk -M (arbitrary precision) is REQUIRED so 64-bit hex values convert without
# precision loss. Run via the shebang or `gawk -M -f convert.awk`.

# raft[1]: 2026-09-03T10:44:20.281531038 raft sm_id: 0x1000000000000001 eid=0x1000000000000002 restart |
BEGIN {
    errors = 0
}

/|$/ {
    split("", fields)      # clear per-record state (arrays are global)
    split("", extra_fields)

    timestamp = $2
    sub("T", " ", timestamp)
    fields["timestamp"] = timestamp

    type = $3
    switch (type) {
        case "raft":
            # Input:  raft[1]: 2026-09-03T10:44:20.281531038 raft sm_id: 0x1000000000000001 eid=0x1000000000000002 restart |
            #
            # Discrepancy: these lines are the schema's `event` variant, but
            # with a different spelling: `sm_id: 0x...` (colon-separated, not
            # k=v) and the event name as a bare trailing word (e.g. `restart`).
            # Mapped to id=eid, state_machine_id=sm_id, name=<word>.
            extra_fields["kind"] = "event"

            extra_fields["state_machine_id"] = parse_id($5)

            key_value($6, eid_kv)
            extra_fields["id"] = parse_id(eid_kv["value"])
            sm_by_event[extra_fields["id"]] = extra_fields["state_machine_id"]

            extra_fields["name"] = $7

            break
        case "event_attribute":
            # Input:  raft[1]: 2026-09-03T10:44:20.281633910 event_attribute eid=0x1000000000000002 raft:role=Follower |
            extra_fields["kind"] = "event_attribute"

            key_value($4, eid_kv)
            extra_fields["event_id"] = parse_id(eid_kv["value"])

            key_value($5, attr_kv)
            extra_fields["key"] = attr_kv["key"]
            extra_fields["value"] = attr_kv["value"]

            break
        case "event_relation":
            # Input:  raft[1]: 2026-09-03T10:44:20.319097740 event_relation sm_id: 0x100000000000000b eid=0x1000000000000015 peid=0x1000000000000011 |
            #
            # Discrepancy 1: no to_sm_id on the line, but the schema requires
            # it. The line's sm_id is the receiver's state machine (from_sm_id)
            # and peid identifies the sender event, so to_sm_id is DERIVED from
            # the earlier line that created the peid event, via an in-memory
            # eid->sm_id map built from `raft` and `state_machine` lines. This
            # assumes the producer line precedes the relation line in the trace
            # (it does in practice).
            #
            # Discrepancy 2: no `relation` value on the line
            # (raft_chronoscope.yaml p2 has none either), but the schema
            # requires `relation` (string). We emit the empty string "".
            extra_fields["kind"] = "event_relation"

            key_value($6, eid_kv)
            extra_fields["to_event_id"] = parse_id(eid_kv["value"])
            key_value($7, peid_kv)
            extra_fields["from_event_id"] = parse_id(peid_kv["value"])

            extra_fields["from_sm_id"] = parse_id($5)

            from_sm = sm_by_event[extra_fields["from_event_id"]]
            if (from_sm == "") {
                printf "event_relation: no sm_id known for peid %s\n", \
                    peid_kv["value"] | "cat 1>&2"
                errors++
                next
            }
            extra_fields["to_sm_id"] = from_sm
            extra_fields["relation"] = ""

            break
        case "state_machine":
            # Input:  sm[70205]: 2026-09-03T10:44:20.308495698 state_machine sm_id=0x1000000000000003 name=FirstRecordState state=NotALeader eid=0x1000000000000004 |
            #
            # Discrepancy: eid=0x... is not required by the schema (spec
            # fields: kind/id/name, optional type). We keep it as
            # extra_fields.event_id so no trace data is lost.
            extra_fields["kind"] = "state_machine"

            key_value($4, sm_id_kv)
            extra_fields["id"] = parse_id(sm_id_kv["value"])

            key_value($5, name_kv)
            extra_fields["name"] = name_kv["value"]

            key_value($6, state_kv)
            extra_fields["type"] = state_kv["value"]

            key_value($7, eid_kv)
            extra_fields["event_id"] = parse_id(eid_kv["value"])
            sm_by_event[extra_fields["event_id"]] = extra_fields["id"]

            break
        case "state_machine_relation":
            # Input:  sm[1]: 2025-06-07T11:00:14.026305714 state_machine_relation from_sm_id=0x7000000000000001 to_sm_id=0x1000000000000001 relation=top-to-raft |
            extra_fields["kind"] = "state_machine_relation"

            key_value($4, from_kv)
            extra_fields["from_sm_id"] = parse_id(from_kv["value"])

            key_value($5, to_kv)
            extra_fields["to_sm_id"] = parse_id(to_kv["value"])

            key_value($6, rel_kv)
            extra_fields["relation"] = rel_kv["value"]

            break
        default:
            printf "UNKNOWN TYPE: %s\n", type | "cat 1>&2"
            errors++
            next
    }

    printf "{"
    print_entries(fields)
    printf ", \"extra_fields\": {"
    print_entries(extra_fields)
    printf "}"
    printf "}\n"
}

END {
    if (errors > 0) {
        printf "%d error(s) occurred\n", errors | "cat 1>&2"
        exit 1
    }
}

# ---------------
# --- Helpers ---
# ---------------

# Prints `"key": "value", "key2": value2, ...`
function print_entries(entries) {
    # Constant key-order for better diffing.
    #
    # IMPORTANT: this list doubles as the ONLY source of key names — any field
    # not listed here is silently DROPPED from the output. It MUST be updated
    # whenever a case below starts emitting a new field, or that field will
    # never appear.
    # NOTE: indexed loop, not `for (k in arr)` — awk gives no ordering
    # guarantees for `in` iteration.
    # Key order matches raft_trace_fat.jsonl: keys are sorted alphabetically.
    n_priority = split("event_id from_event_id from_sm_id id key kind name" \
        " relation state_machine_id to_event_id to_sm_id timestamp type value" \
        , priority, " ")

    add_comma = 0
    for (i = 1; i <= n_priority; i++) {
        key = priority[i]
        if (!(key in entries)) {
            continue
        }

        if (add_comma) {
            printf ", "
        }
        add_comma = 1

        printf "\"%s\": %s", key, fmt(entries[key])
    }
}

# Heuristically reformats string values as JSON ones.
function fmt(value) {
    if (match(value, /^[0-9]+$/)) {
        return value
    }
    if (match(value, /^(true|false)$/)) {
        return value
    }
    return sprintf("\"%s\"", value)
}

# 64-bit hex id -> exact decimal integer (needs gawk -M); passthrough otherwise.
function parse_id(value) {
    if (match(value, /^0x[0-9a-fA-F]+$/)) {
        return sprintf("%d", strtonum(value))
    }
    return value
}

# Parses given `key=value` string.
function key_value(raw, ret) {
    match(raw, /(.*)=/)
    ret["key"] = substr(raw, RSTART, RLENGTH-1)

    match(raw, /=(.*)/)
    ret["value"] = substr(raw, RSTART+1, RLENGTH-1)
}
