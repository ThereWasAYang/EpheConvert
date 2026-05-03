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
交给 Astropy 解析，并按 UTC 处理。

## 使用示例

```python
from epheconvert import KeplerianElements, convert_elements, convert_state, convert_time

state = convert_state(
    [7000e3, 0, 0],
    [0, 7500, 1000],
    from_frame="j2000",
    to_frame="ecef",
    time="2026-05-03T00:00:00",
)

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
    time="2026-05-03T00:00:00",
    epoch_time="2026-05-03T00:00:00",
)

gps = convert_time("2026-05-03T00:00:00", from_system="utc", to_system="gps")
```

## 开发与测试

本工程使用 conda 环境 `py312`。

```bash
conda run -n py312 env PYTHONPATH=src python -m pytest
```

## 文档约定

README 以及后续新增的项目文档尽量使用中文撰写；必要的专业术语、协议字段、
坐标系名称、API 名称和常见缩写可以保留英文。
