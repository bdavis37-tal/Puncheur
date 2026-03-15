"""Ride data model — the core representation of a parsed FIT file.

A Ride is a time-ordered sequence of RidePoint samples, each containing
power, heart rate, cadence, speed, GPS position, and elevation. This is
the foundation that all analytics operate on.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

import numpy as np


@dataclass
class RidePoint:
    """A single data point from a ride recording.

    Attributes:
        timestamp: When this sample was recorded.
        power: Instantaneous power in watts. None if no power meter.
        heart_rate: Heart rate in BPM. None if no HR sensor.
        cadence: Pedaling cadence in RPM. None if no cadence sensor.
        speed: Ground speed in m/s. None if not available.
        latitude: GPS latitude in degrees. None if no GPS fix.
        longitude: GPS longitude in degrees. None if no GPS fix.
        altitude: Elevation in meters above sea level. None if not available.
    """

    timestamp: datetime
    power: Optional[float] = None
    heart_rate: Optional[float] = None
    cadence: Optional[float] = None
    speed: Optional[float] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    altitude: Optional[float] = None


@dataclass
class Ride:
    """A complete ride parsed from a FIT file.

    Contains the raw data points plus computed summary metrics.
    The points list is always sorted by timestamp.

    Attributes:
        name: Optional ride name/title.
        points: Time-ordered list of ride data points.
        source_file: Path to the original FIT file.
    """

    name: str = ""
    points: list[RidePoint] = field(default_factory=list)
    source_file: str = ""

    @property
    def duration_seconds(self) -> float:
        """Total ride duration in seconds."""
        if len(self.points) < 2:
            return 0.0
        return (self.points[-1].timestamp - self.points[0].timestamp).total_seconds()

    @property
    def power_stream(self) -> np.ndarray:
        """Extract power values as a numpy array, replacing None with 0."""
        return np.array([p.power if p.power is not None else 0.0 for p in self.points])

    @property
    def heart_rate_stream(self) -> np.ndarray:
        """Extract heart rate values as a numpy array, replacing None with 0."""
        return np.array([p.heart_rate if p.heart_rate is not None else 0.0 for p in self.points])

    @property
    def cadence_stream(self) -> np.ndarray:
        """Extract cadence values as a numpy array, replacing None with 0."""
        return np.array([p.cadence if p.cadence is not None else 0.0 for p in self.points])

    @property
    def speed_stream(self) -> np.ndarray:
        """Extract speed values as a numpy array, replacing None with 0."""
        return np.array([p.speed if p.speed is not None else 0.0 for p in self.points])

    @property
    def altitude_stream(self) -> np.ndarray:
        """Extract altitude values as a numpy array, replacing None with 0."""
        return np.array([p.altitude if p.altitude is not None else 0.0 for p in self.points])

    @property
    def has_power(self) -> bool:
        """Check if this ride contains any power data."""
        return any(p.power is not None for p in self.points)

    @property
    def has_heart_rate(self) -> bool:
        """Check if this ride contains any heart rate data."""
        return any(p.heart_rate is not None for p in self.points)

    @property
    def has_gps(self) -> bool:
        """Check if this ride contains any GPS data."""
        return any(p.latitude is not None and p.longitude is not None for p in self.points)

    @property
    def avg_power(self) -> float:
        """Average power in watts (excluding zeros/None)."""
        powers = [p.power for p in self.points if p.power is not None and p.power > 0]
        return float(np.mean(powers)) if powers else 0.0

    def normalized_power(self) -> float:
        """Calculate Normalized Power (NP).

        NP is the fourth root of the average of the rolling 30-second
        average power raised to the fourth power. This weights harder
        efforts more heavily than simple average power.
        """
        power = self.power_stream
        if len(power) < 30:
            return self.avg_power

        # Rolling 30-second average
        window = 30
        rolling_avg = np.convolve(power, np.ones(window) / window, mode="valid")

        # Fourth power, then average, then fourth root
        return float(np.power(np.mean(np.power(rolling_avg, 4)), 0.25))

    def intensity_factor(self, ftp: float) -> float:
        """Calculate Intensity Factor (IF = NP / FTP)."""
        if ftp <= 0:
            return 0.0
        return self.normalized_power() / ftp

    def tss(self, ftp: float) -> float:
        """Calculate Training Stress Score.

        TSS = (duration_seconds * NP * IF) / (FTP * 3600) * 100
        """
        if ftp <= 0:
            return 0.0
        np_val = self.normalized_power()
        if_val = np_val / ftp
        return (self.duration_seconds * np_val * if_val) / (ftp * 3600) * 100

    def slice(self, start: datetime, end: datetime) -> Ride:
        """Return a new Ride containing only points within the time window."""
        sliced_points = [p for p in self.points if start <= p.timestamp <= end]
        return Ride(name=self.name, points=sliced_points, source_file=self.source_file)
