"""Segment matcher — aligns ride GPS data to tagged route segments.

Given a ride's GPS track and a ride profile's tagged segments (with start/end
lat/lon), identifies the time windows in the ride that correspond to each
segment. Uses proximity-based matching with a configurable tolerance radius.
"""

from __future__ import annotations

from datetime import timedelta
from typing import Optional

from geopy.distance import geodesic

from puncheur.models.ride import Ride
from puncheur.models.ride_profile import RideProfile
from puncheur.models.segment import Segment, SegmentMatch

# Default matching tolerance in meters
DEFAULT_TOLERANCE_M = 30.0

# Default pre-segment analysis window in seconds
DEFAULT_PRE_SEGMENT_WINDOW_S = 300  # 5 minutes


def _find_closest_point_index(
    ride: Ride,
    target_lat: float,
    target_lon: float,
    tolerance_m: float = DEFAULT_TOLERANCE_M,
    start_index: int = 0,
) -> Optional[int]:
    """Find the ride point closest to a target GPS coordinate.

    Searches from start_index forward, returning the index of the first
    point within the tolerance radius.

    Args:
        ride: The ride to search.
        target_lat: Target latitude in degrees.
        target_lon: Target longitude in degrees.
        tolerance_m: Maximum distance in meters to consider a match.
        start_index: Index to start searching from.

    Returns:
        Index of the closest matching point, or None if no match within tolerance.
    """
    target = (target_lat, target_lon)
    best_index: Optional[int] = None
    best_distance = float("inf")

    for i in range(start_index, len(ride.points)):
        point = ride.points[i]
        if point.latitude is None or point.longitude is None:
            continue

        dist = geodesic(target, (point.latitude, point.longitude)).meters
        if dist < best_distance:
            best_distance = dist
            best_index = i

        # If we've found a match within tolerance and distance is increasing,
        # we've passed the closest point
        if best_distance <= tolerance_m and dist > best_distance * 2:
            break

    if best_distance <= tolerance_m:
        return best_index
    return None


def match_segments(
    ride: Ride,
    profile: RideProfile,
    tolerance_m: float = DEFAULT_TOLERANCE_M,
    pre_segment_window_s: float = DEFAULT_PRE_SEGMENT_WINDOW_S,
) -> list[SegmentMatch]:
    """Match ride data to tagged segments in a ride profile.

    For each segment in the profile, finds the corresponding time window
    in the ride data using GPS proximity matching.

    Args:
        ride: The ride to analyze.
        profile: The ride profile with tagged segments.
        tolerance_m: GPS matching tolerance in meters.
        pre_segment_window_s: Seconds before segment start for pacing analysis.

    Returns:
        List of SegmentMatch objects for each successfully matched segment.
    """
    if not ride.has_gps:
        return []

    matches: list[SegmentMatch] = []
    search_start = 0

    for segment in profile.segments:
        match = _match_single_segment(
            ride, segment, tolerance_m, pre_segment_window_s, search_start
        )
        if match is not None:
            matches.append(match)
            # Advance search to avoid re-matching the same section
            end_idx = _find_closest_point_index(
                ride, segment.end_lat, segment.end_lon, tolerance_m, search_start
            )
            if end_idx is not None:
                search_start = end_idx

    return matches


def _match_single_segment(
    ride: Ride,
    segment: Segment,
    tolerance_m: float,
    pre_segment_window_s: float,
    search_start: int,
) -> Optional[SegmentMatch]:
    """Match a single segment to ride data."""
    start_idx = _find_closest_point_index(
        ride, segment.start_lat, segment.start_lon, tolerance_m, search_start
    )
    if start_idx is None:
        return None

    end_idx = _find_closest_point_index(
        ride, segment.end_lat, segment.end_lon, tolerance_m, start_idx
    )
    if end_idx is None:
        return None

    if end_idx <= start_idx:
        return None

    start_time = ride.points[start_idx].timestamp
    end_time = ride.points[end_idx].timestamp

    # Extract segment ride data
    segment_ride = ride.slice(start_time, end_time)

    # Extract pre-segment data
    pre_start = start_time - timedelta(seconds=pre_segment_window_s)
    pre_segment_ride = ride.slice(pre_start, start_time)

    # Compute segment metrics
    import numpy as np

    power_stream = segment_ride.power_stream
    avg_power = float(np.mean(power_stream)) if len(power_stream) > 0 else 0.0
    max_power = float(np.max(power_stream)) if len(power_stream) > 0 else 0.0
    np_val = segment_ride.normalized_power()

    hr_stream = segment_ride.heart_rate_stream
    avg_hr = float(np.mean(hr_stream[hr_stream > 0])) if np.any(hr_stream > 0) else 0.0

    cadence_stream = segment_ride.cadence_stream
    avg_cadence = (
        float(np.mean(cadence_stream[cadence_stream > 0]))
        if np.any(cadence_stream > 0)
        else 0.0
    )

    duration = (end_time - start_time).total_seconds()

    # Elevation gain
    alt_stream = segment_ride.altitude_stream
    elev_gain = 0.0
    if len(alt_stream) > 1:
        diffs = np.diff(alt_stream)
        elev_gain = float(np.sum(diffs[diffs > 0]))

    return SegmentMatch(
        segment=segment,
        start_time=start_time,
        end_time=end_time,
        ride_data=segment_ride,
        pre_segment_data=pre_segment_ride,
        avg_power=avg_power,
        max_power=max_power,
        normalized_power=np_val,
        avg_heart_rate=avg_hr,
        avg_cadence=avg_cadence,
        duration_seconds=duration,
        elevation_gain=elev_gain,
    )
