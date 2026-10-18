"""Build-time guards: file size, function length, comment budget, layering, framework (stdlib-only)."""

from __future__ import annotations

from pw_foundation.guards.comments import CommentBudget, ProseViolation, scan_comment_budget
from pw_foundation.guards.config import FunctionLimits, GuardsConfig, load_guards_config
from pw_foundation.guards.framework import FrameworkBreach, check_framework
from pw_foundation.guards.framework_config import FrameworkConfig, FrameworkExemption
from pw_foundation.guards.functions import FunctionLengthViolation, scan_function_lengths
from pw_foundation.guards.layering import LayeringViolation, check_layering
from pw_foundation.guards.structure import FileSizeViolation, filter_baselined, scan_file_sizes

__all__ = [
    "CommentBudget",
    "FileSizeViolation",
    "FrameworkBreach",
    "FrameworkConfig",
    "FrameworkExemption",
    "FunctionLengthViolation",
    "FunctionLimits",
    "GuardsConfig",
    "LayeringViolation",
    "ProseViolation",
    "check_framework",
    "check_layering",
    "filter_baselined",
    "load_guards_config",
    "scan_comment_budget",
    "scan_file_sizes",
    "scan_function_lengths",
]
