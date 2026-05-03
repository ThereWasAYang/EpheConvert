"""Conversions among UTC, GPS time, and BeiDou time."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from astropy.time import Time

TimeSystem = Literal["utc", "gps", "bdt"]
GPS_EPOCH_UTC = "1980-01-06T00:00:00"
BDT_EPOCH_UTC = "2006-01-01T00:00:00"


@dataclass(frozen=True)
class TimeConversion:
    """Converted time value.

    UTC is returned as an ISO string. GPS and BDT are returned as continuous
    seconds from their system epochs.
    """

    system: TimeSystem
    value: str | float
    astropy_time: Time


def convert_time(value: Time | str | float, *, from_system: TimeSystem, to_system: TimeSystem) -> TimeConversion:
    """Convert UTC, GPS, and BeiDou time values.

    Numeric UTC values are Unix UTC seconds. GPS values are seconds since
    ``1980-01-06T00:00:00`` GPS. BDT values are seconds since
    ``2006-01-01T00:00:00`` BeiDou Time; BDT is treated as continuous and
    aligned to GPS by the standard 14 second scale offset.
    """

    source = _normalize_system(from_system)
    target = _normalize_system(to_system)
    time = _to_astropy_time(value, source)
    return TimeConversion(target, _from_astropy_time(time, target), time)


def _to_astropy_time(value: Time | str | float, system: TimeSystem) -> Time:
    if isinstance(value, Time):
        return value
    if system == "utc":
        if isinstance(value, (int, float)):
            return Time(float(value), format="unix", scale="utc")
        return Time(value, scale="utc")
    if system == "gps":
        return Time(float(value), format="gps")
    if system == "bdt":
        return Time(_bdt_epoch_gps_seconds() + float(value), format="gps")
    raise ValueError(f"unsupported time system {system!r}")


def _from_astropy_time(time: Time, system: TimeSystem) -> str | float:
    if system == "utc":
        return time.utc.isot
    if system == "gps":
        return float(time.gps)
    if system == "bdt":
        return float(time.gps - _bdt_epoch_gps_seconds())
    raise ValueError(f"unsupported time system {system!r}")


def _bdt_epoch_gps_seconds() -> float:
    return float(Time(BDT_EPOCH_UTC, scale="utc").gps)


def _normalize_system(system: str) -> TimeSystem:
    key = system.strip().lower()
    aliases = {"utc": "utc", "gps": "gps", "gpst": "gps", "bdt": "bdt", "beidou": "bdt", "北斗": "bdt"}
    if key not in aliases:
        raise ValueError(f"unsupported time system {system!r}")
    return aliases[key]  # type: ignore[return-value]
