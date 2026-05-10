"""Jellyfin API interactions."""

from typing import Optional, TypeVar
from urllib.parse import urlencode

import requests

from .classes import (
    BaseItem,
    Config,
    JellyfinEpisode,
    JellyfinMovie,
    JellyfinSeason,
    JellyfinSeries,
)

T = TypeVar("T", bound=BaseItem)

TIMEOUT = 30


def jget(base, path, api_key, params=None):
    """Make GET request to Jellyfin API."""
    params = dict(params or {})
    params["api_key"] = api_key
    url = base.rstrip("/") + path
    r = requests.get(url, params=params, timeout=TIMEOUT)
    r.raise_for_status()
    return r.json()


def authenticate(base, username, password):
    """Authenticate with Jellyfin using username and password."""
    url = base.rstrip("/") + "/Users/AuthenticateByName"
    headers = {
        "Content-Type": "application/json",
        "X-Emby-Authorization": 'MediaBrowser Client="JellyfinDownloader", Device="JellyfinDownloader", DeviceId="JellyfinDownloader", Version="1.0.0"',
    }
    payload = {"Username": username, "Pw": password}
    try:
        resp = requests.post(url, json=payload, headers=headers, timeout=TIMEOUT)
        resp.raise_for_status()
        data = resp.json()
        return data.get("AccessToken")
    except Exception as e:
        print(f"Authentication failed: {e}")
        return None


def build_stream_url(
        config: Config, item_id: str, media_source_id=None, audio_index=None
):
    """Build stream URL with transcoding parameters."""
    params = {
        "api_key": config.api_key,
        "container": "mp4",
        "VideoCodec": config.video_codec,
        "AudioCodec": config.audio_codec,
        "VideoBitrate": config.video_bitrate,
        "MaxStreamingBitrate": config.max_streaming_bitrate,
        "AudioBitrate": config.audio_bitrate,
        "MaxAudioChannels": config.max_audio_channels,
        "SubtitleMethod": config.subtitle_method,
        "allowVideoStreamCopy": "true",
        "allowAudioStreamCopy": "true",
    }
    if media_source_id:
        params["MediaSourceId"] = media_source_id
    if audio_index is not None:
        params["AudioStreamIndex"] = audio_index

    return f"{config.server_url.rstrip('/')}/Videos/{item_id}/stream.mp4?{urlencode(params)}"


def _paginate_items(
        config: Config, endpoint: str, params: dict, model: type[T]
) -> list[T]:
    """Paginate through a Jellyfin list endpoint and parse each item into ``model``."""
    start_index = 0
    limit = 200
    all_items: list[T] = []

    while True:
        data = jget(
            config.server_url,
            endpoint,
            config.api_key,
            params={**params, "StartIndex": start_index, "Limit": limit},
        )
        raw = data.get("Items", [])
        all_items.extend(model(**i) for i in raw)
        total = data.get("TotalRecordCount", len(all_items))
        start_index += len(raw)
        if start_index >= total or not raw:
            break

    return all_items


_LIBRARY_PARAMS = {
    "Recursive": "true",
    "SortBy": "SortName",
    "SortOrder": "Ascending",
    "Fields": "PrimaryImageAspectRatio,MediaSources",
}


def list_movies(config: Config, user_id: str) -> list[JellyfinMovie]:
    """List all movies in the user's library."""
    return _paginate_items(
        config,
        f"/Users/{user_id}/Items",
        {**_LIBRARY_PARAMS, "IncludeItemTypes": "Movie"},
        JellyfinMovie,
    )


def list_series(config: Config, user_id: str) -> list[JellyfinSeries]:
    """List all series in the user's library."""
    return _paginate_items(
        config,
        f"/Users/{user_id}/Items",
        {**_LIBRARY_PARAMS, "IncludeItemTypes": "Series"},
        JellyfinSeries,
    )


def list_seasons(
        config: Config, user_id: str, series_id: str
) -> list[JellyfinSeason]:
    """List all seasons for a given series."""
    return _paginate_items(
        config,
        f"/Shows/{series_id}/Seasons",
        {"UserId": user_id},
        JellyfinSeason,
    )


def list_episodes(
        config: Config,
        user_id: str,
        series_id: str,
        season_id: Optional[str] = None,
) -> list[JellyfinEpisode]:
    """List episodes for a series, optionally filtered to a single season."""
    params: dict = {
        "UserId": user_id,
        "Fields": "MediaSources,Overview,RunTimeTicks,SeriesName,ParentIndexNumber,IndexNumber,Name",
        "SortBy": "IndexNumber",
        "SortOrder": "Ascending",
    }
    if season_id:
        params["SeasonId"] = season_id
    return _paginate_items(
        config,
        f"/Shows/{series_id}/Episodes",
        params,
        JellyfinEpisode,
    )


def get_media_id(
        config: Config, item: JellyfinMovie | JellyfinEpisode
) -> tuple[str, Optional[str]]:
    """Return ``(item_id, media_source_id)`` for a downloadable item.

    Falls back to fetching ``/Items/{id}`` if the item's MediaSources is empty.
    """
    item_id = item.Id
    media_source_id: Optional[str] = None

    if item.MediaSources:
        media_source_id = item.MediaSources[0].Id

    if not media_source_id:
        full = jget(config.server_url, f"/Items/{item_id}", config.api_key)
        ms = full.get("MediaSources") or []
        if ms and isinstance(ms[0], dict):
            media_source_id = ms[0].get("Id")

    return item_id, media_source_id
