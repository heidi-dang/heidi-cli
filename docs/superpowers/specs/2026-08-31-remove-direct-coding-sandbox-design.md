# Host-Native Direct Coding Design

## Goal

Heidi/CPTR gives ChatGPT an authenticated coding workspace on the user's local computer. Direct Coding is host-native execution, not a sandbox product.

## Execution model

`ChatGPT -> Heidi MCP -> CPTR owner-full -> selected CPTR workspace -> native host subprocess/PTY`

`owner-full` remains the default control profile. Commands use the existing CPTR identity, working-directory, session, logging, cancellation, and process-group machinery directly.

## Required removals

Remove the entire Direct Coding sandbox abstraction, including Bubblewrap, systemd sandboxing, container/VM sandbox profiles, automatic sandbox selection, installer/package dependencies used only for sandboxing, sandbox environment variables, compatibility metadata, verification logic, tests, and documentation.

Delete `apps/cptr/cptr/services/command_sandbox.py`. Direct Coding must not import or call it.

Remove these configuration surfaces where they exist:

- `CPTR_DIRECT_CODING_SANDBOX`
- `HEIDI_SANDBOX_PROFILE`
- `CPTR_DIRECT_CODING_CONTAINER_IMAGE`
- `CPTR_DIRECT_CODING_VM_RUNNER`
- Bubblewrap / `bwrap` dependency checks and install steps

## Preserved behavior

The change must preserve:

- default `owner-full` deployment policy;
- selected-workspace cwd semantics;
- native host toolchain and environment access;
- PAM/non-PAM identity handling;
- PTY and non-PTY native execution;
- command sessions, streaming/logging, cancellation, and process-group isolation;
- workspace registration/path semantics;
- MCP tool inventory and the tool-only invariant (no MCP resources capability and no `ui.resourceUri`);
- FDX, Git, OAuth, deployment, and workspace lifecycle behavior unrelated to sandboxing.

## Compatibility

Legacy sandbox environment variables are intentionally removed rather than retained as no-op compatibility flags. Existing deployments should stop persisting them on the next managed install/update.

`release/compatibility.json` must describe Direct Coding as host-native and must not advertise selectable sandbox profiles.

## Acceptance criteria

1. Repository production/runtime/config/docs contain no active Direct Coding sandbox implementation or selectable sandbox profile.
2. `command_sandbox.py` and its sandbox-specific tests are deleted.
3. Direct Coding `run_command` reaches the existing native host subprocess/PTY path directly.
4. Managed installer no longer installs Bubblewrap or writes sandbox configuration.
5. `owner-full` remains the default profile.
6. A regression test rejects reintroduction of the removed sandbox surface.
7. CPTR, installer/compatibility, MCP, and FDX CI remain green.
