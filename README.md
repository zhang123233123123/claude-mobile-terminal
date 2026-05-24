# Mobile Terminal

A lightweight self-hosted web terminal that lets you run any CLI program from your phone — no app install required, just a browser.

Built around the idea that your phone + voice should be enough to get real work done, anywhere.

> **This fork**: adds native Windows support (pywinpty backend), a PowerShell launcher, a mobile virtual key bar (Esc / arrows / Ctrl+C / `/` / `|` / Home / End), and removes HTTP/WS authentication for users who treat the random tunnel URL as the only secret. See [Fork changes](#fork-changes) for details.

## What it does

- **File browser** — navigate your local directories, tap a folder to open a terminal there
- **Session history** — picks up existing sessions (e.g. `claude --resume`) so you never lose context
- **Auto-reconnect** — network drops are handled silently; resumes the same session when back online
- **Virtual key bar** — arrow keys, Ctrl+C, Esc, Tab and other terminal keys missing from mobile keyboards
- **Cross-platform** — works on macOS, Linux, and Windows (via pywinpty)
- **Any CLI program** — Claude Code, Python REPL, Node, Ollama, bash, SSH, anything

## Quick start

### macOS / Linux

```bash
git clone https://github.com/henrCh1/claude-mobile-terminal
cd claude-mobile-terminal

pip install -r requirements.txt

cp .env.example .env
# Edit .env — optional now that auth is removed, but AUTH_PASS may be loaded by other code

cp config.json.example config.json
# Edit config.json — set your allowed directories

./start.sh
```

### Windows (PowerShell)

```powershell
git clone https://github.com/henrCh1/claude-mobile-terminal
cd claude-mobile-terminal

# Install deps — pywinpty replaces ptyprocess on Windows
py -m pip install --user fastapi "uvicorn[standard]" pywinpty

# Install cloudflared (optional, only needed for public access)
winget install --id Cloudflare.cloudflared

Copy-Item config.json.example config.json
# Edit config.json — use Windows paths, e.g. C:\Users\YOU\Desktop
.\start.ps1
```

Cloudflare Tunnel prints a public `https://xxx.trycloudflare.com` URL. Open it on your phone.

## Configuration

**`config.json`** *(copy from `config.json.example`, gitignored — local to each install)*
```json
{
  "allowed_dirs": [
    "C:\\Users\\YOUR_USERNAME\\Desktop",
    "C:\\Users\\YOUR_USERNAME\\Downloads"
  ],
  "port": 8080
}
```

On macOS/Linux use `/Users/you/Desktop` style paths.

**`.env`** *(optional in this fork — auth has been removed)*
```
AUTH_USER=your_username
AUTH_PASS=your_password
```

## Changing the program

By default it runs `claude`. To use something else, edit `server.py`:

```python
cmd = ["claude"]          # Claude Code (default)
cmd = ["python3"]         # Python REPL
cmd = ["node"]            # Node.js
cmd = ["ollama", "run", "llama3"]  # Local LLM
cmd = ["bash"]            # Full shell (Unix)
cmd = ["powershell"]      # PowerShell (Windows)
cmd = ["ssh", "user@host"]         # Remote server
```

## Fork changes

Modifications in this fork relative to [`zhang123233123123/claude-mobile-terminal`](https://github.com/zhang123233123123/claude-mobile-terminal):

### Windows support
- **`server.py`** — conditional import: uses `pywinpty.PtyProcess` on Windows, `ptyprocess.PtyProcessUnicode` on Unix. Drop-in replacement, same `spawn / read / write / setwinsize / terminate` API.
- **`start.ps1`** — PowerShell equivalent of `start.sh`. Loads `.env`, reads `port` from `config.json`, launches uvicorn as a background job, then runs cloudflared in foreground. Falls back to LAN-only mode if cloudflared isn't installed.
- **`config.json`** — untracked from git (`.gitignore`'d); ships as `config.json.example` with Windows-style placeholders. Each install gets a clean working tree.

### Mobile UX
- **`index.html`** — added a horizontally scrollable virtual key bar below the xterm container with: `Esc`, `Tab`, `↑`, `↓`, `←`, `→`, `^C`, `^D`, `Clr`, `/`, `|`, `Home`, `End`. Each key sends the correct ANSI escape sequence over the existing WebSocket. Buttons use `preventDefault()` on `mousedown`/`touchstart` so the mobile soft keyboard stays focused.

### Auth removal
- **`server.py`** — HTTP Basic Auth and WebSocket token check both removed. The random Cloudflare quick-tunnel subdomain becomes the only access secret. Restore the original `auth()` and WS token check if you need real authentication (e.g. when sharing the URL or running on a stable domain).

## Stack

- **Backend** — FastAPI + pywinpty (Windows) / ptyprocess (Unix), PTY proxy over WebSocket
- **Frontend** — xterm.js 5.3 with FitAddon (no build step, CDN only)
- **Tunnel** — Cloudflare Tunnel (`cloudflared`)

## Requirements

- Python 3.9+
- `cloudflared` — `brew install cloudflare/cloudflare/cloudflared` (macOS) or `winget install --id Cloudflare.cloudflared` (Windows)
- The CLI program you want to expose (e.g. `claude`)

## Security note

This fork ships with **no authentication**. Anyone who has the tunnel URL gets a remote shell on your machine. Treat the URL like a password. If you intend to use a named (stable) tunnel or share the URL, re-enable auth by restoring the `auth()` function and `secrets.compare_digest(token, AUTH_PASS)` check in `server.py`.
