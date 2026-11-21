"""Render a provider's selected references using only current server-side facts."""

import re
from typing import Any
from uuid import UUID

from app.ai.assistant.contracts import AnswerPlan, Language
from app.ai.assistant.tools import ToolContext, excerpt
from app.schemas.catalog import BookRead

# Keep the surrounding answer in the reader's language. Catalog text stays verbatim.
MESSAGES = {
    "clarify_topic": (
        "Қай тақырыптағы кітапты іздеп жүрсіз?",
        "Книги на какую тему вас интересуют?",
        "What subject would you like to read about?",
    ),
    "clarify_language": (
        "Кітапты қай тілде оқығыңыз келеді?",
        "На каком языке вы хотите читать?",
        "Which language would you like to read in?",
    ),
    "clarify_availability": (
        "Қазір алуға болатын кітаптарды ғана көрсетейін бе?",
        "Показать только книги, которые можно взять сейчас?",
        "Would you like to see only books you can borrow now?",
    ),
    "unsupported": (
        "Кітап табуға, қолыңыздағы кітаптар мен броньдарды тексеруге немесе кітапхана "
        "ережелерін білуге көмектесе аламын. Кітапты беру мен қайтаруды кітапханашы рәсімдейді.",
        "Я могу найти книгу, проверить ваши выдачи и брони или подсказать правила библиотеки. "
        "Выдачу и возврат книг оформляет библиотекарь.",
        "I can find books, check your loans and reservations, or explain library rules. "
        "A librarian handles checkouts and returns.",
    ),
    "unavailable": (
        "Сұралған деректер қазір қолжетімсіз. Кейінірек қайталап көріңіз.",
        "Запрошенные данные временно недоступны. Попробуйте позже.",
        "The requested records are temporarily unavailable. Please try again later.",
    ),
    "empty": (
        "Каталогтан сұрауыңызға сай кітап табылмады.",
        "В каталоге не нашлось книг по вашему запросу.",
        "I couldn't find a book matching your request in the catalog.",
    ),
    "no_selection": (
        "Іздеу нәтижелерінің ішінен сұрауыңызға сай кітап таба алмадым.",
        "Среди результатов поиска не удалось подобрать книгу по вашему запросу.",
        "I couldn't identify a matching book among the search results.",
    ),
    "more_hits": (
        "Каталогтан {total} нәтиже табылды. Іріктеу үшін алғашқы {count} нәтиже қаралды.",
        "Поиск по каталогу дал результатов: {total}. Для подбора просмотрены первые {count}.",
        "The catalog search returned {total} entries. The first {count} were considered.",
    ),
    "no_recommendations": (
        "Әзірге ұсынуға лайық кітап табылмады.",
        "Пока не удалось подобрать книгу для рекомендации.",
        "I couldn't find a book to recommend this time.",
    ),
    "indexing": (
        "Кейбір кітаптар мағыналық іздеу индексіне әлі қосылған жоқ.",
        "Часть книг ещё не включена в индекс смыслового поиска.",
        "Some books have yet to be indexed for semantic search.",
    ),
    "copies": (
        "Қорда {total} дана, қазір қолжетімдісі — {available} дана.",
        "Всего экземпляров — {total}, доступно сейчас — {available}.",
        "Physical copies: {total}. Available now: {available}.",
    ),
    "no_copies": (
        "Кітап каталогта тіркелген. Физикалық данасы жоқ.",
        "Книга есть в каталоге. Физических экземпляров нет.",
        "The book is in the catalog. There are no physical copies.",
    ),
    "shelves": ("Қолжетімді даналардың орны", "Расположение доступных экземпляров", "Shelves"),
    "unknown_shelf": (
        "Қолжетімді дананың қай сөреде тұрғаны каталогта көрсетілмеген.",
        "Полка для доступных экземпляров не указана в каталоге.",
        "The catalog does not list a shelf for the available copies.",
    ),
    "categories": ("Санаты", "Категория", "Category"),
    "description": ("Каталогтағы сипаттамасы", "Описание в каталоге", "Catalog description"),
    "year": ("Шыққан жылы", "Год издания", "Year published"),
    "language": ("Тілі", "Язык", "Language"),
    "kk": ("қазақша", "казахский", "Kazakh"),
    "ru": ("орысша", "русский", "Russian"),
    "en": ("ағылшынша", "английский", "English"),
    "matched_title": (
        "Кітап атауында «{value}» кездеседі.",
        "В названии книги есть «{value}».",
        "The title mentions “{value}”.",
    ),
    "matched_description": (
        "Каталогтағы сипаттамада «{value}» кездеседі.",
        "В описании книги есть «{value}».",
        "The catalog description mentions “{value}”.",
    ),
    "matched_author": (
        "Авторы — сіз іздеген {value}.",
        "Автор книги — {value}.",
        "It is by the author you searched for, {value}.",
    ),
    "matched_category": (
        "Каталогта «{value}» санатына кіреді.",
        "В каталоге книга отнесена к категории «{value}».",
        "The catalog lists it under “{value}”.",
    ),
    "semantic": (
        "Каталогтағы мағыналық іздеу осы кітапты тақырыбыңызға жақын деп тапты.",
        "Смысловой поиск по каталогу подобрал эту книгу по теме запроса.",
        "Semantic search matched this catalog entry to your topic.",
    ),
    "catalog_match": (
        "Каталог бұл кітапты «{value}» деген сұрау бойынша тапты.",
        "Каталог подобрал эту книгу по запросу «{value}».",
        "The catalog search returned this book for “{value}”.",
    ),
    "popular": (
        "Басқа оқырмандардың осы кітапқа қызығушылығы ескерілді.",
        "При подборе учтён интерес читателей к этой книге.",
        "The selection reflects readers’ interest in this book.",
    ),
    "recent": (
        "Қорға қосылған уақыты бойынша таңдалды.",
        "Подобрана по дате добавления в каталог.",
        "It was selected by date added to the catalog.",
    ),
    "similar": (
        "Мазмұны сіз таңдаған кітапқа ұқсас.",
        "По содержанию похожа на выбранную вами книгу.",
        "Its content is similar to the book you selected.",
    ),
    "history": (
        "Оқу тарихыңызға сүйеніп таңдалды.",
        "Подобрана с учётом вашей истории чтения.",
        "It was selected based on your reading history.",
    ),
    "preferences": (
        "Оқу талғамыңызға сай таңдалды.",
        "Подобрана с учётом ваших читательских предпочтений.",
        "It was selected based on your reading preferences.",
    ),
    "loans": (
        "Қолыңыздағы кітап саны — {total}. Бет: {page}.",
        "Книг у вас на руках: {total}. Страница {page}.",
        "Books on loan: {total}. Page {page}.",
    ),
    "due": (
        "«{title}» — қайтару мерзімі {due_at}.",
        "«{title}» — срок возврата {due_at}.",
        "“{title}” is due {due_at}.",
    ),
    "overdue": ("Мерзімі өткен.", "Срок прошёл.", "Overdue."),
    "reservations": (
        "Белсенді бронь саны — {total}. Бет: {page}.",
        "Активных броней: {total}. Страница {page}.",
        "Active reservations: {total}. Page {page}.",
    ),
    "ready": ("алуға дайын", "готова к выдаче", "ready for pickup"),
    "waiting": ("кезекте", "в очереди", "on the waiting list"),
    "expired": ("алу мерзімі аяқталған", "срок получения истёк", "pickup period ended"),
    "position": (
        "Кезектегі орныңыз — {number}.",
        "Место в очереди: {number}.",
        "Position: {number}.",
    ),
    "rules": (
        "Кітап {borrow_period_days} күнге беріледі. Бір мезетте {max_books_per_user} кітап алуға "
        "болады. Бронь дайын болған соң {reservation_hold_hours} сағат сақталады. Еске салу "
        "хабарламасы қайтару мерзіміне {return_reminder_days} күн қалғанда жіберіледі.",
        "Срок выдачи — {borrow_period_days} дн. Можно взять до {max_books_per_user} книг "
        "одновременно. Готовая бронь хранится {reservation_hold_hours} ч. Напоминание приходит "
        "за {return_reminder_days} дн. до возврата.",
        "The loan period is {borrow_period_days} days, with up to {max_books_per_user} books at "
        "a time. Ready reservations are held for {reservation_hold_hours} hours. A reminder is "
        "sent {return_reminder_days} days before a book is due.",
    ),
    "overdue_policy": (
        "Мерзімі өткен кітап болса, жаңа кітап алуға {borrow}, бронь жасауға {reserve}.",
        "При просрочке брать новые книги {borrow}, бронировать {reserve}.",
        "With overdue loans, new checkouts are {borrow} and reservations are {reserve}.",
    ),
    "allowed": ("болады", "можно", "allowed"),
    "blocked": ("болмайды", "нельзя", "blocked"),
}


def phrase(language: Language, key: str, **values: Any) -> str:
    return MESSAGES[key][("kk", "ru", "en").index(language)].format(**values)


def reason_for(book: BookRead, source: dict[str, Any], row: dict[str, Any], lang: Language) -> str:
    if "reason" in row:
        return phrase(lang, row["reason"])
    query = source.get("q", "").strip()
    if query:
        for field, values in (
            ("matched_category", [category.name for category in book.categories]),
            ("matched_title", [book.title]),
            ("matched_author", [author.full_name for author in book.authors]),
            ("matched_description", [book.description or ""]),
        ):
            for value in values:
                if match := re.search(re.escape(query), value, re.IGNORECASE):
                    specific = (
                        value if field in {"matched_author", "matched_category"} else match[0]
                    )
                    return phrase(lang, field, value=specific)
    if source["tool"] == "semantic_search_books":
        return phrase(lang, "semantic")
    if book.categories:
        return phrase(lang, "matched_category", value=book.categories[0].name)
    if query:
        return phrase(lang, "catalog_match", value=query)
    return ""


def book_text(book: BookRead, source: dict[str, Any], row: dict[str, Any], plan: AnswerPlan) -> str:
    lang = plan.language
    authors = ", ".join(author.full_name for author in book.authors)
    lines = [f"«{book.title}»" + (f" — {authors}" if authors else "")]
    details = plan.presentation == "details" or (
        plan.presentation == "search" and source["tool"] == "get_book_details"
    )
    recommend = plan.presentation == "recommendation" or "reason" in row
    if details:
        categories = ", ".join(category.name for category in book.categories)
        language = (
            phrase(lang, book.language) if book.language in {"kk", "ru", "en"} else book.language
        )
        for label, value in [
            (phrase(lang, "categories"), categories),
            (phrase(lang, "year"), book.publication_year),
            ("ISBN", book.isbn),
            (phrase(lang, "language"), language),
        ]:
            if value:
                lines.append(f"{label}: {value}")
    if recommend and (reason := reason_for(book, source, row, lang)):
        lines.append(reason)
    if (recommend or details) and book.description:
        lines.append(
            f"{phrase(lang, 'description')}: {excerpt(book.description, source.get('q', ''))}"
        )
    if (
        details
        or plan.presentation == "availability"
        or source["tool"] == "check_book_availability"
    ):
        lines.append(
            phrase(lang, "copies", total=book.total_copies, available=book.available_copies)
            if book.total_copies
            else phrase(lang, "no_copies")
        )
        if book.shelf_locations:
            lines.append(f"{phrase(lang, 'shelves')}: {', '.join(book.shelf_locations)}")
        elif book.available_copies:
            lines.append(phrase(lang, "unknown_shelf"))
    return "\n".join(lines)


def evidence_text(result: dict[str, Any], lang: Language, has_books: bool) -> str:
    if result.get("error"):
        return phrase(lang, "unavailable")
    if "rules" in result:
        policy = result["rules"]
        borrow = phrase(lang, "blocked" if policy["block_borrowing_if_overdue"] else "allowed")
        reserve = phrase(lang, "blocked" if policy["block_reservation_if_overdue"] else "allowed")
        return (
            phrase(lang, "rules", **policy)
            + " "
            + phrase(lang, "overdue_policy", borrow=borrow, reserve=reserve)
        )
    if "loans" in result:
        lines = [phrase(lang, "loans", **result)]
        for loan in result["loans"]:
            line = phrase(lang, "due", **loan)
            lines.append(line + (" " + phrase(lang, "overdue") if loan["overdue"] else ""))
        return "\n".join(lines)
    if "reservations" in result:
        lines = [phrase(lang, "reservations", **result)]
        for reservation in result["reservations"]:
            state = phrase(lang, reservation["state"])
            line = f"«{reservation['title']}» — {state}."
            if reservation["queue_position"] is not None:
                line += " " + phrase(lang, "position", number=reservation["queue_position"])
            lines.append(line)
        return "\n".join(lines)
    if result["tool"] == "search_books" and result.get("total", 0) > len(result["books"]):
        count = phrase(lang, "more_hits", total=result["total"], count=len(result["books"]))
        return count if has_books else phrase(lang, "no_selection") + " " + count
    if has_books:
        return ""
    if result["tool"] in {"get_similar_books", "get_recommendations"}:
        return phrase(lang, "no_recommendations")
    return phrase(lang, "no_selection" if result["books"] else "empty")


def render(plan: AnswerPlan, context: ToolContext) -> tuple[str, list[BookRead]]:
    if plan.kind != "results":
        return phrase(plan.language, plan.kind), []
    sources = {
        row["ref"]: (result, row)
        for result in context.results.values()
        for row in result.get("books", [])
    }
    selected = list(plan.book_refs)
    results = [context.results[ref] for ref in dict.fromkeys(plan.evidence_refs)]
    if not selected:
        for result in results:
            if result["tool"] in {"get_book_details", "check_book_availability"}:
                selected.extend(row["ref"] for row in result.get("books", []))
    books: dict[UUID, BookRead] = {}
    entries = []
    for ref in selected:
        book = context.books[ref]
        if book.id not in books:
            source, row = sources[ref]
            entries.append(book_text(book, source, row, plan))
            books[book.id] = book
    summaries = [evidence_text(result, plan.language, bool(books)) for result in results]
    if any(result.get("indexing_pending") for result in results):
        summaries.append(phrase(plan.language, "indexing"))
    paragraphs = [text for text in dict.fromkeys(summaries) if text]
    return "\n\n".join([*entries, *paragraphs]), list(books.values())
