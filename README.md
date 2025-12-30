![Get rickrolled](https://c.tenor.com/x8v1oNUOmg4AAAAC/tenor.gif)

<small>GET RICKROLLED! Lol...</small>

# Rickroll Firewall 🔒🎸

An event-driven “anti-rickroll” agent built with the **Ascender Framework**. Instead of exposing HTTP endpoints, the app boots a link-monitoring graph that listens to desktop link-open events and silently blocks anything matching Rick Astley bait.

> _Never gonna click that link again._

---

## Features
- **Zero-HTTP design** – controllers hydrate via custom hooks, no REST surface required.
- **Desktop aware** – tails `~/.local/share/recently-used.xbel` for new browser launches.
- **Heuristic detection** – pattern matcher and confidence scoring against classic Rickroll URLs.
- **Ascender-native** – services, injectables, and controller hooks match Ascender’s Angular-style DI.
- **Transparent logging** – blocked attempts recorded with timestamps and reasons.

---

## Quick Start
1. **Install prerequisites**
   - Python 3.11+
   - Poetry
   - Ascender CLI (`pip install ascender-framework`)
2. **Install dependencies**
   ```bash
   poetry install
   ```
3. **Run the Ascender app**
   ```bash
   ascender run serve
   ```
4. **Trigger a Rickroll**
   - Open a browser and visit a known Rickroll URL (e.g., `https://youtu.be/dQw4w9WgXcQ`).
   - Watch the terminal logs – the link controller will flag and block the attempt.

For development convenience you can compile the graph without launching a server:

```bash
python -m compileall src
```

---

## Run It As A Daemon (systemd user service)
Keep the firewall on autopilot with a minimal user-level systemd unit.

1. **Discover the Poetry environment path** (one-time):
  ```bash
  POETRY_ENV="$(poetry env info --path)"
  echo "Using env at: $POETRY_ENV"
  ```
2. **Drop in the unit file**:
  ```bash
  mkdir -p ~/.config/systemd/user
  cat <<'EOF' > ~/.config/systemd/user/rickroll-firewall.service
  [Unit]
  Description=Rickroll Firewall (Ascender)
  After=network.target

  [Service]
  Type=simple
  Environment=ASC_MODE=server
  WorkingDirectory=%h/Projects/rickroll-firewall
  ExecStart=%h/Projects/rickroll-firewall/.venv/bin/ascender run serve
  Restart=on-failure
  RestartSec=2

  [Install]
  WantedBy=default.target
  EOF
  ```
  > If Poetry keeps the virtualenv elsewhere, replace `ExecStart` with `$POETRY_ENV/bin/ascender run serve`.
3. **Enable and monitor**:
  ```bash
  systemctl --user daemon-reload
  systemctl --user enable --now rickroll-firewall.service
  journalctl --user -fu rickroll-firewall.service
  ```

That’s it—no root privileges, no cron jobs, and the firewall revives automatically after reboots.

---

## How It Works
- **Services** – `link_monitor_service.py` hosts an async dispatcher and a recent-file watcher injectable, emitting `LinkClickEvent` payloads.
- **Detection** – `services/rickroll_firewall_service.py` packages a detector and firewall service that cache analysis results and keep a rolling block history.
- **Custom Hook** – `controllers/link_hooks.py` defines `@OnLinkOpen`, a `ControllerDecoratorHook` that subscribes controller methods to the monitor when the router graph hydrates.
- **Controller** – `controllers/link_controller.py` runs headless; its hook receives events, waits for the firewall verdict, and logs decisions.

Everything lives inside the Ascender router graph so the lifecycle stays asynchronous and testable.

---

## Project Structure
```
src/
  common/                 # Shared dataclasses for link events and analysis
  controllers/
    link_controller.py    # Standalone controller listening for link-open events
    link_hooks.py         # Custom ControllerDecoratorHook implementation
  services/
    rickroll_firewall_service.py  # Detector + firewall injectables
  link_monitor_service.py # Dispatcher + desktop watcher services
```

---

## Configuration
- Detection runs from static URL patterns; add more heuristics in `RickrollDetectorService._PATTERNS`.
- The watcher polls once per second; tweak `poll_interval` when constructing `DesktopRecentLinkWatcher`.
- Logs use the `RickrollFirewall` logger name. Hook into your logging stack or change levels via standard Python logging config.

---

## Development Workflow
- Generate new services/controllers with Ascender CLI:
  ```bash
  ascender g s my_service
  ascender g c controllers/my-feature --standalone
  ```
- Use `poetry run` to execute scripts inside the virtualenv.
- Keep hooks lightweight – they execute inside the router hydration phase.

---

## Contributing
Issues and PRs are welcome. Please lint the codebase (`python -m compileall src`) and describe any new heuristics or watchers you add.

---

## License
Distributed under the MIT License. See `LICENSE` for details.
