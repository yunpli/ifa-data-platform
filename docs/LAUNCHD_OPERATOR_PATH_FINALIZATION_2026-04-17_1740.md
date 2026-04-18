# Launchd Operator Path Finalization

_Date: 2026-04-17_1740_

## Scope
This batch does **not** keep retrying `launchctl bootstrap` from the current agent/harness shell.
Instead, it finalizes the correct operator path:
- repo-owned launchd service artifacts are ready
- final install/bootstrap must be executed from a proper local logged-in user terminal/session context
- stable operator/runtime docs are updated accordingly

---

## 1. Accepted root-cause judgment
Current launchd bootstrap failure is best explained by:
- **wrong execution context for LaunchAgent bootstrap**

Not primarily:
- bad plist syntax
- wrong GUI domain selection
- stale conflicting loaded service state

Supporting truth:
- `gui/503` is real and queryable
- plist validates with `plutil -lint`
- paths / scripts / logs exist
- current agent/harness shell is not treated as the final trusted LaunchAgent bootstrap environment

---

## 2. What is now ready in the repo
### Service artifacts prepared
- `scripts/unified_daemon_launchd.sh`
- `scripts/unified_daemon_launchd_boot.sh`
- plist target path:
  - `~/Library/LaunchAgents/ai.ifa.unified-runtime.plist`

### What they do
#### `unified_daemon_launchd.sh`
Provides the operator entrypoints:
- `install`
- `start`
- `stop`
- `restart`
- `status`
- `plist`

#### `unified_daemon_launchd_boot.sh`
Preserves startup safety by running:
1. runtime preflight / dirty-state repair
2. only then the actual unified runtime daemon loop

So launchd start does **not** bypass the preflight logic.

---

## 3. Final operator install procedure (run from real local terminal)
This is now the official production operator path on macOS.

### Step 1 — ensure artifacts are present
Repo:
- `/Users/neoclaw/repos/ifa-data-platform`

Scripts:
- `scripts/unified_daemon_launchd.sh`
- `scripts/unified_daemon_launchd_boot.sh`

### Step 2 — install/bootstrap the LaunchAgent
From a proper local logged-in user terminal session:
```bash
cd /Users/neoclaw/repos/ifa-data-platform
zsh scripts/unified_daemon_launchd.sh install
```

### Step 3 — start or kickstart service
```bash
zsh scripts/unified_daemon_launchd.sh start
```

### Step 4 — status
```bash
zsh scripts/unified_daemon_launchd.sh status
```

### Step 5 — stop
```bash
zsh scripts/unified_daemon_launchd.sh stop
```

### Step 6 — restart
```bash
zsh scripts/unified_daemon_launchd.sh restart
```

---

## 4. Exact launchctl-level commands
If operator wants direct launchctl control from the same proper local terminal context:

### plist path
```bash
~/Library/LaunchAgents/ai.ifa.unified-runtime.plist
```

### bootstrap
```bash
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/ai.ifa.unified-runtime.plist
```

### kickstart
```bash
launchctl kickstart -k gui/$(id -u)/ai.ifa.unified-runtime
```

### status
```bash
launchctl print gui/$(id -u)/ai.ifa.unified-runtime
```

### bootout / stop
```bash
launchctl bootout gui/$(id -u)/ai.ifa.unified-runtime
```

### Why `gui/$(id -u)` is still the documented default
The target runtime is a logged-in per-user GUI LaunchAgent model on this Mac.
`gui/$(id -u)` remains the intended documented target.
The issue encountered was not mainly “wrong domain string”; it was the bootstrap **execution context**.

---

## 5. Logs / evidence paths
Launchd-managed service writes to:
- `artifacts/service/unified_daemon.launchd.out.log`
- `artifacts/service/unified_daemon.launchd.err.log`

Preflight output:
- `artifacts/service/runtime_preflight_latest.json`

Runtime/operator DB surfaces remain:
- `ifa2.runtime_worker_schedules`
- `ifa2.runtime_worker_state`
- `ifa2.unified_runtime_runs`
- `ifa2.job_runs`
- `ifa2.archive_runs`
- `ifa2.archive_checkpoints`
- `ifa2.archive_target_catchup`

---

## 6. What is already working vs what still must be done locally
### Already ready in repo
- launchd service scripts
- launchd boot script with preflight preserved
- plist generation path
- stable operator commands documented
- preflight/repair logic integrated into startup path

### Still must be executed from real local terminal context
- final `launchctl bootstrap` / install
- final `launchctl kickstart`
- final survivability validation against gateway restart in that trusted terminal/service context

This is the truthful boundary.

---

## 7. Final truthful judgment
### Ready now
The repo is now prepared with the official macOS launchd-managed production service path.
The preflight logic is preserved in the startup chain.
Operator instructions are now explicit and no longer ambiguous.

### Not yet falsely claimed
This batch does **not** claim that launchd installation/bootstrap has already been fully validated from the current agent/harness shell.
That would be dishonest.

### Correct production statement
- **Repo/installable service artifacts are ready**
- **Final launchd bootstrap/install must be executed from a proper local logged-in user terminal/session context**
- **Agent/harness shell is not the final trusted bootstrap environment**

That is now the official and truthful operator path.
