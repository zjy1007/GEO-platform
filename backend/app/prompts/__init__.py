"""Prompt template loader.

Templates live as YAML next to this module. Placeholders use $-syntax
(string.Template) so the literal JSON braces in examples don't clash with
Python str.format.
"""
import string
from functools import lru_cache
from pathlib import Path

import yaml

PROMPTS_DIR = Path(__file__).parent


@lru_cache
def load_prompt(name: str) -> dict:
    path = PROMPTS_DIR / f"{name}.yaml"
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def render(template: str, /, **values: object) -> str:
    return string.Template(template).safe_substitute(**values)
