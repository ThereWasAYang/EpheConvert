"""Conversions among UTC, GPS time, and BeiDou time."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from astropy.time import Time, TimeDelta

TimeSystem = Literal["utc", "gps", "bdt"]
GPS_EPOCH_UTC = "1980-01-06T00:00:00.000"
BDT_EPOCH_UTC = "2006-01-01T00:00:00.000"


@dataclass(frozen=True)
class TimeConversion:
    """时间转换结果。

    参数:
        system: 输出时间系统，取值为 ``"utc"``、``"gps"`` 或 ``"bdt"``。
        value: 转换后的时间值。``UTC`` 返回毫秒精度的 ISO 字符串；
            ``GPS`` 和 ``BDT`` 返回相对于各自系统历元的连续秒，精确到
            0.001 s。
        astropy_time: 与输出值对应的 Astropy ``Time`` 对象，便于继续做
            高精度时间运算。

    返回:
        不直接返回值；该类实例表示一次时间转换的结果。
    """

    system: TimeSystem
    value: str | float
    astropy_time: Time


def convert_time(value: Time | str | float, *, from_system: TimeSystem, to_system: TimeSystem) -> TimeConversion:
    """在 ``UTC``、``GPS time`` 和 ``BDT``（北斗时间）之间转换。

    参数:
        value: 输入时间值。``UTC`` 可传 ISO 字符串、UTC Unix 秒或 Astropy
            ``Time``；``GPS`` 和 ``BDT`` 传相对于各自系统历元的连续秒。
            所有输入都会规整到毫秒精度。
        from_system: 输入时间系统，支持 ``"utc"``、``"gps"``、``"bdt"``
            及少量别名。
        to_system: 输出时间系统，取值范围与 ``from_system`` 相同。

    返回:
        ``TimeConversion``。其中 ``value`` 是目标时间系统下的值；
        ``astropy_time`` 是同一物理时刻的 Astropy 表示。
    """

    source = _normalize_system(from_system)
    target = _normalize_system(to_system)
    time = _to_astropy_time(value, source)
    return TimeConversion(target, _from_astropy_time(time, target), time)


def add_utc_seconds(utc_time: Time | str | float, seconds: float) -> str:
    """对 UTC 时间加减指定秒数，并返回计算后的 UTC 时间。

    参数:
        utc_time: 输入 UTC 时间。可传 ISO 字符串、UTC Unix 秒或 Astropy
            ``Time``；输入会先规整到毫秒精度。
        seconds: 要加减的秒数，单位为 s。正数表示向后加时间，负数表示
            向前减时间；可以是小数。

    返回:
        毫秒精度的 UTC ISO 字符串。
    """

    base_time = _to_astropy_time(utc_time, "utc")
    shifted = base_time + TimeDelta(_round_milliseconds(seconds), format="sec")
    return _from_astropy_time(shifted, "utc")  # type: ignore[return-value]


def _to_astropy_time(value: Time | str | float, system: TimeSystem) -> Time:
    """把指定时间系统下的输入值转换为 Astropy ``Time``。

    参数:
        value: 输入时间值；会规整到毫秒精度。
        system: 输入值所属时间系统。

    返回:
        毫秒精度的 Astropy ``Time`` 对象。
    """

    if isinstance(value, Time):
        return _with_millisecond_precision(value)
    if system == "utc":
        if isinstance(value, (int, float)):
            return _with_millisecond_precision(Time(float(value), format="unix", scale="utc"))
        return _with_millisecond_precision(Time(value, scale="utc"))
    if system == "gps":
        return _with_millisecond_precision(Time(_round_milliseconds(float(value)), format="gps"))
    if system == "bdt":
        return _with_millisecond_precision(Time(_bdt_epoch_gps_seconds() + _round_milliseconds(float(value)), format="gps"))
    raise ValueError(f"unsupported time system {system!r}")


def _from_astropy_time(time: Time, system: TimeSystem) -> str | float:
    """把 Astropy ``Time`` 转换为指定时间系统的外部值。

    参数:
        time: 待转换的 Astropy ``Time`` 对象。
        system: 目标时间系统。

    返回:
        ``UTC`` 返回毫秒精度 ISO 字符串；``GPS`` 和 ``BDT`` 返回精确到
        0.001 s 的系统连续秒。
    """

    if system == "utc":
        converted = _with_millisecond_precision(time)
        return converted.utc.isot
    if system == "gps":
        return _round_milliseconds(float(time.gps))
    if system == "bdt":
        return _round_milliseconds(float(time.gps - _bdt_epoch_gps_seconds()))
    raise ValueError(f"unsupported time system {system!r}")


def _bdt_epoch_gps_seconds() -> float:
    """计算北斗时间历元在 GPS 连续秒中的位置。

    参数:
        无。

    返回:
        ``BDT_EPOCH_UTC`` 对应的 GPS 连续秒。
    """

    return float(Time(BDT_EPOCH_UTC, scale="utc").gps)


def _with_millisecond_precision(time: Time) -> Time:
    """把 Astropy ``Time`` 规整到毫秒精度。

    参数:
        time: 待规整的 Astropy ``Time`` 对象。

    返回:
        新的 Astropy ``Time`` 对象，其 UTC Unix 秒被四舍五入到 0.001 s，
        字符串显示精度固定为 3 位小数。
    """

    rounded = Time(_round_milliseconds(float(time.utc.unix)), format="unix", scale="utc")
    rounded.precision = 3
    return rounded


def _round_milliseconds(value: float) -> float:
    """把秒数四舍五入到毫秒。

    参数:
        value: 单位为秒的浮点数。

    返回:
        保留 3 位小数的秒数。
    """

    return round(float(value), 3)


def _normalize_system(system: str) -> TimeSystem:
    """规范化时间系统名称和常见别名。

    参数:
        system: 用户传入的时间系统名称或别名。

    返回:
        工程内部统一使用的时间系统名称。
    """

    key = system.strip().lower()
    aliases = {"utc": "utc", "gps": "gps", "gpst": "gps", "bdt": "bdt", "beidou": "bdt", "北斗": "bdt"}
    if key not in aliases:
        raise ValueError(f"unsupported time system {system!r}")
    return aliases[key]  # type: ignore[return-value]
