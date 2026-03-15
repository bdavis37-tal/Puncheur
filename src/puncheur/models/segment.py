"""Segment and attack zone models.

A Segment defines a section of a route (typically a climb) with start/end
GPS coordinates and metadata. A SegmentMatch links a segment definition
to actual ride data — the time window and data slice from when you rode it.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from puncheur.models.ride import Ride


@dataclass
class Segment:
    """A tagged segment on a ride route.

    Segments are the building blocks of ride profiles — they mark the
    climbs, sprints, and key efforts that define a route's character.

    Attributes:
        name: Human-readable name (e.g., "Rea Road Kicker").
        start_lat: GPS latitude of segment start in degrees.
        start_lon: GPS longitude of segment start in degrees.
        end_lat: GPS latitude of segment end in degrees.
        end_lon: GPS longitude of segment end in degrees.
        segment_type: Category — "climb", "sprint", "flat", "descent".
        estimated_duration_seconds: Expected time to complete in seconds.
        avg_gradient_pct: Average gradient as a percentage.
        notes: Tactical notes about this segment.
    """

    name: str
    start_lat: float
    start_lon: float
    end_lat: float
    end_lon: float
    segment_type: str = "climb"
    estimated_duration_seconds: float = 0.0
    avg_gradient_pct: float = 0.0
    notes: str = ""

    def to_dict(self) -> dict:
        """Serialize to dictionary for JSON storage."""
        return {
            "name": self.name,
            "start_lat": self.start_lat,
            "start_lon": self.start_lon,
            "end_lat": self.end_lat,
            "end_lon": self.end_lon,
            "type": self.segment_type,
            "estimated_duration_seconds": self.estimated_duration_seconds,
            "avg_gradient_pct": self.avg_gradient_pct,
            "notes": self.notes,
        }

    @classmethod
    def from_dict(cls, data: dict) -> Segment:
        """Deserialize from dictionary."""
        return cls(
            name=data["name"],
            start_lat=data["start_lat"],
            start_lon=data["start_lon"],
            end_lat=data["end_lat"],
            end_lon=data["end_lon"],
            segment_type=data.get("type", "climb"),
            estimated_duration_seconds=data.get("estimated_duration_seconds", 0.0),
            avg_gradient_pct=data.get("avg_gradient_pct", 0.0),
            notes=data.get("notes", ""),
        )


@dataclass
class SegmentMatch:
    """A matched segment from actual ride data.

    Created by the segment matcher when aligning a ride's GPS track
    to a ride profile's tagged segments.

    Attributes:
        segment: The segment definition that was matched.
        start_time: Timestamp when the rider entered the segment.
        end_time: Timestamp when the rider exited the segment.
        ride_data: Slice of ride data covering this segment.
        pre_segment_data: Slice of ride data for the approach window.
        avg_power: Average power during the segment.
        max_power: Peak power during the segment.
        normalized_power: Normalized power during the segment.
        avg_heart_rate: Average HR during the segment.
        avg_cadence: Average cadence during the segment.
        duration_seconds: Actual time to complete the segment.
    """

    segment: Segment
    start_time: datetime
    end_time: datetime
    ride_data: Optional[Ride] = None
    pre_segment_data: Optional[Ride] = None
    avg_power: float = 0.0
    max_power: float = 0.0
    normalized_power: float = 0.0
    avg_heart_rate: float = 0.0
    avg_cadence: float = 0.0
    duration_seconds: float = 0.0
    wbal_at_entry: float = 0.0
    elevation_gain: float = 0.0
