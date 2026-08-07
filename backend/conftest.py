"""Ensures backend/ is importable as the package root for pytest (`from guardrails.x import y`,
`from correlation.x import y`, etc.) regardless of where pytest is invoked from."""
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
