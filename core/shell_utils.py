"""
Utility helpers for running shell commands with safe limits.
"""

from __future__ import annotations

import subprocess
from typing import Tuple


def truncate_bytes(text: str, max_bytes: int) -> str:
    """Truncate a string to a maximum UTF-8 byte length."""
    if max_bytes <= 0:
        return ""
    data = text.encode("utf-8", errors="replace")
    if len(data) <= max_bytes:
        return text
    truncated = data[:max_bytes]
    # Ensure valid UTF-8
    text_out = truncated.decode("utf-8", errors="ignore")
    return text_out + "\n[truncated]"


def run_bash_command(command: str, timeout_seconds: int, max_output_bytes: int) -> Tuple[int, str]:
    """Run a bash command with timeout and output cap."""
    result = subprocess.run(
        ["/bin/bash", "-lc", command],
        capture_output=True,
        text=True,
        timeout=timeout_seconds,
    )

    output = (result.stdout or "") + (result.stderr or "")
    output = truncate_bytes(output, max_output_bytes)
    return result.returncode, output
