"""Execute users flows, publish sanitized evidence, and verify expected demo outcomes."""

import argparse
import os
import secrets
import shutil
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from threading import Thread

from robot.api import ExecutionResult

ROOT = Path(__file__).resolve().parents[1]


def start_local_api():
    """Run the actual separate FastAPI project, not a handwritten HTTP fixture."""
    import uvicorn
    from demo_api.main import create_app

    key = secrets.token_urlsafe(32)
    listener = socket.socket()
    listener.bind(("127.0.0.1", 0))
    listener.listen(128)
    port = listener.getsockname()[1]
    app = create_app({"local-demo": key})
    server = uvicorn.Server(uvicorn.Config(app, log_level="warning", access_log=False))
    thread = Thread(target=server.run, kwargs={"sockets": [listener]}, daemon=True)
    thread.start()
    deadline = time.monotonic() + 10
    while not server.started:
        if not thread.is_alive() or time.monotonic() > deadline:
            raise RuntimeError("Local FastAPI could not start")
        time.sleep(0.05)
    return server, thread, listener, f"http://127.0.0.1:{port}", key


def run_suite(suite, output, mode, console, env, language="en"):
    key = env["DEMO_API_KEY"].encode()
    output.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="users-demo-") as staging:
        process = subprocess.run(
            [
                sys.executable,
                "-m",
                "robot",
                "--outputdir",
                staging,
                "--console",
                console,
                "--variable",
                f"LOGGER_MODE:{mode}",
                "--variable",
                f"REPORT_LANGUAGE:{language}",
                str(suite),
            ],
            cwd=ROOT,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            check=False,
        )
        transcript = process.stdout.replace(key, b"[REDACTED]")
        sys.stdout.buffer.write(transcript)
        (output / "console.log").write_bytes(transcript)
        # Robot output.xml also stores resolved arguments; protect every published artifact.
        for source in Path(staging).rglob("*"):
            if source.is_file():
                target = output / source.relative_to(staging)
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(source.read_bytes().replace(key, b"[REDACTED]"))
    if process.returncode >= 250:
        raise RuntimeError(f"Robot execution error: {process.returncode}")
    result = ExecutionResult(str(output / "output.xml"))
    tests = []

    def collect(suite):
        tests.extend(suite.tests)
        for child in suite.suites:
            collect(child)

    collect(result.suite)
    for test in tests:
        expected = (
            "FAIL"
            if "expected-failure" in test.tags
            else ("SKIP" if "USR-004" in test.name else "PASS")
        )
        if test.status != expected:
            raise RuntimeError(f"Unexpected status for {test.name}: {test.status}; {test.message}")
    reports = list((output / "cases").glob("*.html"))
    if len(reports) != len(tests):
        raise RuntimeError("Expected exactly one HTML per test")
    for artifact in output.rglob("*"):
        if artifact.is_file() and key in artifact.read_bytes():
            raise RuntimeError("Credential found in published evidence")
    print(f"Verified {len(tests)} test outcomes and {len(reports)} secret-free case reports.")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--local", action="store_true", help="Use dev dependency Demo Users API")
    parser.add_argument("--logger-mode", choices=["summary", "failures", "full"], default="summary")
    parser.add_argument("--console", choices=["verbose", "quiet", "none"], default="quiet")
    parser.add_argument("--language", choices=["en", "es"], default="en")
    args = parser.parse_args()
    env = os.environ.copy()
    server = thread = listener = None
    if args.local:
        server, thread, listener, url, key = start_local_api()
        env.update(DEMO_BASE_URL=url, DEMO_API_KEY=key)
    if not env.get("DEMO_API_KEY") or not env.get("DEMO_BASE_URL"):
        raise SystemExit("Set DEMO_BASE_URL and DEMO_API_KEY, or use --local for CI verification.")
    try:
        # Known output folders only; never remove a caller-selected path.
        for folder, suite in [("results", "usuarios.robot"), ("results-ddt", "usuarios_ddt.robot")]:
            output = ROOT / folder
            if output.exists():
                shutil.rmtree(output)
            run_suite(
                ROOT / "tests" / suite, output, args.logger_mode, args.console, env, args.language
            )
    finally:
        if server is not None:
            server.should_exit = True
            thread.join(timeout=10)
            listener.close()


if __name__ == "__main__":
    main()
