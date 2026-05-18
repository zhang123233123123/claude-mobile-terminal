# Mobile Terminal

A lightweight self-hosted web terminal that lets you run any CLI program from your phone — no app install required, just a browser.

Built around the idea that your phone + voice should be enough to get real work done, anywhere.

## What it does

- **File browser** — navigate your local directories, tap a folder to open a terminal there
- **Session history** — picks up existing sessions (e.g. `claude --resume`) so you never lose context
- **Auto-reconnect** — network drops are handled silently; resumes the same session when back online
- **Secure** — HTTP Basic Auth + token-protected WebSocket; exposed via Cloudflare Tunnel (no public IP needed)
- **Any CLI program** — Claude Code, Python REPL, Node, Ollama, bash, SSH, anything

## Quick start

```bash
# 1. Clone
git clone https://github.com/zhang123233123123/claude-mobile-terminal
cd claude-mobile-terminal

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure
cp .env.example .env
# Edit .env — set AUTH_USER and AUTH_PASS

# 4. Edit config.json — set your allowed directories
# 5. Start
./start.sh
```

Cloudflare Tunnel prints a public `https://xxx.trycloudflare.com` URL. Open it on your phone.

## Configuration

**`.env`**
```
AUTH_USER=your_username
AUTH_PASS=your_password
```

**`config.json`**
```json
{
  "allowed_dirs": [
    "/Users/you/Desktop",
    "/Users/you/Downloads"
  ],
  "port": 8080
}
```

## Changing the program

By default it runs `claude`. To use something else, edit `server.py`:

```python
cmd = ["claude"]          # Claude Code (default)
cmd = ["python3"]         # Python REPL
cmd = ["node"]            # Node.js
cmd = ["ollama", "run", "llama3"]  # Local LLM
cmd = ["bash"]            # Full shell
cmd = ["ssh", "user@host"]         # Remote server
```

## Stack

- **Backend** — FastAPI + ptyprocess (PTY proxy over WebSocket)
- **Frontend** — xterm.js (no build step, CDN only)
- **Tunnel** — Cloudflare Tunnel (`cloudflared`)

## Requirements

- Python 3.9+
- `cloudflared` (`brew install cloudflare/cloudflare/cloudflared`)
- The CLI program you want to expose (e.g. `claude`)
