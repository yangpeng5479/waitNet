"""Compression preset definitions and parameter model."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional


class RateMode(str, Enum):
    VBR = "vbr"
    CBR = "cbr"


@dataclass
class CompressionSettings:
    """FFmpeg encoding parameters for a single compression job."""

    channels: int = 1
    codec: str = "libmp3lame"
    rate_mode: RateMode = RateMode.VBR
    qscale: int = 8
    bitrate_kbps: Optional[int] = None
    sample_rate: Optional[int] = None

    def build_ffmpeg_args(self) -> list[str]:
        args = ["-ac", str(self.channels), "-codec:a", self.codec]
        if self.sample_rate:
            args.extend(["-ar", str(self.sample_rate)])
        if self.rate_mode == RateMode.VBR:
            args.extend(["-qscale:a", str(self.qscale)])
        elif self.bitrate_kbps:
            args.extend(["-b:a", f"{self.bitrate_kbps}k"])
        return args


@dataclass
class CompressionProfile:
    id: str
    name: str
    description: str
    settings: CompressionSettings
    is_default: bool = False


PROFILES: list[CompressionProfile] = [
    CompressionProfile(
        id="recommended",
        name="推荐配置",
        description="单声道 + libmp3lame + VBR qscale 8",
        settings=CompressionSettings(channels=1, rate_mode=RateMode.VBR, qscale=8),
        is_default=True,
    ),
    CompressionProfile(
        id="high_compression",
        name="高压缩",
        description="单声道 + 64kbps CBR，体积更小",
        settings=CompressionSettings(
            channels=1, rate_mode=RateMode.CBR, bitrate_kbps=64
        ),
    ),
    CompressionProfile(
        id="high_quality",
        name="高质量",
        description="立体声 + VBR qscale 4，音质更好",
        settings=CompressionSettings(channels=2, rate_mode=RateMode.VBR, qscale=4),
    ),
    CompressionProfile(
        id="custom",
        name="自定义",
        description="手动调整声道、比特率、VBR 质量等参数",
        settings=CompressionSettings(),
    ),
]


def get_default_profile() -> CompressionProfile:
    for profile in PROFILES:
        if profile.is_default:
            return profile
    return PROFILES[0]


def get_profile_by_id(profile_id: str) -> CompressionProfile:
    for profile in PROFILES:
        if profile.id == profile_id:
            return profile
    return get_default_profile()
