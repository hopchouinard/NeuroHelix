"""Utility helpers for Typer command groups."""

from __future__ import annotations

from typing import Iterable, List, Optional, Type

from typer.core import TyperGroup


class DefaultCommandGroup(TyperGroup):
    """Typer group that falls back to a default command when none is provided."""

    default_command: Optional[str] = None

    def parse_args(self, ctx, args: Iterable[str]):  # type: ignore[override]
        args_list: List[str] = list(args)
        if self.default_command and not self._has_explicit_command(args_list):
            args_list.insert(0, self.default_command)
        return super().parse_args(ctx, args_list)

    def _has_explicit_command(self, args: List[str]) -> bool:
        """Return True if the args already include a known subcommand."""
        for arg in args:
            if arg.startswith("-"):
                continue
            return arg in self.commands
        return False


def create_default_command_group(default_command: str) -> Type[DefaultCommandGroup]:
    """Factory returning a Typer group class with a preset default command."""

    class _Group(DefaultCommandGroup):
        pass

    _Group.default_command = default_command
    return _Group
