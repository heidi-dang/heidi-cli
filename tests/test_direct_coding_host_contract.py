from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

ACTIVE_SURFACES = (
    ROOT / "apps/cptr/cptr/utils/tools.py",
    ROOT / "scripts/install-core.sh",
    ROOT / "scripts/install-lib.sh",
    ROOT / "scripts/verify-stack.sh",
    ROOT / "release/compatibility.json",
)

FORBIDDEN_DIRECT_CODING_SANDBOX_MARKERS = (
    "cptr.services.command_sandbox",
    "CPTR_DIRECT_CODING_SANDBOX",
    "HEIDI_SANDBOX_PROFILE",
    "CPTR_DIRECT_CODING_CONTAINER_IMAGE",
    "CPTR_DIRECT_CODING_VM_RUNNER",
    '"bubblewrap"',
    "bwrap",
)


def test_direct_coding_has_no_sandbox_implementation_or_configuration_surface() -> None:
    implementation = ROOT / "apps/cptr/cptr/services/command_sandbox.py"
    legacy_tests = ROOT / "apps/cptr/tests/test_command_sandbox.py"

    assert not implementation.exists(), "Direct Coding sandbox implementation must be removed"
    assert not legacy_tests.exists(), "sandbox-specific CPTR tests must be removed"

    offenders: list[str] = []
    for path in ACTIVE_SURFACES:
        text = path.read_text(encoding="utf-8")
        for marker in FORBIDDEN_DIRECT_CODING_SANDBOX_MARKERS:
            if marker in text:
                offenders.append(f"{path.relative_to(ROOT)}: {marker}")

    assert not offenders, "active sandbox surface remains:\n" + "\n".join(offenders)


def test_owner_full_remains_the_managed_default() -> None:
    installer = (ROOT / "scripts/install-core.sh").read_text(encoding="utf-8")
    assert "state_default HEIDI_CONTROL_PROFILE owner-full" in installer
