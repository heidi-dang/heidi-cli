# UI Port Plan: Reference UI → Heidi CLI UI

## Overview

Port design/CSS from reference UI (`/tmp/work-theme-reference`) into existing Vite React UI (`ui/`), replacing socket.io with existing SSE client.

## Reference UI Structure

```
/tmp/work-theme-reference/
├── App.tsx              # Main app component
├── components/
│   ├── AgentArea.tsx    # Agent selection/display
│   ├── ChatArea.tsx     # Chat messages
│   ├── DeviceFlowModal.tsx  # OAuth device flow
│   ├── HeifiLogo.tsx    # Logo component
│   ├── RightSidebar.tsx # Right panel (tools/history)
│   ├── SettingsModal.tsx # Settings dialog
│   ├── Sidebar.tsx      # Left sidebar (nav)
│   ├── SshForm.tsx      # SSH connection form
│   └── TerminalArea.tsx # Terminal output
└── lib/
    └── sshServer.ts     # API client (socket.io based)
```

## Current Heidi CLI UI Structure

```
ui/
├── src/
│   ├── App.tsx
│   ├── main.tsx
│   ├── api/
│   │   ├── heidi.ts    # REST client ✓
│   │   └── stream.ts   # SSE client ✓
│   ├── components/
│   │   ├── AgentArea.tsx
│   │   ├── ChatArea.tsx
│   │   ├── Sidebar.tsx
│   │   ├── TerminalArea.tsx
│   │   ├── SettingsModal.tsx
│   │   └── RightSidebar.tsx
│   └── types/
│       └── index.ts
└── vite.config.ts
```

## Port Steps

### Phase 1: Design Copy

1. **Copy CSS/Theme** - Extract styles from reference components
   - Color palette
   - Typography
   - Layout/spacing
   - Component styling

2. **Update App.tsx** - Adopt reference layout structure
   - Keep existing API integration
   - Adapt component composition

3. **Component Updates** - Replace styles, keep logic
   - AgentArea: Copy styling, keep heidi.ts integration
   - ChatArea: Copy styling, keep message handling
   - Sidebar: Copy styling, keep navigation
   - TerminalArea: Copy styling, keep SSE streaming
   - SettingsModal: Copy styling
   - RightSidebar: Copy styling

### Phase 2: API Integration (if needed)

1. **SSH Client** - Replace socket.io with REST/SSE
   - Reference: `lib/sshServer.ts`
   - Target: Create `src/api/ssh.ts` using existing `heidi.ts` patterns

2. **Device Flow** - Port OAuth device flow
   - Reference: `DeviceFlowModal.tsx`
   - Implement using heidi backend `/auth/device/*` endpoints

## Key Differences to Handle

| Reference | Current | Action |
|-----------|---------|--------|
| socket.io | SSE | Keep existing SSE (`stream.ts`) |
| No types | TypeScript | Keep types (`types/index.ts`) |
| Full app | UI shell | Adapt to existing structure |

## NOT in Scope

- Node.js backend (reference has Express/socket.io)
- Database changes
- API contract changes

## Testing Checklist

- [ ] UI builds without errors
- [ ] Health check works
- [ ] Agent list loads
- [ ] Chat messages send/receive
- [ ] Terminal streaming works
- [ ] Settings persist
- [ ] SSH form renders (even if backend stub)
