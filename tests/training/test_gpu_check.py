"""
Unit tests for aerosafety/training/gpu_check.py.

No GPU expected in CI — tests verify that check_gpu() returns False without
crashing, and that error messages are informative.
"""

from __future__ import annotations

import pytest

from aerosafety.training.gpu_check import GpuStatus, check_gpu, require_gpu


class TestCheckGpu:
    def test_returns_gpu_status(self) -> None:
        status = check_gpu()
        assert isinstance(status, GpuStatus)

    def test_does_not_raise(self) -> None:
        # Must never raise — always returns GpuStatus
        check_gpu()

    def test_no_gpu_in_ci(self) -> None:
        # CI / CPU-only machines should report unavailable
        status = check_gpu()
        assert status.available is False, (
            f"Expected no GPU in CI but got available=True with {status.device_count} device(s). "
            "If this is running on a GPU machine, this test should be skipped."
        )

    def test_device_count_zero_without_gpu(self) -> None:
        status = check_gpu()
        if not status.available:
            assert status.device_count == 0

    def test_devices_empty_without_gpu(self) -> None:
        status = check_gpu()
        if not status.available:
            assert status.devices == []

    def test_torch_version_present_if_torch_installed(self) -> None:
        try:
            import torch  # noqa: F401
            installed = True
        except ImportError:
            installed = False
        status = check_gpu()
        if installed:
            assert status.torch_version != ""

    def test_error_field_set_if_torch_missing(self, monkeypatch: pytest.MonkeyPatch) -> None:
        import builtins
        real_import = builtins.__import__

        def mock_import(name, *args, **kwargs):
            if name == "torch":
                raise ImportError("mock: no torch")
            return real_import(name, *args, **kwargs)

        monkeypatch.setattr(builtins, "__import__", mock_import)
        # Re-import to hit the mock
        import importlib
        import aerosafety.training.gpu_check as gc_mod
        importlib.reload(gc_mod)
        status = gc_mod.check_gpu()
        assert status.available is False
        assert status.error is not None
        assert "aerosafety[gpu]" in status.error


class TestRequireGpu:
    def test_raises_runtime_error_without_gpu(self) -> None:
        status = check_gpu()
        if not status.available:
            with pytest.raises(RuntimeError, match="GPU required"):
                require_gpu()

    def test_error_message_mentions_dry_run(self) -> None:
        status = check_gpu()
        if not status.available:
            with pytest.raises(RuntimeError) as exc_info:
                require_gpu()
            assert "--dry-run" in str(exc_info.value)

    def test_error_message_mentions_gpu_extras(self) -> None:
        status = check_gpu()
        if not status.available:
            with pytest.raises(RuntimeError) as exc_info:
                require_gpu()
            assert "aerosafety[gpu]" in str(exc_info.value)
