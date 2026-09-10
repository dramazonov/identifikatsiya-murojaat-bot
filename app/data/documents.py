"""Static content for the "📚 Расмий ҳужжатлар" section.

``DOCUMENTS`` lists the real legal acts that govern animal identification in
Uzbekistan. Every field below (document type, number, date, official title,
issuing body, source URL) was checked against the official legislation
portal (lex.uz) -- nothing here is invented or placeholder content, and no
article/paragraph number is cited because the acts themselves were not
inspected at that level of detail.

If a future stage needs to add more documents, extend this list following
the same shape; ``get_document`` and ``format_basis_line`` below will keep
working without changes.
"""

from __future__ import annotations

DOCUMENTS: list[dict] = [
    {
        "id": "orq_1079",
        "header": "📜 Ўзбекистон Республикасининг Қонуни",
        "number": "№ ЎРҚ-1079",
        "date": "06.08.2025",
        "title": (
            "Ҳайвонларни идентификация қилиш, рўйхатга олиш ва кузатиш "
            "тўғрисида"
        ),
        # Reused both as the list-menu button label and as the "📌 Асос: ..."
        # reference line shown under related FAQ answers.
        "short_ref": "ЎРҚ-1079-сон Қонун",
        "source_url": "https://lex.uz/uz/docs/-7670550",
    },
    {
        "id": "qm_748",
        "header": "📜 Ўзбекистон Республикаси Вазирлар Маҳкамасининг қарори",
        "number": "№ 748",
        "date": "22.09.2017",
        "title": (
            "Ҳайвонларни идентификация қилиш, уларни ҳисобга олиш, ҳисобдан "
            "чиқариш ва сақлаш тартибини такомиллаштириш тўғрисида"
        ),
        "short_ref": "748-сон Қарор",
        "source_url": "https://lex.uz/uz/docs/-3359038",
    },
    {
        "id": "pq_285",
        "header": "📜 Ўзбекистон Республикаси Президентининг қарори",
        "number": "№ ПҚ-285",
        "date": "24.08.2023",
        "title": (
            "Чорвачиликда идентификация қилиш тизими ва наслчилик соҳасини "
            "такомиллаштиришга оид қўшимча чора-тадбирлар тўғрисида"
        ),
        "short_ref": "ПҚ-285-сон Қарор",
        "source_url": "https://lex.uz/uz/docs/-6583141",
    },
]


def get_document(document_id: str) -> dict | None:
    """Return the document dict for this id, or None if it doesn't exist."""
    for document in DOCUMENTS:
        if document["id"] == document_id:
            return document
    return None


def get_documents(document_ids: list[str]) -> list[dict]:
    """Return the documents for these ids, skipping any that don't exist."""
    documents = []
    for document_id in document_ids:
        document = get_document(document_id)
        if document is not None:
            documents.append(document)
    return documents


def format_document_text(document: dict) -> str:
    """Render a document's detail view text (header, number, date, title)."""
    return (
        f"{document['header']}\n\n"
        f"{document['number']}\n"
        f"📅 {document['date']}\n\n"
        f"{document['title']}"
    )


def format_basis_line(document_ids: list[str]) -> str:
    """Render the "📌 Асос: ..." reference line for these document ids.

    Returns an empty string if none of the ids resolve to a real document,
    so callers can safely append the result without an extra `if` check.
    """
    documents = get_documents(document_ids)
    if not documents:
        return ""

    refs = "; ".join(document["short_ref"] for document in documents)
    return f"📌 Асос: {refs}."
