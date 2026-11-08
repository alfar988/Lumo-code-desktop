# -*- coding: utf-8 -*-
"""User-level Windows bootstrapper for Lumo Code.

Installs the latest public source from alfar988/Lumo-code, a private embedded
Python runtime, and Git for Windows (for the agent's Bash execution tools).
No administrator privileges are requested by this bootstrapper.
"""
from __future__ import annotations

import argparse
import json
import os
import platform
import shutil
import subprocess
import sys
import tempfile
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from pathlib import Path, PurePosixPath

OWNER = "alfar988"
REPO = "Lumo-code"
PYTHON_VERSION = "3.13.17"
PYTHON_EMBED_URL = (
    "https://www.python.org/ftp/python/"
    f"{PYTHON_VERSION}/python-{PYTHON_VERSION}-embed-amd64.zip"
)
USER_AGENT = "LumoCode-Windows-Installer/1.0"
CHUNK_SIZE = 1024 * 1024


def install_root() -> Path:
    local = os.environ.get("LOCALAPPDATA")
    if local:
        return Path(local) / "LumoCode"
    return Path.home() / "AppData" / "Local" / "Programs" / "LumoCode"


def workspace_path() -> Path:
    return Path.home() / "workspace"


def request_bytes(url: str, *, timeout: int = 60) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=timeout) as response:
        final_host = urllib.parse.urlparse(response.geturl()).hostname or ""
        allowed = {"api.github.com", "github.com", "codeload.github.com", "www.python.org", "python.org"}
        if final_host not in allowed:
            raise RuntimeError(f"Unexpected download host: {final_host}")
        return response.read()


def request_json(url: str) -> dict:
    return json.loads(request_bytes(url).decode("utf-8"))


def download_file(url: str, destination: Path) -> None:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    destination.parent.mkdir(parents=True, exist_ok=True)
    with urllib.request.urlopen(req, timeout=120) as response, destination.open("wb") as out:
        final_host = urllib.parse.urlparse(response.geturl()).hostname or ""
        allowed = {
            "api.github.com", "github.com", "codeload.github.com", "www.python.org", "python.org",
            "objects.githubusercontent.com", "release-assets.githubusercontent.com",
        }
        if final_host not in allowed:
            raise RuntimeError(f"Unexpected download host: {final_host}")
        while True:
            chunk = response.read(CHUNK_SIZE)
            if not chunk:
                break
            out.write(chunk)


def safe_extract_zip(archive: Path, destination: Path, *, strip_first_component: bool = False) -> None:
    """Extract ZIP contents while rejecting absolute paths and traversal."""
    destination.mkdir(parents=True, exist_ok=True)
    base = destination.resolve()
    with zipfile.ZipFile(archive) as zf:
        members = zf.infolist()
        root_component = None
        if strip_first_component:
            names = [PurePosixPath(m.filename).parts for m in members if m.filename]
            if not names or any(not p for p in names):
                raise RuntimeError("The source archive is empty or malformed.")
            root_component = names[0][0]
            if any(parts[0] != root_component for parts in names):
                raise RuntimeError("Archive has inconsistent root entries.")
        for member in members:
            parts = PurePosixPath(member.filename).parts
            if not parts:
                continue
            if PurePosixPath(member.filename).is_absolute() or any(p in ("..", "") for p in parts):
                raise RuntimeError(f"Unsafe path in ZIP archive: {member.filename}")
            if strip_first_component:
                parts = parts[1:]
            if not parts:
                continue
            target = (destination.joinpath(*parts)).resolve()
            if base not in target.parents and target != base:
                raise RuntimeError(f"Unsafe extraction destination: {member.filename}")
            if member.is_dir() or member.filename.endswith("/"):
                target.mkdir(parents=True, exist_ok=True)
            else:
                target.parent.mkdir(parents=True, exist_ok=True)
                with zf.open(member) as src, target.open("wb") as dst:
                    shutil.copyfileobj(src, dst)


def install_source(root: Path) -> Path:
    """Fetch repository's default branch and replace the local source atomically."""
    repo_api = f"https://api.github.com/repos/{OWNER}/{REPO}"
    metadata = request_json(repo_api)
    branch = metadata.get("default_branch")
    if not isinstance(branch, str) or not branch or branch.startswith("/"):
        raise RuntimeError("GitHub did not provide a valid repository default branch.")
    archive_url = (
        f"https://codeload.github.com/{OWNER}/{REPO}/zip/refs/heads/"
        f"{urllib.parse.quote(branch, safe='')}"
    )
    root.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".lumo-source-stage-", dir=str(root)) as tmp:
        stage = Path(tmp)
        archive = stage / "source.zip"
        download_file(archive_url, archive)
        extracted = stage / "extract"
        safe_extract_zip(archive, extracted, strip_first_component=True)
        if not (extracted / "run.py").is_file() or not (extracted / "lumo" / "cli.py").is_file():
            raise RuntimeError("The GitHub archive does not look like a Lumo Code source tree.")
        target = root / "source"
        backup = root / "source.previous"
        if backup.exists():
            shutil.rmtree(backup)
        moved_old = False
        try:
            if target.exists():
                target.replace(backup)
                moved_old = True
            extracted.replace(target)
            if backup.exists():
                shutil.rmtree(backup)
        except Exception:
            if moved_old and backup.exists() and not target.exists():
                backup.replace(target)
            raise
    return root / "source"


def python_executable(root: Path) -> Path:
    return root / "runtime" / "python.exe"


def ensure_python(root: Path) -> Path:
    exe = python_executable(root)
    if exe.is_file():
        return exe
    runtime_dir = exe.parent
    runtime_dir.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".lumo-python-", dir=str(root)) as tmp:
        archive = Path(tmp) / "python-embed.zip"
        download_file(PYTHON_EMBED_URL, archive)
        safe_extract_zip(archive, runtime_dir)
    pth = runtime_dir / f"python{PYTHON_VERSION.split('.')[0]}{PYTHON_VERSION.split('.')[1]}._pth"
    if not pth.exists():
        raise RuntimeError("The downloaded Python embeddable package is missing its ._pth file.")
    contents = pth.read_text(encoding="utf-8")
    if "import site" not in contents:
        contents = contents.replace("#import site", "import site")
        pth.write_text(contents, encoding="utf-8")
    check = subprocess.run([str(exe), "--version"], capture_output=True, text=True, timeout=20)
    if check.returncode != 0:
        raise RuntimeError("Bundled Python failed its startup check: " + (check.stderr or check.stdout).strip())
    return exe


def git_bash(root: Path) -> Path | None:
    candidates = [
        root / "git" / "bin" / "bash.exe",
        Path(os.environ.get("ProgramFiles", r"C:\Program Files")) / "Git" / "bin" / "bash.exe",
        Path(os.environ.get("LOCALAPPDATA", str(Path.home() / "AppData" / "Local"))) / "Programs" / "Git" / "bin" / "bash.exe",
    ]
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    found = shutil.which("bash")
    return Path(found) if found else None


def ensure_git_bash(root: Path) -> Path:
    bash = git_bash(root)
    if bash:
        return bash
    print("Installing Git for Windows (required for Lumo's Bash command tools)...", flush=True)
    release = request_json("https://api.github.com/repos/git-for-windows/git/releases/latest")
    assets = release.get("assets", [])
    choices = [
        asset for asset in assets
        if isinstance(asset.get("name"), str)
        and asset["name"].endswith("-64-bit.exe")
        and "portable" not in asset["name"].lower()
        and isinstance(asset.get("browser_download_url"), str)
    ]
    if not choices:
        raise RuntimeError("Could not locate the official Git for Windows x64 installer.")
    asset = sorted(choices, key=lambda a: a["name"])[-1]
    with tempfile.TemporaryDirectory(prefix=".lumo-git-", dir=str(root)) as tmp:
        installer = Path(tmp) / asset["name"]
        download_file(asset["browser_download_url"], installer)
        git_dir = root / "git"
        args = [
            str(installer), "/VERYSILENT", "/NORESTART", "/NOCANCEL", "/SP-",
            "/CURRENTUSER", f"/DIR={git_dir}",
            '/COMPONENTS="icons,assoc,assoc_sh"',
            "/o:PathOption=BashOnly", "/o:BashTerminalOption=ConHost",
        ]
        completed = subprocess.run(args, timeout=900)
        if completed.returncode != 0:
            raise RuntimeError(f"Git for Windows installer exited with code {completed.returncode}.")
    bash = git_bash(root)
    if not bash:
        raise RuntimeError("Git setup completed, but bash.exe could not be found.")
    return bash


def launch_lumo(root: Path, *, install: bool) -> int:
    if platform.system() != "Windows":
        raise RuntimeError("This bootstrap package supports Windows 10/11 x64 only.")
    if platform.machine().lower() not in {"amd64", "x86_64"}:
        raise RuntimeError("This build supports Windows x64 only (ARM64 is not packaged).")
    root.mkdir(parents=True, exist_ok=True)
    source = install_source(root) if install or not (root / "source" / "run.py").is_file() else root / "source"
    py = ensure_python(root)
    bash = ensure_git_bash(root)
    ws = workspace_path()
    ws.mkdir(parents=True, exist_ok=True)

    env = os.environ.copy()
    git_root = str(bash.parent.parent)
    env["PATH"] = os.pathsep.join([
        str(bash.parent), str(Path(git_root) / "cmd"), str(Path(git_root) / "usr" / "bin"), env.get("PATH", "")
    ])
    env["LUMO_WINDOWS_BASH"] = str(bash)
    flags = getattr(subprocess, "CREATE_NEW_CONSOLE", 0)
    proc = subprocess.Popen([str(py), str(source / "run.py"), str(ws)], cwd=str(ws), env=env, creationflags=flags)
    return proc.pid


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Lumo Code Windows installer/launcher")
    parser.add_argument("--install-and-launch", action="store_true", help="install latest source/runtime and launch Lumo")
    parser.add_argument("--launch", action="store_true", help="launch installed Lumo")
    args = parser.parse_args(argv)
    try:
        pid = launch_lumo(install_root(), install=args.install_and_launch)
        print(f"Lumo Code started (PID {pid}).", flush=True)
        return 0
    except (OSError, urllib.error.URLError, zipfile.BadZipFile, RuntimeError, subprocess.SubprocessError) as exc:
        print(f"\nLumo Code setup/launch failed:\n{exc}\n", file=sys.stderr, flush=True)
        print("Check your internet connection and try launching Lumo Code again.", file=sys.stderr, flush=True)
        input("Press Enter to close...")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
