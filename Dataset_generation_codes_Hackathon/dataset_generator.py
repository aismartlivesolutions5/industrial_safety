# dataset_generator_bulk_drug.py
# Efficient synthetic time-series dataset generator for Bulk Drug Factory Safety
# Creates realistic correlated sensor patterns (not pure random).
# Output: CSV with timestamp + asset_id + sensor columns.
#
# Run:
#   python dataset_generator_bulk_drug.py
#
# Output default:
#   /teamspace/studios/this_studio/Dataset_generation_codes/Hackathon/data/bulk_drug_factory_safety_90d_1min.csv

import os
import math
from datetime import datetime, timedelta

import numpy as np
import pandas as pd


# =========================
# CONFIG
# =========================
OUT_DIR = "/teamspace/studios/this_studio/Dataset_generation_codes/Hackathon/data"
OUT_FILE = os.path.join(OUT_DIR, "bulk_drug_factory_safety_90d_1min.csv")

DAYS = 90
FREQ_SECONDS = 60  # 1 minute
ASSETS = ["BOILER_A1", "BOILER_A2", "BOILER_B1", "BOILER_B2", "REACTOR_C1", "REACTOR_C2"]

START_TIME = datetime(2025, 11, 1, 0, 0, 0)  # choose any start date
SEED = 2025

# Chunk writing to keep memory low
CHUNK_MINUTES = 24 * 60  # write day-by-day chunks (1440 rows per asset per chunk)

# Columns (sensors + minimal context)
COLUMNS = [
    "timestamp",
    "asset_id",
    "boiler_pressure_bar",
    "boiler_temperature_c",
    "voc_ppm",
    "nh3_ppm",
    "h2s_ppm",
    "lel_percent",
    "vibration_rms",
    "active_alarm_count",
    "days_since_last_maintenance",
]


# =========================
# Helper functions
# =========================
def sigmoid(x: np.ndarray) -> np.ndarray:
    return 1.0 / (1.0 + np.exp(-x))


def clamp(x: np.ndarray, lo: float, hi: float) -> np.ndarray:
    return np.minimum(np.maximum(x, lo), hi)


def ar1_noise(rng: np.random.Generator, n: int, phi: float, sigma: float) -> np.ndarray:
    """AR(1) noise gives smooth, realistic sensor jitter (not white random)."""
    e = rng.normal(0, sigma, size=n).astype(np.float32)
    x = np.zeros(n, dtype=np.float32)
    for i in range(1, n):
        x[i] = phi * x[i - 1] + e[i]
    return x


def daily_load_profile(minutes_of_day: np.ndarray) -> np.ndarray:
    """
    Production/load pattern:
    - ramps up morning
    - high daytime
    - ramps down evening
    """
    t = minutes_of_day.astype(np.float32)

    # morning ramp: 6:00 -> 9:00
    ramp_up = sigmoid((t - 360) / 40)  # 360 min = 6 AM
    # evening ramp down: 18:00 -> 22:00
    ramp_down = sigmoid((t - 1080) / 50)  # 1080 min = 6 PM

    # daytime plateau ~ ramp_up - ramp_down
    load = clamp(ramp_up - ramp_down + 0.15, 0.05, 1.0)
    return load


def schedule_maintenance_days(rng: np.random.Generator, total_days: int) -> np.ndarray:
    """
    Maintenance every ~14 to 35 days, with some randomness.
    Returns days_since_last_maintenance for each day.
    """
    days_since = np.zeros(total_days, dtype=np.int32)
    next_due = int(rng.integers(12, 20))
    last_reset = 0
    for d in range(total_days):
        days_since[d] = d - last_reset
        if (d - last_reset) >= next_due:
            # maintenance happens (reset)
            last_reset = d
            next_due = int(rng.integers(14, 36))
            days_since[d] = 0
    return days_since


def inject_leak_events(
    rng: np.random.Generator,
    n: int,
    base_intensity: float,
    expected_events: int,
    min_len: int,
    max_len: int,
) -> np.ndarray:
    """
    Creates a smooth leak intensity curve over time (0..1).
    - expected_events: roughly how many leak episodes in the chunk
    - each leak lasts min_len..max_len minutes
    """
    intensity = np.zeros(n, dtype=np.float32)
    if expected_events <= 0:
        return intensity

    # pick event start indices
    starts = rng.choice(np.arange(0, max(1, n - max_len)), size=expected_events, replace=False)
    for s in starts:
        L = int(rng.integers(min_len, max_len + 1))
        e = min(n, s + L)
        # smooth bell-shaped curve (rise -> peak -> fall)
        x = np.linspace(-2.5, 2.5, e - s).astype(np.float32)
        curve = np.exp(-(x ** 2)).astype(np.float32)
        curve = curve / (curve.max() + 1e-6)
        intensity[s:e] = np.maximum(intensity[s:e], base_intensity * curve)

    # small smoothing using cumulative-like effect (still efficient)
    intensity = 0.6 * intensity + 0.4 * np.concatenate([[0.0], intensity[:-1]])
    return clamp(intensity, 0.0, 1.0)


def alarms_from_conditions(
    pressure: np.ndarray,
    temp: np.ndarray,
    voc: np.ndarray,
    nh3: np.ndarray,
    h2s: np.ndarray,
    lel: np.ndarray,
    vib: np.ndarray,
    days_since_maint: np.ndarray,
) -> np.ndarray:
    """
    Rule-like alarm counts (0..7) derived from combined abnormality.
    This is NOT a risk score; it's an operational 'active alarm count' signal.
    """
    score = np.zeros_like(pressure, dtype=np.float32)

    # pressure instability proxy
    score += (pressure > 11.5).astype(np.float32) * 1.3
    score += (pressure > 12.5).astype(np.float32) * 1.6

    # temperature high
    score += (temp > 175).astype(np.float32) * 1.2
    score += (temp > 190).astype(np.float32) * 1.8

    # gas
    score += (voc > 120).astype(np.float32) * 1.1
    score += (nh3 > 50).astype(np.float32) * 1.4
    score += (h2s > 20).astype(np.float32) * 1.6
    score += (lel > 10).astype(np.float32) * 1.8

    # vibration
    score += (vib > 4.5).astype(np.float32) * 1.4
    score += (vib > 6.5).astype(np.float32) * 1.8

    # overdue maintenance increases nuisance alarms
    score += (days_since_maint > 45).astype(np.float32) * 0.6
    score += (days_since_maint > 70).astype(np.float32) * 1.0

    # convert to alarm count with soft saturation
    alarms = np.floor(clamp(score, 0.0, 7.0)).astype(np.int32)
    return alarms


# =========================
# Core generator (chunked)
# =========================
def generate_chunk_for_asset(
    rng: np.random.Generator,
    asset_id: str,
    chunk_start: datetime,
    minutes: int,
    maint_days_series: np.ndarray,
    day_index_start: int,
) -> pd.DataFrame:
    """
    Generate one asset's time-series chunk:
    - uses daily load profile
    - couples pressure/temp
    - correlates gases + LEL during leak events
    - increases vibration drift with overdue maintenance
    """
    # timestamps
    ts = np.array([chunk_start + timedelta(minutes=i) for i in range(minutes)], dtype="datetime64[ns]")

    # minute-of-day for each point
    minutes_of_day = np.array([(chunk_start + timedelta(minutes=i)).hour * 60 +
                              (chunk_start + timedelta(minutes=i)).minute for i in range(minutes)],
                              dtype=np.int32)

    load = daily_load_profile(minutes_of_day)  # 0..1

    # base operating regimes per asset (slightly different)
    if "BOILER" in asset_id:
        base_pressure = rng.uniform(8.5, 10.5)     # bar
        base_temp = rng.uniform(150, 175)          # C
        pressure_gain = rng.uniform(1.8, 2.8)
        temp_gain = rng.uniform(18, 35)
    else:
        # reactors: different baseline
        base_pressure = rng.uniform(2.0, 5.5)
        base_temp = rng.uniform(80, 135)
        pressure_gain = rng.uniform(0.8, 1.6)
        temp_gain = rng.uniform(12, 28)

    # smooth correlated noise
    p_noise = ar1_noise(rng, minutes, phi=0.985, sigma=0.03)
    t_noise = ar1_noise(rng, minutes, phi=0.988, sigma=0.12)

    # pressure and temp coupling with load (not random)
    boiler_pressure = (base_pressure + pressure_gain * load + p_noise).astype(np.float32)
    boiler_temperature = (base_temp + temp_gain * load + 1.6 * p_noise + t_noise).astype(np.float32)

    # maintenance days at minute level (from per-day schedule)
    day_offsets = np.array([(chunk_start + timedelta(minutes=i)).date() for i in range(minutes)])
    # map dates to day indices
    # compute day index from START_TIME date
    start_date = START_TIME.date()
    day_idx = np.array([(d - start_date).days for d in day_offsets], dtype=np.int32)
    day_idx = clamp(day_idx, 0, len(maint_days_series)-1).astype(np.int32)
    days_since_maint = maint_days_series[day_idx].astype(np.int32)

    # vibration increases slightly with load, and drifts upward if maintenance overdue
    v_noise = ar1_noise(rng, minutes, phi=0.98, sigma=0.05)
    overdue_factor = clamp((days_since_maint.astype(np.float32) - 25.0) / 60.0, 0.0, 1.0)
    vibration_rms = (1.2 + 1.1 * load + 2.8 * overdue_factor + v_noise).astype(np.float32)
    vibration_rms = clamp(vibration_rms, 0.2, 12.0)

    # leak intensity events (rare, but realistic)
    # boilers tend to have fewer chemical leaks than reactors in many setups
    if "BOILER" in asset_id:
        expected_events = max(0, int(rng.poisson(0.6)))  # ~0-1 per day chunk
        base_intensity = float(rng.uniform(0.6, 0.95))
    else:
        expected_events = max(0, int(rng.poisson(1.2)))  # ~1-2 per day chunk
        base_intensity = float(rng.uniform(0.7, 1.0))

    leak = inject_leak_events(
        rng=rng,
        n=minutes,
        base_intensity=base_intensity,
        expected_events=expected_events,
        min_len=20,   # minutes
        max_len=180,  # minutes
    )

    # background gases rise a bit with load (process/solvent usage) + smooth noise
    voc_base = rng.uniform(8, 35)
    nh3_base = rng.uniform(0.5, 6.0)
    h2s_base = rng.uniform(0.2, 3.0)

    voc_noise = ar1_noise(rng, minutes, phi=0.985, sigma=0.8)
    nh3_noise = ar1_noise(rng, minutes, phi=0.985, sigma=0.25)
    h2s_noise = ar1_noise(rng, minutes, phi=0.985, sigma=0.18)

    # leak drives gas spikes (correlated) and LEL increases with VOC + leak severity
    voc_ppm = (voc_base + 45 * load + voc_noise + 280 * leak).astype(np.float32)
    nh3_ppm = (nh3_base + 6 * load + nh3_noise + 110 * leak).astype(np.float32)
    h2s_ppm = (h2s_base + 3 * load + h2s_noise + 60 * leak).astype(np.float32)

    voc_ppm = clamp(voc_ppm, 0, 1200)
    nh3_ppm = clamp(nh3_ppm, 0, 300)
    h2s_ppm = clamp(h2s_ppm, 0, 150)

    # LEL% depends mostly on VOC + leak; keep in 0..100
    lel_noise = ar1_noise(rng, minutes, phi=0.985, sigma=0.12)
    lel_percent = (0.1 + 0.02 * voc_ppm + 18.0 * leak + lel_noise).astype(np.float32)
    lel_percent = clamp(lel_percent, 0.0, 100.0)

    # alarms derived from combined conditions (not labels)
    active_alarm_count = alarms_from_conditions(
        boiler_pressure, boiler_temperature, voc_ppm, nh3_ppm, h2s_ppm, lel_percent,
        vibration_rms, days_since_maint
    )

    df = pd.DataFrame({
        "timestamp": ts,
        "asset_id": asset_id,
        "boiler_pressure_bar": boiler_pressure,
        "boiler_temperature_c": boiler_temperature,
        "voc_ppm": voc_ppm,
        "nh3_ppm": nh3_ppm,
        "h2s_ppm": h2s_ppm,
        "lel_percent": lel_percent,
        "vibration_rms": vibration_rms,
        "active_alarm_count": active_alarm_count,
        "days_since_last_maintenance": days_since_maint,
    }, columns=COLUMNS)

    return df


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    rng = np.random.default_rng(SEED)

    total_minutes = DAYS * 24 * 60
    chunk_minutes = CHUNK_MINUTES
    n_chunks = math.ceil(total_minutes / chunk_minutes)

    # Write header once
    if os.path.exists(OUT_FILE):
        os.remove(OUT_FILE)

    log_lines = []
    log_lines.append(f"Generating dataset: days={DAYS}, freq={FREQ_SECONDS}s, assets={len(ASSETS)}, out={OUT_FILE}")

    # Pre-build maintenance schedule per asset (per day)
    maint_by_asset = {}
    for a in ASSETS:
        # each asset gets its own schedule
        maint_by_asset[a] = schedule_maintenance_days(
            rng=np.random.default_rng(SEED + abs(hash(a)) % 100000),
            total_days=DAYS + 2
        )

    # chunked generation + append
    current = START_TIME
    for ci in range(n_chunks):
        remaining = total_minutes - ci * chunk_minutes
        this_chunk = min(chunk_minutes, remaining)

        chunk_frames = []
        for a in ASSETS:
            local_rng = np.random.default_rng(SEED + ci * 1000 + (abs(hash(a)) % 100000))
            df_a = generate_chunk_for_asset(
                rng=local_rng,
                asset_id=a,
                chunk_start=current,
                minutes=this_chunk,
                maint_days_series=maint_by_asset[a],
                day_index_start=(current.date() - START_TIME.date()).days,
            )
            chunk_frames.append(df_a)

        df_chunk = pd.concat(chunk_frames, axis=0, ignore_index=True)

        # keep sorted by timestamp then asset_id (optional but neat)
        df_chunk.sort_values(["timestamp", "asset_id"], inplace=True)

        # append to CSV
        df_chunk.to_csv(OUT_FILE, mode="a", index=False, header=(ci == 0))

        current = current + timedelta(minutes=this_chunk)

        if (ci + 1) % 5 == 0 or (ci + 1) == n_chunks:
            log_lines.append(f"Chunk {ci+1}/{n_chunks} written. Rows so far ~ {(ci+1)*this_chunk*len(ASSETS)}")

    print("\n".join(log_lines))
    print("Done.")
    print("Output:", OUT_FILE)


if __name__ == "__main__":
    main()
