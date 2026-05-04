"""README 使用示例集合。

运行方式:
    conda run -n py312 env PYTHONPATH=src python examples/readme_examples.py

也可以在交互环境中单独导入并调用某个函数，逐项验证。
"""

from __future__ import annotations

from epheconvert import (
    KeplerianElements,
    add_time_seconds,
    add_utc_seconds,
    convert_elements,
    convert_state,
    convert_time,
    elements_to_state,
    state_to_elements,
)


TIME = "2026-05-03T00:00:00.123"
NTN_EPOCH = "2026-05-03T00:00:00.000"
GPS_TIME = convert_time(TIME, from_system="utc", to_system="gps").value
GPS_NTN_EPOCH = convert_time(NTN_EPOCH, from_system="utc", to_system="gps").value
BDT_TIME = convert_time(TIME, from_system="utc", to_system="bdt").value
BDT_NTN_EPOCH = convert_time(NTN_EPOCH, from_system="utc", to_system="bdt").value


def print_state(name, state):
    """打印状态矢量转换结果。

    参数:
        name: 示例名称。
        state: ``convert_state`` 返回的 ``StateVector``。

    返回:
        None。该函数只负责把结果打印到标准输出。
    """

    print(f"\n{name}")
    print("position_m =", state.position_m)
    print("velocity_mps =", state.velocity_mps)


def print_elements(name, elements):
    """打印开普勒六根数转换结果。

    参数:
        name: 示例名称。
        elements: ``convert_elements`` 或 ``state_to_elements`` 返回的
            ``KeplerianElements``。

    返回:
        None。该函数只负责把结果打印到标准输出。
    """

    print(f"\n{name}")
    print(elements)


def print_time(name, converted):
    """打印时间转换结果。

    参数:
        name: 示例名称。
        converted: ``convert_time`` 返回的 ``TimeConversion``。

    返回:
        None。该函数只负责把结果打印到标准输出。
    """

    print(f"\n{name}")
    print(f"{converted.system} =", converted.value)


def example_j2000_to_ecef_state():
    """示例：把 ``J2000`` 下的位置和速度转换到 ``ECEF``。

    参数:
        无。

    返回:
        ``StateVector``，表示 ``ECEF`` 下的位置和速度。
    """

    return convert_state(
        [7000e3, 0, 0],
        [0, 7500, 1000],
        from_frame="j2000",
        to_frame="ecef",
        time=TIME,
        time_system="utc",
    )


def example_ecef_to_ntn_state():
    """示例：把 ``ECEF`` 下的位置和速度转换到 ``NTN-ECI``。

    参数:
        无。

    返回:
        ``StateVector``，表示 ``NTN-ECI`` 下的位置和速度。
    """

    return convert_state(
        [6378137.0, 0, 0],
        [0, 0, 0],
        from_frame="ecef",
        to_frame="ntn-eci",
        time="2026-05-03T00:10:00.123",
        epoch_time=NTN_EPOCH,
        time_system="utc",
        epoch_time_system="utc",
    )


def example_gps_time_state_conversion():
    """示例：使用 GPS time 输入进行状态矢量转换。

    参数:
        无。

    返回:
        ``StateVector``，表示 ``NTN-ECI`` 下的位置和速度。
    """

    return convert_state(
        [7000e3, 0, 0],
        [0, 7500, 1000],
        from_frame="j2000",
        to_frame="ntn-eci",
        time=GPS_TIME,
        epoch_time=GPS_NTN_EPOCH,
        time_system="gps",
        epoch_time_system="gps",
    )


def example_bdt_time_state_conversion():
    """示例：使用 BDT 输入进行状态矢量转换。

    参数:
        无。

    返回:
        ``StateVector``，表示 ``NTN-ECI`` 下的位置和速度。
    """

    return convert_state(
        [7000e3, 0, 0],
        [0, 7500, 1000],
        from_frame="j2000",
        to_frame="ntn-eci",
        time=BDT_TIME,
        epoch_time=BDT_NTN_EPOCH,
        time_system="bdt",
        epoch_time_system="bdt",
    )


def example_all_state_conversions():
    """示例：四种坐标参考系之间的全部有向状态矢量转换。

    参数:
        无。

    返回:
        ``dict``。键为 ``from_to`` 形式的转换名称，值为对应的
        ``StateVector``。
    """

    position_m = [7000e3, 0, 0]
    velocity_mps = [0, 7500, 1000]
    return {
        "ecef_to_ntn": convert_state(position_m, velocity_mps, from_frame="ecef", to_frame="ntn-eci", time=TIME, epoch_time=NTN_EPOCH, time_system="utc", epoch_time_system="utc"),
        "ecef_to_teme": convert_state(position_m, velocity_mps, from_frame="ecef", to_frame="teme", time=TIME, time_system="utc"),
        "ecef_to_j2000": convert_state(position_m, velocity_mps, from_frame="ecef", to_frame="j2000", time=TIME, time_system="utc"),
        "ntn_to_ecef": convert_state(position_m, velocity_mps, from_frame="ntn-eci", to_frame="ecef", time=TIME, epoch_time=NTN_EPOCH, time_system="utc", epoch_time_system="utc"),
        "ntn_to_teme": convert_state(position_m, velocity_mps, from_frame="ntn-eci", to_frame="teme", time=TIME, epoch_time=NTN_EPOCH, time_system="utc", epoch_time_system="utc"),
        "ntn_to_j2000": convert_state(position_m, velocity_mps, from_frame="ntn-eci", to_frame="j2000", time=TIME, epoch_time=NTN_EPOCH, time_system="utc", epoch_time_system="utc"),
        "teme_to_ecef": convert_state(position_m, velocity_mps, from_frame="teme", to_frame="ecef", time=TIME, time_system="utc"),
        "teme_to_ntn": convert_state(position_m, velocity_mps, from_frame="teme", to_frame="ntn-eci", time=TIME, epoch_time=NTN_EPOCH, time_system="utc", epoch_time_system="utc"),
        "teme_to_j2000": convert_state(position_m, velocity_mps, from_frame="teme", to_frame="j2000", time=TIME, time_system="utc"),
        "j2000_to_ecef": convert_state(position_m, velocity_mps, from_frame="j2000", to_frame="ecef", time=TIME, time_system="utc"),
        "j2000_to_ntn": convert_state(position_m, velocity_mps, from_frame="j2000", to_frame="ntn-eci", time=TIME, epoch_time=NTN_EPOCH, time_system="utc", epoch_time_system="utc"),
        "j2000_to_teme": convert_state(position_m, velocity_mps, from_frame="j2000", to_frame="teme", time=TIME, time_system="utc"),
    }


def example_ntn_to_teme_elements():
    """示例：把 ``NTN-ECI`` 下的开普勒六根数转换到 ``TEME``。

    参数:
        无。

    返回:
        ``KeplerianElements``，表示 ``TEME`` 下的开普勒六根数。
    """

    elements = KeplerianElements(
        a_m=7000e3,
        eccentricity=0.001,
        inclination_rad=0.9,
        raan_rad=0.4,
        argp_rad=0.2,
        true_anomaly_rad=1.0,
    )
    return convert_elements(
        elements,
        from_frame="ntn-eci",
        to_frame="teme",
        time=TIME,
        epoch_time=NTN_EPOCH,
        time_system="utc",
        epoch_time_system="utc",
    )


def example_gps_time_element_conversion():
    """示例：使用 GPS time 输入进行开普勒六根数转换。

    参数:
        无。

    返回:
        ``KeplerianElements``，表示 ``NTN-ECI`` 下的开普勒六根数。
    """

    elements = KeplerianElements(
        a_m=7000e3,
        eccentricity=0.001,
        inclination_rad=0.9,
        raan_rad=0.4,
        argp_rad=0.2,
        true_anomaly_rad=1.0,
    )
    return convert_elements(
        elements,
        from_frame="j2000",
        to_frame="ntn-eci",
        time=GPS_TIME,
        epoch_time=GPS_NTN_EPOCH,
        time_system="gps",
        epoch_time_system="gps",
    )


def example_bdt_time_element_conversion():
    """示例：使用 BDT 输入进行开普勒六根数转换。

    参数:
        无。

    返回:
        ``KeplerianElements``，表示 ``NTN-ECI`` 下的开普勒六根数。
    """

    elements = KeplerianElements(
        a_m=7000e3,
        eccentricity=0.001,
        inclination_rad=0.9,
        raan_rad=0.4,
        argp_rad=0.2,
        true_anomaly_rad=1.0,
    )
    return convert_elements(
        elements,
        from_frame="j2000",
        to_frame="ntn-eci",
        time=BDT_TIME,
        epoch_time=BDT_NTN_EPOCH,
        time_system="bdt",
        epoch_time_system="bdt",
    )


def example_all_element_conversions():
    """示例：三种惯性参考系之间的全部有向开普勒六根数转换。

    参数:
        无。

    返回:
        ``dict``。键为 ``from_to`` 形式的转换名称，值为对应的
        ``KeplerianElements``。
    """

    elements = KeplerianElements(
        a_m=7000e3,
        eccentricity=0.001,
        inclination_rad=0.9,
        raan_rad=0.4,
        argp_rad=0.2,
        true_anomaly_rad=1.0,
    )
    return {
        "ntn_to_teme": convert_elements(elements, from_frame="ntn-eci", to_frame="teme", time=TIME, epoch_time=NTN_EPOCH, time_system="utc", epoch_time_system="utc"),
        "ntn_to_j2000": convert_elements(elements, from_frame="ntn-eci", to_frame="j2000", time=TIME, epoch_time=NTN_EPOCH, time_system="utc", epoch_time_system="utc"),
        "teme_to_ntn": convert_elements(elements, from_frame="teme", to_frame="ntn-eci", time=TIME, epoch_time=NTN_EPOCH, time_system="utc", epoch_time_system="utc"),
        "teme_to_j2000": convert_elements(elements, from_frame="teme", to_frame="j2000", time=TIME, time_system="utc"),
        "j2000_to_ntn": convert_elements(elements, from_frame="j2000", to_frame="ntn-eci", time=TIME, epoch_time=NTN_EPOCH, time_system="utc", epoch_time_system="utc"),
        "j2000_to_teme": convert_elements(elements, from_frame="j2000", to_frame="teme", time=TIME, time_system="utc"),
    }


def example_elements_state_round_trip():
    """示例：开普勒六根数与惯性系笛卡尔状态矢量互转。

    参数:
        无。

    返回:
        ``tuple``。第 1 项为 ``StateVector``，第 2 项为恢复出的
        ``KeplerianElements``。
    """

    elements = KeplerianElements(
        a_m=7200e3,
        eccentricity=0.01,
        inclination_rad=0.7,
        raan_rad=1.2,
        argp_rad=0.4,
        true_anomaly_rad=2.0,
    )
    state = elements_to_state(elements)
    restored_elements = state_to_elements(state.position_m, state.velocity_mps)
    return state, restored_elements


def example_all_time_conversions():
    """示例：三种时间系统之间的全部有向转换。

    参数:
        无。

    返回:
        ``dict``。键为 ``from_to`` 形式的转换名称，值为对应的
        ``TimeConversion``。
    """

    utc_to_gps = convert_time(TIME, from_system="utc", to_system="gps")
    utc_to_bdt = convert_time(TIME, from_system="utc", to_system="bdt")
    return {
        "utc_to_gps": utc_to_gps,
        "utc_to_bdt": utc_to_bdt,
        "gps_to_utc": convert_time(utc_to_gps.value, from_system="gps", to_system="utc"),
        "gps_to_bdt": convert_time(utc_to_gps.value, from_system="gps", to_system="bdt"),
        "bdt_to_utc": convert_time(utc_to_bdt.value, from_system="bdt", to_system="utc"),
        "bdt_to_gps": convert_time(utc_to_bdt.value, from_system="bdt", to_system="gps"),
    }


def example_add_utc_seconds():
    """示例：对 UTC 时间加减指定秒数。

    参数:
        无。

    返回:
        ``dict``。键表示加减方向，值为计算后的毫秒精度 UTC ISO 字符串。
    """

    return {
        "plus_1_234_seconds": add_utc_seconds(TIME, 1.234),
        "minus_0_124_seconds": add_utc_seconds(TIME, -0.124),
        "gps_plus_1_234_seconds": add_time_seconds(GPS_TIME, 1.234, system="gps").value,
        "bdt_minus_0_124_seconds": add_time_seconds(BDT_TIME, -0.124, system="bdt").value,
    }


def main():
    """顺序运行 README 中的全部示例。

    参数:
        无。

    返回:
        None。结果会打印到标准输出。
    """

    print_state("J2000 -> ECEF 状态矢量", example_j2000_to_ecef_state())
    print_state("ECEF -> NTN-ECI 状态矢量", example_ecef_to_ntn_state())
    print_state("GPS time 输入的 J2000 -> NTN-ECI 状态矢量", example_gps_time_state_conversion())
    print_state("BDT 输入的 J2000 -> NTN-ECI 状态矢量", example_bdt_time_state_conversion())

    print("\n全部状态矢量转换")
    for name, state in example_all_state_conversions().items():
        print_state(name, state)

    print_elements("NTN-ECI -> TEME 开普勒六根数", example_ntn_to_teme_elements())
    print_elements("GPS time 输入的 J2000 -> NTN-ECI 开普勒六根数", example_gps_time_element_conversion())
    print_elements("BDT 输入的 J2000 -> NTN-ECI 开普勒六根数", example_bdt_time_element_conversion())

    print("\n全部开普勒六根数转换")
    for name, elements in example_all_element_conversions().items():
        print_elements(name, elements)

    state, restored_elements = example_elements_state_round_trip()
    print_state("开普勒六根数 -> 状态矢量", state)
    print_elements("状态矢量 -> 开普勒六根数", restored_elements)

    print("\n全部时间转换")
    for name, converted in example_all_time_conversions().items():
        print_time(name, converted)

    print("\nUTC 时间加减秒")
    for name, utc_time in example_add_utc_seconds().items():
        print(f"{name} = {utc_time}")


if __name__ == "__main__":
    main()
