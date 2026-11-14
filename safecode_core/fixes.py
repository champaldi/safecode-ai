"""Fix library: EN/RU texts and the text transformations behind rule-based fixes."""
import re

TEXTS = {
    "sql-injection": {
        "en": ("SQL injection",
               "User input is placed straight into the SQL string. Use a parameterized query so the database treats it as data, not code.",
               "An attacker can read or delete any table, for example dump every user record through the search field."),
        "ru": ("SQL-инъекция",
               "Пользовательский ввод подставляется прямо в SQL-строку. Используйте параметризованный запрос: тогда база воспринимает ввод как данные, а не как код.",
               "Атакующий может прочитать или удалить любые таблицы, например выгрузить всех пользователей через поле поиска."),
    },
    "hardcoded-secret": {
        "en": ("Hardcoded secret",
               "The secret is written in the source and ends up in git history. Read it from an environment variable.",
               "Anyone who can see the repository or a fork gets access to the service; the secret must then be revoked and reissued."),
        "ru": ("Секрет в коде",
               "Секрет записан в исходниках и попадёт в историю git. Читайте его из переменной окружения.",
               "Любой, кто видит репозиторий или его форк, получает доступ к сервису; секрет придётся отзывать и перевыпускать."),
    },
    "weak-hash": {
        "en": ("Weak hash for passwords",
               "MD5/SHA-1 are fast to brute-force and have known collisions. SHA-256 is the minimum; for passwords use a salted slow hash (bcrypt, scrypt, argon2).",
               "After a database leak, passwords hashed this way are recovered on a GPU within hours."),
        "ru": ("Слабое хеширование паролей",
               "MD5/SHA-1 быстро перебираются и имеют известные коллизии. SHA-256 — минимум; для паролей используйте медленный хеш с солью (bcrypt, scrypt, argon2).",
               "После утечки базы такие пароли подбираются на видеокарте за несколько часов."),
    },
    "insecure-random": {
        "en": ("Insecure random for a token",
               "The random module is predictable. Use the secrets module for tokens, codes and keys.",
               "An attacker can predict a password-reset token and take over someone else's account."),
        "ru": ("Небезопасный генератор для токена",
               "Модуль random предсказуем. Для токенов, кодов и ключей используйте модуль secrets.",
               "Атакующий может предсказать токен сброса пароля и захватить чужой аккаунт."),
    },
    "shell-injection": {
        "en": ("Command injection (shell=True)",
               "A string with user input is executed by the shell. Pass arguments as a list and drop shell=True.",
               "Characters like ; | && let an attacker run arbitrary commands on your server."),
        "ru": ("Внедрение команд (shell=True)",
               "Строка с пользовательским вводом выполняется оболочкой. Передавайте аргументы списком и уберите shell=True.",
               "Символы ; | && позволяют атакующему выполнить произвольные команды на вашем сервере."),
    },
}

REASONS = {
    "test": {"en": "Code in a test file or test function",
             "ru": "Код в тестовом файле или тестовой функции"},
    "const_sql": {"en": "SQL string is constant, no user input can reach it",
                  "ru": "SQL-строка константная, пользовательский ввод в неё не попадает"},
    "hash_nonpw": {"en": "md5/sha1 is not near password-related names (looks like a checksum or cache key)",
                   "ru": "md5/sha1 не рядом с именами, связанными с паролями (похоже на контрольную сумму или ключ кэша)"},
    "random_nonsec": {"en": "random is not used for a security-sensitive value",
                      "ru": "random не используется для значения, критичного для безопасности"},
    "literal_cmd": {"en": "Command is fully literal, no user input",
                    "ru": "Команда полностью литеральная, без пользовательского ввода"},
}

LABELS = {
    "en": {"why": "Why it matters", "manual": "Manual fix", "nofix": "No automatic fix; parametrize or rewrite manually.",
           "resolved": "Resolved since last run", "filtered": "Filtered findings", "scan": "scan time",
           "engine": "rule-based engine (no AI)", "engine_ai": "AI verdict enabled", "dash": "Dashboard",
           "none": "No real findings.", "pass": "PASS", "fail": "FAIL", "skipped": "Could not parse (skipped)"},
    "ru": {"why": "Почему это важно", "manual": "Ручное исправление", "nofix": "Автоисправления нет; параметризуйте или перепишите вручную.",
           "resolved": "Исправлено с прошлого запуска", "filtered": "Отфильтровано", "scan": "время скана",
           "engine": "rule-based движок (без ИИ)", "engine_ai": "Вердикт ИИ включён", "dash": "Дашборд",
           "none": "Реальных находок нет.", "pass": "ПРОЙДЕНО", "fail": "НЕ ПРОЙДЕНО", "skipped": "Не удалось разобрать (пропущено)"},
}


def texts(rule, lang):
    return TEXTS[rule].get(lang, TEXTS[rule]["en"])


def reason_text(key, lang):
    return REASONS[key].get(lang, REASONS[key]["en"])


def parametrize(src: str):
    """shortcut: only f"..." with double quotes and simple {expr}; anything else -> manual fix."""
    m = re.fullmatch(r'f"(.*)"', src, re.S)
    if not m or '"' in m.group(1):
        return None
    params = []

    def sub(mm):
        if mm.group(1) is not None:  # '...' quoted piece
            inner = mm.group(1)
            if "{" not in inner:
                return mm.group(0)
            e = re.fullmatch(r"\{([^{}]+)\}", inner)
            params.append(e.group(1) if e else f'f"{inner}"')
        else:
            params.append(mm.group(2))
        return "?"

    body = re.sub(r"'([^']*)'|\{([^{}]+)\}", sub, m.group(1))
    if not params:
        return None
    tup = f"({params[0]},)" if len(params) == 1 else f"({', '.join(params)})"
    return f'"{body}", {tup}'  # qmark style (sqlite3); use %s for psycopg


def shell_list(src: str):
    """f"ls -l {d}" -> ["ls", "-l", d]. shortcut: tokens split on spaces outside braces."""
    m = re.fullmatch(r'f"(.*)"', src, re.S)
    if not m or '"' in m.group(1):
        return None
    out = []
    for tok in re.findall(r"(?:\{[^{}]*\}|\S)+", m.group(1)):
        e = re.fullmatch(r"\{([^{}!:]+)\}", tok)
        out.append(e.group(1) if e else (f'f"{tok}"' if "{" in tok else f'"{tok}"'))
    return "[" + ", ".join(out) + "]"
