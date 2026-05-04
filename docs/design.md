# EpheConvert 设计文档

本文档说明 EpheConvert 当前三个核心功能的设计思路、实现路径、关键假设和已知限制。工程代码位于 `src/epheconvert`，示例代码位于 `examples/readme_examples.py`。

## 总体设计

EpheConvert 的目标是提供一组轻量 Python API，用于完成 3GPP NR NTN 场景中常见的参考系、轨道根数和时间系统转换。当前实现按功能拆成三个模块：

- `coordinates.py`：负责 `ECEF`、`NTN-ECI`、`TEME`、`J2000` 之间的位置坐标和速度矢量转换。
- `elements.py`：负责 `NTN-ECI`、`TEME`、`J2000` 之间的开普勒六根数转换，以及六根数和状态矢量之间的互转。
- `time.py`：负责 `UTC`、`GPS time`、`BDT`（北斗时间）之间的互转，以及通用时间加减秒的工具函数。

工程的公共 API 从 `src/epheconvert/__init__.py` 导出。用户通常只需要从 `epheconvert` 直接导入 `convert_state`、`convert_elements`、`convert_time`、`add_time_seconds`、`add_utc_seconds` 等函数。

## 统一约定

### 单位

状态矢量采用 SI 单位：

- 位置坐标：m。
- 速度矢量：m/s。
- 标准引力参数 `mu_m3_s2`：m^3/s^2。
- 角度：rad。
- 时间连续秒：s。

开普勒六根数中的半长轴 `a_m` 使用 m，所有角度使用 rad。

### 时间精度

工程中的时间统一规整到毫秒精度。具体规则是：

- 时间字符串默认按 UTC 交给 Astropy 解析后，按 UTC Unix 秒四舍五入到 0.001 s。
- 数值形式的 UTC 输入按 UTC Unix 秒解释，并四舍五入到 0.001 s。
- 状态矢量和开普勒根数转换可以通过 `time_system="gps"` 让数值 `time` 和 `epoch_time` 按 GPS 连续秒解释，也可以通过 `time_system="bdt"` 按北斗连续秒解释；可以通过 `epoch_time_system` 单独指定 `epoch_time` 的时间系统。
- `GPS time` 和 `BDT` 的连续秒输入、输出都保留到 0.001 s。
- UTC 输出使用 ISO 字符串，并固定保留 3 位毫秒。

这一逻辑集中在 `time._to_astropy_time()` 和 `time._with_millisecond_precision()` 中实现，`coordinates._to_time()` 会复用同一套解析逻辑。

### 参考系名称

参考系名称会先经过规范化处理。用户可以传入小写主名称，也可以传入部分别名：

- `ecef`：别名包括 `itrs`、`wgs84`。
- `ntn-eci`：别名包括 `ntneci`。
- `teme`：直接对应 Astropy 的 `TEME`。
- `j2000`：别名包括 `gcrs`、`eme2000`。

当前代码中，`j2000` 作为工程内部的地心惯性参考系名称使用，计算链路上采用 Astropy `GCRS` 表示。它适合本工程当前“惯性参考系间状态量转换”的需求；如果后续需要严格区分 ICRS、GCRS、EME2000、J2000 mean equator/equinox 等天文定义，需要进一步拆分这些参考系名称。

## 状态矢量参考系转换

### 目标

状态矢量转换需要支持 `ECEF`、`NTN-ECI`、`TEME`、`J2000` 四种参考系之间任意两两转换。状态矢量由位置坐标和速度矢量组成，使用 `StateVector` 表示。

```python
StateVector(position_m, velocity_mps)
```

其中：

- `position_m` 是形状为 `(3,)` 的数组。
- `velocity_mps` 是形状为 `(3,)` 的数组。

`StateVector.__post_init__()` 会把输入转换为 `numpy.ndarray`，并检查形状是否为三维向量。

### 核心入口

状态矢量转换入口是：

```python
convert_state(
    position_m,
    velocity_mps,
    from_frame,
    to_frame,
    time,
    epoch_time=None,
    time_system="utc",
    epoch_time_system=None,
)
```

设计上，`convert_state()` 做四件事：

1. 把输入位置和速度封装成 `StateVector`。
2. 按 `time_system` 把 `time` 解析为毫秒精度的 Astropy `Time`。
3. 规范化 `from_frame` 和 `to_frame`。
4. 如果涉及 `NTN-ECI`，按 `epoch_time_system` 或 `time_system` 解析 `epoch_time`。
5. 先把源参考系转换到内部惯性表示，再从内部惯性表示转换到目标参考系。

`time_system` 支持 `utc`、`gps`、`bdt` 及少量别名。实际使用中如果输入大多来自接收机或星历消息中的 GPS time，可以直接传 GPS 连续秒：

```python
convert_state(..., time=gps_time, epoch_time=gps_epoch, time_system="gps", epoch_time_system="gps")
```

如果输入是 BDT，则传北斗连续秒：

```python
convert_state(..., time=bdt_time, epoch_time=bdt_epoch, time_system="bdt", epoch_time_system="bdt")
```

内部惯性表示使用 `GCRS`/`J2000` 作为中间层。这样不同参考系之间不需要各自实现一套直接转换，只要实现“到中间层”和“从中间层返回”两类函数即可。

### ECEF 和 TEME 的实现

`ECEF` 通过 Astropy 的 `ITRS` 表示，`TEME` 通过 Astropy 的 `TEME` 表示。

转换流程是：

1. 使用 `CartesianRepresentation` 表示位置。
2. 使用 `CartesianDifferential` 表示速度。
3. 将二者组合成 Astropy `SkyCoord`。
4. 调用 Astropy 的 `transform_to()` 完成 `ITRS`、`TEME`、`GCRS` 之间的转换。
5. 从转换后的 `SkyCoord` 中提取位置和速度，重新封装成 `StateVector`。

相关函数：

- `_state_to_coord()`：把 `StateVector` 转成带速度微分的 `SkyCoord`。
- `_coord_to_state()`：从 `SkyCoord` 取回 m 和 m/s 单位的状态量。
- `_astropy_frame()`：按工程内部名称构造 Astropy 的 `ITRS` 或 `TEME` 参考系实例。

### NTN-ECI 的设计

本工程中 `NTN-ECI` 的定义是：

1. 它是地心惯性参考系。
2. 在参考时刻 `epoch_time`，它的坐标轴与 `ECEF` 重合。
3. 参考时刻之后，它的坐标轴保持惯性固定，不随地球自转。

因此，`NTN-ECI` 可以看作“在 `epoch_time` 这一瞬间由 ECEF 姿态锚定出来的惯性系”。

实现方式是：

1. 在 `epoch_time`，取 ECEF 的三个单位基向量。
2. 将这三个单位基向量从 `ITRS(epoch_time)` 转换到 `GCRS(epoch_time)`。
3. 把转换后的三个向量按列组成旋转矩阵。
4. 使用 SVD 对矩阵做正交化，得到稳定的正交旋转矩阵。
5. 对于 `NTN-ECI -> GCRS/J2000`，左乘该旋转矩阵。
6. 对于 `GCRS/J2000 -> NTN-ECI`，左乘该旋转矩阵的转置。

对应函数是 `_ntn_to_gcrs_matrix(epoch_time)`。该函数使用 `lru_cache(maxsize=128)` 缓存结果，因为同一个 `epoch_time` 通常会反复用于多次转换。

需要注意的是，当前实现对 `NTN-ECI` 和 `GCRS/J2000` 之间的速度转换使用同一个姿态旋转矩阵，不额外加入随时间变化的旋转角速度项。这符合“NTN-ECI 是惯性系”的设计：一旦由 `epoch_time` 锚定，轴系不再随地球转动。

### 转换路径

对于任意转换，代码采用统一路径：

```text
源参考系 -> GCRS/J2000 内部表示 -> 目标参考系
```

例如：

- `ECEF -> TEME`：`ITRS -> GCRS -> TEME`
- `TEME -> ECEF`：`TEME -> GCRS -> ITRS`
- `NTN-ECI -> ECEF`：`NTN-ECI -> GCRS -> ITRS`
- `J2000 -> NTN-ECI`：`GCRS/J2000 -> NTN-ECI`

这种设计让新增参考系时只需要补充它与内部中间层之间的转换关系。

## 开普勒六根数转换

### 目标

开普勒六根数转换支持 `NTN-ECI`、`TEME`、`J2000` 三种惯性参考系之间任意两两转换。`ECEF` 是随地球自转的地固系，不适合作为经典开普勒根数定义所在的惯性参考系，因此没有提供 `ECEF` 下的开普勒根数转换。

六根数使用 `KeplerianElements` 表示：

- `a_m`：半长轴，单位 m。
- `eccentricity`：偏心率。
- `inclination_rad`：轨道倾角，单位 rad。
- `raan_rad`：升交点赤经，单位 rad。
- `argp_rad`：近地点幅角，单位 rad。
- `true_anomaly_rad`：真近点角，单位 rad。

当前实现面向椭圆轨道，要求：

- `a_m > 0`
- `0 <= eccentricity < 1`

### 转换思路

开普勒根数不是直接在两个参考系之间变换，而是通过笛卡尔状态矢量作为中间层：

```text
源参考系六根数 -> 源参考系状态矢量 -> 目标参考系状态矢量 -> 目标参考系六根数
```

入口函数是：

```python
convert_elements(
    elements,
    from_frame,
    to_frame,
    time,
    epoch_time=None,
    time_system="utc",
    epoch_time_system=None,
    mu_m3_s2=EARTH_MU_M3_S2,
)
```

具体流程：

1. `_require_inertial_elements_frame()` 检查源和目标参考系是否属于 `NTN-ECI`、`TEME`、`J2000`。
2. `elements_to_state()` 把源参考系下的六根数转换为源参考系下的状态矢量。
3. `convert_state()` 完成状态矢量参考系转换，并继承 `time_system` / `epoch_time_system` 对 GPS time 等输入的支持。
4. `state_to_elements()` 把目标参考系下的状态矢量恢复为目标参考系下的六根数。

这样做的好处是复用状态矢量转换模块，避免为每一对根数参考系单独推导角元素转换公式。

### 六根数到状态矢量

`elements_to_state()` 采用经典两体轨道公式。

先在轨道平面坐标系 `PQW` 中计算：

```text
p = a * (1 - e^2)
r = p / (1 + e * cos(nu))
r_pqw = [r * cos(nu), r * sin(nu), 0]
v_pqw = sqrt(mu / p) * [-sin(nu), e + cos(nu), 0]
```

然后通过三次旋转把 `PQW` 转到目标惯性系：

```text
R = Rz(raan) * Rx(inclination) * Rz(argp)
```

最后：

```text
r_inertial = R * r_pqw
v_inertial = R * v_pqw
```

相关辅助函数：

- `_rotation_x()`：生成绕 x 轴旋转矩阵。
- `_rotation_z()`：生成绕 z 轴旋转矩阵。

### 状态矢量到六根数

`state_to_elements()` 使用经典反解公式：

1. 计算位置模长 `|r|` 和速度模长 `|v|`。
2. 计算角动量向量 `h = r x v`。
3. 计算节点向量 `n = k x h`。
4. 计算偏心率向量：

```text
e_vec = (v x h) / mu - r / |r|
```

5. 由轨道机械能计算半长轴：

```text
energy = |v|^2 / 2 - mu / |r|
a = -mu / (2 * energy)
```

6. 由向量夹角关系计算倾角、RAAN、近地点幅角和真近点角。
7. 使用 `_angle_0_2pi()` 把角度归一化到 `[0, 2*pi)`。

代码中对接近圆轨道或赤道轨道的退化情形做了简化处理：

- 节点向量接近 0 时，RAAN 置为 0。
- 偏心率接近 0 时，近地点幅角置为 0。
- 圆轨道下使用相应的替代角定义计算真近点角。

这些处理可以保证常见近圆轨道不会直接因为角元素退化而失败，但退化轨道的部分角元素本身没有唯一物理意义，使用时应关注状态矢量是否保持一致。

## 时间系统转换

### 目标

时间转换支持三种系统：

- `UTC`
- `GPS time`
- `BDT`（北斗时间）

入口函数是：

```python
convert_time(value, from_system, to_system)
```

如果只需要对 UTC 时间加减一段秒数，可以使用工具函数：

```python
add_utc_seconds(utc_time, seconds)
```

如果需要对 GPS time 或 BDT 加减秒数，可以使用通用工具函数：

```python
add_time_seconds(value, seconds, system="gps")
```

如果需要把 GPS/BDT 连续时间显示成对应时间系统自己的 ISO 字符串，可以使用：

```python
gps_seconds_to_iso(gps_seconds)
gps_milliseconds_to_iso(gps_milliseconds)
bdt_seconds_to_iso(bdt_seconds)
bdt_milliseconds_to_iso(bdt_milliseconds)
```

返回值是 `TimeConversion`：

- `system`：输出时间系统。
- `value`：输出值。UTC 为 ISO 字符串，GPS/BDT 为连续秒。
- `astropy_time`：同一物理时刻对应的 Astropy `Time` 对象。

`add_utc_seconds()` 的返回值是毫秒精度 UTC ISO 字符串。
`add_time_seconds()` 返回 `TimeConversion`，输出系统与输入 `system` 保持一致。
四个连续时间转 ISO 函数返回对应时间系统下的毫秒精度 ISO 字符串，不转换为 UTC。

### 设计思路

时间转换统一使用 Astropy `Time` 作为中间表示：

```text
输入时间系统 -> Astropy Time -> 输出时间系统
```

这样可以复用 Astropy 对 UTC、GPS、闰秒等时间尺度的处理。

时间加减秒也复用同一套时间处理逻辑：

1. 将输入时间通过 `_to_astropy_time(value, system)` 转为毫秒精度 Astropy `Time`。
2. 将 `seconds` 四舍五入到 0.001 s。
3. 使用 Astropy `TimeDelta(..., format="sec")` 做时间平移。
4. 通过 `_from_astropy_time(..., system)` 输出同一时间系统下的毫秒精度结果。

这样可以让 UTC、GPS time、BDT 的加减秒与系统时间转换共享同一套毫秒精度和闰秒处理规则。

GPS/BDT 连续秒或连续毫秒转 ISO 字符串不经过 Astropy 的 UTC 表示，而是按各自
系统历元直接展开：

```text
GPS ISO = 1980-01-06T00:00:00.000 + GPS 连续时间
BDT ISO = 2006-01-01T00:00:00.000 + BDT 连续时间
```

这种设计用于显示“GPS 时间系统下的日历时间”或“BDT 时间系统下的日历时间”。
它与 `convert_time(..., to_system="utc")` 不同，后者会输出同一物理时刻对应的
UTC 字符串，并包含 UTC/GPS 闰秒关系。

### UTC

UTC 输入可以是：

- ISO 时间字符串，例如 `2026-05-03T00:00:00.123`。
- UTC Unix 秒数值。
- Astropy `Time` 对象。

输出 UTC 时使用 `time.utc.isot`，并通过 `precision = 3` 固定为毫秒格式。

### GPS time

GPS time 使用 Astropy 的 `format="gps"`。它表示从 GPS 历元开始的连续秒。GPS 历元定义为：

```text
1980-01-06T00:00:00.000
```

输入 GPS time 时，数值按 GPS 连续秒解释。输出 GPS time 时返回 GPS 连续秒，并保留到 0.001 s。若需要显示为 GPS 时间系统自己的 ISO 字符串，可使用 `gps_seconds_to_iso()` 或 `gps_milliseconds_to_iso()`。

### BDT

北斗时间历元定义为：

```text
2006-01-01T00:00:00.000
```

工程中将 BDT 表示为从该历元开始的连续秒。实现上先计算 BDT 历元对应的 GPS 连续秒：

```python
Time(BDT_EPOCH_UTC, scale="utc").gps
```

然后：

- `BDT -> Astropy Time`：把 BDT 秒数加到 BDT 历元对应的 GPS 秒上，再构造 Astropy GPS 时间。
- `Astropy Time -> BDT`：用当前时刻的 GPS 秒减去 BDT 历元对应的 GPS 秒。

这种实现利用 Astropy 处理 UTC 与 GPS 之间的闰秒关系，避免手写闰秒表。

若需要显示为 BDT 时间系统自己的 ISO 字符串，可使用 `bdt_seconds_to_iso()` 或
`bdt_milliseconds_to_iso()`。这类显示转换按 BDT 历元直接展开，不转换为 UTC。

## 依赖选择

### Astropy

Astropy 负责：

- `ITRS`、`TEME`、`GCRS` 参考系转换。
- 带速度微分的坐标转换。
- UTC、GPS 等时间尺度处理。
- IERS 数据支持。

代码中设置了：

```python
iers.conf.auto_download = False
```

这会阻止运行时自动联网下载 IERS 数据，优先使用随安装包提供的数据。这样在网络受限环境中也能运行。测试中可能仍会看到 Astropy 缓存目录权限警告，但不影响当前功能。

### NumPy

NumPy 负责：

- 三维向量和矩阵计算。
- 叉乘、点乘、范数。
- 三角函数。
- SVD 正交化。

## 测试设计

测试文件是 `tests/test_epheconvert.py`，主要覆盖：

- 状态矢量在多组参考系之间往返转换后应接近原值。
- `NTN-ECI` 在 `epoch_time` 与 `ECEF` 的位置方向一致。
- 开普勒六根数与状态矢量互转后，状态矢量应保持一致。
- 开普勒根数跨惯性参考系转换后，与直接转换状态矢量的结果一致。
- UTC、GPS time、BDT 能够往返转换。
- UTC 时间可以加减正数、负数和小数秒。
- 时间输入超过毫秒时，会四舍五入到毫秒。

示例脚本 `examples/readme_examples.py` 不是严格单元测试，但可以作为人工验证入口。它把 README 中的示例整理成独立函数，方便逐项运行。

## 已知限制与后续方向

当前实现优先满足工程初始功能闭环，仍有一些边界需要注意：

- `j2000` 当前作为 GCRS/EME2000 类地心惯性表示使用，尚未严格拆分不同天文惯性系定义。
- 开普勒六根数当前面向椭圆轨道，不支持抛物线、双曲线轨道。
- 对圆轨道、赤道轨道等退化情形，部分角元素没有唯一物理意义，代码采用常见简化约定。
- `NTN-ECI` 的实现依赖 `epoch_time` 处 ECEF 相对 GCRS 的姿态。若后续需要完全贴合某个 3GPP ASN.1 字段或协议版本中的时间字段编码，需要增加协议层解析。
- 当前没有引入地球非球形引力、摄动传播或轨道动力学积分；本工程只做同一时刻的参考系和表示形式转换。

后续可考虑扩展：

- 更严格的 `J2000`、`GCRS`、`ICRS`、`EME2000` 区分。
- 支持更多轨道根数形式，例如平均近点角、偏近点角、赤道根数、非奇异根数。
- 增加批量数组输入，提高大量星历点转换效率。
- 增加命令行工具，方便从 CSV 或 JSON 文件批量转换。
