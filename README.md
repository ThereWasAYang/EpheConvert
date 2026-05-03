# EpheConvert

EpheConvert 是一个用于星历与时间系统转换的 Python 工程，当前提供以下能力：

- 在 `ECEF`、`NTN-ECI`、`TEME`、`J2000` 之间转换笛卡尔位置坐标和速度矢量。
- 在 `NTN-ECI`、`TEME`、`J2000` 之间转换开普勒六根数。
- 在 `UTC`、`GPS time`、`BDT`（北斗时间）之间转换时间。

## NTN-ECI 定义

在本工程中，`NTN-ECI` 被定义为一种地心惯性参考系。它的参考时刻由
`epoch_time` 指定；在该参考时刻，`NTN-ECI` 的坐标轴与 `ECEF` 重合。
参考时刻之后，`NTN-ECI` 坐标轴保持惯性固定，不随地球自转。

数值形式的 `time` 和 `epoch_time` 按 UTC Unix 秒解释。字符串形式的时间会
交给 Astropy 解析，并按 UTC 处理。工程中的时间统一使用毫秒精度；输入若包含
更细的小数秒，会四舍五入到 0.001 s，UTC 字符串输出固定保留 3 位毫秒。

## 使用示例

### 位置坐标和速度矢量转换

下面示例把 `J2000` 下的位置、速度转换到 `ECEF`。返回值是
`StateVector`，其中 `position_m` 是目标参考系下的位置坐标，单位为 m；
`velocity_mps` 是目标参考系下的速度矢量，单位为 m/s。

```python
from epheconvert import convert_state

state = convert_state(
    [7000e3, 0, 0],
    [0, 7500, 1000],
    from_frame="j2000",
    to_frame="ecef",
    time="2026-05-03T00:00:00.123",
)

print(state.position_m)
print(state.velocity_mps)
```

如果转换涉及 `NTN-ECI`，需要同时给出 `epoch_time`：

```python
from epheconvert import convert_state

state = convert_state(
    [6378137.0, 0, 0],
    [0, 0, 0],
    from_frame="ecef",
    to_frame="ntn-eci",
    time="2026-05-03T00:10:00.123",
    epoch_time="2026-05-03T00:00:00.000",
)
```

### 开普勒六根数转换

下面示例把 `NTN-ECI` 下的开普勒六根数转换到 `TEME`。角度单位均为 rad，
半长轴单位为 m。返回值是目标参考系下的 `KeplerianElements`。

```python
from epheconvert import KeplerianElements, convert_elements

elements = KeplerianElements(
    a_m=7000e3,
    eccentricity=0.001,
    inclination_rad=0.9,
    raan_rad=0.4,
    argp_rad=0.2,
    true_anomaly_rad=1.0,
)

teme_elements = convert_elements(
    elements,
    from_frame="ntn-eci",
    to_frame="teme",
    time="2026-05-03T00:00:00.123",
    epoch_time="2026-05-03T00:00:00.000",
)

print(teme_elements)
```

也可以在开普勒六根数和惯性系笛卡尔状态矢量之间互转：

```python
from epheconvert import KeplerianElements, elements_to_state, state_to_elements

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
```

### UTC、GPS time 和北斗时间转换

下面示例把 UTC 转换为 GPS time，再转换为 BDT。`UTC` 输出为毫秒精度 ISO
字符串；`GPS time` 和 `BDT` 输出为相对于各自系统历元的连续秒，精确到
0.001 s。

```python
from epheconvert import convert_time

gps = convert_time("2026-05-03T00:00:00.123", from_system="utc", to_system="gps")
bdt = convert_time(gps.value, from_system="gps", to_system="bdt")
utc = convert_time(bdt.value, from_system="bdt", to_system="utc")

print(gps.value)
print(bdt.value)
print(utc.value)
```

## 开发与测试

本工程使用 conda 环境 `py312`。

```bash
conda run -n py312 env PYTHONPATH=src python -m pytest
```

## 文档约定

README 以及后续新增的项目文档尽量使用中文撰写；必要的专业术语、协议字段、
坐标系名称、API 名称和常见缩写可以保留英文。
