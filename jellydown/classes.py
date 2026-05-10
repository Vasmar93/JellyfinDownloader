from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class Config(BaseModel):
    # We define defaults directly in the class
    server_url: str = ""
    api_key: str = ""
    video_codec: str = "h264"
    audio_codec: str = "aac"
    video_bitrate: int = 4_000_000
    max_streaming_bitrate: int = 4_000_000
    audio_bitrate: int = 128_000
    max_audio_channels: int = 2
    subtitle_method: str = "Encode"
    download_path: str = ""


class JellyfinUserData(BaseModel):
    IsFavorite: bool
    ItemId: str
    Key: str
    PlayCount: int
    PlaybackPositionTicks: int
    Played: bool
    UnplayedItemCount: Optional[int] = None


class BaseItem(BaseModel):
    model_config = ConfigDict(extra="ignore")

    Id: str
    Name: str
    Type: str
    ServerId: str
    IsFolder: bool = False
    LocationType: Optional[str] = None
    MediaType: Optional[str] = None
    OfficialRating: Optional[str] = None
    CommunityRating: Optional[float] = None
    PremiereDate: Optional[datetime] = None
    ProductionYear: Optional[int] = None
    RunTimeTicks: Optional[int] = None
    PrimaryImageAspectRatio: Optional[float] = None
    ChannelId: Optional[str] = None
    BackdropImageTags: list[str] = []
    ImageTags: dict[str, str] = {}
    ImageBlurHashes: dict[str, dict[str, str]] = {}
    UserData: Optional[JellyfinUserData] = None


class MediaSource(BaseModel):
    model_config = ConfigDict(extra="ignore")

    Id: str
    Name: Optional[str] = None
    Path: Optional[str] = None
    Container: Optional[str] = None
    Protocol: Optional[str] = None
    Type: Optional[str] = None
    VideoType: Optional[str] = None
    Bitrate: Optional[int] = None
    Size: Optional[int] = None
    RunTimeTicks: Optional[int] = None
    ETag: Optional[str] = None
    DefaultAudioStreamIndex: Optional[int] = None
    DefaultSubtitleStreamIndex: Optional[int] = None
    TranscodingSubProtocol: Optional[str] = None
    IsRemote: bool = False
    IsInfiniteStream: bool = False
    ReadAtNativeFramerate: bool = False
    SupportsDirectPlay: bool = False
    SupportsDirectStream: bool = False
    SupportsTranscoding: bool = False
    SupportsProbing: bool = False
    RequiresOpening: bool = False
    RequiresClosing: bool = False
    RequiresLooping: bool = False
    HasSegments: bool = False
    IgnoreDts: bool = False
    IgnoreIndex: bool = False
    GenPtsInput: bool = False
    UseMostCompatibleTranscodingProfile: bool = False
    Formats: list[str] = []
    MediaAttachments: list[dict] = []
    MediaStreams: list[dict] = []
    RequiredHttpHeaders: dict[str, str] = {}


class JellyfinSeries(BaseItem):
    Status: Optional[str] = None
    EndDate: Optional[datetime] = None
    AirDays: list[str] = []


class JellyfinMovie(BaseItem):
    Container: Optional[str] = None
    VideoType: Optional[str] = None
    HasSubtitles: Optional[bool] = None
    CriticRating: Optional[float] = None
    MediaSources: list[MediaSource] = []


class JellyfinSeason(BaseItem):
    IndexNumber: Optional[int] = None
    ParentIndexNumber: Optional[int] = None
    SeriesId: Optional[str] = None
    SeriesName: Optional[str] = None
    SeriesPrimaryImageTag: Optional[str] = None
    ChildCount: Optional[int] = None
    RecursiveItemCount: Optional[int] = None


class JellyfinEpisode(BaseItem):
    IndexNumber: Optional[int] = None
    ParentIndexNumber: Optional[int] = None
    SeriesId: Optional[str] = None
    SeriesName: Optional[str] = None
    SeasonId: Optional[str] = None
    SeasonName: Optional[str] = None
    Container: Optional[str] = None
    VideoType: Optional[str] = None
    HasSubtitles: Optional[bool] = None
    Overview: Optional[str] = None
    MediaSources: list[MediaSource] = []


@dataclass
class AudioTrack:
    index: int
    language: str
    codec: Optional[str]
    bitrate: Optional[int]
    title: Optional[str]
    display_title: Optional[str]
    is_default: bool
    is_forced: bool
    is_hearing_impaired: bool
