"""
gpu_check.py — Honest GPU availability detection.

Returns False in CPU-only environments; training scripts use this to gate
non-dry-run execution. Never lies about hardware.

Usage
-----
    from aerosafety.training.gpu_check import check_gpu, require_gpu

    status = check_gpu()           # always returns GpuStatus; never raises
    require_gpu()                  # raises RuntimeError if no GPU
"""

from __future__ import annotations

import sys
from dataclasses import dataclass, field


@dataclass
class GpuStatus:
    available: bool
    device_count: int
    devices: list[dict[str, object]] = field(default_factory=list)
    torch_version: str = ""
    cuda_version: str = ""
    error: str | None = None  # set if torch import failed


def check_gpu() -> GpuStatus:
    """
    Detect GPU availability via torch.

    Returns GpuStatus with available=False if torch is not installed or if
    no CUDA devices are present. Never raises.
    """
    try:
        import torch  # noqa: PLC0415
    except ImportError:
        return GpuStatus(
            available=False,
            device_count=0,
            error=(
                "torch is not installed. "
                "Install GPU dependencies: pip install 'aerosafety[gpu]'"
            ),
        )

    if not torch.cuda.is_available():
        return GpuStatus(
            available=False,
            device_count=0,
            torch_version=torch.__version__,
            cuda_version=str(torch.version.cuda or "N/A"),
        )

    count = torch.cuda.device_count()
    devices = []
    for i in range(count):
        props = torch.cuda.get_device_properties(i)
        devices.append({
            "index": i,
            "name": props.name,
            "total_memory_gb": round(props.total_memory / 1024**3, 2),
            "major": props.major,
            "minor": props.minor,
        })

    return GpuStatus(
        available=True,
        device_count=count,
        devices=devices,
        torch_version=torch.__version__,
        cuda_version=str(torch.version.cuda or "N/A"),
    )


def require_gpu(min_devices: int = 1) -> GpuStatus:
    """
    Raise RuntimeError if GPU is not available or count is below min_devices.

    Parameters
    ----------
    min_devices:
        Minimum number of GPU devices required.

    Returns
    -------
    GpuStatus if requirement is met.

    Raises
    ------
    RuntimeError
        If no GPU is available or device count is below min_devices.
    """
    status = check_gpu()
    if not status.available:
        raise RuntimeError(
            "GPU required for non-dry-run training but none detected. "
            f"Details: {status.error or 'torch.cuda.is_available() returned False'}. "
            "Use --dry-run for CPU-only pipeline validation, or connect a GPU. "
            "Install GPU dependencies: pip install 'aerosafety[gpu]'"
        )
    if status.device_count < min_devices:
        raise RuntimeError(
            f"Training requires {min_devices} GPU(s) but only {status.device_count} detected."
        )
    return status


def print_gpu_status() -> None:
    """Print a human-readable GPU status report to stdout."""
    status = check_gpu()
    if status.error:
        print(f"GPU status: UNAVAILABLE — {status.error}")
        return
    if not status.available:
        print(
            f"GPU status: UNAVAILABLE (torch {status.torch_version}, "
            f"CUDA {status.cuda_version})"
        )
        return
    print(f"GPU status: {status.device_count} device(s) available (torch {status.torch_version})")
    for d in status.devices:
        print(f"  [{d['index']}] {d['name']} — {d['total_memory_gb']} GB")


if __name__ == "__main__":
    print_gpu_status()
    status = check_gpu()
    sys.exit(0 if status.available else 1)
