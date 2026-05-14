"""
Security-enforced sandbox for OS interaction.
The SafeBashTool runs only read-only commands and rejects destructive ones
at a regex-based blocklist before any execution.
"""

from sandbox.safe_bash_tool import SafeBashTool

__all__ = ["SafeBashTool"]
