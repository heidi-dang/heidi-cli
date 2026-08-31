# Direct Coding Sandbox Removal Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Remove the entire CPTR Direct Coding sandbox abstraction and make Direct Coding always use native host execution under the existing owner-full authority model.

**Architecture:** `run_command` keeps the existing identity, cwd, PTY/subprocess, session, logging, and cancellation machinery and no longer wraps Direct Coding commands in an isolation profile. Installer, compatibility, verification, tests, and docs lose the sandbox configuration surface entirely.

**Tech Stack:** Python/FastAPI CPTR, Bash installer/verification, JSON compatibility contract, pytest, GitHub Actions.

**Spec:** `docs/superpowers/specs/2026-08-31-remove-direct-coding-sandbox-design.md`

## Global Constraints

- Keep `owner-full` as the default control profile.
- Do not add MCP resources capability, `ui.resourceUri`, or any Apps UI entrypoint.
- Preserve command sessions, cwd semantics, identity handling, PTY/subprocess execution, logging, cancellation, Git/FDX/OAuth behavior.
- Remove rather than deprecate/no-op the Direct Coding sandbox configuration surface.

---

### Task 1: Add removal regression contract

**Files:**
- Create: `tests/test_direct_coding_host_contract.py`

**Interfaces:**
- Consumes: repository source tree.
- Produces: a CI contract that fails while sandbox implementation/configuration remains.

- [ ] Add assertions that runtime/install/compatibility sources do not contain `command_sandbox`, `CPTR_DIRECT_CODING_SANDBOX`, `HEIDI_SANDBOX_PROFILE`, `CPTR_DIRECT_CODING_CONTAINER_IMAGE`, `CPTR_DIRECT_CODING_VM_RUNNER`, or Bubblewrap/`bwrap` dependency wiring.
- [ ] Run root pytest through PR CI and verify RED against current code.
- [ ] Commit the failing contract.

### Task 2: Switch Direct Coding to native host execution

**Files:**
- Modify: `apps/cptr/cptr/utils/tools.py`
- Delete: `apps/cptr/cptr/services/command_sandbox.py`
- Delete: `apps/cptr/tests/test_command_sandbox.py`

**Interfaces:**
- Consumes: existing `run_command` native PTY/subprocess path.
- Produces: Direct Coding commands that execute directly using that path.

- [ ] Remove sandbox imports from `tools.py`.
- [ ] Remove the `direct_coding` sandbox wrapping block without changing identity/cwd/session behavior.
- [ ] Delete sandbox implementation and sandbox-specific tests.
- [ ] Verify CPTR tests in PR CI.

### Task 3: Remove installer/config/verification sandbox surface

**Files:**
- Modify: `scripts/install-core.sh`
- Modify: `scripts/install-lib.sh`
- Modify: `scripts/verify-stack.sh`
- Modify related installer contract tests if they encode sandbox behavior.

**Interfaces:**
- Consumes: existing managed installation flow.
- Produces: owner-full host-native CPTR configuration with no sandbox variables/dependency installation.

- [ ] Remove `SANDBOX_PROFILE` and all sandbox env persistence.
- [ ] Replace sandbox-specific dependency installation with only still-required security dependencies (`age`, `age-keygen`, `setcap`/`libcap2-bin`).
- [ ] Remove verification checks for sandbox profile/Bubblewrap.
- [ ] Keep owner-full default behavior unchanged.
- [ ] Verify installer/root tests and shell syntax in PR CI.

### Task 4: Update compatibility/docs contracts

**Files:**
- Modify: `release/compatibility.json`
- Modify docs/readmes returned by repository-wide sandbox searches.

**Interfaces:**
- Consumes: current compatibility schema.
- Produces: host-native Direct Coding documentation with no selectable sandbox profiles.

- [ ] Remove sandbox profile/default fields from compatibility metadata.
- [ ] Describe Direct Coding as host-native owner-authorized execution.
- [ ] Remove Bubblewrap/systemd/container/VM sandbox documentation.
- [ ] Verify `scripts/verify-compatibility.py` and root tests in PR CI.

### Task 5: Repository-wide closure verification

**Files:**
- Modify: `tests/test_direct_coding_host_contract.py` only if a false-positive exemption is required for historical design/plan documentation.

**Interfaces:**
- Consumes: complete branch.
- Produces: evidence that active sandbox code/configuration is gone.

- [ ] Search active source/config/docs for removed identifiers and confirm no applicable references remain.
- [ ] Run complete PR CI: installer, MCP, CPTR, FDX.
- [ ] Review PR diff for unrelated changes and MCP UI regressions.
- [ ] Only after green CI, mark PR ready and merge.
