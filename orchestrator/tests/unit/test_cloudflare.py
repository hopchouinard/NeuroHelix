"""Tests for Cloudflare service."""

from __future__ import annotations

import subprocess
from types import SimpleNamespace

import pytest

from services.cloudflare import CloudflareService


def test_cloudflare_service_not_configured(tmp_path):
    service = CloudflareService(repo_root=tmp_path)
    assert not service.is_configured
    assert service.get_latest_deployment_id() is None


def test_cloudflare_service_parses_output(monkeypatch, tmp_path):
    service = CloudflareService(
        repo_root=tmp_path,
        project_name="demo",
        api_token="token",
    )

    captured = {}

    def fake_run(cmd, **kwargs):  # type: ignore[override]
        captured["cmd"] = cmd
        return SimpleNamespace(
            returncode=0,
            stdout="12345abc | 2025-01-01 | git | Success",
            stderr="",
        )

    monkeypatch.setattr(subprocess, "run", fake_run)

    deploy_id = service.get_latest_deployment_id()
    assert deploy_id == "12345abc"
    assert "wrangler" in captured["cmd"]
