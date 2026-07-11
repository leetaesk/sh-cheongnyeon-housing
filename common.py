#!/usr/bin/env python3
"""Shared bits for the pipeline scripts. WORK is the repo root (this file's dir),
so every script runs from a fresh clone without editing paths."""
import os, re

WORK = os.path.dirname(os.path.abspath(__file__))

def natkey(s):
    """Natural sort key: '10호' sorts after '2호'."""
    return [int(t) if t.isdigit() else t for t in re.split(r"(\d+)", s)]
