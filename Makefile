SHELL:=/bin/bash

.PHONY: test
test: clean
	./system-test mkdb
	diff -u <(printf "6\n38\n34\n5\n") <(echo "select count(*) from state_machine;" \
	" select count(*) from event;" \
	" select count(*) from event_relation;" \
	" select count(*) from state_machine_relation;" | \
	sqlite3 test/chronoscope.db)


.PHONY: clean
clean:
	./system-test clean


.PHONY: dev-test
dev-test: dev-clean
	python3 -m chronoscope create -v -t test/raft_trace.jsonl
	./test/browse chronoscope.db ' '


.PHONY: dev-clean
dev-clean:
	rm -fv chronoscope.db
	rm -fv tree_111_*.png *.svg *.vcd *.gtkw
