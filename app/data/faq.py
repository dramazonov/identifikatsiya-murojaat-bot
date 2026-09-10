"""Static FAQ content for the "❓ Тайёр савол-жавоблар" section.

``FAQ_CATEGORIES`` is an ordered list of categories, each with an ``id``
(used as a compact callback_data identifier), a display ``title``, and a
list of ``questions`` (each a {"question", "answer"} dict, optionally with
a ``related_documents`` list of ids from ``app.data.documents.DOCUMENTS``).

This is sample/placeholder content for Stage 6. None of the answers cite a
specific law or decree number -- wherever the exact legal basis isn't given,
the neutral phrase "амалдаги қонунчиликка мувофиқ" ("in accordance with the
current legislation") is used instead of inventing one.

``related_documents`` was added in Stage 8 to point a question at one or
more real documents from ``app.data.documents`` -- only where that link is
genuinely about the document's subject. It never cites a specific
article/paragraph, since the acts weren't inspected at that level of
detail; the FAQ handler renders it as a "📌 Асос: ..." line plus a button
to open the document.
"""

from __future__ import annotations

FAQ_CATEGORIES: list[dict] = [
    {
        "id": "identification",
        "title": "🐄 Ҳайвонларни идентификация қилиш",
        "questions": [
            {
                "question": "Ҳайвонларни идентификация қилиш нима?",
                "answer": (
                    "Ҳайвонларни идентификация қилиш — ҳайвонни белгиланган тартибда "
                    "идентификация рақами бериш, маълумотларини ахборот тизимида қайд "
                    "этиш ва унинг ҳаракати ҳамда ҳолатини кузатиш имконини берувчи "
                    "жараён."
                ),
                "related_documents": ["orq_1079"],
            },
            {
                "question": "Ҳайвонни идентификация қилиш нима учун керак?",
                "answer": (
                    "Идентификация ҳайвоннинг эгаси, тури, жинси, ёши ва бошқа зарур "
                    "маълумотларини ҳисобга олиш, ҳайвонлар ҳаракатини кузатиш ҳамда "
                    "ветеринария назоратини самарали ташкил этиш учун амалга оширилади."
                ),
                "related_documents": ["orq_1079"],
            },
            {
                "question": "Ҳайвонни қандай идентификация қилиш мумкин?",
                "answer": (
                    "Ҳайвонларни идентификация қилиш белгиланган тартибда идентификация "
                    "воситалари орқали амалга оширилади. Аниқ тартиб ва талаблар амалдаги "
                    "қонунчилик ҳужжатларига мувофиқ белгиланади."
                ),
                "related_documents": ["orq_1079", "qm_748"],
            },
        ],
    },
    {
        "id": "registration",
        "title": "📋 Рўйхатдан ўтказиш ва ҳисобдан чиқариш",
        "questions": [
            {
                "question": "Ҳайвон сўйилса нима қилиш керак?",
                "answer": "Ҳайвон сўйилганда уни белгиланган тартибда ҳисобдан чиқариш учун мурожаат қилиш лозим.",
                "related_documents": ["qm_748"],
            },
            {
                "question": "Ҳайвон нобуд бўлса нима қилиш керак?",
                "answer": "Ҳайвон нобуд бўлган тақдирда уни белгиланган тартибда ҳисобдан чиқариш учун мурожаат қилиш лозим.",
                "related_documents": ["qm_748"],
            },
            {
                "question": "Янги туғилган ҳайвонни қачон рўйхатдан ўтказиш керак?",
                "answer": (
                    "Янги туғилган ҳайвонни белгиланган муддатларда рўйхатдан ўтказиш "
                    "лозим. Аниқ муддатлар амалдаги қонунчиликка мувофиқ белгиланади."
                ),
                "related_documents": ["orq_1079", "qm_748"],
            },
            {
                "question": "Ҳайвон сотилганда нима қилиш керак?",
                "answer": (
                    "Ҳайвон сотилганда унинг эгаси ўзгариши амалдаги қонунчиликка мувофиқ "
                    "идентификация тизимида қайд этилиши лозим."
                ),
                "related_documents": ["qm_748"],
            },
        ],
    },
    {
        "id": "id_number",
        "title": "🏷️ Идентификация рақами ва бирка",
        "questions": [
            {
                "question": "Идентификация рақами нима?",
                "answer": (
                    "Идентификация рақами — ҳар бир ҳайвонга бериладиган ва уни бошқа "
                    "ҳайвонлардан фарқлаш имконини берувчи ягона рақам."
                ),
                "related_documents": ["orq_1079"],
            },
            {
                "question": "Идентификация биркаси нима учун керак?",
                "answer": (
                    "Идентификация биркаси ҳайвоннинг идентификация рақамини жисмоний "
                    "тарзда акс эттириб, уни визуал аниқлаш имконини беради."
                ),
                "related_documents": ["qm_748"],
            },
            {
                "question": "Бирка йўқолса нима қилиш керак?",
                "answer": (
                    "Бирка йўқолган тақдирда уни тиклаш учун амалдаги қонунчиликка "
                    "мувофиқ тегишли идорага мурожаат қилиш лозим."
                ),
                "related_documents": ["qm_748"],
            },
            {
                "question": "Идентификация рақамини қаердан билиб олса бўлади?",
                "answer": "Идентификация рақами ҳайвонга бириктирилган бирка ва тегишли ҳужжатларда кўрсатилади.",
            },
        ],
    },
    {
        "id": "appeals",
        "title": "📨 Мурожаатлар",
        "questions": [
            {
                "question": "Мурожаатни қандай юбориш мумкин?",
                "answer": (
                    "Ботнинг асосий менюсидаги «📨 Мурожаат юбориш» бўлими орқали "
                    "Ф.И.Ш., телефон рақами, ҳудуд ва мурожаат матнини киритиб юбориш "
                    "мумкин."
                ),
            },
            {
                "question": "Мурожаат рақами нима учун берилади?",
                "answer": (
                    "Ҳар бир мурожаатга алоҳида рақам берилади. Ушбу рақам орқали "
                    "мурожаатни кейинчалик аниқлаш ва унинг ҳолатини назорат қилиш "
                    "имконияти яратилади."
                ),
            },
            {
                "question": "Телефон рақамини қандай киритиш керак?",
                "answer": "Телефон рақамини Telegram орқали «📱 Рақамимни юбориш» тугмаси ёрдамида юборишингиз мумкин.",
            },
            {
                "question": "Қайси ҳудудни танлаш керак?",
                "answer": "Ҳайвон рўйхатдан ўтказилган ёки мурожаатга тегишли бўлган вилоят ҳамда туман/шаҳарни танланг.",
            },
        ],
    },
    {
        "id": "other",
        "title": "📞 Бошқа саволлар",
        "questions": [
            {
                "question": "Бот қандай ишлайди?",
                "answer": (
                    "Бот орқали тайёр савол-жавоблар билан танишиш, мурожаат ва таклиф "
                    "юбориш, шунингдек расмий ҳужжатлар билан танишиш мумкин."
                ),
            },
            {
                "question": "Маълумотларим хавфсизми?",
                "answer": (
                    "Сиз киритган маълумотлар фақат хизмат кўрсатиш мақсадида "
                    "ишлатилади ва амалдаги қонунчиликка мувофиқ ҳимояланади."
                ),
            },
            {
                "question": "Мурожаатимга қачон жавоб оламан?",
                "answer": "Мурожаатлар масъул ходимлар томонидан имкон қадар қисқа муддатда кўриб чиқилади.",
            },
            {
                "question": "Саволимга жавоб тополмадим, нима қилишим керак?",
                "answer": "Бундай ҳолда «📨 Мурожаат юбориш» бўлими орқали саволингизни ёзиб юборишингиз мумкин.",
            },
        ],
    },
]


def get_category(category_id: str) -> dict | None:
    """Return the category dict for this id, or None if it doesn't exist."""
    for category in FAQ_CATEGORIES:
        if category["id"] == category_id:
            return category
    return None


def get_question(category_id: str, question_index: int) -> dict | None:
    """Return the {"question", "answer"} dict at this index within a category.

    Returns None if the category doesn't exist or the index is out of range.
    """
    category = get_category(category_id)
    if category is None:
        return None

    questions = category["questions"]
    if 0 <= question_index < len(questions):
        return questions[question_index]
    return None
