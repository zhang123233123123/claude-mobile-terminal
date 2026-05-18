import asyncio
import json
import os
import secrets
from datetime import datetime
from pathlib import Path

import ptyprocess
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Query, Depends, HTTPException, status
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials

app = FastAPI()
security = HTTPBasic()

AUTH_USER = os.environ.get("AUTH_USER", "admin")
AUTH_PASS = os.environ.get("AUTH_PASS", "")


def auth(credentials: HTTPBasicCredentials = Depends(security)):
    valid = (
        secrets.compare_digest(credentials.username.encode(), AUTH_USER.encode()) and
        secrets.compare_digest(credentials.password.encode(), AUTH_PASS.encode())
    )
    if not valid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            headers={"WWW-Authenticate": "Basic"},
        )

BASE_DIR = Path(__file__).parent
HTML_FILE = BASE_DIR / "index.html"
CONFIG_FILE = BASE_DIR / "config.json"


def load_config() -> dict:
    if CONFIG_FILE.exists():
        return json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
    return {"allowed_dirs": [], "port": 8080}


def is_path_allowed(path: Path, allowed_dirs: list) -> bool:
    resolved = path.resolve()
    for d in allowed_dirs:
        try:
            resolved.relative_to(Path(d).resolve())
            return True
        except ValueError:
            pass
    return False


@app.get("/")
async def index(_: None = Depends(auth)):
    html = HTML_FILE.read_text(encoding="utf-8").replace("__WS_TOKEN__", AUTH_PASS)
    return HTMLResponse(html)


def encode_project_path(path: str) -> str:
    return "".join(c if c.isalnum() else "-" for c in path)


def extract_text(content) -> str:
    if isinstance(content, str):
        return content.strip()
    if isinstance(content, list):
        for block in content:
            if isinstance(block, dict) and block.get("type") == "text":
                return block["text"].strip()
    return ""


@app.get("/api/claude-sessions")
async def claude_sessions(path: str = "", _: None = Depends(auth)):
    project_dir = Path.home() / ".claude" / "projects" / encode_project_path(path)
    if not project_dir.is_dir():
        return []

    sessions = []
    for f in sorted(project_dir.glob("*.jsonl"), key=lambda x: x.stat().st_mtime, reverse=True):
        session_id = f.stem
        mtime = datetime.fromtimestamp(f.stat().st_mtime)
        messages = []  # list of {"role": "user"|"assistant", "text": str}
        try:
            with open(f, encoding="utf-8", errors="replace") as fp:
                for line in fp:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        event = json.loads(line)
                        etype = event.get("type")
                        if etype in ("user", "assistant"):
                            text = extract_text(event.get("message", {}).get("content", ""))
                            if text:
                                messages.append({"role": etype, "text": text})
                    except json.JSONDecodeError:
                        pass
        except Exception:
            pass

        title = messages[0]["text"][:60] if messages else session_id[:8]
        # Return up to 6 messages as preview (truncated)
        preview = [{"role": m["role"], "text": m["text"][:120]} for m in messages[:6]]

        sessions.append({
            "id": session_id,
            "title": title,
            "last_modified": mtime.strftime("%Y-%m-%d %H:%M"),
            "message_count": len(messages),
            "preview": preview,
        })

    return sessions


@app.get("/api/latest-session")
async def latest_session(path: str = "", _: None = Depends(auth)):
    project_dir = Path.home() / ".claude" / "projects" / encode_project_path(path)
    if not project_dir.is_dir():
        return {"session_id": ""}
    files = list(project_dir.glob("*.jsonl"))
    if not files:
        return {"session_id": ""}
    latest = max(files, key=lambda f: f.stat().st_mtime)
    return {"session_id": latest.stem}


@app.get("/api/files")
async def list_files(path: str = "", _: None = Depends(auth)):
    cfg = load_config()
    allowed_dirs = cfg.get("allowed_dirs", [])

    if not path:
        return [
            {"name": Path(d).name, "path": str(d), "type": "dir"}
            for d in allowed_dirs if Path(d).is_dir()
        ]

    req = Path(path).resolve()
    if not is_path_allowed(req, allowed_dirs):
        return JSONResponse(status_code=403, content={"error": "路径不在允许范围内"})
    if not req.is_dir():
        return JSONResponse(status_code=400, content={"error": "不是目录"})

    items = []
    try:
        for item in sorted(req.iterdir(), key=lambda x: (x.is_file(), x.name.lower())):
            if item.name.startswith("."):
                continue
            items.append({
                "name": item.name,
                "path": str(item),
                "type": "dir" if item.is_dir() else "file",
            })
    except PermissionError:
        pass
    return items


@app.websocket("/terminal")
async def terminal_ws(
    websocket: WebSocket,
    path: str = Query(default=""),
    session_id: str = Query(default=""),
    token: str = Query(default=""),
):
    if not secrets.compare_digest(token.encode(), AUTH_PASS.encode()):
        await websocket.close(code=4001)
        return
    await websocket.accept()
    cfg = load_config()
    allowed_dirs = cfg.get("allowed_dirs", [])

    work_dir = str(Path.home())
    if path:
        p = Path(path).resolve()
        if is_path_allowed(p, allowed_dirs) and p.is_dir():
            work_dir = str(p)

    env = os.environ.copy()
    env["TERM"] = "xterm-256color"

    cmd = ["claude", "--resume", session_id] if session_id else ["claude"]

    proc = ptyprocess.PtyProcessUnicode.spawn(
        cmd,
        cwd=work_dir,
        env=env,
        dimensions=(24, 220),
    )

    loop = asyncio.get_event_loop()

    async def read_pty():
        while proc.isalive():
            try:
                data = await loop.run_in_executor(None, proc.read, 4096)
                await websocket.send_text(data)
            except Exception:
                break
        try:
            await websocket.send_text("\r\n[进程已退出]\r\n")
        except Exception:
            pass

    read_task = asyncio.create_task(read_pty())

    try:
        while True:
            raw = await websocket.receive_text()
            msg = json.loads(raw)
            if msg["type"] == "input":
                proc.write(msg["data"])
            elif msg["type"] == "resize":
                proc.setwinsize(int(msg["rows"]), int(msg["cols"]))
    except WebSocketDisconnect:
        pass
    finally:
        read_task.cancel()
        if proc.isalive():
            proc.terminate()
