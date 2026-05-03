"""State-vector conversions among ECEF, NTN-ECI, TEME, and J2000.

The NTN-ECI frame used here follows the NR NTN convention described by the
project: it is an inertial geocentric frame whose axes coincide with ECEF at
``epoch_time``. Positions are metres and velocities are metres per second.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from typing import Literal

import numpy as np
from astropy import units as u
from astropy.coordinates import (
    CartesianDifferential,
    CartesianRepresentation,
    GCRS,
    ITRS,
    SkyCoord,
    TEME,
)
from astropy.time import Time
from astropy.utils import iers

iers.conf.auto_download = False

FrameName = Literal["ecef", "ntn-eci", "teme", "j2000"]


@dataclass(frozen=True)
class StateVector:
    """Cartesian state vector in metres and metres per second."""

    position_m: np.ndarray
    velocity_mps: np.ndarray

    def __post_init__(self) -> None:
        object.__setattr__(self, "position_m", _as_vector(self.position_m, "position_m"))
        object.__setattr__(self, "velocity_mps", _as_vector(self.velocity_mps, "velocity_mps"))


def convert_state(
    position_m: np.ndarray | list[float] | tuple[float, float, float],
    velocity_mps: np.ndarray | list[float] | tuple[float, float, float],
    *,
    from_frame: FrameName,
    to_frame: FrameName,
    time: Time | str | float,
    epoch_time: Time | str | float | None = None,
) -> StateVector:
    """Convert a Cartesian state between supported frames.

    ``time`` is the state epoch. Numeric times are interpreted as seconds after
    Unix UTC. ``epoch_time`` is required when either frame is ``"ntn-eci"`` and
    has the same numeric convention.
    """

    state = StateVector(np.asarray(position_m, dtype=float), np.asarray(velocity_mps, dtype=float))
    obstime = _to_time(time)
    source = _normalize_frame(from_frame)
    target = _normalize_frame(to_frame)

    if source == target:
        return state

    gcrs_state = _to_gcrs(state, source, obstime, _to_epoch(epoch_time, source, target))
    return _from_gcrs(gcrs_state, target, obstime, _to_epoch(epoch_time, source, target))


def _to_gcrs(state: StateVector, frame: FrameName, obstime: Time, epoch_time: Time | None) -> StateVector:
    if frame == "j2000":
        return state
    if frame == "ntn-eci":
        assert epoch_time is not None
        rot = _ntn_to_gcrs_matrix(epoch_time)
        return StateVector(rot @ state.position_m, rot @ state.velocity_mps)

    coord = _state_to_coord(state, _astropy_frame(frame, obstime))
    transformed = coord.transform_to(GCRS(obstime=obstime))
    return _coord_to_state(transformed)


def _from_gcrs(state: StateVector, frame: FrameName, obstime: Time, epoch_time: Time | None) -> StateVector:
    if frame == "j2000":
        return state
    if frame == "ntn-eci":
        assert epoch_time is not None
        rot = _ntn_to_gcrs_matrix(epoch_time)
        return StateVector(rot.T @ state.position_m, rot.T @ state.velocity_mps)

    coord = _state_to_coord(state, GCRS(obstime=obstime))
    transformed = coord.transform_to(_astropy_frame(frame, obstime))
    return _coord_to_state(transformed)


def _state_to_coord(state: StateVector, frame: ITRS | TEME | GCRS) -> SkyCoord:
    rep = CartesianRepresentation(*(state.position_m * u.m))
    diff = CartesianDifferential(*(state.velocity_mps * (u.m / u.s)))
    return SkyCoord(rep.with_differentials(diff), frame=frame)


def _coord_to_state(coord: SkyCoord) -> StateVector:
    cart = coord.cartesian
    diff = cart.differentials["s"]
    return StateVector(
        cart.xyz.to_value(u.m),
        diff.d_xyz.to_value(u.m / u.s),
    )


def _astropy_frame(frame: FrameName, obstime: Time) -> ITRS | TEME:
    if frame == "ecef":
        return ITRS(obstime=obstime)
    if frame == "teme":
        return TEME(obstime=obstime)
    raise ValueError(f"{frame!r} is not an Astropy-backed frame")


@lru_cache(maxsize=128)
def _ntn_to_gcrs_matrix(epoch_time: Time) -> np.ndarray:
    basis = np.eye(3)
    columns = []
    for axis in basis:
        coord = SkyCoord(
            CartesianRepresentation(*(axis * u.m)),
            frame=ITRS(obstime=epoch_time),
        ).transform_to(GCRS(obstime=epoch_time))
        columns.append(coord.cartesian.xyz.to_value(u.m))
    matrix = np.column_stack(columns)
    u_mat, _, vh_mat = np.linalg.svd(matrix)
    return u_mat @ vh_mat


def _normalize_frame(frame: str) -> FrameName:
    key = frame.strip().lower().replace("_", "-")
    aliases = {
        "itrs": "ecef",
        "wgs84": "ecef",
        "ntneci": "ntn-eci",
        "ntn-eci": "ntn-eci",
        "gcrs": "j2000",
        "eme2000": "j2000",
        "j2000": "j2000",
        "teme": "teme",
        "ecef": "ecef",
    }
    if key not in aliases:
        raise ValueError(f"unsupported frame {frame!r}")
    return aliases[key]  # type: ignore[return-value]


def _to_time(value: Time | str | float) -> Time:
    if isinstance(value, Time):
        return value
    if isinstance(value, (int, float)):
        return Time(float(value), format="unix", scale="utc")
    return Time(value, scale="utc")


def _to_epoch(epoch_time: Time | str | float | None, source: FrameName, target: FrameName) -> Time | None:
    if source != "ntn-eci" and target != "ntn-eci":
        return None
    if epoch_time is None:
        raise ValueError("epoch_time is required for NTN-ECI conversions")
    return _to_time(epoch_time)


def _as_vector(value: np.ndarray, name: str) -> np.ndarray:
    vector = np.asarray(value, dtype=float)
    if vector.shape != (3,):
        raise ValueError(f"{name} must be a 3-vector")
    return vector
