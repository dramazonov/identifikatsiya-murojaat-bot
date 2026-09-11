from __future__ import annotations

from typing import Final

DEFAULT_LANGUAGE: Final[str] = "uz_cyrl"
SUPPORTED_LANGUAGES: Final[tuple[str, ...]] = ("uz_latn", "uz_cyrl", "ru", "en")

LANGUAGE_LABELS: Final[dict[str, str]] = {
    "uz_latn": "🇺🇿 O‘zbekcha",
    "uz_cyrl": "🇺🇿 Ўзбекча",
    "ru": "🇷🇺 Русский",
    "en": "🇬🇧 English",
}

_MESSAGES: dict[str, dict[str, str]] = {
    "language.choose": {
        "uz_latn": "🌐 Tilni tanlang / Тилни танланг\nВыберите язык / Choose a language:",
        "uz_cyrl": "🌐 Tilni tanlang / Тилни танланг\nВыберите язык / Choose a language:",
        "ru": "🌐 Tilni tanlang / Тилни танланг\nВыберите язык / Choose a language:",
        "en": "🌐 Tilni tanlang / Тилни танланг\nВыберите язык / Choose a language:",
    },
    "registration.ask_full_name": {
        "uz_latn": "Iltimos, F.I.Sh.ingizni kiriting:",
        "uz_cyrl": "Илтимос, Ф.И.Ш.ингизни киритинг:",
        "ru": "Пожалуйста, введите Ф.И.О.:",
        "en": "Please enter your full name:",
    },
    "registration.invalid_full_name": {
        "uz_latn": "Iltimos, to‘liq ism-familiyangizni kiriting (kamida 5 ta belgi).",
        "uz_cyrl": "Илтимос, тўлиқ исм-фамилиянгизни киритинг (камида 5 та белги).",
        "ru": "Пожалуйста, введите полное имя (не менее 5 символов).",
        "en": "Please enter your full name (at least 5 characters).",
    },
    "registration.ask_phone": {
        "uz_latn": "📱 Telefon raqamingizni faqat quyidagi tugma orqali yuboring:",
        "uz_cyrl": "📱 Телефон рақамингизни фақат қуйидаги тугма орқали юборинг:",
        "ru": "📱 Отправьте свой номер телефона только с помощью кнопки ниже:",
        "en": "📱 Share your phone number using the button below:",
    },
    "registration.manual_phone_rejected": {
        "uz_latn": "⚠️ Telefon raqamini qo‘lda kiritish qabul qilinmaydi. Quyidagi tugma orqali o‘z raqamingizni yuboring.",
        "uz_cyrl": "⚠️ Телефон рақамини қўлда киритиш қабул қилинмайди. Қуйидаги тугма орқали ўз рақамингизни юборинг.",
        "ru": "⚠️ Номер телефона вручную не принимается. Отправьте свой номер кнопкой ниже.",
        "en": "⚠️ Manually typed phone numbers are not accepted. Share your own number with the button below.",
    },
    "registration.wrong_contact": {
        "uz_latn": "⚠️ Faqat o‘zingizning Telegram akkauntingizga tegishli telefon raqamini yuborishingiz mumkin.",
        "uz_cyrl": "⚠️ Фақат ўзингизнинг Telegram аккаунтингизга тегишли телефон рақамини юборишингиз мумкин.",
        "ru": "⚠️ Можно отправить только номер телефона, принадлежащий вашему Telegram-аккаунту.",
        "en": "⚠️ You can only share the phone number linked to your own Telegram account.",
    },
    "registration.invalid_phone": {
        "uz_latn": "⚠️ Telegram yuborgan telefon raqami noto‘g‘ri formatda. Iltimos, qayta urinib ko‘ring.",
        "uz_cyrl": "⚠️ Telegram юборган телефон рақами нотўғри форматда. Илтимос, қайта уриниб кўринг.",
        "ru": "⚠️ Telegram передал номер в неверном формате. Пожалуйста, попробуйте ещё раз.",
        "en": "⚠️ Telegram returned an invalid phone number format. Please try again.",
    },
    "registration.phone_accepted": {
        "uz_latn": "✅ Telefon raqami tasdiqlandi.",
        "uz_cyrl": "✅ Телефон рақами тасдиқланди.",
        "ru": "✅ Номер телефона подтверждён.",
        "en": "✅ Phone number verified.",
    },
    "registration.ask_region": {
        "uz_latn": "Viloyatingizni tanlang:",
        "uz_cyrl": "Вилоятингизни танланг:",
        "ru": "Выберите область:",
        "en": "Select your region:",
    },
    "registration.invalid_region": {
        "uz_latn": "Iltimos, viloyatni tugmalar orqali tanlang:",
        "uz_cyrl": "Илтимос, вилоятни тугмалар орқали танланг:",
        "ru": "Пожалуйста, выберите область с помощью кнопок:",
        "en": "Please select a region using the buttons:",
    },
    "registration.ask_district": {
        "uz_latn": "Tuman yoki shaharni tanlang:",
        "uz_cyrl": "Туман ёки шаҳарни танланг:",
        "ru": "Выберите район или город:",
        "en": "Select a district or city:",
    },
    "registration.invalid_district": {
        "uz_latn": "Iltimos, tuman yoki shaharni tugmalar orqali tanlang:",
        "uz_cyrl": "Илтимос, туман ёки шаҳарни тугмалар орқали танланг:",
        "ru": "Пожалуйста, выберите район или город с помощью кнопок:",
        "en": "Please select a district or city using the buttons:",
    },
    "registration.location_saved": {
        "uz_latn": "✅ Hudud ma’lumotlari qabul qilindi.",
        "uz_cyrl": "✅ Ҳудуд маълумотлари қабул қилинди.",
        "ru": "✅ Данные о регионе сохранены.",
        "en": "✅ Location information saved.",
    },
    "menu.title": {
        "uz_latn": "🏠 ASOSIY MENYU\n\nKerakli bo‘limni tanlang:",
        "uz_cyrl": "🏠 АСОСИЙ МЕНЮ\n\nКеракли бўлимни танланг:",
        "ru": "🏠 ГЛАВНОЕ МЕНЮ\n\nВыберите нужный раздел:",
        "en": "🏠 MAIN MENU\n\nChoose a section:",
    },
    "menu.faq": {
        "uz_latn": "❓ Tayyor savol-javoblar",
        "uz_cyrl": "❓ Тайёр савол-жавоблар",
        "ru": "❓ Готовые вопросы и ответы",
        "en": "❓ FAQ",
    },
    "menu.appeal": {
        "uz_latn": "📨 Murojaat yuborish",
        "uz_cyrl": "📨 Мурожаат юбориш",
        "ru": "📨 Отправить обращение",
        "en": "📨 Send an appeal",
    },
    "menu.suggestion": {
        "uz_latn": "💡 Taklif yuborish",
        "uz_cyrl": "💡 Таклиф юбориш",
        "ru": "💡 Отправить предложение",
        "en": "💡 Send a suggestion",
    },
    "menu.documents": {
        "uz_latn": "📚 Qaror, qonun va rasmiy hujjatlar",
        "uz_cyrl": "📚 Қарор, қонун ва расмий ҳужжатлар билан танишиш",
        "ru": "📚 Законы и официальные документы",
        "en": "📚 Laws and official documents",
    },
    "menu.admin_contact": {
        "uz_latn": "👨‍💼 Admin bilan bog‘lanish",
        "uz_cyrl": "👨‍💼 Админ билан боғланиш",
        "ru": "👨‍💼 Связаться с администратором",
        "en": "👨‍💼 Contact an administrator",
    },
    "button.share_phone": {
        "uz_latn": "📱 Telefon raqamimni yuborish",
        "uz_cyrl": "📱 Телефон рақамимни юбориш",
        "ru": "📱 Отправить мой номер",
        "en": "📱 Share my phone number",
    },
    "button.back": {
        "uz_latn": "⬅️ Orqaga",
        "uz_cyrl": "⬅️ Орқага",
        "ru": "⬅️ Назад",
        "en": "⬅️ Back",
    },
    "button.home": {
        "uz_latn": "🏠 Asosiy menyu",
        "uz_cyrl": "🏠 Асосий меню",
        "ru": "🏠 Главное меню",
        "en": "🏠 Main menu",
    },
    "button.official_source": {
        "uz_latn": "🔗 Rasmiy manba",
        "uz_cyrl": "🔗 Расмий манба",
        "ru": "🔗 Официальный источник",
        "en": "🔗 Official source",
    },
    "appeal.ask": {
        "uz_latn": "Murojaatingizni yozing:",
        "uz_cyrl": "Мурожаатингизни ёзинг:",
        "ru": "Напишите ваше обращение:",
        "en": "Write your appeal:",
    },
    "appeal.invalid": {
        "uz_latn": "Murojaat matni noto‘g‘ri. 5–4000 ta belgi kiriting.",
        "uz_cyrl": "Мурожаат матни нотўғри. 5–4000 та белги киритинг.",
        "ru": "Некорректный текст обращения. Введите от 5 до 4000 символов.",
        "en": "Invalid appeal text. Enter 5–4000 characters.",
    },
    "appeal.success": {
        "uz_latn": "Murojaatingiz qabul qilindi.\n\nMurojaat raqami: {appeal_number}\n\nMurojaatingiz mas’ul xodimlar tomonidan ko‘rib chiqiladi.",
        "uz_cyrl": "Мурожаатингиз қабул қилинди.\n\nМурожаат рақами: {appeal_number}\n\nМурожаатингиз масъул ходимлар томонидан кўриб чиқилади.",
        "ru": "Ваше обращение принято.\n\nНомер обращения: {appeal_number}\n\nОбращение будет рассмотрено ответственными сотрудниками.",
        "en": "Your appeal has been accepted.\n\nAppeal number: {appeal_number}\n\nIt will be reviewed by responsible staff.",
    },
    "appeal.admin_answer": {
        "uz_latn": "📩 <b>Murojaatingiz bo‘yicha javob</b>\n\n🆔 <b>Murojaat raqami:</b> {appeal_number}\n\n📝 <b>Javob:</b>\n\n{admin_answer}\n\nMurojaatingiz ko‘rib chiqildi. Rahmat!",
        "uz_cyrl": "📩 <b>Мурожаатингиз бўйича жавоб</b>\n\n🆔 <b>Мурожаат рақами:</b> {appeal_number}\n\n📝 <b>Жавоб:</b>\n\n{admin_answer}\n\nМурожаатингиз кўриб чиқилди. Раҳмат!",
        "ru": "📩 <b>Ответ по вашему обращению</b>\n\n🆔 <b>Номер обращения:</b> {appeal_number}\n\n📝 <b>Ответ:</b>\n\n{admin_answer}\n\nВаше обращение рассмотрено. Спасибо!",
        "en": "📩 <b>Response to your appeal</b>\n\n🆔 <b>Appeal number:</b> {appeal_number}\n\n📝 <b>Response:</b>\n\n{admin_answer}\n\nYour appeal has been reviewed. Thank you!",
    },
    "suggestion.ask": {
        "uz_latn": "Taklifingizni yozing:",
        "uz_cyrl": "Таклифингизни ёзинг:",
        "ru": "Напишите ваше предложение:",
        "en": "Write your suggestion:",
    },
    "suggestion.invalid": {
        "uz_latn": "Taklif matni noto‘g‘ri. 5–4000 ta belgi kiriting.",
        "uz_cyrl": "Таклиф матни нотўғри. 5–4000 та белги киритинг.",
        "ru": "Некорректный текст предложения. Введите от 5 до 4000 символов.",
        "en": "Invalid suggestion text. Enter 5–4000 characters.",
    },
    "suggestion.success": {
        "uz_latn": "✅ Taklifingiz qabul qilindi.\n\nTaklif raqami: {suggestion_number}",
        "uz_cyrl": "✅ Таклифингиз қабул қилинди.\n\nТаклиф рақами: {suggestion_number}",
        "ru": "✅ Ваше предложение принято.\n\nНомер предложения: {suggestion_number}",
        "en": "✅ Your suggestion has been accepted.\n\nSuggestion number: {suggestion_number}",
    },
    "admin_contact.ask": {
        "uz_latn": "💬 Adminga yuborish uchun xabaringizni yozing:",
        "uz_cyrl": "💬 Админга юбориш учун хабарингизни ёзинг:",
        "ru": "💬 Напишите сообщение администратору:",
        "en": "💬 Write a message to the administrator:",
    },
    "admin_contact.invalid": {
        "uz_latn": "Xabar matni noto‘g‘ri. 2–4000 ta belgi kiriting.",
        "uz_cyrl": "Хабар матни нотўғри. 2–4000 та белги киритинг.",
        "ru": "Некорректный текст сообщения. Введите от 2 до 4000 символов.",
        "en": "Invalid message text. Enter 2–4000 characters.",
    },
    "admin_contact.success": {
        "uz_latn": "✅ Xabaringiz qabul qilindi.\n\nMurojaat raqami: {contact_number}\n\nAdminlar tomonidan ko‘rib chiqiladi.",
        "uz_cyrl": "✅ Хабарингиз қабул қилинди.\n\nМурожаат рақами: {contact_number}\n\nАдминлар томонидан кўриб чиқилади.",
        "ru": "✅ Ваше сообщение принято.\n\nНомер: {contact_number}\n\nОно будет рассмотрено администраторами.",
        "en": "✅ Your message has been accepted.\n\nReference number: {contact_number}\n\nIt will be reviewed by administrators.",
    },
    "admin_contact.answer": {
        "uz_latn": "👨‍💼 <b>Admindan javob</b>\n\n📌 <b>Xabar raqami:</b> {contact_number}\n\n💬 <b>Javob:</b>\n\n{admin_answer}",
        "uz_cyrl": "👨‍💼 <b>Админдан жавоб</b>\n\n📌 <b>Хабар рақами:</b> {contact_number}\n\n💬 <b>Жавоб:</b>\n\n{admin_answer}",
        "ru": "👨‍💼 <b>Ответ администратора</b>\n\n📌 <b>Номер сообщения:</b> {contact_number}\n\n💬 <b>Ответ:</b>\n\n{admin_answer}",
        "en": "👨‍💼 <b>Administrator response</b>\n\n📌 <b>Message number:</b> {contact_number}\n\n💬 <b>Response:</b>\n\n{admin_answer}",
    },
    "common.error": {
        "uz_latn": "Xatolik yuz berdi. Iltimos, birozdan so‘ng qayta urinib ko‘ring.",
        "uz_cyrl": "Хатолик юз берди. Илтимос, бироздан сўнг қайта уриниб кўринг.",
        "ru": "Произошла ошибка. Пожалуйста, попробуйте позже.",
        "en": "An error occurred. Please try again later.",
    },
    "common.rate_limited": {
        "uz_latn": "⏳ Juda tez-tez yuboryapsiz. Biroz kutib, qayta urinib ko‘ring.",
        "uz_cyrl": "⏳ Сиз жуда тез-тез юбормоқдасиз. Бир оз кутиб қайта уриниб кўринг.",
        "ru": "⏳ Слишком много запросов. Подождите немного и попробуйте снова.",
        "en": "⏳ Too many requests. Please wait a moment and try again.",
    },
    "faq.intro": {
        "uz_latn": "Kerakli bo‘limni tanlang:",
        "uz_cyrl": "Керакли бўлимни танланг:",
        "ru": "Выберите нужный раздел:",
        "en": "Choose a section:",
    },
    "faq.not_found": {
        "uz_latn": "Bo‘lim topilmadi. Ro‘yxatdan qayta tanlang.",
        "uz_cyrl": "Бўлим топилмади. Рўйхатдан қайта танланг.",
        "ru": "Раздел не найден. Выберите снова.",
        "en": "Section not found. Please choose again.",
    },
    "faq.choose_question": {
        "uz_latn": "Savolni tanlang:",
        "uz_cyrl": "Саволни танланг:",
        "ru": "Выберите вопрос:",
        "en": "Choose a question:",
    },
    "documents.intro": {
        "uz_latn": "Quyidagi hujjatlardan birini tanlang:",
        "uz_cyrl": "Қуйидаги ҳужжатлардан бирини танланг:",
        "ru": "Выберите один из документов:",
        "en": "Choose a document:",
    },
    "documents.not_found": {
        "uz_latn": "Hujjat topilmadi. Ro‘yxatdan qayta tanlang.",
        "uz_cyrl": "Ҳужжат топилмади. Рўйхатдан қайта танланг.",
        "ru": "Документ не найден. Выберите снова.",
        "en": "Document not found. Please choose again.",
    },
}


def normalize_language(language_code: str | None) -> str:
    return language_code if language_code in SUPPORTED_LANGUAGES else DEFAULT_LANGUAGE


def t(key: str, language_code: str | None = None, **kwargs: object) -> str:
    language = normalize_language(language_code)
    translations = _MESSAGES.get(key)
    if translations is None:
        raise KeyError(f"Unknown translation key: {key}")
    text = translations.get(language) or translations[DEFAULT_LANGUAGE]
    return text.format(**kwargs) if kwargs else text


def all_texts(key: str) -> tuple[str, ...]:
    translations = _MESSAGES.get(key)
    if translations is None:
        raise KeyError(f"Unknown translation key: {key}")
    return tuple(dict.fromkeys(translations.values()))
