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
    """笛卡尔状态矢量。

    参数:
        position_m: 三维位置坐标，单位为 m。
        velocity_mps: 三维速度矢量，单位为 m/s。

    返回:
        不直接返回值；该类实例表示一组位置和速度。
    """

    position_m: np.ndarray
    velocity_mps: np.ndarray

    def __post_init__(self) -> None:
        """校验并规范化状态矢量字段。

        参数:
            self: 当前 ``StateVector`` 实例。

        返回:
            None。校验通过后，字段会被转换为形状为 ``(3,)`` 的
            ``numpy.ndarray``。
        """

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
    """在支持的参考系之间转换笛卡尔状态矢量。

    参数:
        position_m: 输入位置三维坐标，单位为 m。
        velocity_mps: 输入速度三维矢量，单位为 m/s。
        from_frame: 输入参考系，支持 ``"ecef"``、``"ntn-eci"``、
            ``"teme"``、``"j2000"`` 及少量别名。
        to_frame: 输出参考系，取值范围与 ``from_frame`` 相同。
        time: 状态矢量对应的时刻。数值按 UTC Unix 秒解释；字符串按 UTC
            交给 Astropy 解析；内部会规整到毫秒精度。
        epoch_time: ``NTN-ECI`` 的参考时刻。只要输入或输出参考系包含
            ``"ntn-eci"``，该参数就是必填项；数值和毫秒精度约定与
            ``time`` 相同。

    返回:
        ``StateVector``，其中 ``position_m`` 和 ``velocity_mps`` 分别是
        目标参考系下的位置和速度。
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
    """把任意受支持参考系下的状态矢量转换到内部 GCRS/J2000 表示。

    参数:
        state: 输入状态矢量。
        frame: 输入参考系名称。
        obstime: 状态矢量对应的 Astropy 时间。
        epoch_time: ``NTN-ECI`` 的参考时刻；非 ``NTN-ECI`` 转换可为
            ``None``。

    返回:
        ``GCRS``/``J2000`` 表示下的 ``StateVector``。
    """

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
    """把内部 GCRS/J2000 状态矢量转换到目标参考系。

    参数:
        state: ``GCRS``/``J2000`` 表示下的输入状态矢量。
        frame: 目标参考系名称。
        obstime: 状态矢量对应的 Astropy 时间。
        epoch_time: ``NTN-ECI`` 的参考时刻；非 ``NTN-ECI`` 转换可为
            ``None``。

    返回:
        目标参考系下的 ``StateVector``。
    """

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
    """把 ``StateVector`` 封装为 Astropy ``SkyCoord``。

    参数:
        state: 输入状态矢量，单位为 m 和 m/s。
        frame: Astropy 坐标参考系实例，例如 ``ITRS``、``TEME`` 或
            ``GCRS``。

    返回:
        带位置和速度微分信息的 ``SkyCoord``。
    """

    rep = CartesianRepresentation(*(state.position_m * u.m))
    diff = CartesianDifferential(*(state.velocity_mps * (u.m / u.s)))
    return SkyCoord(rep.with_differentials(diff), frame=frame)


def _coord_to_state(coord: SkyCoord) -> StateVector:
    """从 Astropy ``SkyCoord`` 提取 ``StateVector``。

    参数:
        coord: 带笛卡尔位置和速度微分的 Astropy 坐标对象。

    返回:
        ``StateVector``，位置单位为 m，速度单位为 m/s。
    """

    cart = coord.cartesian
    diff = cart.differentials["s"]
    return StateVector(
        cart.xyz.to_value(u.m),
        diff.d_xyz.to_value(u.m / u.s),
    )


def _astropy_frame(frame: FrameName, obstime: Time) -> ITRS | TEME:
    """构造由 Astropy 直接支持的参考系对象。

    参数:
        frame: 工程内部参考系名称；这里只接受 ``"ecef"`` 或
            ``"teme"``。
        obstime: 参考系对应的观测时刻。

    返回:
        ``ITRS`` 或 ``TEME`` 参考系实例。
    """

    if frame == "ecef":
        return ITRS(obstime=obstime)
    if frame == "teme":
        return TEME(obstime=obstime)
    raise ValueError(f"{frame!r} is not an Astropy-backed frame")


@lru_cache(maxsize=128)
def _ntn_to_gcrs_matrix(epoch_time: Time) -> np.ndarray:
    """计算 ``NTN-ECI`` 到 GCRS/J2000 的旋转矩阵。

    参数:
        epoch_time: ``NTN-ECI`` 与 ``ECEF`` 重合的参考时刻。

    返回:
        形状为 ``(3, 3)`` 的正交旋转矩阵，用于把 ``NTN-ECI`` 分量转换到
        GCRS/J2000 分量。
    """

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
    """规范化参考系名称和常见别名。

    参数:
        frame: 用户传入的参考系名称或别名。

    返回:
        工程内部统一使用的参考系名称。
    """

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
    """把外部时间输入转换为 Astropy ``Time``。

    参数:
        value: Astropy ``Time``、UTC 时间字符串，或 UTC Unix 秒数值；输入
            会规整到毫秒精度。

    返回:
        毫秒精度的 Astropy ``Time`` 对象。
    """

    if isinstance(value, Time):
        return _with_millisecond_precision(value)
    if isinstance(value, (int, float)):
        return _with_millisecond_precision(Time(float(value), format="unix", scale="utc"))
    return _with_millisecond_precision(Time(value, scale="utc"))


def _to_epoch(epoch_time: Time | str | float | None, source: FrameName, target: FrameName) -> Time | None:
    """解析 ``NTN-ECI`` 转换所需的参考时刻。

    参数:
        epoch_time: 用户传入的 ``NTN-ECI`` 参考时刻。
        source: 输入参考系名称。
        target: 输出参考系名称。

    返回:
        当转换涉及 ``NTN-ECI`` 时返回 Astropy ``Time``；否则返回
        ``None``。
    """

    if source != "ntn-eci" and target != "ntn-eci":
        return None
    if epoch_time is None:
        raise ValueError("epoch_time is required for NTN-ECI conversions")
    return _to_time(epoch_time)


def _as_vector(value: np.ndarray, name: str) -> np.ndarray:
    """校验并转换三维向量。

    参数:
        value: 待校验的数组或可转换为数组的对象。
        name: 参数名称，用于错误信息。

    返回:
        形状为 ``(3,)`` 的 ``numpy.ndarray``。
    """

    vector = np.asarray(value, dtype=float)
    if vector.shape != (3,):
        raise ValueError(f"{name} must be a 3-vector")
    return vector


def _with_millisecond_precision(time: Time) -> Time:
    """把 Astropy ``Time`` 规整到毫秒精度。

    参数:
        time: 待规整的 Astropy ``Time`` 对象。

    返回:
        新的 Astropy ``Time`` 对象，其 UTC Unix 秒被四舍五入到 0.001 s，
        字符串显示精度固定为 3 位小数。
    """

    rounded = Time(round(float(time.utc.unix), 3), format="unix", scale="utc")
    rounded.precision = 3
    return rounded
