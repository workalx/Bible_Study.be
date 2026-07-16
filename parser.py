import os
import json
import concurrent.futures

import requests
from bs4 import BeautifulSoup


BOOKS = {

    # Старий Заповіт

    "Буття": 1,
    "Вихід": 2,
    "Левит": 3,
    "Числа": 4,
    "Повторення Закону": 5,

    "Ісус Навин": 6,
    "Суддів": 7,
    "Рут": 8,

    "1 Самуїла": 9,
    "2 Самуїла": 10,
    "1 Царів": 11,
    "2 Царів": 12,

    "1 Хронік": 13,
    "2 Хронік": 14,

    "Ездри": 15,
    "Неемії": 16,
    "Естер": 17,

    "Йова": 18,
    "Псалом": 19,
    "Приповісті": 20,
    "Екклезіяста": 21,
    "Пісня над піснями": 22,

    "Ісаї": 23,
    "Єремії": 24,
    "Плач Єремії": 25,
    "Єзекіїля": 26,
    "Даниїла": 27,

    "Осії": 28,
    "Йоїла": 29,
    "Амоса": 30,
    "Овдія": 31,
    "Йони": 32,
    "Михея": 33,
    "Наума": 34,
    "Авакума": 35,
    "Софонії": 36,
    "Огія": 37,
    "Захарії": 38,
    "Малахії": 39,


    # Новий Заповіт

    "Матвія": 40,
    "Марка": 41,
    "Луки": 42,
    "Івана": 43,

    "Дії": 44,

    "Римлян": 52,
    "1 Коринтян": 53,
    "2 Коринтян": 54,
    "Галатів": 55,
    "Ефесян": 56,
    "Филип'ян": 57,
    "Колосян": 58,

    "1 Солунян": 59,
    "2 Солунян": 60,

    "1 Тимофія": 61,
    "2 Тимофія": 62,
    "Тита": 63,
    "Филимона": 64,

    "Євреїв": 65,
    "Якова": 45,

    "1 Петра": 46,
    "2 Петра": 47,

    "1 Івана": 48,
    "2 Івана": 49,
    "3 Івана": 50,

    "Юди": 51,

    "Об'явлення": 66
}


# Порядок книг для відображення у списку (Старий Заповіт, потім Новий) —
# такий самий порядок, що й у випадаючому списку на сторінці пошуку.
OT_BOOKS = [
    "Буття", "Вихід", "Левит", "Числа", "Повторення Закону",
    "Ісус Навин", "Суддів", "Рут",
    "1 Самуїла", "2 Самуїла", "1 Царів", "2 Царів",
    "1 Хронік", "2 Хронік",
    "Ездри", "Неемії", "Естер",
    "Йова", "Псалом", "Приповісті", "Екклезіяста", "Пісня над піснями",
    "Ісаї", "Єремії", "Плач Єремії", "Єзекіїля", "Даниїла",
    "Осії", "Йоїла", "Амоса", "Овдія", "Йони", "Михея",
    "Наума", "Авакума", "Софонії", "Огія", "Захарії", "Малахії",
]

NT_BOOKS = [
    "Матвія", "Марка", "Луки", "Івана",
    "Дії",
    "Римлян", "1 Коринтян", "2 Коринтян", "Галатів", "Ефесян",
    "Филип'ян", "Колосян",
    "1 Солунян", "2 Солунян",
    "1 Тимофія", "2 Тимофія", "Тита", "Филимона",
    "Євреїв", "Якова",
    "1 Петра", "2 Петра",
    "1 Івана", "2 Івана", "3 Івана",
    "Юди",
    "Об'явлення",
]

BOOK_ORDER = OT_BOOKS + NT_BOOKS


# Стандартна кількість розділів у кожній книзі — потрібна, щоб знати,
# скільки розділів завантажувати для повного тексту книги.
BOOK_CHAPTERS = {
    "Буття": 50, "Вихід": 40, "Левит": 27, "Числа": 36, "Повторення Закону": 34,
    "Ісус Навин": 24, "Суддів": 21, "Рут": 4,
    "1 Самуїла": 31, "2 Самуїла": 24, "1 Царів": 22, "2 Царів": 25,
    "1 Хронік": 29, "2 Хронік": 36,
    "Ездри": 10, "Неемії": 13, "Естер": 10,
    "Йова": 42, "Псалом": 150, "Приповісті": 31, "Екклезіяста": 12, "Пісня над піснями": 8,
    "Ісаї": 66, "Єремії": 52, "Плач Єремії": 5, "Єзекіїля": 48, "Даниїла": 12,
    "Осії": 14, "Йоїла": 3, "Амоса": 9, "Овдія": 1, "Йони": 4, "Михея": 7,
    "Наума": 3, "Авакума": 3, "Софонії": 3, "Огія": 2, "Захарії": 14, "Малахії": 4,
    "Матвія": 28, "Марка": 16, "Луки": 24, "Івана": 21,
    "Дії": 28,
    "Римлян": 16, "1 Коринтян": 16, "2 Коринтян": 13, "Галатів": 6, "Ефесян": 6,
    "Филип'ян": 4, "Колосян": 4,
    "1 Солунян": 5, "2 Солунян": 3,
    "1 Тимофія": 6, "2 Тимофія": 4, "Тита": 3, "Филимона": 1,
    "Євреїв": 13, "Якова": 5,
    "1 Петра": 5, "2 Петра": 3,
    "1 Івана": 5, "2 Івана": 1, "3 Івана": 1,
    "Юди": 1,
    "Об'явлення": 22,
}

CACHE_DIR = os.path.join(os.path.dirname(__file__), "book_cache")


def _fetch_chapter(book, chapter):
    """Завантажує сторінку розділу і повертає (soup, error).

    Якщо сталася помилка (немає книги, немає з'єднання, таймаут тощо),
    soup буде None, а error міститиме текст повідомлення для користувача.
    """

    if book not in BOOKS:
        return None, "Книгу не знайдено"

    book_id = BOOKS[book]

    url = f"https://bible.net.ua/translation/ubo/{book_id}/{chapter}/"

    try:
        response = requests.get(url, timeout=15)
    except requests.exceptions.RequestException:
        return None, "Помилка підключення"

    if response.status_code != 200:
        return None, "Помилка підключення"

    return BeautifulSoup(response.text, "html.parser"), None


def get_verse(book, chapter, verse):

    soup, error = _fetch_chapter(book, chapter)

    if error:
        return error

    numbers = soup.find_all(
        "div",
        class_="col-xs-1 text-end"
    )

    for number_div in numbers:

        a = number_div.find("a")

        if a and a.get_text(strip=True) == str(verse):

            verse_div = number_div.find_next_sibling(
                "div",
                class_="col-xs-11 text-verse"
            )

            if verse_div:
                return verse_div.get_text(
                    " ",
                    strip=True
                )

    return "Вірш не знайдено"


def get_verses(book, chapter, verse_from, verse_to):

    soup, error = _fetch_chapter(book, chapter)

    if error:
        return {"error": error}

    numbers = soup.find_all(
        "div",
        class_="col-xs-1 text-end"
    )

    result = []
    current_verse = 1

    for number_div in numbers:

        a = number_div.find("a")
        a_text = a.get_text(strip=True) if a else ""

        if a_text.isdigit():
            current_verse = int(a_text)

        if current_verse >= verse_from and current_verse <= verse_to:

            verse_div = number_div.find_next_sibling(
                "div",
                class_="col-xs-11 text-verse"
            )

            if verse_div:
                text = verse_div.get_text(" ", strip=True)
                result.append({
                    "number": current_verse,
                    "text": text
                })

    if not result:
        return {"error": "Вірші не знайдено"}

    return {"verses": result}


def get_full_book(book):
    """Завантажує ввесь текст книги (усі розділи, усі вірші).

    Розділи завантажуються паралельно (мережевий I/O, тож потоки тут
    цілком доречні), а результат кешується у JSON-файл — щоб повторне
    відкриття тієї самої книги було миттєвим і не робило десятки
    запитів до сайту заново.
    """

    if book not in BOOKS:
        return {"error": "Книгу не знайдено"}

    total_chapters = BOOK_CHAPTERS.get(book)
    if not total_chapters:
        return {"error": "Невідома кількість розділів для цієї книги"}

    os.makedirs(CACHE_DIR, exist_ok=True)
    cache_path = os.path.join(CACHE_DIR, f"{book}.json")

    if os.path.exists(cache_path):
        try:
            with open(cache_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (OSError, json.JSONDecodeError):
            pass  # кеш пошкоджено — завантажимо наново

    def fetch_one(chapter):
        return chapter, get_verses(book, chapter, 1, 9999)

    chapters = {}

    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
        futures = [
            executor.submit(fetch_one, chapter)
            for chapter in range(1, total_chapters + 1)
        ]
        for future in concurrent.futures.as_completed(futures):
            chapter, result = future.result()
            if "error" not in result:
                chapters[chapter] = result["verses"]

    if not chapters:
        return {"error": "Не вдалося завантажити текст книги"}

    data = {
        "chapters": [
            {"chapter": ch, "verses": chapters[ch]}
            for ch in sorted(chapters.keys())
        ]
    }

    try:
        with open(cache_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False)
    except OSError:
        pass  # кешування не критичне — просто повернемо результат без нього

    return data


def get_verse_range(book, chapter_from, verse_from, chapter_to, verse_to):
    """Завантажує текст точного діапазону "розділ:вірш" — "розділ:вірш"
    (для тематичного уривка). Діапазон може охоплювати кілька розділів:
    у першому розділі беремо від verse_from і до кінця, у проміжних —
    розділи цілком, в останньому — від початку і до verse_to.
    """

    if book not in BOOKS:
        return {"error": "Книгу не знайдено"}

    verse_from = verse_from or 1
    verse_to = verse_to or 9999

    if (chapter_from, verse_from) > (chapter_to, verse_to):
        chapter_from, verse_from, chapter_to, verse_to = (
            chapter_to, verse_to, chapter_from, verse_from
        )

    if chapter_from == chapter_to:
        tasks = [(chapter_from, verse_from, verse_to)]
    else:
        tasks = [(chapter_from, verse_from, 9999)]
        for ch in range(chapter_from + 1, chapter_to):
            tasks.append((ch, 1, 9999))
        tasks.append((chapter_to, 1, verse_to))

    def fetch_one(task):
        ch, vf, vt = task
        return ch, get_verses(book, ch, vf, vt)

    chapters = {}

    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
        futures = [executor.submit(fetch_one, t) for t in tasks]
        for future in concurrent.futures.as_completed(futures):
            ch, result = future.result()
            if "error" not in result:
                chapters[ch] = result["verses"]

    if not chapters:
        return {"error": "Не вдалося завантажити текст уривку"}

    return {
        "chapters": [
            {"chapter": ch, "verses": chapters[ch]}
            for ch in sorted(chapters.keys())
        ]
    }
