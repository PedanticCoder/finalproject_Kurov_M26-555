import argparse
import shlex

from valutatrade_hub.core import usecases
from valutatrade_hub.core.utils import init_storage


class SilentArgumentParser(argparse.ArgumentParser):
    """Переопределяем парсер, чтобы он не завершал программу (sys.exit) при ошибке ввода."""

    def error(self, message: str) -> None:
        raise ValueError(f"Ошибка аргументов: {message}")


def build_parser() -> SilentArgumentParser:
    """Настраивает дерево всех доступных CLI-команд."""
    parser = SilentArgumentParser(prog="", add_help=True)
    subparsers = parser.add_subparsers(dest="command", required=True)

    # 1. register
    p_reg = subparsers.add_parser("register", help="Регистрация нового пользователя")
    p_reg.add_argument("--username", required=True, type=str)
    p_reg.add_argument("--password", required=True, type=str)

    # 2. login
    p_login = subparsers.add_parser("login", help="Вход в систему")
    p_login.add_argument("--username", required=True, type=str)
    p_login.add_argument("--password", required=True, type=str)

    # 3. show-portfolio
    p_show = subparsers.add_parser("show-portfolio", help="Показать портфель")
    p_show.add_argument("--base", default="USD", type=str)

    # 4. buy
    p_buy = subparsers.add_parser("buy", help="Купить валюту")
    p_buy.add_argument("--currency", required=True, type=str)
    p_buy.add_argument("--amount", required=True, type=float)

    # 5. sell
    p_sell = subparsers.add_parser("sell", help="Продать валюту")
    p_sell.add_argument("--currency", required=True, type=str)
    p_sell.add_argument("--amount", required=True, type=float)

    # 6. get-rate
    p_rate = subparsers.add_parser("get-rate", help="Получить курс валюты")
    p_rate.add_argument("--from", dest="from_curr", required=True, type=str)
    p_rate.add_argument("--to", dest="to_curr", required=True, type=str)

    return parser


def run_cli() -> None:
    """Главный цикл интерактивного консольного интерфейса."""
    init_storage()
    parser = build_parser()

    print("Добро пожаловать в ValutaTrade Hub! Введите команду (или 'exit' для выхода).")

    while True:
        try:
            raw_input = input("\n> ").strip()
            if not raw_input:
                continue
            if raw_input.lower() in ("exit", "quit"):
                print("До свидания!")
                break

            tokens = shlex.split(raw_input)
            args = parser.parse_args(tokens)

            if args.command == "register":
                print(usecases.register_user(args.username, args.password))

            elif args.command == "login":
                print(usecases.login_user(args.username, args.password))

            elif args.command == "show-portfolio":
                print(usecases.show_portfolio(args.base))

            elif args.command == "buy":
                print(usecases.buy_currency(args.currency, args.amount))

            elif args.command == "sell":
                print(usecases.sell_currency(args.currency, args.amount))

            elif args.command == "get-rate":
                rate, updated_at = usecases.get_exchange_rate(args.from_curr, args.to_curr)
                rev_rate = 1.0 / rate if rate != 0 else 0.0
                c_from = args.from_curr.upper()
                c_to = args.to_curr.upper()
                print(f"Курс {c_from}→{c_to}: {rate:.8f} (обновлено: {updated_at})")
                print(f"Обратный курс {c_to}→{c_from}: {rev_rate:.2f}")

        except SystemExit:
            # Срабатывает при вызове --help, просто продолжаем цикл
            continue
        except (ValueError, PermissionError, TypeError) as e:
            print(e)
        except KeyboardInterrupt:
            print("\nВыход из программы.")
            break
