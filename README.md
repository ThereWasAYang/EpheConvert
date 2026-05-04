# EpheConvert

EpheConvert 是一个用于星历与时间系统转换的 Python 工程，当前提供以下能力：

- 在 `ECEF`、`NTN-ECI`、`TEME`、`J2000` 之间转换笛卡尔位置坐标和速度矢量。
- 在 `NTN-ECI`、`TEME`、`J2000` 之间转换开普勒六根数。
- 在 `UTC`、`GPS time`、`BDT`（北斗时间）之间转换时间。

## NTN-ECI 定义

在本工程中，`NTN-ECI` 被定义为一种地心惯性参考系。它的参考时刻由
`epoch_time` 指定；在该参考时刻，`NTN-ECI` 的坐标轴与 `ECEF` 重合。
参考时刻之后，`NTN-ECI` 坐标轴保持惯性固定，不随地球自转。

默认情况下，数值形式的 `time` 和 `epoch_time` 按 UTC Unix 秒解释，字符串
形式的时间会交给 Astropy 解析，并按 UTC 处理。实际工程中如果拿到的是
`GPS time`，可以给涉及时间的函数传入 `time_system="gps"`；此时数值时间按
GPS 连续秒解释。如果输入是 `BDT`（北斗时间），可以传入 `time_system="bdt"`；
此时数值时间按北斗连续秒解释。工程中的时间统一使用毫秒精度；输入若包含更细
的小数秒，会四舍五入到 0.001 s，UTC 字符串输出固定保留 3 位毫秒。

本工程依赖 Astropy 的 IERS 数据完成高精度地固/天球参考系转换。代码允许
Astropy 在网络可用时自动下载最新 IERS 数据；如果部署环境不能联网，应定期更新
`astropy-iers-data` 包，避免使用过旧的地球定向参数。

## 使用示例

README 中的示例已经整理到 [examples/readme_examples.py](examples/readme_examples.py)。
可以一次运行全部示例，也可以导入该文件中的单个函数逐项验证。

```bash
conda run -n py312 env PYTHONPATH=src python examples/readme_examples.py
```

更详细的功能设计和实现说明见 [docs/design.md](docs/design.md)。

### 位置坐标和速度矢量转换

`ECEF`、`NTN-ECI`、`TEME`、`J2000` 四种参考系之间支持任意两两转换。
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
    time_system="utc",
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
    time_system="utc",
    epoch_time_system="utc",
)
```

如果实际输入是 GPS time，可以把 `time` 和 `epoch_time` 都传成 GPS 连续秒，
并设置 `time_system="gps"` 和 `epoch_time_system="gps"`：

```python
from epheconvert import convert_state, convert_time

gps_time = convert_time("2026-05-03T00:00:00.123", from_system="utc", to_system="gps").value
gps_epoch = convert_time("2026-05-03T00:00:00.000", from_system="utc", to_system="gps").value

state = convert_state(
    [7000e3, 0, 0],
    [0, 7500, 1000],
    from_frame="j2000",
    to_frame="ntn-eci",
    time=gps_time,
    epoch_time=gps_epoch,
    time_system="gps",
    epoch_time_system="gps",
)
```

如果实际输入是 BDT，可以把 `time` 和 `epoch_time` 都传成北斗连续秒，并设置
`time_system="bdt"` 和 `epoch_time_system="bdt"`：

```python
from epheconvert import convert_state, convert_time

bdt_time = convert_time("2026-05-03T00:00:00.123", from_system="utc", to_system="bdt").value
bdt_epoch = convert_time("2026-05-03T00:00:00.000", from_system="utc", to_system="bdt").value

state = convert_state(
    [7000e3, 0, 0],
    [0, 7500, 1000],
    from_frame="j2000",
    to_frame="ntn-eci",
    time=bdt_time,
    epoch_time=bdt_epoch,
    time_system="bdt",
    epoch_time_system="bdt",
)
```

四种参考系之间的其他有向转换只需要修改 `from_frame` 和 `to_frame`。例如：

```python
from epheconvert import convert_state

position_m = [7000e3, 0, 0]
velocity_mps = [0, 7500, 1000]
time = "2026-05-03T00:00:00.123"
epoch_time = "2026-05-03T00:00:00.000"

ecef_to_ntn = convert_state(position_m, velocity_mps, from_frame="ecef", to_frame="ntn-eci", time=time, epoch_time=epoch_time, time_system="utc", epoch_time_system="utc")
ecef_to_teme = convert_state(position_m, velocity_mps, from_frame="ecef", to_frame="teme", time=time, time_system="utc")
ecef_to_j2000 = convert_state(position_m, velocity_mps, from_frame="ecef", to_frame="j2000", time=time, time_system="utc")

ntn_to_ecef = convert_state(position_m, velocity_mps, from_frame="ntn-eci", to_frame="ecef", time=time, epoch_time=epoch_time, time_system="utc", epoch_time_system="utc")
ntn_to_teme = convert_state(position_m, velocity_mps, from_frame="ntn-eci", to_frame="teme", time=time, epoch_time=epoch_time, time_system="utc", epoch_time_system="utc")
ntn_to_j2000 = convert_state(position_m, velocity_mps, from_frame="ntn-eci", to_frame="j2000", time=time, epoch_time=epoch_time, time_system="utc", epoch_time_system="utc")

teme_to_ecef = convert_state(position_m, velocity_mps, from_frame="teme", to_frame="ecef", time=time, time_system="utc")
teme_to_ntn = convert_state(position_m, velocity_mps, from_frame="teme", to_frame="ntn-eci", time=time, epoch_time=epoch_time, time_system="utc", epoch_time_system="utc")
teme_to_j2000 = convert_state(position_m, velocity_mps, from_frame="teme", to_frame="j2000", time=time, time_system="utc")

j2000_to_ecef = convert_state(position_m, velocity_mps, from_frame="j2000", to_frame="ecef", time=time, time_system="utc")
j2000_to_ntn = convert_state(position_m, velocity_mps, from_frame="j2000", to_frame="ntn-eci", time=time, epoch_time=epoch_time, time_system="utc", epoch_time_system="utc")
j2000_to_teme = convert_state(position_m, velocity_mps, from_frame="j2000", to_frame="teme", time=time, time_system="utc")
```

### 开普勒六根数转换

`NTN-ECI`、`TEME`、`J2000` 三种惯性参考系之间支持任意两两转换。角度单位
均为 rad，半长轴单位为 m。返回值是目标参考系下的 `KeplerianElements`。
本工程统一使用的六根数顺序为：半长轴、偏心率、近地点幅角、升交点赤经、
轨道倾角、平近点角。

```python
from epheconvert import KeplerianElements, convert_elements

elements = KeplerianElements(
    a_m=7000e3,
    eccentricity=0.001,
    argp_rad=0.2,
    raan_rad=0.4,
    inclination_rad=0.9,
    mean_anomaly_rad=1.0,
)

teme_elements = convert_elements(
    elements,
    from_frame="ntn-eci",
    to_frame="teme",
    time="2026-05-03T00:00:00.123",
    epoch_time="2026-05-03T00:00:00.000",
    time_system="utc",
    epoch_time_system="utc",
)

print(teme_elements)
```

三种参考系之间的全部有向转换示例如下：

```python
from epheconvert import KeplerianElements, convert_elements

elements = KeplerianElements(
    a_m=7000e3,
    eccentricity=0.001,
    argp_rad=0.2,
    raan_rad=0.4,
    inclination_rad=0.9,
    mean_anomaly_rad=1.0,
)

time = "2026-05-03T00:00:00.123"
epoch_time = "2026-05-03T00:00:00.000"

ntn_to_teme = convert_elements(elements, from_frame="ntn-eci", to_frame="teme", time=time, epoch_time=epoch_time, time_system="utc", epoch_time_system="utc")
ntn_to_j2000 = convert_elements(elements, from_frame="ntn-eci", to_frame="j2000", time=time, epoch_time=epoch_time, time_system="utc", epoch_time_system="utc")

teme_to_ntn = convert_elements(elements, from_frame="teme", to_frame="ntn-eci", time=time, epoch_time=epoch_time, time_system="utc", epoch_time_system="utc")
teme_to_j2000 = convert_elements(elements, from_frame="teme", to_frame="j2000", time=time, time_system="utc")

j2000_to_ntn = convert_elements(elements, from_frame="j2000", to_frame="ntn-eci", time=time, epoch_time=epoch_time, time_system="utc", epoch_time_system="utc")
j2000_to_teme = convert_elements(elements, from_frame="j2000", to_frame="teme", time=time, time_system="utc")
```

开普勒六根数转换同样支持 GPS time 输入：

```python
from epheconvert import KeplerianElements, convert_elements, convert_time

elements = KeplerianElements(
    a_m=7000e3,
    eccentricity=0.001,
    argp_rad=0.2,
    raan_rad=0.4,
    inclination_rad=0.9,
    mean_anomaly_rad=1.0,
)

gps_time = convert_time("2026-05-03T00:00:00.123", from_system="utc", to_system="gps").value
gps_epoch = convert_time("2026-05-03T00:00:00.000", from_system="utc", to_system="gps").value

ntn_elements = convert_elements(
    elements,
    from_frame="j2000",
    to_frame="ntn-eci",
    time=gps_time,
    epoch_time=gps_epoch,
    time_system="gps",
    epoch_time_system="gps",
)
```

BDT 输入方式类似：

```python
from epheconvert import KeplerianElements, convert_elements, convert_time

elements = KeplerianElements(
    a_m=7000e3,
    eccentricity=0.001,
    argp_rad=0.2,
    raan_rad=0.4,
    inclination_rad=0.9,
    mean_anomaly_rad=1.0,
)

bdt_time = convert_time("2026-05-03T00:00:00.123", from_system="utc", to_system="bdt").value
bdt_epoch = convert_time("2026-05-03T00:00:00.000", from_system="utc", to_system="bdt").value

ntn_elements = convert_elements(
    elements,
    from_frame="j2000",
    to_frame="ntn-eci",
    time=bdt_time,
    epoch_time=bdt_epoch,
    time_system="bdt",
    epoch_time_system="bdt",
)
```

也可以在开普勒六根数和惯性系笛卡尔状态矢量之间互转：

```python
from epheconvert import KeplerianElements, elements_to_state, state_to_elements

elements = KeplerianElements(
    a_m=7200e3,
    eccentricity=0.01,
    argp_rad=0.4,
    raan_rad=1.2,
    inclination_rad=0.7,
    mean_anomaly_rad=2.0,
)

state = elements_to_state(elements)
restored_elements = state_to_elements(state.position_m, state.velocity_mps)
```

### UTC、GPS time 和北斗时间转换

`UTC`、`GPS time`、`BDT` 三种时间系统之间支持任意两两转换。`UTC` 输出为
毫秒精度 ISO 字符串；`GPS time` 和 `BDT` 输出为相对于各自系统历元的连续秒，
精确到 0.001 s。

```python
from epheconvert import add_time_seconds, add_utc_seconds, convert_time

utc_to_gps = convert_time("2026-05-03T00:00:00.123", from_system="utc", to_system="gps")
utc_to_bdt = convert_time("2026-05-03T00:00:00.123", from_system="utc", to_system="bdt")

gps_to_utc = convert_time(utc_to_gps.value, from_system="gps", to_system="utc")
gps_to_bdt = convert_time(utc_to_gps.value, from_system="gps", to_system="bdt")

bdt_to_utc = convert_time(utc_to_bdt.value, from_system="bdt", to_system="utc")
bdt_to_gps = convert_time(utc_to_bdt.value, from_system="bdt", to_system="gps")
```

如果需要把 GPS/BDT 的连续秒或连续毫秒显示为对应时间系统自己的 ISO 字符串，
可以使用下面四个函数。注意这些结果是 GPS/BDT 时间系统下的 ISO 字符串，不是
UTC ISO 字符串。

```python
from epheconvert import (
    bdt_milliseconds_to_iso,
    bdt_seconds_to_iso,
    gps_milliseconds_to_iso,
    gps_seconds_to_iso,
)

gps_iso_from_seconds = gps_seconds_to_iso(1461801618.123)
gps_iso_from_milliseconds = gps_milliseconds_to_iso(1461801618123)

bdt_iso_from_seconds = bdt_seconds_to_iso(641692804.123)
bdt_iso_from_milliseconds = bdt_milliseconds_to_iso(641692804123)

print(gps_iso_from_seconds)
print(gps_iso_from_milliseconds)
print(bdt_iso_from_seconds)
print(bdt_iso_from_milliseconds)
```

如果只需要对一个 UTC 时间加减指定秒数，可以使用 `add_utc_seconds()`。秒数
可以是正数、负数或小数，返回值仍是毫秒精度 UTC ISO 字符串。

```python
from epheconvert import add_utc_seconds

later = add_utc_seconds("2026-05-03T00:00:00.123", 1.234)
earlier = add_utc_seconds("2026-05-03T00:00:00.123", -0.124)

print(later)
print(earlier)
```

如果输入是 GPS time，可以使用通用的 `add_time_seconds()`，返回同一时间系统
下的结果：

```python
from epheconvert import add_time_seconds, convert_time

gps_time = convert_time("2026-05-03T00:00:00.123", from_system="utc", to_system="gps").value
gps_later = add_time_seconds(gps_time, 1.234, system="gps")

print(gps_later.value)
```

BDT 也使用同一个通用函数：

```python
from epheconvert import add_time_seconds, convert_time

bdt_time = convert_time("2026-05-03T00:00:00.123", from_system="utc", to_system="bdt").value
bdt_earlier = add_time_seconds(bdt_time, -0.124, system="bdt")

print(bdt_earlier.value)
```

## 开发与测试

本工程使用 conda 环境 `py312`。

```bash
conda run -n py312 env PYTHONPATH=src python -m pytest
```

## 文档约定

README 以及后续新增的项目文档尽量使用中文撰写；必要的专业术语、协议字段、
坐标系名称、API 名称和常见缩写可以保留英文。
