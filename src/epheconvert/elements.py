"""Keplerian element conversions for inertial Earth-centred frames."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .coordinates import FrameName, StateVector, convert_state

EARTH_MU_M3_S2 = 3.986004418e14
_TOL = 1e-12


@dataclass(frozen=True)
class KeplerianElements:
    """Classical Keplerian elements.

    Angles are radians. ``a_m`` is the semi-major axis in metres.
    """

    a_m: float
    eccentricity: float
    inclination_rad: float
    raan_rad: float
    argp_rad: float
    true_anomaly_rad: float


def convert_elements(
    elements: KeplerianElements,
    *,
    from_frame: FrameName,
    to_frame: FrameName,
    time,
    epoch_time=None,
    mu_m3_s2: float = EARTH_MU_M3_S2,
) -> KeplerianElements:
    """Convert Keplerian elements among NTN-ECI, TEME, and J2000."""

    _require_inertial_elements_frame(from_frame)
    _require_inertial_elements_frame(to_frame)
    state = elements_to_state(elements, mu_m3_s2=mu_m3_s2)
    converted = convert_state(
        state.position_m,
        state.velocity_mps,
        from_frame=from_frame,
        to_frame=to_frame,
        time=time,
        epoch_time=epoch_time,
    )
    return state_to_elements(converted.position_m, converted.velocity_mps, mu_m3_s2=mu_m3_s2)


def elements_to_state(elements: KeplerianElements, *, mu_m3_s2: float = EARTH_MU_M3_S2) -> StateVector:
    """Convert classical Keplerian elements to an inertial Cartesian state."""

    a = float(elements.a_m)
    e = float(elements.eccentricity)
    inc = float(elements.inclination_rad)
    raan = float(elements.raan_rad)
    argp = float(elements.argp_rad)
    nu = float(elements.true_anomaly_rad)

    if a <= 0:
        raise ValueError("a_m must be positive for elliptic orbits")
    if not 0 <= e < 1:
        raise ValueError("eccentricity must satisfy 0 <= e < 1")

    p = a * (1 - e * e)
    radius = p / (1 + e * np.cos(nu))
    r_pqw = np.array([radius * np.cos(nu), radius * np.sin(nu), 0.0])
    v_pqw = np.sqrt(mu_m3_s2 / p) * np.array([-np.sin(nu), e + np.cos(nu), 0.0])

    rotation = _rotation_z(raan) @ _rotation_x(inc) @ _rotation_z(argp)
    return StateVector(rotation @ r_pqw, rotation @ v_pqw)


def state_to_elements(
    position_m,
    velocity_mps,
    *,
    mu_m3_s2: float = EARTH_MU_M3_S2,
) -> KeplerianElements:
    """Convert an inertial Cartesian state to classical Keplerian elements."""

    r_vec = np.asarray(position_m, dtype=float)
    v_vec = np.asarray(velocity_mps, dtype=float)
    r_norm = np.linalg.norm(r_vec)
    v_norm = np.linalg.norm(v_vec)
    if r_vec.shape != (3,) or v_vec.shape != (3,):
        raise ValueError("position_m and velocity_mps must be 3-vectors")
    if r_norm <= 0:
        raise ValueError("position vector must be non-zero")

    h_vec = np.cross(r_vec, v_vec)
    h_norm = np.linalg.norm(h_vec)
    if h_norm <= 0:
        raise ValueError("angular momentum is zero")

    k_vec = np.array([0.0, 0.0, 1.0])
    n_vec = np.cross(k_vec, h_vec)
    n_norm = np.linalg.norm(n_vec)
    e_vec = np.cross(v_vec, h_vec) / mu_m3_s2 - r_vec / r_norm
    e = np.linalg.norm(e_vec)

    energy = v_norm * v_norm / 2 - mu_m3_s2 / r_norm
    if abs(energy) <= _TOL:
        raise ValueError("parabolic orbits are not represented by finite a_m")
    a = -mu_m3_s2 / (2 * energy)

    inc = np.arccos(np.clip(h_vec[2] / h_norm, -1.0, 1.0))
    raan = _angle_0_2pi(np.arctan2(n_vec[1], n_vec[0])) if n_norm > _TOL else 0.0

    if n_norm > _TOL and e > _TOL:
        argp = _angle_0_2pi(np.arctan2(np.dot(np.cross(n_vec, e_vec), h_vec) / h_norm, np.dot(n_vec, e_vec)))
    else:
        argp = 0.0

    if e > _TOL:
        nu = _angle_0_2pi(np.arctan2(np.dot(np.cross(e_vec, r_vec), h_vec) / h_norm, np.dot(e_vec, r_vec)))
    elif n_norm > _TOL:
        nu = _angle_0_2pi(np.arctan2(np.dot(np.cross(n_vec, r_vec), h_vec) / h_norm, np.dot(n_vec, r_vec)))
    else:
        nu = _angle_0_2pi(np.arctan2(r_vec[1], r_vec[0]))

    return KeplerianElements(a, e, inc, raan, argp, nu)


def _rotation_x(angle: float) -> np.ndarray:
    c = np.cos(angle)
    s = np.sin(angle)
    return np.array([[1.0, 0.0, 0.0], [0.0, c, -s], [0.0, s, c]])


def _rotation_z(angle: float) -> np.ndarray:
    c = np.cos(angle)
    s = np.sin(angle)
    return np.array([[c, -s, 0.0], [s, c, 0.0], [0.0, 0.0, 1.0]])


def _angle_0_2pi(angle: float) -> float:
    return float(angle % (2 * np.pi))


def _require_inertial_elements_frame(frame: str) -> None:
    key = frame.strip().lower().replace("_", "-")
    if key not in {"ntn-eci", "ntneci", "teme", "j2000", "gcrs", "eme2000"}:
        raise ValueError("Keplerian elements are supported only for NTN-ECI, TEME, and J2000")
