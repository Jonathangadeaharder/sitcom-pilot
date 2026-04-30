from __future__ import annotations

import logging
import platform
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

_REGISTRY_NAMES = {
    "text2image": "text2image.mlx",
    "image2image": "image2image.mlx",
    "image2video": "image2video.mlx",
    "text2speech": "text2speech.fish_mlx",
    "audio2subtitle": "audio2subtitle.mlx",
}

_IMPORT_SPECS = {
    "text2image": ("text2image.providers", "text2image"),
    "image2image": ("image2image.providers", "image2image"),
    "image2video": ("image2video.providers", "image2video"),
    "text2speech": ("text2speech.providers", "text2speech"),
    "audio2subtitle": ("audio2subtitle.providers", "audio2subtitle"),
}


@dataclass
class ProviderAvailability:
    available: dict[str, str] = field(default_factory=dict)
    missing: dict[str, str] = field(default_factory=dict)

    @property
    def all_available(self) -> bool:
        return len(self.missing) == 0


def _try_import(module_name: str, package_label: str) -> bool:
    try:
        __import__(module_name)
        return True
    except ImportError:
        logger.debug("Provider package %s not available", package_label)
        return False


def ensure_registered() -> ProviderAvailability:
    avail = ProviderAvailability()
    for capability, (module_name, package_label) in _IMPORT_SPECS.items():
        if _try_import(module_name, package_label):
            avail.available[capability] = _REGISTRY_NAMES[capability]
        else:
            avail.missing[capability] = package_label
    return avail


def auto_configure() -> dict[str, str]:
    config: dict[str, str] = {}
    if platform.system() == "Darwin" and platform.machine() == "arm64":
        config["preferred_backend"] = "mlx"
        for cap, reg_name in _REGISTRY_NAMES.items():
            config[cap] = reg_name
    else:
        config["preferred_backend"] = "cli"
        for cap in _REGISTRY_NAMES:
            config[cap] = ""
    return config


def provider_name(capability: str) -> str:
    return _REGISTRY_NAMES.get(capability, "")
