import numpy as np
import pytest

from epheconvert import KeplerianElements, add_utc_seconds, convert_elements, convert_state, convert_time
from epheconvert.elements import elements_to_state, state_to_elements


TIME = "2026-05-03T00:00:00.123"
NTN_EPOCH = "2026-05-03T00:00:00.000"


@pytest.mark.parametrize(
    ("source", "target"),
    [
        ("ecef", "ntn-eci"),
        ("ecef", "teme"),
        ("ecef", "j2000"),
        ("ntn-eci", "teme"),
        ("teme", "j2000"),
        ("j2000", "ntn-eci"),
    ],
)
def test_state_round_trip(source, target):
    position = np.array([7000000.0, -1200000.0, 1300000.0])
    velocity = np.array([950.0, 7200.0, -1100.0])

    converted = convert_state(
        position,
        velocity,
        from_frame=source,
        to_frame=target,
        time=TIME,
        epoch_time=NTN_EPOCH,
    )
    restored = convert_state(
        converted.position_m,
        converted.velocity_mps,
        from_frame=target,
        to_frame=source,
        time=TIME,
        epoch_time=NTN_EPOCH,
    )

    assert np.allclose(restored.position_m, position, atol=1e-3)
    assert np.allclose(restored.velocity_mps, velocity, atol=1e-6)


def test_ntn_eci_matches_ecef_at_epoch_for_position_orientation():
    position = np.array([6378137.0, 10.0, -20.0])
    velocity = np.zeros(3)

    converted = convert_state(
        position,
        velocity,
        from_frame="ecef",
        to_frame="ntn-eci",
        time=NTN_EPOCH,
        epoch_time=NTN_EPOCH,
    )

    assert np.allclose(converted.position_m, position, atol=1e-3)


def test_elements_round_trip_state():
    elements = KeplerianElements(
        a_m=7200000.0,
        eccentricity=0.01,
        inclination_rad=0.7,
        raan_rad=1.2,
        argp_rad=0.4,
        true_anomaly_rad=2.0,
    )

    state = elements_to_state(elements)
    restored = state_to_elements(state.position_m, state.velocity_mps)
    restored_state = elements_to_state(restored)

    assert np.allclose(restored_state.position_m, state.position_m, atol=1e-6)
    assert np.allclose(restored_state.velocity_mps, state.velocity_mps, atol=1e-9)


def test_convert_elements_between_inertial_frames_preserves_cartesian_state():
    elements = KeplerianElements(
        a_m=7200000.0,
        eccentricity=0.02,
        inclination_rad=0.8,
        raan_rad=0.6,
        argp_rad=0.3,
        true_anomaly_rad=1.7,
    )

    converted = convert_elements(
        elements,
        from_frame="ntn-eci",
        to_frame="j2000",
        time=TIME,
        epoch_time=NTN_EPOCH,
    )

    ntn_state = elements_to_state(elements)
    j2000_state = elements_to_state(converted)
    expected = convert_state(
        ntn_state.position_m,
        ntn_state.velocity_mps,
        from_frame="ntn-eci",
        to_frame="j2000",
        time=TIME,
        epoch_time=NTN_EPOCH,
    )
    assert np.allclose(j2000_state.position_m, expected.position_m, atol=1e-5)
    assert np.allclose(j2000_state.velocity_mps, expected.velocity_mps, atol=1e-8)


def test_time_conversions():
    utc = "2006-01-01T00:00:00.123"
    gps = convert_time(utc, from_system="utc", to_system="gps")
    bdt = convert_time(gps.value, from_system="gps", to_system="bdt")
    restored_utc = convert_time(bdt.value, from_system="bdt", to_system="utc")

    assert bdt.value == pytest.approx(0.123)
    assert restored_utc.value == "2006-01-01T00:00:00.123"


def test_time_inputs_are_rounded_to_milliseconds():
    utc = convert_time("2006-01-01T00:00:00.1236", from_system="utc", to_system="utc")
    gps = convert_time(0.1236, from_system="bdt", to_system="bdt")

    assert utc.value == "2006-01-01T00:00:00.124"
    assert gps.value == pytest.approx(0.124)


def test_add_utc_seconds_supports_fractional_positive_and_negative_offsets():
    assert add_utc_seconds("2026-05-03T00:00:00.123", 1.234) == "2026-05-03T00:00:01.357"
    assert add_utc_seconds("2026-05-03T00:00:00.123", -0.124) == "2026-05-02T23:59:59.999"


def test_add_utc_seconds_rounds_inputs_and_offset_to_milliseconds():
    assert add_utc_seconds("2026-05-03T00:00:00.1236", 0.0006) == "2026-05-03T00:00:00.125"
