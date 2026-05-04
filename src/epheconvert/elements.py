"""Keplerian element conversions for inertial Earth-centred frames."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .coordinates import FrameName, StateVector, convert_state
from .time import TimeSystem

EARTH_MU_M3_S2 = 3.986004418e14
_TOL = 1e-12


@dataclass(frozen=True)
class KeplerianElements:
    """经典开普勒六根数。

    参数:
        a_m: 半长轴，单位为 m；当前实现面向椭圆轨道，应为正数。
        eccentricity: 偏心率；当前实现要求 ``0 <= eccentricity < 1``。
        inclination_rad: 轨道倾角，单位为 rad。
        raan_rad: 升交点赤经 RAAN，单位为 rad。
        argp_rad: 近地点幅角 argument of perigee，单位为 rad。
        true_anomaly_rad: 真近点角，单位为 rad。

    返回:
        不直接返回值；该类实例表示一组开普勒六根数。
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
    time_system: TimeSystem = "utc",
    epoch_time_system: TimeSystem | None = None,
    mu_m3_s2: float = EARTH_MU_M3_S2,
) -> KeplerianElements:
    """在 ``NTN-ECI``、``TEME``、``J2000`` 之间转换开普勒六根数。

    参数:
        elements: 输入参考系下的开普勒六根数。
        from_frame: 输入根数所在参考系，支持 ``"ntn-eci"``、``"teme"``、
            ``"j2000"`` 及少量别名。
        to_frame: 输出根数所在参考系，取值范围与 ``from_frame`` 相同。
        time: 根数对应的时刻；传递给状态矢量转换函数。默认按 UTC 解释；
            当 ``time_system="gps"`` 时，数值按 GPS 连续秒解释。
        epoch_time: ``NTN-ECI`` 的参考时刻。只要转换涉及 ``NTN-ECI``，
            该参数就是必填项。
        time_system: ``time`` 所属时间系统，支持 ``"utc"``、``"gps"``、
            ``"bdt"`` 及少量别名。
        epoch_time_system: ``epoch_time`` 所属时间系统；不传时默认使用
            ``time_system``。
        mu_m3_s2: 中心天体标准引力参数，单位为 m^3/s^2；默认使用地球
            ``GM``。

    返回:
        目标参考系下的 ``KeplerianElements``。
    """

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
        time_system=time_system,
        epoch_time_system=epoch_time_system,
    )
    return state_to_elements(converted.position_m, converted.velocity_mps, mu_m3_s2=mu_m3_s2)


def elements_to_state(elements: KeplerianElements, *, mu_m3_s2: float = EARTH_MU_M3_S2) -> StateVector:
    """把经典开普勒六根数转换为惯性系笛卡尔状态矢量。

    参数:
        elements: 输入开普勒六根数，角度单位为 rad。
        mu_m3_s2: 中心天体标准引力参数，单位为 m^3/s^2；默认使用地球
            ``GM``。

    返回:
        ``StateVector``，表示与输入根数等价的位置和速度。
    """

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
    """把惯性系笛卡尔状态矢量转换为经典开普勒六根数。

    参数:
        position_m: 三维位置坐标，单位为 m。
        velocity_mps: 三维速度矢量，单位为 m/s。
        mu_m3_s2: 中心天体标准引力参数，单位为 m^3/s^2；默认使用地球
            ``GM``。

    返回:
        ``KeplerianElements``，角度单位为 rad，半长轴单位为 m。
    """

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
    """生成绕 x 轴旋转的方向余弦矩阵。

    参数:
        angle: 旋转角，单位为 rad。

    返回:
        形状为 ``(3, 3)`` 的旋转矩阵。
    """

    c = np.cos(angle)
    s = np.sin(angle)
    return np.array([[1.0, 0.0, 0.0], [0.0, c, -s], [0.0, s, c]])


def _rotation_z(angle: float) -> np.ndarray:
    """生成绕 z 轴旋转的方向余弦矩阵。

    参数:
        angle: 旋转角，单位为 rad。

    返回:
        形状为 ``(3, 3)`` 的旋转矩阵。
    """

    c = np.cos(angle)
    s = np.sin(angle)
    return np.array([[c, -s, 0.0], [s, c, 0.0], [0.0, 0.0, 1.0]])


def _angle_0_2pi(angle: float) -> float:
    """把角度归一化到 ``[0, 2*pi)``。

    参数:
        angle: 输入角度，单位为 rad。

    返回:
        归一化后的角度，单位为 rad。
    """

    return float(angle % (2 * np.pi))


def _require_inertial_elements_frame(frame: str) -> None:
    """检查开普勒根数转换是否使用受支持的惯性参考系。

    参数:
        frame: 用户传入的参考系名称或别名。

    返回:
        None。若参考系不受支持，则抛出 ``ValueError``。
    """

    key = frame.strip().lower().replace("_", "-")
    if key not in {"ntn-eci", "ntneci", "teme", "j2000", "gcrs", "eme2000"}:
        raise ValueError("Keplerian elements are supported only for NTN-ECI, TEME, and J2000")
