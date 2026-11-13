import json
from pathlib import Path
from typing import Any

DATA_DIR = Path("data")
USERS_FILE = DATA_DIR / "users.json"
PORTFOLIOS_FILE = DATA_DIR / "portfolios.json"
RATES_FILE = DATA_DIR / "rates.json"


def init_storage() -> None:
    """Создаёт папку data и пустые JSON-файлы при их отсутствии."""
    DATA_DIR.mkdir(exist_ok=True)
    if not USERS_FILE.exists():
        save_json(USERS_FILE, [])
    if not PORTFOLIOS_FILE.exists():
        save_json(PORTFOLIOS_FILE, [])
    if not RATES_FILE.exists():
        default_rates = {
            "EUR_USD": {"rate": 1.0786, "updated_at": "2025-10-09T10:30:00"},
            "BTC_USD": {"rate": 59337.21, "updated_at": "2025-10-09T10:29:42"},
            "RUB_USD": {"rate": 0.01016, "updated_at": "2025-10-09T10:31:12"},
            "ETH_USD": {"rate": 3720.00, "updated_at": "2025-10-09T10:35:00"},
            "source": "StubService",
            "last_refresh": "2025-10-09T10:35:00",
        }
        save_json(RATES_FILE, default_rates)


def load_json(filepath: Path) -> Any:
    """Читает данные из JSON-файла."""
    if not filepath.exists():
        init_storage()
    with open(filepath, "r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return [] if filepath != RATES_FILE else {}


def save_json(filepath: Path, data: Any) -> None:
    """Сохраняет данные в JSON-файл."""
    filepath.parent.mkdir(exist_ok=True)
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
