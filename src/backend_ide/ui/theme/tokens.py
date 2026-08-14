"""Theme Design Tokens for PySide6 Desktop Application."""

from enum import StrEnum

from pydantic import BaseModel, ConfigDict


class ThemeMode(StrEnum):
    """Supported theme modes."""

    SYSTEM = "system"
    LIGHT = "light"
    DARK = "dark"


class ThemePalette(BaseModel):
    """Color palette tokens for UI styling."""

    model_config = ConfigDict(frozen=True)

    bg_main: str
    bg_sidebar: str
    bg_surface: str
    bg_input: str
    bg_hover: str
    border: str
    border_active: str
    text_primary: str
    text_secondary: str
    text_muted: str
    text_on_accent: str
    accent: str
    accent_hover: str
    success: str
    success_hover: str
    warning: str
    danger: str
    info: str


DARK_PALETTE = ThemePalette(
    bg_main="#181825",
    bg_sidebar="#11111b",
    bg_surface="#1e1e2e",
    bg_input="#313244",
    bg_hover="#45475a",
    border="#45475a",
    border_active="#89b4fa",
    text_primary="#cdd6f4",
    text_secondary="#a6adc8",
    text_muted="#6c7086",
    text_on_accent="#11111b",
    accent="#89b4fa",
    accent_hover="#b4befe",
    success="#a6e3a1",
    success_hover="#94e2d5",
    warning="#f9e2af",
    danger="#f38ba8",
    info="#89dceb",
)

LIGHT_PALETTE = ThemePalette(
    bg_main="#eff1f5",
    bg_sidebar="#e6e9ef",
    bg_surface="#ffffff",
    bg_input="#dce0e6",
    bg_hover="#ccd0da",
    border="#bcc0cc",
    border_active="#1e66f5",
    text_primary="#4c4f69",
    text_secondary="#5c5f77",
    text_muted="#8c8fa1",
    text_on_accent="#11111b",
    accent="#1e66f5",
    accent_hover="#209fb5",
    success="#40a02b",
    success_hover="#179299",
    warning="#df8e1d",
    danger="#d20f39",
    info="#04a5e5",
)
