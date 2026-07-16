import sys
import os
import json
import secrets
import datetime

# Не створювати .pyc файли (__pycache__), щоб застарілий кеш байт-коду
# ніколи не підміняв актуальний код (саме через це не відкривалась
# сторінка "Загальний огляд" — Python підвантажував старий закешований app.py).
sys.dont_write_bytecode = True

from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from werkzeug.security import generate_password_hash, check_password_hash

from parser import (
    get_verse, get_verses, get_full_book, get_verse_range,
    BOOKS, OT_BOOKS, NT_BOOKS, BOOK_ORDER, BOOK_CHAPTERS
)


app = Flask(__name__)

# Логін "admin" — єдиний обліковий запис з доступом до сторінки статистики
# (/admin). Достатньо зареєструватись під цим логіном через звичайну форму
# реєстрації — жодного окремого пароля в коді не зберігається.
ADMIN_USERNAME = "admin"

# Секретний ключ потрібен Flask для підпису сесійних кук (щоб працював вхід/реєстрація).
# Якщо файл секрету відсутній — створюємо один раз і надалі використовуємо його,
# щоб сесії користувачів не "злітали" після кожного перезапуску сервера.
SECRET_KEY_FILE = os.path.join(os.path.dirname(__file__), ".secret_key")

if os.environ.get("SECRET_KEY"):
    # На хостингу файлова система часто ефемерна (скидається при кожному
    # перезапуску), тож там секрет краще задавати змінною середовища —
    # інакше сесії користувачів "злітатимуть" після кожного деплою.
    app.secret_key = os.environ["SECRET_KEY"]
elif os.path.exists(SECRET_KEY_FILE):
    with open(SECRET_KEY_FILE, "r", encoding="utf-8") as f:
        app.secret_key = f.read().strip()
else:
    app.secret_key = secrets.token_hex(32)
    with open(SECRET_KEY_FILE, "w", encoding="utf-8") as f:
        f.write(app.secret_key)

USERS_FILE = os.path.join(os.path.dirname(__file__), "users.json")
EXCERPTS_FILE = os.path.join(os.path.dirname(__file__), "excerpts.json")
NOTES_FILE = os.path.join(os.path.dirname(__file__), "overview_notes.json")
ANALYTICS_FILE = os.path.join(os.path.dirname(__file__), "analytics.json")


def load_users():

    if not os.path.exists(USERS_FILE):
        return {}

    with open(USERS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_users(users):

    with open(USERS_FILE, "w", encoding="utf-8") as f:
        json.dump(users, f, ensure_ascii=False, indent=2)


def load_excerpts():

    if not os.path.exists(EXCERPTS_FILE):
        return {}

    with open(EXCERPTS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def persist_excerpts(all_excerpts):

    with open(EXCERPTS_FILE, "w", encoding="utf-8") as f:
        json.dump(all_excerpts, f, ensure_ascii=False, indent=2)


def excerpts_key(username, book):
    return f"{username}::{book}"


def load_notes():

    if not os.path.exists(NOTES_FILE):
        return {}

    with open(NOTES_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def persist_notes(all_notes):

    with open(NOTES_FILE, "w", encoding="utf-8") as f:
        json.dump(all_notes, f, ensure_ascii=False, indent=2)


def load_analytics():

    if not os.path.exists(ANALYTICS_FILE):
        return {"total_visits": 0, "unique_visitors": [], "visits_by_date": {}}

    with open(ANALYTICS_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    data.setdefault("total_visits", 0)
    data.setdefault("unique_visitors", [])
    data.setdefault("visits_by_date", {})
    return data


def persist_analytics(data):

    with open(ANALYTICS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


@app.before_request
def track_visit():
    # Рахуємо кожен візит на сторінку застосунку (крім статичних файлів і
    # самої адмін-панелі, щоб перегляд статистики не спотворював статистику).
    # Унікальних відвідувачів рахуємо за анонімним ідентифікатором у сесії —
    # окремо від логіна, тож рахуються й ті, хто ще не зареєструвався.
    if request.path.startswith("/static") or request.path.startswith("/admin"):
        return

    if "visitor_id" not in session:
        session["visitor_id"] = secrets.token_hex(8)

    data = load_analytics()
    data["total_visits"] += 1

    visitor_id = session["visitor_id"]
    if visitor_id not in data["unique_visitors"]:
        data["unique_visitors"].append(visitor_id)

    today = datetime.date.today().isoformat()
    data["visits_by_date"][today] = data["visits_by_date"].get(today, 0) + 1

    persist_analytics(data)


@app.route("/")
def home():
    # Сторінка 1 — вступ до індуктивного методу вивчення Біблії
    return render_template("index.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    # Сторінка 2 — реєстрація / вхід, щоб надалі зберігати нотатки користувача
    error = None

    if request.method == "POST":

        action = request.form.get("action", "register")
        username = (request.form.get("username") or "").strip()
        password = request.form.get("password") or ""

        if not username or not password:
            error = "Заповніть логін і пароль"

        else:
            users = load_users()

            if action == "login":

                user = users.get(username)

                if user and check_password_hash(user["password"], password):
                    user["last_login"] = datetime.datetime.now().isoformat()
                    save_users(users)
                    session["username"] = username
                    return redirect(url_for("overview"))

                error = "Невірний логін або пароль"

            else:

                if username in users:
                    error = "Користувач з таким логіном вже існує"

                else:
                    now = datetime.datetime.now().isoformat()
                    users[username] = {
                        "password": generate_password_hash(password),
                        "registered_at": now,
                        "last_login": now
                    }
                    save_users(users)
                    session["username"] = username
                    return redirect(url_for("overview"))

    return render_template("register.html", error=error)


@app.route("/logout")
def logout():

    session.pop("username", None)

    return redirect(url_for("home"))


@app.route("/overview")
def overview():
    # Сторінка 3 — загальний огляд: список усіх книг проєкту
    if "username" not in session:
        return redirect(url_for("register"))

    return render_template(
        "books.html",
        ot_books=OT_BOOKS,
        nt_books=NT_BOOKS,
        username=session["username"],
        is_admin=(session["username"] == ADMIN_USERNAME)
    )


@app.route("/overview/<book>")
def overview_book(book):
    # Сторінка 4 — огляд обраної книги за системою індуктивного вивчення
    if "username" not in session:
        return redirect(url_for("register"))

    if book not in BOOKS:
        return redirect(url_for("overview"))

    return render_template("book_overview.html", book=book)


@app.route("/overview/<book>/notes")
def overview_notes(book):
    # Стара окрема сторінка нотаток об'єднана з детальним оглядом (read_book) —
    # огляд книги тепер заповнюється прямо в бічній панелі поруч із текстом.
    return redirect(url_for("read_book", book=book))


@app.route("/overview/<book>/save", methods=["POST"])
def save_overview(book):
    # Зберігає заповнене дослідження на сервері (щоб підвантажувати назад при
    # відкритті сторінки) і повертає готовий текст файлу — сам файл користувач
    # отримує через звичайне завантаження в браузері (не запис на диск сервера).
    if "username" not in session:
        return jsonify({"error": "Потрібно спочатку увійти"}), 401

    if book not in BOOKS:
        return jsonify({"error": "Книгу не знайдено"}), 404

    data = request.get_json(silent=True) or {}

    note_values = {
        "author": data.get("author", ""),
        "recipients": data.get("recipients", ""),
        "purpose": data.get("purpose", ""),
        "main_idea": data.get("main_idea", ""),
        "key_verse": data.get("key_verse", ""),
        "theme": data.get("theme", ""),
    }

    all_notes = load_notes()
    all_notes[excerpts_key(session["username"], book)] = note_values
    persist_notes(all_notes)

    fields = [
        ("Хто автор", note_values["author"]),
        ("Отримувачі", note_values["recipients"]),
        ("Ціль написання", note_values["purpose"]),
        ("Головна думка (ідея) книги", note_values["main_idea"]),
        ("Ключовий вірш книги", note_values["key_verse"]),
        ("Тема книги", note_values["theme"]),
    ]

    lines = [f"Загальний огляд книги «{book}»", ""]

    for title, value in fields:
        value = (value or "").strip()
        lines.append(title)
        lines.append("-" * len(title))
        lines.append(value if value else "(не заповнено)")
        lines.append("")

    content = "\n".join(lines)

    return jsonify({
        "message": "Огляд книги збережено. Файл завантажується...",
        "filename": "Загальний огляд книги.txt",
        "content": content
    })


@app.route("/overview/<book>/excerpts", methods=["POST"])
def save_excerpts(book):
    # Зберігає список тематичних уривків (розділ:вірш — розділ:вірш),
    # визначених користувачем прямо на сторінці з текстом книги.
    if "username" not in session:
        return jsonify({"error": "Потрібно спочатку увійти"}), 401

    if book not in BOOKS:
        return jsonify({"error": "Книгу не знайдено"}), 404

    data = request.get_json(silent=True) or {}
    total_chapters = BOOK_CHAPTERS.get(book, 1)
    raw_excerpts = data.get("excerpts") or []
    excerpts = []

    for item in raw_excerpts:
        title = (item.get("title") or "").strip()
        if not title:
            continue

        try:
            chapter_from = int(item.get("chapter_from"))
            verse_from = int(item.get("verse_from"))
            chapter_to = int(item.get("chapter_to"))
            verse_to = int(item.get("verse_to"))
        except (TypeError, ValueError):
            continue

        chapter_from = max(1, min(chapter_from, total_chapters))
        chapter_to = max(1, min(chapter_to, total_chapters))
        verse_from = max(1, verse_from)
        verse_to = max(1, verse_to)

        if (chapter_from, verse_from) > (chapter_to, verse_to):
            chapter_from, verse_from, chapter_to, verse_to = (
                chapter_to, verse_to, chapter_from, verse_from
            )

        excerpts.append({
            "title": title,
            "chapter_from": chapter_from,
            "verse_from": verse_from,
            "chapter_to": chapter_to,
            "verse_to": verse_to
        })

    if not excerpts:
        return jsonify({"error": "Додай хоча б один уривок — назву й межі"}), 400

    all_excerpts = load_excerpts()
    all_excerpts[excerpts_key(session["username"], book)] = excerpts
    persist_excerpts(all_excerpts)

    lines = [f"Тематичні уривки книги «{book}»", ""]
    for i, ex in enumerate(excerpts, start=1):
        rng = f"{ex['chapter_from']}:{ex['verse_from']}–{ex['chapter_to']}:{ex['verse_to']}"
        lines.append(f"{i}. {ex['title']} ({rng})")
    content = "\n".join(lines)

    return jsonify({
        "message": f"Збережено уривків: {len(excerpts)}. Список завантажується файлом...",
        "filename": "Тематичні уривки.txt",
        "content": content,
        "excerpts": excerpts
    })


@app.route("/overview/<book>/excerpt/<int:num>")
def read_excerpt(book, num):
    # Детальний огляд одного тематичного уривка (за номером у списку,
    # який користувач створив на сторінці з текстом книги).
    if "username" not in session:
        return redirect(url_for("register"))

    if book not in BOOKS:
        return redirect(url_for("overview"))

    all_excerpts = load_excerpts()
    saved = all_excerpts.get(excerpts_key(session["username"], book), [])

    if not saved:
        return redirect(url_for("read_book", book=book))

    if num < 1 or num > len(saved):
        return redirect(url_for("read_excerpt", book=book, num=1))

    excerpt = saved[num - 1]

    return render_template(
        "excerpt.html",
        book=book,
        num=num,
        total=len(saved),
        excerpt_title=excerpt["title"],
        chapter_from=excerpt["chapter_from"],
        verse_from=excerpt["verse_from"],
        chapter_to=excerpt["chapter_to"],
        verse_to=excerpt["verse_to"]
    )


@app.route("/overview/<book>/excerpt/<int:num>/save", methods=["POST"])
def save_excerpt_notes(book, num):
    # Формує текстовий підсумок прогресу по одному уривку (позначені ключові
    # слова, нотатки, висновки) — файл користувач отримує через завантаження
    # в браузері, щоб кожен крок дослідження можна було зберегти окремо.
    if "username" not in session:
        return jsonify({"error": "Потрібно спочатку увійти"}), 401

    if book not in BOOKS:
        return jsonify({"error": "Книгу не знайдено"}), 404

    all_excerpts = load_excerpts()
    saved = all_excerpts.get(excerpts_key(session["username"], book), [])

    if num < 1 or num > len(saved):
        return jsonify({"error": "Уривок не знайдено"}), 404

    excerpt = saved[num - 1]
    data = request.get_json(silent=True) or {}

    keywords = data.get("keywords") or {}
    notes = data.get("notes") or {}
    conclusions = data.get("conclusions") or {}

    groups = {}
    for word, color in keywords.items():
        if not isinstance(word, str) or not word:
            continue
        groups.setdefault(color, []).append(word)

    rng = f"{excerpt['chapter_from']}:{excerpt['verse_from']}–{excerpt['chapter_to']}:{excerpt['verse_to']}"
    lines = [f"Уривок {num} з {len(saved)}: {excerpt['title']} ({rng})", ""]

    if not groups:
        lines.append("Ключові слова ще не позначені.")
    else:
        for color, words in groups.items():
            lines.append("Ключові слова: " + ", ".join(words))
            note_text = (notes.get(color) or "").strip()
            concl_text = (conclusions.get(color) or "").strip()
            lines.append("Нотатки: " + (note_text if note_text else "(не заповнено)"))
            lines.append("Висновок: " + (concl_text if concl_text else "(не заповнено)"))
            lines.append("")

    content = "\n".join(lines)

    safe_title = "".join(c for c in excerpt["title"] if c not in '\\/:*?"<>|').strip()
    safe_title = safe_title or f"уривок {num}"
    filename = f"Уривок {num} - {safe_title}.txt"

    return jsonify({
        "message": f"Уривок {num} збережено. Файл завантажується...",
        "filename": filename,
        "content": content,
        "is_last": num >= len(saved),
        "next_num": (num + 1) if num < len(saved) else None
    })


@app.route("/overview/<book>/excerpt/<int:num>/text")
def excerpt_text(book, num):
    # JSON з текстом одного уривка для сторінки excerpt.html
    if "username" not in session:
        return jsonify({"error": "Потрібно спочатку увійти"}), 401

    if book not in BOOKS:
        return jsonify({"error": "Книгу не знайдено"}), 404

    all_excerpts = load_excerpts()
    saved = all_excerpts.get(excerpts_key(session["username"], book), [])

    if num < 1 or num > len(saved):
        return jsonify({"error": "Уривок не знайдено"}), 404

    excerpt = saved[num - 1]
    result = get_verse_range(
        book,
        excerpt["chapter_from"],
        excerpt["verse_from"],
        excerpt["chapter_to"],
        excerpt["verse_to"]
    )

    if "error" in result:
        return jsonify(result), 502

    return jsonify(result)


@app.route("/overview/<book>/read")
def read_book(book):
    # Детальний огляд у контексті "Загального огляду" — повний текст книги
    # з бічною панеллю, що об'єднує 1) "Огляд книги" (нотатки: автор,
    # отримувачі, ціль тощо) і 2) "Тематичні уривки" (поділ за розділом/віршем).
    if "username" not in session:
        return redirect(url_for("register"))

    if book not in BOOKS:
        return redirect(url_for("overview"))

    all_excerpts = load_excerpts()
    saved = all_excerpts.get(excerpts_key(session["username"], book), [])

    all_notes = load_notes()
    saved_notes = all_notes.get(excerpts_key(session["username"], book), {})

    return render_template(
        "read.html",
        book=book,
        total_chapters=BOOK_CHAPTERS.get(book, 1),
        saved_excerpts=saved,
        saved_notes=saved_notes
    )


@app.route("/overview/<book>/full-text")
def full_text(book):
    # JSON з усім текстом книги для сторінки read.html
    if "username" not in session:
        return jsonify({"error": "Потрібно спочатку увійти"}), 401

    if book not in BOOKS:
        return jsonify({"error": "Книгу не знайдено"}), 404

    result = get_full_book(book)

    if "error" in result:
        return jsonify(result), 502

    return jsonify(result)


@app.route("/detail")
def detail():
    # Детальний огляд — сторінка пошуку конкретного вірша.
    # Якщо прийшли з огляду книги (?book=...), одразу підставляємо цю книгу в список.
    selected_book = request.args.get("book")

    return render_template(
        "overview.html",
        book_order=BOOK_ORDER,
        selected_book=selected_book
    )


@app.route("/verse", methods=["POST"])
def verse():

    data = request.get_json(silent=True) or {}

    book = data.get("book")
    if not book:
        return jsonify({"text": "Не вказано книгу"}), 400

    try:
        chapter = int(data.get("chapter"))
    except (TypeError, ValueError):
        return jsonify({"text": "Розділ повинен бути числом"}), 400

    try:
        verse_from = int(data.get("verse", 1))
    except (TypeError, ValueError):
        return jsonify({"text": "Вірш повинен бути числом"}), 400

    verse_to_raw = data.get("verse_to")
    verse_to = None
    if verse_to_raw not in (None, ""):
        try:
            verse_to = int(verse_to_raw)
        except (TypeError, ValueError):
            return jsonify({"text": "Кінцевий вірш повинен бути числом"}), 400

    if verse_to and verse_to < verse_from:
        return jsonify({"text": "Кінцевий вірш не може бути меншим за початковий"}), 400

    if verse_to and verse_to >= verse_from:

        result = get_verses(
            book,
            chapter,
            verse_from,
            verse_to
        )

        if "error" in result:
            return jsonify({"text": result["error"]})

        return jsonify({
            "verses": result["verses"]
        })

    text = get_verse(
        book,
        chapter,
        verse_from
    )

    return jsonify({
        "text": text
    })


def _format_dt(value):
    # Приводить ISO-дату/час у зрозумілий вигляд для адмін-панелі;
    # порожнє/відсутнє значення показуємо як "—".
    if not value:
        return "—"
    try:
        dt = datetime.datetime.fromisoformat(value)
        return dt.strftime("%d.%m.%Y %H:%M")
    except (TypeError, ValueError):
        return value


def _parse_dt(value):
    if not value:
        return None
    try:
        return datetime.datetime.fromisoformat(value)
    except (TypeError, ValueError):
        return None


def _build_user_books(all_excerpts, all_notes):
    # Книги, якими займається кожен користувач — зі списку уривків і нотаток
    # огляду (ключі мають формат "логін::назва книги").
    user_books = {}

    for key, excerpts in all_excerpts.items():
        if "::" not in key:
            continue
        username, book = key.split("::", 1)
        entry = user_books.setdefault(username, {}).setdefault(
            book, {"excerpts": 0, "has_overview": False}
        )
        entry["excerpts"] = len(excerpts)

    NOTE_FIELDS = ["author", "recipients", "purpose", "main_idea", "key_verse", "theme"]
    for key, note_values in all_notes.items():
        if "::" not in key:
            continue
        username, book = key.split("::", 1)
        entry = user_books.setdefault(username, {}).setdefault(
            book, {"excerpts": 0, "has_overview": False}
        )
        entry["has_overview"] = any((note_values.get(f) or "").strip() for f in NOTE_FIELDS)

    return user_books


def _visits_chart_data(analytics, days=14):
    # Останні N днів (включно з сьогодні) для стовпчикового графіка відвідувань.
    visits_by_date = analytics.get("visits_by_date", {})
    today = datetime.date.today()
    counts = []
    for i in range(days - 1, -1, -1):
        d = today - datetime.timedelta(days=i)
        counts.append((d, visits_by_date.get(d.isoformat(), 0)))
    max_count = max((c for _, c in counts), default=0) or 1
    return [
        {
            "date": d.isoformat(),
            "label": d.strftime("%d.%m"),
            "count": c,
            "pct": round(c / max_count * 100)
        }
        for d, c in counts
    ]


def _book_popularity(user_books):
    stats = {}
    for username, books in user_books.items():
        for book, data in books.items():
            entry = stats.setdefault(book, {"book": book, "users": 0, "excerpts": 0})
            entry["users"] += 1
            entry["excerpts"] += data["excerpts"]
    return sorted(stats.values(), key=lambda s: (-s["users"], -s["excerpts"], s["book"]))


@app.route("/admin")
def admin_dashboard():
    # Сторінка статистики — доступна лише під логіном ADMIN_USERNAME.
    if session.get("username") != ADMIN_USERNAME:
        if "username" in session:
            return redirect(url_for("overview"))
        return redirect(url_for("register"))

    users = load_users()
    all_excerpts = load_excerpts()
    all_notes = load_notes()
    analytics = load_analytics()

    user_books = _build_user_books(all_excerpts, all_notes)

    user_rows = []
    for username, info in users.items():
        books = user_books.get(username, {})
        book_list = [
            {"book": book, "excerpts": data["excerpts"], "has_overview": data["has_overview"]}
            for book, data in sorted(books.items())
        ]
        registered_dt = _parse_dt(info.get("registered_at"))
        last_login_dt = _parse_dt(info.get("last_login"))
        user_rows.append({
            "username": username,
            "is_admin": username == ADMIN_USERNAME,
            "registered_at": _format_dt(info.get("registered_at")),
            "registered_sort": registered_dt.timestamp() if registered_dt else 0,
            "last_login": _format_dt(info.get("last_login")),
            "last_login_sort": last_login_dt.timestamp() if last_login_dt else 0,
            "books": book_list,
            "books_count": len(book_list)
        })

    user_rows.sort(key=lambda r: r["username"].lower())

    today = datetime.date.today().isoformat()
    visits_by_date = analytics.get("visits_by_date", {})

    week_ago = datetime.datetime.now() - datetime.timedelta(days=7)
    new_users_7d = 0
    recent_users = []
    for username, info in users.items():
        dt = _parse_dt(info.get("registered_at"))
        recent_users.append((username, dt))
        if dt and dt >= week_ago:
            new_users_7d += 1
    recent_users.sort(key=lambda item: item[1] or datetime.datetime.min, reverse=True)
    recent_users = [
        {"username": u, "registered_at": _format_dt(dt.isoformat()) if dt else "—"}
        for u, dt in recent_users[:5]
    ]

    return render_template(
        "admin.html",
        total_users=len(users),
        total_visits=analytics.get("total_visits", 0),
        unique_visitors=len(analytics.get("unique_visitors", [])),
        visits_today=visits_by_date.get(today, 0),
        users_studying=len([r for r in user_rows if r["books_count"] > 0]),
        total_books_in_progress=sum(r["books_count"] for r in user_rows),
        new_users_7d=new_users_7d,
        recent_users=recent_users,
        visits_chart=_visits_chart_data(analytics),
        book_stats=_book_popularity(user_books),
        user_rows=user_rows,
        admin_username=ADMIN_USERNAME,
        deleted_user=request.args.get("deleted"),
        delete_error=request.args.get("delete_error")
    )


@app.route("/admin/users/<username>/delete", methods=["POST"])
def admin_delete_user(username):
    # Видаляє користувача та всі його дані (уривки, огляд книг).
    # Самого адміністратора видалити не можна — щоб не втратити доступ до панелі.
    if session.get("username") != ADMIN_USERNAME:
        if "username" in session:
            return redirect(url_for("overview"))
        return redirect(url_for("register"))

    if username == ADMIN_USERNAME:
        return redirect(url_for("admin_dashboard", delete_error="Не можна видалити обліковий запис адміністратора"))

    users = load_users()
    if username not in users:
        return redirect(url_for("admin_dashboard", delete_error="Користувача не знайдено"))

    del users[username]
    save_users(users)

    prefix = f"{username}::"

    all_excerpts = load_excerpts()
    for key in [k for k in all_excerpts if k.startswith(prefix)]:
        del all_excerpts[key]
    persist_excerpts(all_excerpts)

    all_notes = load_notes()
    for key in [k for k in all_notes if k.startswith(prefix)]:
        del all_notes[key]
    persist_notes(all_notes)

    return redirect(url_for("admin_dashboard", deleted=username))


if __name__ == "__main__":

    app.run(
        debug=True
    )
