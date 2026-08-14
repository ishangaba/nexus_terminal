from fastapi import APIRouter
from pydantic import BaseModel

from config import USER_CONFIGURABLE_KEYS, apply_settings_overrides, settings
from db.models import delete_setting, set_setting

router = APIRouter(prefix="/api/v1/settings")

KEY_LABELS = {
    "alpha_vantage_api_key": "Alpha Vantage",
    "finnhub_api_key": "Finnhub",
    "anthropic_api_key": "Anthropic",
    "marketaux_api_key": "Marketaux",
    "fred_api_key": "FRED",
}


def _mask(value: str) -> str | None:
    if not value:
        return None
    if len(value) <= 4:
        return "•" * len(value)
    return "••••••••" + value[-4:]


class SettingsUpdate(BaseModel):
    alpha_vantage_api_key: str | None = None
    finnhub_api_key: str | None = None
    anthropic_api_key: str | None = None
    marketaux_api_key: str | None = None
    fred_api_key: str | None = None


@router.get("")
def read_settings():
    return {
        key: {"label": KEY_LABELS[key], "configured": bool(getattr(settings, key)), "masked": _mask(getattr(settings, key))}
        for key in USER_CONFIGURABLE_KEYS
    }


@router.put("")
def update_settings(body: SettingsUpdate):
    updates = body.model_dump(exclude_unset=True)
    for key, value in updates.items():
        if key not in USER_CONFIGURABLE_KEYS:
            continue
        if value:
            set_setting(key, value)
    apply_settings_overrides()
    return read_settings()


@router.delete("/{key}")
def clear_setting(key: str):
    if key not in USER_CONFIGURABLE_KEYS:
        return read_settings()
    delete_setting(key)
    setattr(settings, key, "")
    apply_settings_overrides()
    return read_settings()
