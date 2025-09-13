from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Literal


class UpdateCadence(str, Enum):
    OFF = "off"
    LAUNCH = "launch"
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"

    def __str__(self) -> str:
        # Return the raw value for friendlier serialization and tests
        return str(self.value)


class UpdateAction(str, Enum):
    NO_CHECK = "no_check"  
    PROMPT = "prompt" 
    AUTO = "auto" 

    def __str__(self) -> str:
        # Return the raw value for friendlier serialization and tests
        return str(self.value)


@dataclass
class UpdateSchedule:
    cadence: UpdateCadence = UpdateCadence.OFF
    last_check_ts: Optional[float] = None  # epoch seconds


@dataclass
class AppUpdateConfig:
    schedule: UpdateSchedule = field(default_factory=UpdateSchedule)
    action: UpdateAction = UpdateAction.PROMPT


@dataclass
class YTDLPUpdateConfig:
    enabled: bool = True
    schedule: UpdateSchedule = field(
        default_factory=lambda: UpdateSchedule(UpdateCadence.DAILY)
    )


@dataclass
class NotificationSpec:
    category: Literal["info", "success", "fail"]
    message: str
    duration_ms: int
    sticky: bool = False


@dataclass
class DownloadItem:
    source_url: str
    normalized_url: str
    target_format: str
    output_path: Optional[str] = None
    state: str = "CREATED"  # consider enum later
    progress: float = 0.0
    error: Optional[str] = None
