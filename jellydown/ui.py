import math
import os
import sys
from pathlib import Path

import requests

from .classes import (
    Config,
    JellyfinEpisode,
    JellyfinMovie,
    JellyfinSeason,
    JellyfinSeries,
)
from .config import save_config
from .download import download_stream, download_direct, should_skip_transcode
from .utils import sanitize_filename, episode_filename


def prompt_int(
        prompt: str, default: int = 1, min_value: int = 1, max_value: int = 9999
) -> int:
    """Prompt user for an integer with validation."""
    raw = input(prompt).strip()
    if raw == "":
        return default
    if not raw.isdigit():
        print(f"Invalid number; using {default}.")
        return default
    value = int(raw)
    return max(min_value, min(max_value, value))


def pick_movie_or_show_from_list(
        movie_series_list: list[JellyfinMovie] | list[JellyfinSeries],
        title: str = "Choose",
        page_size: int = 25,
) -> JellyfinMovie | JellyfinSeries | str | None:
    """Interactive paginated picker for selecting from a list of options."""
    if not movie_series_list:
        return None

    page = 0
    pages = math.ceil(len(movie_series_list) / page_size)
    while True:
        start = page * page_size
        end = min(len(movie_series_list), start + page_size)
        print(
            f"\n{title} (showing {start + 1}-{end} of {len(movie_series_list)}; page {page + 1}/{pages})"
        )
        for i in range(start, end):
            print(f"  {i + 1:4d}. {movie_series_list[i].Name}")

        print(
            "\nCommands: number = select, n = next page, p = prev page, b = back, q = quit"
        )
        command = input("> ").strip().lower()

        if command == "q":
            sys.exit(0)
        if command == "b":
            return "BACK"
        if command == "n":
            if page + 1 < pages:
                page += 1
            continue
        if command == "p":
            if page > 0:
                page -= 1
            continue

        if command.isdigit():
            index = int(command) - 1
            if 0 <= index < len(movie_series_list):
                return movie_series_list[index]

        print("Invalid input.")


def pick_season_from_list(
        seasons: list[JellyfinSeason],
        title: str = "Seasons",
        page_size: int = 25,
) -> JellyfinSeason | str | None:
    """Interactive paginated picker for seasons. Returns the picked season, 'BACK', or None."""
    if not seasons:
        return None

    page = 0
    pages = math.ceil(len(seasons) / page_size)
    while True:
        start = page * page_size
        end = min(len(seasons), start + page_size)
        print(
            f"\n{title} (showing {start + 1}-{end} of {len(seasons)}; page {page + 1}/{pages})"
        )
        for i in range(start, end):
            s = seasons[i]
            n = s.IndexNumber
            label = s.Name or (f"Season {n}" if n is not None else "Season")
            print(f"  {i + 1:4d}. {label}")

        print(
            "\nCommands: number = select, n = next page, p = prev page, b = back, q = quit"
        )
        command = input("> ").strip().lower()

        if command == "q":
            sys.exit(0)
        if command == "b":
            return "BACK"
        if command == "n":
            if page + 1 < pages:
                page += 1
            continue
        if command == "p":
            if page > 0:
                page -= 1
            continue

        if command.isdigit():
            index = int(command) - 1
            if 0 <= index < len(seasons):
                return seasons[index]

        print("Invalid input.")


def pick_option_from_list(
        options: list[dict],
        title: str = "Choose",
        page_size: int = 25,
) -> str | None:
    """Picker for ``[{"label": ..., "value": ...}, ...]`` option lists.

    Returns the selected ``value``, the literal ``"BACK"``, or ``None``.
    """
    if not options:
        return None

    page = 0
    pages = math.ceil(len(options) / page_size)
    while True:
        start = page * page_size
        end = min(len(options), start + page_size)
        print(
            f"\n{title} (showing {start + 1}-{end} of {len(options)}; page {page + 1}/{pages})"
        )
        for i in range(start, end):
            print(f"  {i + 1:4d}. {options[i]['label']}")

        print(
            "\nCommands: number = select, n = next page, p = prev page, b = back, q = quit"
        )
        command = input("> ").strip().lower()

        if command == "q":
            sys.exit(0)
        if command == "b":
            return "BACK"
        if command == "n":
            if page + 1 < pages:
                page += 1
            continue
        if command == "p":
            if page > 0:
                page -= 1
            continue

        if command.isdigit():
            index = int(command) - 1
            if 0 <= index < len(options):
                return options[index]["value"]

        print("Invalid input.")


def pick_episode_from_list(
        episodes: list[JellyfinEpisode],
        title: str = "Episodes",
        page_size: int = 25,
) -> JellyfinEpisode | str | None:
    """Interactive paginated picker for episodes. Returns the picked episode, 'BACK', or None."""
    if not episodes:
        return None

    page = 0
    pages = math.ceil(len(episodes) / page_size)
    while True:
        start = page * page_size
        end = min(len(episodes), start + page_size)
        print(
            f"\n{title} (showing {start + 1}-{end} of {len(episodes)}; page {page + 1}/{pages})"
        )
        for i in range(start, end):
            ep = episodes[i]
            s = ep.ParentIndexNumber
            e = ep.IndexNumber
            name = ep.Name or "Untitled"
            if s is not None and e is not None:
                label = f"S{s:02d}E{e:02d} - {name}"
            else:
                label = name
            print(f"  {i + 1:4d}. {label}")

        print(
            "\nCommands: number = select, n = next page, p = prev page, b = back, q = quit"
        )
        command = input("> ").strip().lower()

        if command == "q":
            sys.exit(0)
        if command == "b":
            return "BACK"
        if command == "n":
            if page + 1 < pages:
                page += 1
            continue
        if command == "p":
            if page > 0:
                page -= 1
            continue

        if command.isdigit():
            index = int(command) - 1
            if 0 <= index < len(episodes):
                return episodes[index]

        print("Invalid input.")


def settings_menu(config: Config):
    """Interactive settings menu for configuring transcoding options."""
    while True:
        print("\n--- Settings ---")
        print(f"1. Video Codec ({config.video_codec})")
        print(f"2. Audio Codec ({config.audio_codec})")
        bitrate_display = (
            "No transcoding (original files)"
            if config.video_bitrate == 0
            else config.video_bitrate
        )
        print(f"3. Video Bitrate ({bitrate_display})")
        print(f"4. Audio Bitrate ({config.audio_bitrate})")
        print(f"5. Max Audio Channels ({config.max_audio_channels})")
        print("b. Back")

        choice = input("Select setting to edit: ").strip().lower()
        if choice == "b":
            save_config(config)
            break

        if choice == "1":
            options = [
                {
                    "label": "H.264 (AVC) - Recommended, high compatibility",
                    "value": "h264",
                },
                {
                    "label": "H.265 (HEVC) - High efficiency, requires hardware support",
                    "value": "hevc",
                },
                {"label": "Custom...", "value": "CUSTOM"},
            ]
            video_codec = pick_option_from_list(options, title="Select Video Codec")
            if video_codec and video_codec != "BACK":
                if video_codec == "CUSTOM":
                    config.video_codec = input("Video Codec [h264]: ").strip() or "h264"
                else:
                    config.video_codec = video_codec

        elif choice == "2":
            options = [
                {"label": "AAC - Recommended, high compatibility", "value": "aac"},
                {"label": "MP3", "value": "mp3"},
                {"label": "AC3", "value": "ac3"},
                {"label": "OPUS", "value": "opus"},
                {"label": "Custom...", "value": "CUSTOM"},
            ]
            audio_codec = pick_option_from_list(options, title="Select Audio Codec")
            if audio_codec and audio_codec != "BACK":
                if audio_codec == "CUSTOM":
                    config.audio_codec = input("Audio Codec [aac]: ").strip() or "aac"
                else:
                    config.audio_codec = audio_codec

        elif choice == "3":
            print(
                "Video Bitrate (set to 0 to always download original files without transcoding)"
            )
            config.video_bitrate = prompt_int(
                "Video Bitrate: ", default=4000000, min_value=0, max_value=100000000
            )
            config.max_streaming_bitrate = config.video_bitrate
        elif choice == "4":
            config.audio_bitrate = prompt_int(
                "Audio Bitrate: ", default=128000, max_value=1000000
            )
        elif choice == "5":
            config.max_audio_channels = prompt_int(
                "Max Audio Channels: ", default=2, max_value=8
            )


def handle_movies(config: Config, user_id: str):
    """Handle movie browsing and downloading"""
    from .api import list_movies

    movies = list_movies(config, user_id)
    if not movies:
        print("No movies found.")
        return

    while True:
        picked = pick_movie_or_show_from_list(movies, title="Movies")
        if picked in (None, "BACK") or not isinstance(picked, JellyfinMovie):
            break

        selected_index = movies.index(picked)
        process_download_or_stream(config, movies, selected_index, user_id)


def get_subtitles(
        config: Config,
        user_id: str,
        item_id: str,
        movie_or_episode_filename: str,
        output_dir: Path,
):
    # Ensure output directory exists
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    # We remove the video extension from the filename
    movie_or_episode_filename = os.path.splitext(movie_or_episode_filename)[0]

    session = requests.Session()
    # Jellyfin often requires the token in the header AND sometimes as a query param
    session.headers.update({"X-Emby-Token": config.api_key})

    playback_endpoint = f"{config.server_url}/Items/{item_id}/PlaybackInfo"

    try:
        response = session.post(playback_endpoint, params={"userId": user_id})
        response.raise_for_status()
        data = response.json()
    except Exception as e:
        print(f"Failed to reach PlaybackInfo: {e}")
        return

    media_sources = data.get("MediaSources", [])

    # Map Jellyfin Codecs to file extensions
    codec_map = {
        "subrip": "srt",
        "srt": "srt",
        "ass": "ass",
        "ssa": "ass",
        "mov_text": "srt",
        "vtt": "vtt",
        "pgssub": "sup",  # PGS is image-based
        "pgs": "sup",
    }

    print(f"\n--- Subtitle List for {movie_or_episode_filename} ---")
    subtitle_options = []
    for source in media_sources:
        s_id = source.get("Id")
        for stream in source.get("MediaStreams", []):
            if stream.get("Type") == "Subtitle":
                raw_codec = stream.get("Codec", "srt").lower()
                ext = codec_map.get(raw_codec, "srt")  # Default to srt if unknown

                subtitle_options.append(
                    {
                        "stream_index": stream.get("Index"),
                        "source_id": s_id,
                        "title": stream.get("DisplayTitle", "Subtitle"),
                        "lang": stream.get("Language", "und"),
                        "ext": ext,
                    }
                )
                print(
                    f"[{len(subtitle_options)}] {stream.get('DisplayTitle')} (Format: {raw_codec})"
                )

    if not subtitle_options:
        print("No subtitles found.")
        return

    choice = input("\nPick a number or type 'all': ").strip().lower()

    if choice == "all":
        to_download = subtitle_options
    elif choice.isdigit() and 1 <= int(choice) <= len(subtitle_options):
        to_download = [subtitle_options[int(choice) - 1]]
    else:
        return

    for sub in to_download:
        download_url = f"{config.server_url}/Videos/{item_id}/{sub['source_id']}/Subtitles/{sub['stream_index']}/Stream.{sub['ext']}"
        params = {"api_key": config.api_key}

        print(f"Downloading {sub['title']}...")
        res = session.get(download_url, params=params)

        if res.status_code == 200:
            clean_name = f"{movie_or_episode_filename}.{sub['lang']}.{sub['ext']}"
            with open(os.path.join(output_dir, clean_name), "wb") as f:
                f.write(res.content)
            print(f"Saved: {clean_name}")
        else:
            print(
                f"Error {res.status_code}: Server rejected the request for this format."
            )


def process_download_or_stream(
        config: Config,
        items: list[JellyfinMovie] | list[JellyfinEpisode],
        selected_index: int,
        user_id: str,
):
    from .api import get_media_id, build_stream_url
    from .download import get_audio_index

    target_item = items[selected_index]
    item_id, media_source_id = get_media_id(config, target_item)
    stream_url = build_stream_url(config, item_id, media_source_id=media_source_id)

    print("\nStream URL:")
    print(stream_url)

    confirm_download = ""
    while confirm_download.lower() != "y" and confirm_download.lower() != "n":
        confirm_download = input("\nDownload? (y/N): ").strip().lower()
        if confirm_download == "y":
            count = 1
            if (
                    target_item.Type != "Movie"
                    and len(items) > 1
                    and selected_index < len(items) - 1
            ):
                print(
                    "\nYou can download multiple items in sequence. If you want your choice and the next 2 episodes, enter 3."
                )
                count = prompt_int(
                    "How many items to download (including this one)? [default 1]: ",
                    default=1,
                )

            default_path = config.download_path
            if default_path:
                out_dir_raw = input(
                    f"Output directory [blank = {default_path}]: "
                ).strip()
            else:
                out_dir_raw = input(
                    "Output directory (blank = current folder): "
                ).strip()

            if out_dir_raw:
                output_directory = Path(out_dir_raw)
                config.download_path = out_dir_raw
                save_config(config)
            elif default_path:
                output_directory = Path(default_path)
            else:
                output_directory = Path(".")

            for i in range(selected_index, min(len(items), selected_index + count)):
                item = items[i]
                if isinstance(item, JellyfinMovie):
                    filename = sanitize_filename(item.Name or "Movie") + ".mp4"
                else:
                    filename = episode_filename(item, ".mp4")

                if i > 0:
                    item_id, media_source_id = get_media_id(config, item)

                sub_option = ""
                while sub_option.lower() != "y" and sub_option.lower() != "n":
                    sub_option = input("\nDownload subtitles? (y/N): ").strip().lower()
                    if sub_option.lower() == "y":
                        get_subtitles(
                            config, user_id, item_id, filename, output_directory
                        )
                    elif sub_option.lower() == "n":
                        print("\nSkipping subtitles...")
                    else:
                        print("\nPick a valid option.")

                output_path = output_directory / filename

                print(f"\nDownloading {filename}")
                print(f"-> {output_path}")

                if should_skip_transcode(item, config.video_bitrate):
                    download_direct(config, item.Id, output_path)
                else:
                    audio_index = get_audio_index(config, item_id)
                    stream_url = build_stream_url(
                        config,
                        item_id,
                        media_source_id,
                        audio_index,
                    )

                    duration_ticks = item.RunTimeTicks
                    estimated_size = 0
                    if duration_ticks and config.video_bitrate > 0:
                        duration_seconds = duration_ticks / 10_000_000
                        total_bitrate = config.video_bitrate + config.audio_bitrate
                        print(
                            f"Configured with VideoBitrate={config.video_bitrate}, AudioBitrate={config.audio_bitrate}, MaxStreamingBitrate={config.max_streaming_bitrate}"
                        )
                        if (
                                config.max_streaming_bitrate
                                and config.max_streaming_bitrate < total_bitrate
                        ):
                            total_bitrate = config.max_streaming_bitrate
                        estimated_size = (total_bitrate * duration_seconds) / 8
                        print(
                            f"Estimated size: ~{estimated_size / 1e6:.1f} MB (based on {total_bitrate / 1e6:.2f} Mbps and {duration_seconds:.0f} seconds)"
                        )

                    download_stream(stream_url, output_path, estimated_size)
            print("\nDone.")
        elif confirm_download == "n":
            break
        else:
            print("\nPick a valid option.")

    input("\nPress Enter to continue...")
