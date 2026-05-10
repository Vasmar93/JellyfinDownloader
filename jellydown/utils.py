"""Utility functions for JellyfinDownloader."""

import re

from .classes import JellyfinEpisode


def sanitize_filename(s: str) -> str:
    """Remove invalid characters from filename."""
    s = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s.rstrip(" .")


def episode_filename(item: JellyfinEpisode, default_ext: str = ".mp4") -> str:
    """Generate filename for an episode."""
    series = item.SeriesName or "Unknown Series"
    season = item.ParentIndexNumber
    epnum = item.IndexNumber
    title = item.Name or "Untitled"

    if isinstance(season, int) and isinstance(epnum, int):
        base = f"{series} - S{season:02d}E{epnum:02d} - {title}"
    else:
        base = f"{series} - {title}"

    return sanitize_filename(base) + default_ext


def format_size(size_bytes: int) -> str:
    for unit in ["B", "KB", "MB", "GB"]:
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024

    return f"{size_bytes:.1f} TB"


def format_bitrate(bitrate: int | None) -> str:
    if bitrate is None:
        return "Unknown"

    if bitrate >= 1_000_000:
        return f"{bitrate / 1_000_000:.2f} Mbps"

    return f"{bitrate / 1_000:.0f} kbps"
