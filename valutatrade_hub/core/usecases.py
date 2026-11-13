import secrets
from datetime import datetime, timedelta
from typing import Optional

from valutatrade_hub.core.models import Portfolio, User, Wallet
from valutatrade_hub.core.utils import (
    PORTFOLIOS_FILE,
    RATES_FILE,
    USERS_FILE,
    load_json,
    save_json,
)

# Текущая сессия пользователя в памяти
CURRENT_USER: Optional[User] = None


def get_current_user() -> User:
    """Проверяет, выполнен ли вход в систему."""
    if CURRENT_USER is None:
        raise PermissionError("Сначала выполните login")
    return CURRENT_USER


def register_user(username: str, password: str) -> str:
    """Регистрирует нового пользователя и создаёт пустой портфель."""
    clean_name = username.strip()
    if not clean_name:
        raise ValueError("Имя пользователя не может быть пустым")
    if len(password) < 4:
        raise ValueError("Пароль должен быть не короче 4 символов")

    users_data = load_json(USERS_FILE)
    for u in users_data:
        if u["username"].lower() == clean_name.lower():
            raise ValueError(f"Имя пользователя '{clean_name}' уже занято")

    new_id = max((u["user_id"] for u in users_data), default=0) + 1
    salt = secrets.token_hex(4)
    now = datetime.now()

    user = User(
        user_id=new_id,
        username=clean_name,
        hashed_password="",
        salt=salt,
        registration_date=now,
    )
    user.change_password(password)

    users_data.append(
        {
            "user_id": user.user_id,
            "username": user.username,
            "hashed_password": user.hashed_password,
            "salt": user.salt,
            "registration_date": now.isoformat(timespec="seconds"),
        }
    )
    save_json(USERS_FILE, users_data)

    portfolios_data = load_json(PORTFOLIOS_FILE)
    portfolios_data.append({"user_id": new_id, "wallets": {}})
    save_json(PORTFOLIOS_FILE, portfolios_data)

    return f"Пользователь '{clean_name}' зарегистрирован (id={new_id}). Войдите: login --username {clean_name} --password ****"


def login_user(username: str, password: str) -> str:
    """Авторизует пользователя и сохраняет сессию."""
    global CURRENT_USER
    users_data = load_json(USERS_FILE)

    user_record = next((u for u in users_data if u["username"] == username), None)
    if not user_record:
        raise ValueError(f"Пользователь '{username}' не найден")

    user = User(
        user_id=user_record["user_id"],
        username=user_record["username"],
        hashed_password=user_record["hashed_password"],
        salt=user_record["salt"],
        registration_date=datetime.fromisoformat(user_record["registration_date"]),
    )

    if not user.verify_password(password):
        raise ValueError("Неверный пароль")

    CURRENT_USER = user
    return f"Вы вошли как '{user.username}'"


def _load_user_portfolio(user_id: int) -> Portfolio:
    """Загружает портфель пользователя из JSON в модель Portfolio."""
    portfolios_data = load_json(PORTFOLIOS_FILE)
    record = next((p for p in portfolios_data if p["user_id"] == user_id), None)

    wallets = {}
    if record:
        for code, w_data in record.get("wallets", {}).items():
            wallets[code] = Wallet(currency_code=code, balance=w_data["balance"])

    return Portfolio(user_id=user_id, wallets=wallets)


def _save_user_portfolio(portfolio: Portfolio) -> None:
    """Сохраняет состояние портфеля пользователя обратно в JSON."""
    portfolios_data = load_json(PORTFOLIOS_FILE)
    wallets_dict = {
        code: {"balance": wallet.balance} for code, wallet in portfolio.wallets.items()
    }

    updated = False
    for record in portfolios_data:
        if record["user_id"] == portfolio.user_id:
            record["wallets"] = wallets_dict
            updated = True
            break

    if not updated:
        portfolios_data.append({"user_id": portfolio.user_id, "wallets": wallets_dict})

    save_json(PORTFOLIOS_FILE, portfolios_data)


def get_exchange_rate(from_curr: str, to_curr: str) -> tuple[float, str]:
    """Возвращает кортеж (курс, время_обновления) для пары валют."""
    c_from = from_curr.upper().strip()
    c_to = to_curr.upper().strip()

    if not c_from or not c_to:
        raise ValueError("Коды валют не могут быть пустыми")

    if c_from == c_to:
        return 1.0, datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    rates_data = load_json(RATES_FILE)

    # Базовые курсы относительно USD (из кеша или заглушки)
    usd_rates = {"USD": 1.0}
    last_updated = rates_data.get("last_refresh", datetime.now().isoformat(timespec="seconds"))

    for key, val in rates_data.items():
        if key.endswith("_USD") and isinstance(val, dict):
            curr = key.replace("_USD", "")
            usd_rates[curr] = val["rate"]
            last_updated = val.get("updated_at", last_updated)

    # Проверка свежести кеша (5 минут) — заглушка обновления при устаревании
    try:
        upd_dt = datetime.fromisoformat(last_updated)
        if datetime.now() - upd_dt > timedelta(minutes=5):
            # Здесь в будущем будет вызов Parser Service
            last_updated = datetime.now().isoformat(timespec="seconds")
    except ValueError:
        pass

    if c_from not in usd_rates or c_to not in usd_rates:
        raise ValueError(f"Курс {c_from}→{c_to} недоступен. Повторите попытку позже.")

    rate = usd_rates[c_from] / usd_rates[c_to]
    formatted_time = last_updated.replace("T", " ")
    return rate, formatted_time


def show_portfolio(base_currency: str = "USD") -> str:
    """Формирует отчёт по портфелю пользователя в базовой валюте."""
    user = get_current_user()
    base = base_currency.upper().strip()

    # Проверка существования базовой валюты
    try:
        get_exchange_rate(base, "USD")
    except ValueError:
        raise ValueError(f"Неизвестная базовая валюта '{base}'")

    portfolio = _load_user_portfolio(user.user_id)
    if not portfolio.wallets:
        return f"Портфель пользователя '{user.username}' пуст."

    lines = [f"Портфель пользователя '{user.username}' (база: {base}):"]
    total_value = 0.0

    for code, wallet in portfolio.wallets.items():
        rate, _ = get_exchange_rate(code, base)
        converted = wallet.balance * rate
        total_value += converted
        lines.append(f"- {code}: {wallet.balance:.4f}  → {converted:,.2f} {base}")

    lines.append("---------------------------------")
    lines.append(f"ИТОГО: {total_value:,.2f} {base}")
    return "\n".join(lines)


def buy_currency(currency: str, amount: float) -> str:
    """Покупка валюты пользователем."""
    user = get_current_user()
    code = currency.upper().strip()

    if not code:
        raise ValueError("Код валюты не может быть пустым")
    if amount <= 0:
        raise ValueError("'amount' должен быть положительным числом")

    try:
        rate, _ = get_exchange_rate(code, "USD")
    except ValueError:
        raise ValueError(f"Не удалось получить курс для {code}→USD")

    portfolio = _load_user_portfolio(user.user_id)

    if code not in portfolio.wallets:
        portfolio.add_currency(code)

    wallet = portfolio.get_wallet(code)
    old_balance = wallet.balance
    wallet.deposit(amount)

    _save_user_portfolio(portfolio)
    estimated_cost = amount * rate

    return (
        f"Покупка выполнена: {amount:.4f} {code} по курсу {rate:.2f} USD/{code}\n"
        f"Изменения в портфеле:\n"
        f"- {code}: было {old_balance:.4f} → стало {wallet.balance:.4f}\n"
        f"Оценочная стоимость покупки: {estimated_cost:,.2f} USD"
    )


def sell_currency(currency: str, amount: float) -> str:
    """Продажа валюты пользователем."""
    user = get_current_user()
    code = currency.upper().strip()

    if not code:
        raise ValueError("Код валюты не может быть пустым")
    if amount <= 0:
        raise ValueError("'amount' должен быть положительным числом")

    portfolio = _load_user_portfolio(user.user_id)

    if code not in portfolio.wallets:
        raise ValueError(
            f"У вас нет кошелька '{code}'. Добавьте валюту: она создаётся автоматически при первой покупке."
        )

    wallet = portfolio.get_wallet(code)
    if wallet.balance < amount:
        raise ValueError(
            f"Недостаточно средств: доступно {wallet.balance:.4f} {code}, требуется {amount:.4f} {code}"
        )

    try:
        rate, _ = get_exchange_rate(code, "USD")
    except ValueError:
        raise ValueError(f"Не удалось получить курс для {code}→USD")

    old_balance = wallet.balance
    wallet.withdraw(amount)

    _save_user_portfolio(portfolio)
    revenue = amount * rate

    return (
        f"Продажа выполнена: {amount:.4f} {code} по курсу {rate:.2f} USD/{code}\n"
        f"Изменения в портфеле:\n"
        f"- {code}: было {old_balance:.4f} → стало {wallet.balance:.4f}\n"
        f"Оценочная выручка: {revenue:,.2f} USD"
    )
