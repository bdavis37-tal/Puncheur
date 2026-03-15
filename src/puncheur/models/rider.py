"""Rider profile model.

Represents a cyclist's physiological profile: FTP, weight, power zones,
W' (anaerobic capacity), and max heart rate. Power zones can be auto-calculated
from FTP using Coggan's standard percentages.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from puncheur.config import coggan_power_zones, get_rider_profile_path, load_json, save_json


@dataclass
class Rider:
    """A cyclist's profile and physiological characteristics.

    Attributes:
        name: Rider's name.
        ftp: Functional Threshold Power in watts.
        weight_kg: Body weight in kilograms.
        power_zones: Power zone boundaries as {zone_name: [lower, upper]}.
        max_heart_rate: Maximum heart rate in BPM.
        w_prime: W' (W-prime) anaerobic capacity in joules.
    """

    name: str = ""
    ftp: int = 200
    weight_kg: float = 75.0
    power_zones: dict[str, list[int]] = field(default_factory=dict)
    max_heart_rate: int = 185
    w_prime: int = 20000

    def __post_init__(self) -> None:
        """Auto-calculate power zones from FTP if not provided."""
        if not self.power_zones:
            self.power_zones = coggan_power_zones(self.ftp)

    @property
    def w_per_kg(self) -> float:
        """FTP in watts per kilogram."""
        if self.weight_kg <= 0:
            return 0.0
        return self.ftp / self.weight_kg

    def zone_for_power(self, power: float) -> str:
        """Return the zone name for a given power value."""
        for zone_name, (lower, upper) in self.power_zones.items():
            if lower <= power <= upper:
                return zone_name
        return "z7_neuromuscular"

    def to_dict(self) -> dict:
        """Serialize to dictionary for JSON storage."""
        return {
            "name": self.name,
            "ftp": self.ftp,
            "weight_kg": self.weight_kg,
            "power_zones": self.power_zones,
            "max_heart_rate": self.max_heart_rate,
            "w_prime": self.w_prime,
        }

    @classmethod
    def from_dict(cls, data: dict) -> Rider:
        """Deserialize from dictionary."""
        return cls(
            name=data.get("name", ""),
            ftp=data.get("ftp", 200),
            weight_kg=data.get("weight_kg", 75.0),
            power_zones=data.get("power_zones", {}),
            max_heart_rate=data.get("max_heart_rate", 185),
            w_prime=data.get("w_prime", 20000),
        )

    def save(self, path: Optional[Path] = None) -> None:
        """Save rider profile to JSON file."""
        save_json(path or get_rider_profile_path(), self.to_dict())

    @classmethod
    def load(cls, path: Optional[Path] = None) -> Rider:
        """Load rider profile from JSON file."""
        data = load_json(path or get_rider_profile_path())
        return cls.from_dict(data)
