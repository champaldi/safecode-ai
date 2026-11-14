# Run 1: PR opened with patch 01 (head sha dryrun-sha-1)

===== summary comment (created) =====
<!-- safecode-ai-summary -->
<!-- safecode-ai-state:{"open": {"80b29f35b66a": ["\u0421\u043b\u0430\u0431\u043e\u0435 \u0445\u0435\u0448\u0438\u0440\u043e\u0432\u0430\u043d\u0438\u0435 \u043f\u0430\u0440\u043e\u043b\u0435\u0439", "app/app.py", 8], "5ff3e42887e1": ["SQL\u002d\u0438\u043d\u044a\u0435\u043a\u0446\u0438\u044f", "app/app.py", 36]}, "resolved": {}} -->
### 5 raw → 2 real, 3 filtered (60% noise removed)

**SafeCode AI: НЕ ПРОЙДЕНО** — 2 finding(s) at or above `high`

- `app/app.py:8` **Слабое хеширование паролей** (`high`, CWE-327)
- `app/app.py:36` **SQL-инъекция** (`critical`, CWE-89)

<details><summary>Отфильтровано (3)</summary>

- `app/app.py:12` Слабое хеширование паролей — md5/sha1 не рядом с именами, связанными с паролями (похоже на контрольную сумму или ключ кэша)
- `app/app.py:41` SQL-инъекция — SQL-строка константная, пользовательский ввод в неё не попадает
- `app/tests/test_search.py:3` Секрет в коде — Код в тестовом файле или тестовой функции

</details>

<sub>время скана 0.0s · rule-based движок (без ИИ)</sub>

===== inline comment app/app.py:8-8 =====
<!-- safecode-finding:80b29f35b66a -->
**Слабое хеширование паролей** · `high` · CWE-327

MD5/SHA-1 быстро перебираются и имеют известные коллизии. SHA-256 — минимум; для паролей используйте медленный хеш с солью (bcrypt, scrypt, argon2).

**Почему это важно:** После утечки базы такие пароли подбираются на видеокарте за несколько часов.

```suggestion
    return hashlib.sha256(password.encode()).hexdigest()
```

<sub>Rule-based fix</sub>

===== inline comment app/app.py:36-36 =====
<!-- safecode-finding:5ff3e42887e1 -->
**SQL-инъекция** · `critical` · CWE-89

Пользовательский ввод подставляется прямо в SQL-строку. Используйте параметризованный запрос: тогда база воспринимает ввод как данные, а не как код.

**Почему это важно:** Атакующий может прочитать или удалить любые таблицы, например выгрузить всех пользователей через поле поиска.

```suggestion
        rows = db.execute("SELECT id, name FROM users WHERE name LIKE ?", (f"%{q}%",)).fetchall()
```

<sub>Rule-based fix</sub>

===== check run SafeCode AI: FAILURE =====
SafeCode AI: 2 blocking finding(s)

### 5 raw → 2 real, 3 filtered (60% noise removed)

**SafeCode AI: НЕ ПРОЙДЕНО** — 2 finding(s) at or above `high`

- `app/app.py:8` **Слабое хеширование паролей** (`high`, CWE-327)
- `app/app.py:36` **SQL-инъекция** (`critical`, CWE-89)

<details><summary>Отфильтровано (3)</summary>

- `app/app.py:12` Слабое хеширование паролей — md5/sha1 не рядом с именами, связанными с паролями (похоже на контрольную сумму или ключ кэша)
- `app/app.py:41` SQL-инъекция — SQL-строка константная, пользовательский ввод в неё не попадает
- `app/tests/test_search.py:3` Секрет в коде — Код в тестовом файле или тестовой функции

</details>

<sub>время скана 0.0s · rule-based движок (без ИИ)</sub>


# Run 2: after Commit suggestion (head sha dryrun-sha-2)

===== summary comment (updated in place) =====
<!-- safecode-ai-summary -->
<!-- safecode-ai-state:{"open": {}, "resolved": {"80b29f35b66a": ["\u0421\u043b\u0430\u0431\u043e\u0435 \u0445\u0435\u0448\u0438\u0440\u043e\u0432\u0430\u043d\u0438\u0435 \u043f\u0430\u0440\u043e\u043b\u0435\u0439", "app/app.py", 8], "5ff3e42887e1": ["SQL\u002d\u0438\u043d\u044a\u0435\u043a\u0446\u0438\u044f", "app/app.py", 36]}} -->
### 3 raw → 0 real, 3 filtered (100% noise removed)

**SafeCode AI: ПРОЙДЕНО**

Реальных находок нет.

**Исправлено с прошлого запуска:**
- ~~**Слабое хеширование паролей**~~ `app/app.py`
- ~~**SQL-инъекция**~~ `app/app.py`

<details><summary>Отфильтровано (3)</summary>

- `app/app.py:12` Слабое хеширование паролей — md5/sha1 не рядом с именами, связанными с паролями (похоже на контрольную сумму или ключ кэша)
- `app/app.py:41` SQL-инъекция — SQL-строка константная, пользовательский ввод в неё не попадает
- `app/tests/test_search.py:3` Секрет в коде — Код в тестовом файле или тестовой функции

</details>

<sub>время скана 0.0s · rule-based движок (без ИИ)</sub>

===== reply to inline comment 2 =====
Resolved in dryrun-

===== reply to inline comment 3 =====
Resolved in dryrun-

===== check run SafeCode AI: SUCCESS =====
SafeCode AI: passed

### 3 raw → 0 real, 3 filtered (100% noise removed)

**SafeCode AI: ПРОЙДЕНО**

Реальных находок нет.

**Исправлено с прошлого запуска:**
- ~~**Слабое хеширование паролей**~~ `app/app.py`
- ~~**SQL-инъекция**~~ `app/app.py`

<details><summary>Отфильтровано (3)</summary>

- `app/app.py:12` Слабое хеширование паролей — md5/sha1 не рядом с именами, связанными с паролями (похоже на контрольную сумму или ключ кэша)
- `app/app.py:41` SQL-инъекция — SQL-строка константная, пользовательский ввод в неё не попадает
- `app/tests/test_search.py:3` Секрет в коде — Код в тестовом файле или тестовой функции

</details>

<sub>время скана 0.0s · rule-based движок (без ИИ)</sub>
