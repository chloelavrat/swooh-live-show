VENV     := /tmp/lpx_venv
PYTHON   := $(VENV)/bin/python
PIP      := $(VENV)/bin/pip
PYTEST   := $(VENV)/bin/pytest
NPM      := npm --prefix control_room

# ── Setup ──────────────────────────────────────────────────────────────────────

.PHONY: setup
setup: setup-python setup-node

setup-python:
	python3 -m venv $(VENV)
	$(PIP) install --quiet pyyaml pytest

setup-node:
	$(NPM) install

# ── Config conversion ──────────────────────────────────────────────────────────

.PHONY: convert
convert:
	$(PYTHON) lpx_95_custom/scripts/convert_configs.py

# ── Run targets ────────────────────────────────────────────────────────────────

# bridge + UI only  (use with real Launchpad X + Ableton)
.PHONY: run
run: convert
	@echo "Starting bridge + UI  (Ctrl-C stops all)"
	@trap 'kill 0' INT; \
	  $(NPM) run bridge & \
	  $(NPM) run dev & \
	  wait

# bridge + simulator + UI  (no hardware needed)
.PHONY: run-simulator
run-simulator: convert
	@echo "Starting bridge + simulator + UI  (Ctrl-C stops all)"
	@trap 'kill 0' INT; \
	  $(NPM) run bridge & \
	  $(PYTHON) lpx_95_custom/scripts/simulator.py & \
	  $(NPM) run dev & \
	  wait

# simulator only  (quick behavior test, no bridge/UI)
.PHONY: simulator
simulator: convert
	cd lpx_95_custom && $(PYTHON) scripts/simulator.py

# ── Tests ──────────────────────────────────────────────────────────────────────

.PHONY: test
test: convert
	cd lpx_95_custom && $(PYTEST) tests/ -v

# ── Build (production bundle) ──────────────────────────────────────────────────

.PHONY: build
build: convert
	$(NPM) run build

# ── Install Ableton script ─────────────────────────────────────────────────────

.PHONY: install
install: convert
	$(PYTHON) lpx_95_custom/scripts/install.py

# ── Clean ──────────────────────────────────────────────────────────────────────

.PHONY: clean
clean:
	rm -rf control_room/dist control_room/node_modules
	rm -rf lpx_95_custom/__pycache__ lpx_95_custom/**/__pycache__
	find lpx_95_custom -name "*.pyc" -delete
