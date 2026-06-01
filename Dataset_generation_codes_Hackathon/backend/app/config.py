import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import List


def _env_list(name: str, default: str) -> List[str]:
    raw = os.getenv(name, default)
    return [item.strip() for item in raw.split(",") if item.strip()]


@dataclass(frozen=True)
class Settings:
    # app/ folder
    APP_DIR: Path = field(default_factory=lambda: Path(__file__).resolve().parent)

    # Will be set in __post_init__
    ROOT_DIR: Path = field(init=False)
    DATA_DIR: Path = field(init=False)
    MODEL_DIR: Path = field(init=False)

    DATA_MASTER: Path = field(init=False)
    DATA_DAILY: Path = field(init=False)
    DATA_EVENTS: Path = field(init=False)
    DATA_EVENTS_SHAP: Path = field(init=False)

    XGB_JSON: Path = field(init=False)
    XGB_META: Path = field(init=False)
    GLOBAL_SHAP_JSON: Path = field(init=False)
    ISO_THRESHOLDS_JSON: Path = field(init=False)

    APP_NAME: str = field(default_factory=lambda: os.getenv("APP_NAME", "Bulk Drug Safety API"))
    APP_VERSION: str = field(default_factory=lambda: os.getenv("APP_VERSION", "2.0.0"))
    DEBUG: bool = field(default_factory=lambda: os.getenv("DEBUG", "true").lower() == "true")
    CORS_ORIGINS: List[str] = field(default_factory=lambda: _env_list("CORS_ORIGINS", "*"))

    GEMINI_API_KEY: str = field(default_factory=lambda: os.getenv("GEMINI_API_KEY", ""))
    GEMINI_MODEL: str = field(default_factory=lambda: os.getenv("GEMINI_MODEL", "gemini-2.5-pro"))

    ISO_PREFIX: str = field(default_factory=lambda: os.getenv("ISO_PREFIX", "isoforest_"))
    BASE_FEATURES: List[str] = field(
        default_factory=lambda: [
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
    )
    ROLL_WINDOWS: List[int] = field(default_factory=lambda: [5, 15, 60])
    SLOPE_WINDOW: int = field(default_factory=lambda: 15)

    DEFAULT_TIMESERIES_MINUTES: int = field(default_factory=lambda: int(os.getenv("DEFAULT_TIMESERIES_MINUTES", "60")))
    MAX_TIMESERIES_ROWS: int = field(default_factory=lambda: int(os.getenv("MAX_TIMESERIES_ROWS", "20000")))

    VOC_HIGH: float = field(default_factory=lambda: float(os.getenv("VOC_HIGH", "120")))
    NH3_HIGH: float = field(default_factory=lambda: float(os.getenv("NH3_HIGH", "25")))
    H2S_HIGH: float = field(default_factory=lambda: float(os.getenv("H2S_HIGH", "10")))
    LEL_HIGH: float = field(default_factory=lambda: float(os.getenv("LEL_HIGH", "20")))
    VIB_HIGH: float = field(default_factory=lambda: float(os.getenv("VIB_HIGH", "3.0")))
    MAINT_HIGH_DAYS: float = field(default_factory=lambda: float(os.getenv("MAINT_HIGH_DAYS", "30")))
    ALARM_HIGH: float = field(default_factory=lambda: float(os.getenv("ALARM_HIGH", "2")))

    def __post_init__(self):
        # app/ -> backend/ -> Hackathon/
        root_dir = self.APP_DIR.parent.parent
        data_dir = Path(os.getenv("DATA_DIR", str(root_dir / "data")))
        model_dir = Path(os.getenv("MODEL_DIR", str(root_dir / "models")))

        object.__setattr__(self, "ROOT_DIR", root_dir)
        object.__setattr__(self, "DATA_DIR", data_dir)
        object.__setattr__(self, "MODEL_DIR", model_dir)

        object.__setattr__(
            self,
            "DATA_MASTER",
            Path(os.getenv("DATA_MASTER", str(data_dir / "bulk_drug_factory_MASTER_scored.csv"))),
        )
        object.__setattr__(
            self,
            "DATA_DAILY",
            Path(os.getenv("DATA_DAILY", str(data_dir / "daily_asset_summary.csv"))),
        )
        object.__setattr__(
            self,
            "DATA_EVENTS",
            Path(os.getenv("DATA_EVENTS", str(data_dir / "high_risk_events.csv"))),
        )
        object.__setattr__(
            self,
            "DATA_EVENTS_SHAP",
            Path(os.getenv("DATA_EVENTS_SHAP", str(data_dir / "high_risk_events_with_shap.csv"))),
        )

        object.__setattr__(
            self,
            "XGB_JSON",
            Path(os.getenv("XGB_JSON", str(model_dir / "bulk_drug_safety_xgb_cpu_es_model.json"))),
        )
        object.__setattr__(
            self,
            "XGB_META",
            Path(os.getenv("XGB_META", str(model_dir / "bulk_drug_safety_xgb_cpu_es_model_metadata.json"))),
        )
        object.__setattr__(
            self,
            "GLOBAL_SHAP_JSON",
            Path(os.getenv("GLOBAL_SHAP_JSON", str(model_dir / "bulk_drug_xgb_shap_global.json"))),
        )
        object.__setattr__(
            self,
            "ISO_THRESHOLDS_JSON",
            Path(os.getenv("ISO_THRESHOLDS_JSON", str(model_dir / "isoforest_thresholds.json"))),
        )


settings = Settings()