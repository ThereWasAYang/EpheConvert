# EpheConvert

EpheConvert provides Python helpers for:

- Cartesian position and velocity conversion among ECEF, NTN-ECI, TEME, and J2000.
- Keplerian six-element conversion among NTN-ECI, TEME, and J2000.
- UTC, GPS time, and BeiDou time conversion.

## NTN-ECI Definition

In this project, `NTN-ECI` is an Earth-centred inertial frame. At its reference
instant `epoch_time`, its axes coincide with ECEF. After that instant, the
`NTN-ECI` axes remain inertially fixed instead of rotating with Earth.

Numeric `time` and `epoch_time` inputs are UTC Unix seconds. String time inputs
are parsed by Astropy as UTC.

## Example

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

## Development

Use the conda environment named `py312`.

```bash
conda run -n py312 env PYTHONPATH=src python -m pytest
```
