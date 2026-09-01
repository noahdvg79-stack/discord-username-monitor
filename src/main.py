import itertools
import os
import random
import string
from datetime import datetime, timezone
from pathlib import Path

import requests
import yaml


ROOT = Path(__file__).resolve().parent.parent
CONFIG_FILE = ROOT / "config.yml"
SEEN_FILE = ROOT / "seen.txt"


def load_config():
    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def valid_username(username, config):
    length = config["length"]

    if not 2 <= length <= 32:
        return False

    if len(username) != length:
        return False

    if any(c not in config["characters"] for c in username):
        return False

    if not config.get("allow_consecutive_periods", False):
        if ".." in username:
            return False

    return True


def load_seen():
    if not SEEN_FILE.exists():
        return set()

    return {
        line.strip()
        for line in SEEN_FILE.read_text(encoding="utf-8").splitlines()
        if line.strip()
    }


def save_seen(seen):
    SEEN_FILE.write_text(
        "\n".join(sorted(seen)) + "\n",
        encoding="utf-8"
    )


def generate_candidates(config, seen):
    chars = config["characters"]
    length = config["length"]
    amount = config["candidates_per_run"]

    candidates = []

    # Random generation prevents GitHub Actions from repeatedly
    # walking the same predictable sequence.
    attempts = 0
    max_attempts = amount * 100

    while len(candidates) < amount and attempts < max_attempts:
        attempts += 1

        username = "".join(
            random.choice(chars)
            for _ in range(length)
        )

        if username in seen:
            continue

        if not valid_username(username, config):
            continue

        candidates.append(username)
        seen.add(username)

    return candidates


def notify_discord(webhook_url, username):
    now = datetime.now(timezone.utc)

    timestamp = now.strftime("%d %B %Y, %H:%M:%S UTC")

    content = (
        f"🎉 Discord username found: `{username}`\n"
        f"Found: {timestamp}"
    )

    response = requests.post(
        webhook_url,
        json={"content": content},
        timeout=15,
    )

    response.raise_for_status()


def main():
    config = load_config()

    webhook_url = os.environ.get("DISCORD_WEBHOOK_URL")

    if config["webhook"]["enabled"] and not webhook_url:
        raise RuntimeError(
            "DISCORD_WEBHOOK_URL GitHub Secret is missing."
        )

    seen = load_seen()

    candidates = generate_candidates(config, seen)

    print(f"Generated {len(candidates)} candidates.")

    # IMPORTANT:
    # This project deliberately does not probe Discord itself.
    #
    # Connect your authorized availability provider here.
    #
    # Example:
    #
    # available = availability_provider(username)
    #
    # if available:
    #     notify_discord(webhook_url, username)

    for username in candidates:
        print(f"Candidate: {username}")

    save_seen(seen)


if __name__ == "__main__":
    main()
