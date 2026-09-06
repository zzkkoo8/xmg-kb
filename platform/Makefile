.PHONY: init-runtime test test-phase1-contract test-phase1-live

init-runtime:
	mkdir -p ../work/parsed ../work/normalized ../work/quarantine ../work/temp ../logs ../backups ../_archive

test: init-runtime
	python3 -m pytest tests -q

test-phase1-contract:
	python3 -m pytest tests/phase1 -q -m "not live"

test-phase1-live:
	@test -n "$(COMPONENT)" || (echo "COMPONENT is required" >&2; exit 2)
	../platform/bootstrap.sh --verify "$(COMPONENT)"
