from __future__ import annotations

from getpass import getpass
import os
from pathlib import Path
import secrets
import tempfile


ENV_PATH = Path(".env")
PLACEHOLDER_PREFIX = "replace-with-"


def read_values(lines: list[str]) -> dict[str, str]:
    values: dict[str, str] = {}
    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        values[key] = value
    return values


def prompt_password() -> str:
    while True:
        password = getpass("Create interview demo password (12+ characters): ")
        confirmation = getpass("Confirm interview demo password: ")
        if password != confirmation:
            print("Passwords did not match. Try again.")
        elif len(password) < 12:
            print("Password must contain at least 12 characters.")
        elif "\n" in password or "\r" in password:
            print("Password cannot contain a newline.")
        else:
            return password


def update_lines(lines: list[str], updates: dict[str, str]) -> list[str]:
    remaining = dict(updates)
    output: list[str] = []
    for line in lines:
        if "=" in line and not line.lstrip().startswith("#"):
            key = line.split("=", 1)[0].strip()
            if key in remaining:
                output.append(f"{key}={remaining.pop(key)}\n")
                continue
        output.append(line)
    if remaining:
        if output and output[-1].strip():
            output.append("\n")
        output.append("# Controlled interview demo\n")
        output.extend(f"{key}={value}\n" for key, value in remaining.items())
    return output


def main() -> None:
    if not ENV_PATH.exists():
        raise SystemExit("Missing .env. Copy .env.example to .env first.")
    lines = ENV_PATH.read_text(encoding="utf-8").splitlines(keepends=True)
    values = read_values(lines)
    updates: dict[str, str] = {}

    password = values.get("ALADDIN_DEMO_PASSWORD", "")
    if not password or password.startswith(PLACEHOLDER_PREFIX):
        updates["ALADDIN_DEMO_PASSWORD"] = prompt_password()

    api_token = values.get("ALADDIN_API_TOKEN", "")
    if len(api_token) < 24 or api_token.startswith(PLACEHOLDER_PREFIX):
        updates["ALADDIN_API_TOKEN"] = secrets.token_hex(24)

    if not values.get("ALADDIN_RATE_LIMIT_PER_MINUTE"):
        updates["ALADDIN_RATE_LIMIT_PER_MINUTE"] = "20"
    if not values.get("ALADDIN_MAX_GENERATIONS_PER_DAY"):
        updates["ALADDIN_MAX_GENERATIONS_PER_DAY"] = "50"

    if not updates:
        print("Interview demo security settings are already configured.")
        return

    updated = update_lines(lines, updates)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=".env.",
        dir=ENV_PATH.parent,
        text=True,
    )
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as target:
            target.writelines(updated)
        os.chmod(temporary_name, 0o600)
        os.replace(temporary_name, ENV_PATH)
    finally:
        if os.path.exists(temporary_name):
            os.unlink(temporary_name)
    print("Interview demo security settings saved to .env (values hidden).")


if __name__ == "__main__":
    main()
