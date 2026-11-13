#!/usr/bin/env python3

import hashlib
from datetime import datetime

class User:
    """Класс, представляющий пользователя системы валютного кошелька."""

    def __init__(
        self,
        user_id: int,
        username: str,
        hashed_password: str,
        salt: str,
        registration_date: datetime,
    ) -> None:
        """Инициализация защищённых атрибутов пользователя."""
        self._user_id: int = user_id
        self._username: str = username
        self._hashed_password: str = hashed_password
        self._salt: str = salt
        self._registration_date: datetime = registration_date

    @property
    def user_id(self) -> int:
        """Геттер для ID пользователя."""
        return self._user_id

    @property
    def username(self) -> str:
        """Геттер для имени пользователя."""
        return self._username

    @username.setter
    def username(self, value: str) -> None:
        """Сеттер для имени пользователя с валидацией."""
        if not value or not value.strip():
            raise ValueError("Имя пользователя не может быть пустым.")
        self._username = value.strip()

    @property
    def hashed_password(self) -> str:
        """Геттер для хеша пароля."""
        return self._hashed_password

    @property
    def salt(self) -> str:
        """Геттер для соли."""
        return self._salt

    @property
    def registration_date(self) -> datetime:
        """Геттер для даты регистрации."""
        return self._registration_date

    def get_user_info(self) -> str:
        """Возвращает строковую информацию о пользователе (без пароля и соли)."""
        formatted_date = self._registration_date.strftime("%Y-%m-%dT%H:%M:%S")
        return (
            f"ID: {self._user_id} | "
            f"Username: {self._username} | "
            f"Registered: {formatted_date}"
        )

    def change_password(self, new_password: str) -> None:
        """Изменяет пароль пользователя с проверкой длины и хешированием."""
        if not new_password or len(new_password) < 4:
            raise ValueError("Пароль должен быть не короче 4 символов.")

        secret_string = f"{new_password}{self._salt}"
        self._hashed_password = hashlib.sha256(secret_string.encode("utf-8")).hexdigest()

    def verify_password(self, password: str) -> bool:
        """Проверяет, совпадает ли введённый пароль с текущим хешем."""
        secret_string = f"{password}{self._salt}"
        input_hash = hashlib.sha256(secret_string.encode("utf-8")).hexdigest()
        return input_hash == self._hashed_password
    
class Wallet:
    """Класс, представляющий кошелёк пользователя для одной конкретной валюты."""

    def __init__(self, currency_code: str, balance: float = 0.0) -> None:
        """Инициализация кошелька."""
        self.currency_code: str = currency_code.upper().strip()
        self.balance = balance  

    @property
    def balance(self) -> float:
        """Геттер для получения текущего значения баланса."""
        return self._balance

    @balance.setter
    def balance(self, value: float) -> None:
        """Сеттер для баланса, запрещающий некорректные типы и отрицательные значения."""
        if not isinstance(value, (int, float)):
            raise TypeError("Баланс должен быть числом (int или float).")
        if value < 0:
            raise ValueError("Баланс кошелька не может быть отрицательным.")
        self._balance = float(value)

    def deposit(self, amount: float) -> None:
        """Пополнение баланса кошелька."""
        if not isinstance(amount, (int, float)):
            raise TypeError("Сумма пополнения должна быть числом.")
        if amount <= 0:
            raise ValueError("Сумма пополнения должна быть строго больше нуля.")

        self.balance += amount

    def withdraw(self, amount: float) -> None:
        """Снятие средств с кошелька с проверкой доступного остатка."""
        if not isinstance(amount, (int, float)):
            raise TypeError("Сумма снятия должна быть числом.")
        if amount <= 0:
            raise ValueError("Сумма снятия должна быть строго больше нуля.")
        if amount > self._balance:
            raise ValueError(
                f"Недостаточно средств. Запрошено: {amount}, доступно: {self._balance}"
            )

        self.balance -= amount

    def get_balance_info(self) -> str:
        """Вывод информации о текущем балансе."""
        return f"Валюта: {self.currency_code} | Баланс: {self._balance:.4f}"

class Portfolio:
    """Класс для управления всеми кошельками одного пользователя."""

    def __init__(self, user_id: int, wallets: dict[str, Wallet] | None = None) -> None:
        """Инициализация портфеля пользователя."""
        self._user_id: int = user_id
        self._wallets: dict[str, Wallet] = wallets if wallets is not None else {}

    @property
    def user_id(self) -> int:
        """Геттер для ID владельца портфеля."""
        return self._user_id

    @property
    def wallets(self) -> dict[str, Wallet]:
        """Геттер, возвращающий копию словаря кошельков для безопасности."""
        return self._wallets.copy()

    def add_currency(self, currency_code: str) -> None:
        """Добавляет новый пустой кошелёк в портфель, если его ещё нет."""
        code_upper = currency_code.upper().strip()
        
        if not code_upper:
            raise ValueError("Код валюты не может быть пустым.")
        if code_upper in self._wallets:
            raise ValueError(f"Кошелёк для валюты {code_upper} уже существует.")
        
        self._wallets[code_upper] = Wallet(currency_code=code_upper, balance=0.0)

    def get_wallet(self, currency_code: str) -> Wallet:
        """Возвращает объект Wallet по коду валюты."""
        code_upper = currency_code.upper().strip()
        if code_upper not in self._wallets:
            raise ValueError(f"Кошелёк для валюты {code_upper} не найден в портфеле.")
        return self._wallets[code_upper]

    def get_total_value(self, base_currency: str = 'USD') -> float:
        """Возвращает общую стоимость всех валют пользователя в базовой валюте."""
        target_currency = base_currency.upper().strip()
        
        exchange_rates = {
            "USD": 1.0,
            "EUR": 1.08,   
            "BTC": 95000.0, 
            "RUB": 0.010,   
        }

        if target_currency not in exchange_rates:
            raise ValueError(f"Курс для базовой валюты {target_currency} не поддерживается.")

        total_in_usd = 0.0

        for code, wallet in self._wallets.items():
            if code not in exchange_rates:
                continue
            value_in_usd = wallet.balance * exchange_rates[code]
            total_in_usd += value_in_usd

        return total_in_usd / exchange_rates[target_currency]

