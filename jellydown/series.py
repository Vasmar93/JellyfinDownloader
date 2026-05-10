from .api import list_episodes, list_seasons, list_series
from .classes import (
    Config,
    JellyfinEpisode,
    JellyfinSeason,
    JellyfinSeries,
)
from .ui import (
    pick_episode_from_list,
    pick_movie_or_show_from_list,
    pick_season_from_list,
    process_download_or_stream,
)


def handle_series(config: Config, user_id: str):
    """Handle series browsing and download."""

    series_items = list_series(config, user_id)
    if not series_items:
        print("No series found.")
        return

    while True:
        series = pick_movie_or_show_from_list(series_items, title="Series")
        if series in (None, "BACK") or not isinstance(series, JellyfinSeries):
            break

        print(f"\nSelected series: {series.Name}")

        seasons = list_seasons(config, user_id, series.Id)
        if not seasons:
            print("No seasons found for this series.")
            continue

        season = pick_season_from_list(
            seasons, title=f"Seasons of {series.Name}"
        )
        if season in (None, "BACK") or not isinstance(season, JellyfinSeason):
            continue

        season_label = season.Name or (
            f"Season {season.IndexNumber}" if season.IndexNumber is not None else "Season"
        )

        episodes = list_episodes(
            config, user_id, series.Id, season_id=season.Id
        )
        if not episodes:
            print("No episodes found in that season.")
            continue

        episode = pick_episode_from_list(
            episodes, title=f"Episodes in {season_label}"
        )
        if episode in (None, "BACK") or not isinstance(episode, JellyfinEpisode):
            continue

        selected_index = episodes.index(episode)
        process_download_or_stream(config, episodes, selected_index, user_id)
