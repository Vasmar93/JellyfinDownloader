"""Download functions for JellyfinDownloader."""

import time
from pathlib import Path

import requests

from .classes import Config, JellyfinEpisode, JellyfinMovie, AudioTrack
from .utils import format_bitrate

TIMEOUT = 30


def select_audio_track_index(audio_tracks: list[AudioTrack]) -> int:
    print("\n--- Available Audio Tracks ---")
    for i, track in enumerate(audio_tracks):
        print(
            f"[{i}] {track.display_title or track.title} (codec: {track.codec} - bitrate: {format_bitrate(track.bitrate)})"
        )

    while True:
        try:
            choice = int(input(f"\nSelect track number (0-{len(audio_tracks) - 1}): "))
            if 0 <= choice < len(audio_tracks):
                selected_index = audio_tracks[choice].index
                print(
                    f"Downloading video with track number {choice} ({selected_index}): {audio_tracks[choice].display_title or audio_tracks[choice].language}"
                )
                return selected_index
            else:
                print(f"Please enter a number between 0 and {len(audio_tracks) - 1}.")
        except ValueError:
            print("Invalid input. Please enter a number.")


def get_audio_tracks(config: Config, item_id: str) -> list[AudioTrack]:
    url = f"{config.server_url.rstrip('/')}/Items/{item_id}?api_key={config.api_key}"

    resp = requests.get(url, timeout=TIMEOUT).json()

    media_streams = resp.get("MediaSources", [{}])[0].get("MediaStreams", [])

    audio_tracks = [
        AudioTrack(
            index=s["Index"],
            language=s.get("Language", "und"),
            codec=s.get("Codec"),
            bitrate=s.get("BitRate"),
            title=s.get("Title"),
            display_title=s.get("DisplayTitle"),
            is_default=s.get("IsDefault", False),
            is_forced=s.get("IsForced", False),
            is_hearing_impaired=s.get("IsHearingImpaired", False),
        )
        for s in media_streams
        if s.get("Type") == "Audio"
    ]

    return audio_tracks


def get_audio_index(config: Config, item_id: str) -> int | None:
    audio_tracks = get_audio_tracks(config, item_id)

    if not audio_tracks:
        print("No audio tracks found.")
        return None

    if len(audio_tracks) == 1:
        print(
            f"Downloading with only available audio track: {audio_tracks[0].display_title or audio_tracks[0].language}"
        )
        return audio_tracks[0].index

    return select_audio_track_index(audio_tracks)


def download_stream(stream_url: str, output_path: Path, estimated_size: int = 0):
    """Download stream directly using requests."""
    response = requests.get(stream_url, stream=True, timeout=TIMEOUT)
    response.raise_for_status()

    total_size = int(response.headers.get("content-length", 0))
    if not total_size and estimated_size:
        total_size = estimated_size

    downloaded = 0
    start_time = time.time()
    last_update = start_time

    with open(output_path, "wb") as f:
        for chunk in response.iter_content(chunk_size=8192):
            if chunk:
                f.write(chunk)
                downloaded += len(chunk)
                current_time = time.time()

                # Update every 0.5 seconds
                if current_time - last_update >= 0.5:
                    elapsed = current_time - start_time
                    speed = downloaded / elapsed if elapsed > 0 else 0

                    if total_size > 0:
                        percent = (downloaded / total_size) * 100
                        remaining = total_size - downloaded
                        eta = remaining / speed if speed > 0 else 0
                        print(
                            f"\rProgress: {percent:.1f}% ({downloaded / 1e6:.1f}/{total_size / 1e6:.1f} MB) "
                            f"Speed: {speed / 1e6:.1f} MB/s ETA: {int(eta)}s",
                            end="",
                        )
                    else:
                        print(
                            f"\rDownloaded: {downloaded / 1e6:.1f} MB Speed: {speed / 1e6:.1f} MB/s",
                            end="",
                        )

                    last_update = current_time

    elapsed = time.time() - start_time
    speed = downloaded / elapsed if elapsed > 0 else 0
    print(
        f"\nCompleted: {downloaded / 1e6:.1f} MB in {elapsed:.1f}s (avg: {speed / 1e6:.1f} MB/s)"
    )


def download_direct(config: Config, item_id: str, output_path: Path):
    """Download original file directly without transcoding."""
    url = f"{config.server_url.rstrip('/')}/Items/{item_id}/Download?api_key={config.api_key}"

    print("Downloading original file (no transcoding)...")
    response = requests.get(url, stream=True, timeout=TIMEOUT)
    response.raise_for_status()

    total_size = int(response.headers.get("content-length", 0))
    downloaded = 0
    start_time = time.time()
    last_update = start_time

    with open(output_path, "wb") as f:
        for chunk in response.iter_content(chunk_size=8192):
            if chunk:
                f.write(chunk)
                downloaded += len(chunk)
                current_time = time.time()

                # Update every 0.5 seconds
                if current_time - last_update >= 0.5:
                    elapsed = current_time - start_time
                    speed = downloaded / elapsed if elapsed > 0 else 0

                    if total_size > 0:
                        percent = (downloaded / total_size) * 100
                        remaining = total_size - downloaded
                        eta = remaining / speed if speed > 0 else 0
                        print(
                            f"\rProgress: {percent:.1f}% ({downloaded / 1e6:.1f}/{total_size / 1e6:.1f} MB) "
                            f"Speed: {speed / 1e6:.1f} MB/s ETA: {int(eta)}s",
                            end="",
                        )
                    else:
                        print(
                            f"\rDownloaded: {downloaded / 1e6:.1f} MB Speed: {speed / 1e6:.1f} MB/s",
                            end="",
                        )

                    last_update = current_time

    elapsed = time.time() - start_time
    speed = downloaded / elapsed if elapsed > 0 else 0
    print(
        f"\nCompleted: {downloaded / 1e6:.1f} MB in {elapsed:.1f}s (avg: {speed / 1e6:.1f} MB/s)"
    )


def should_skip_transcode(item: JellyfinMovie | JellyfinEpisode, bitrate: int) -> bool:
    """
    Check if the original file should be downloaded without transcoding.

    Returns True if:
    - Bitrate is set to 0 (user wants original files always)
    - Original file is already smaller than transcoded would be
    """
    if bitrate == 0:
        print("Bitrate set to 0 - downloading original file.")
        return True

    duration_ticks = item.RunTimeTicks
    if not duration_ticks or not item.MediaSources:
        return False

    original_size = item.MediaSources[0].Size
    if not original_size:
        return False

    # 10,000,000 ticks = 1 second
    duration_seconds = duration_ticks / 10_000_000

    bitrate_bytes_per_sec = bitrate / 8
    expected_size = bitrate_bytes_per_sec * duration_seconds

    if original_size <= expected_size * 1.05:
        print(f"Original size ({original_size / 1e6:.1f} MB) is already optimal.")
        print(f"Skipping transcode (would be ~{expected_size / 1e6:.1f} MB).")
        return True

    return False
