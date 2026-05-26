"""
SourceModule: data class holding everything the agents need about one source file.
"""

from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class SourceModule:
    path: Path                        # absolute path
    relative_path: Path               # relative to codebase root
    source_code: str                  # full source text
    language: str = "python"
    functions: list[str] = field(default_factory=list)   # function names found
    classes: list[str] = field(default_factory=list)     # class names found
    imports: list[str] = field(default_factory=list)     # import lines
    docstring: str = ""
