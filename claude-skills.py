#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Repo-root entry: run claude-skills from a checkout without `pip install`.

Use either of:
    python3 claude-skills.py
    python3 -m claude_skills      # after `pip install -e .`
    claude-skills                  # console script after `pip install`
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from claude_skills.cli import main  # noqa: E402

if __name__ == "__main__":
    main()
