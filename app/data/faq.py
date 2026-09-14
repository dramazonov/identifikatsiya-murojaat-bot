"""Localized FAQ knowledge base.

Stable category ids and question indexes are used in callbacks.  Citizen-facing
content is resolved at render time for uz_latn, uz_cyrl, ru and en.
"""

from __future__ import annotations

from app.i18n import DEFAULT_LANGUAGE, normalize_language


def _l(uz_latn: str, uz_cyrl: str, ru: str, en: str) -> dict[str, str]:
    return {"uz_latn": uz_latn, "uz_cyrl": uz_cyrl, "ru": ru, "en": en}


FAQ_CATEGORIES: list[dict] = [
    {
        "id": "identification",
        "title": _l(
            "🐄 Hayvonlarni identifikatsiya qilish",
            "🐄 Ҳайвонларни идентификация қилиш",
            "🐄 Идентификация животных",
            "🐄 Animal identification",
        ),
        "questions": [
            {
                "question": _l(
                    "Hayvonlarni identifikatsiya qilish nima?",
                    "Ҳайвонларни идентификация қилиш нима?",
                    "Что такое идентификация животных?",
                    "What is animal identification?",
                ),
                "answer": _l(
                    "Hayvonlarni identifikatsiya qilish — hayvonga belgilangan tartibda identifikatsiya raqami berish, uning ma’lumotlarini axborot tizimida qayd etish hamda harakati va holatini kuzatish imkonini beruvchi jarayon.",
                    "Ҳайвонларни идентификация қилиш — ҳайвонни белгиланган тартибда идентификация рақами бериш, маълумотларини ахборот тизимида қайд этиш ва унинг ҳаракати ҳамда ҳолатини кузатиш имконини берувчи жараён.",
                    "Идентификация животных — это процесс присвоения животному идентификационного номера в установленном порядке, регистрации сведений о нем в информационной системе и обеспечения возможности отслеживать его перемещение и состояние.",
                    "Animal identification is the process of assigning an animal an identification number under the established procedure, recording its data in the information system, and enabling its movement and status to be traced.",
                ),
                "related_documents": ["orq_1079"],
            },
            {
                "question": _l(
                    "Hayvonni identifikatsiya qilish nima uchun kerak?",
                    "Ҳайвонни идентификация қилиш нима учун керак?",
                    "Зачем нужна идентификация животного?",
                    "Why is animal identification needed?",
                ),
                "answer": _l(
                    "Identifikatsiya hayvonning egasi, turi, jinsi, yoshi va boshqa zarur ma’lumotlarini hisobga olish, hayvonlar harakatini kuzatish hamda veterinariya nazoratini samarali tashkil etish uchun amalga oshiriladi.",
                    "Идентификация ҳайвоннинг эгаси, тури, жинси, ёши ва бошқа зарур маълумотларини ҳисобга олиш, ҳайвонлар ҳаракатини кузатиш ҳамда ветеринария назоратини самарали ташкил этиш учун амалга оширилади.",
                    "Идентификация проводится для учета владельца, вида, пола, возраста и других необходимых сведений о животном, отслеживания перемещения животных и эффективной организации ветеринарного контроля.",
                    "Identification is used to record the animal’s owner, species, sex, age and other required information, track animal movements, and organize veterinary control effectively.",
                ),
                "related_documents": ["orq_1079"],
            },
            {
                "question": _l(
                    "Hayvonni qanday identifikatsiya qilish mumkin?",
                    "Ҳайвонни қандай идентификация қилиш мумкин?",
                    "Как проводится идентификация животного?",
                    "How is an animal identified?",
                ),
                "answer": _l(
                    "Hayvonlarni identifikatsiya qilish belgilangan tartibda identifikatsiya vositalari orqali amalga oshiriladi. Aniq tartib va talablar amaldagi qonunchilik hujjatlariga muvofiq belgilanadi.",
                    "Ҳайвонларни идентификация қилиш белгиланган тартибда идентификация воситалари орқали амалга оширилади. Аниқ тартиб ва талаблар амалдаги қонунчилик ҳужжатларига мувофиқ белгиланади.",
                    "Идентификация животных проводится в установленном порядке с использованием средств идентификации. Конкретный порядок и требования определяются действующим законодательством.",
                    "Animals are identified under the established procedure using approved identification means. The specific procedure and requirements are determined by applicable legislation.",
                ),
                "related_documents": ["orq_1079", "qm_748"],
            },
        ],
    },
    {
        "id": "registration",
        "title": _l(
            "📋 Ro‘yxatdan o‘tkazish va hisobdan chiqarish",
            "📋 Рўйхатдан ўтказиш ва ҳисобдан чиқариш",
            "📋 Регистрация и снятие с учета",
            "📋 Registration and deregistration",
        ),
        "questions": [
            {
                "question": _l("Hayvon so‘yilsa nima qilish kerak?", "Ҳайвон сўйилса нима қилиш керак?", "Что делать, если животное забито?", "What should I do if an animal is slaughtered?"),
                "answer": _l("Hayvon so‘yilganda uni belgilangan tartibda hisobdan chiqarish uchun murojaat qilish lozim.", "Ҳайвон сўйилганда уни белгиланган тартибда ҳисобдан чиқариш учун мурожаат қилиш лозим.", "После убоя животного необходимо обратиться для его снятия с учета в установленном порядке.", "When an animal is slaughtered, an application must be submitted to deregister it under the established procedure."),
                "related_documents": ["qm_748"],
            },
            {
                "question": _l("Hayvon nobud bo‘lsa nima qilish kerak?", "Ҳайвон нобуд бўлса нима қилиш керак?", "Что делать, если животное погибло?", "What should I do if an animal dies?"),
                "answer": _l("Hayvon nobud bo‘lgan taqdirda uni belgilangan tartibda hisobdan chiqarish uchun murojaat qilish lozim.", "Ҳайвон нобуд бўлган тақдирда уни белгиланган тартибда ҳисобдан чиқариш учун мурожаат қилиш лозим.", "В случае гибели животного необходимо обратиться для его снятия с учета в установленном порядке.", "If an animal dies, an application must be submitted to deregister it under the established procedure."),
                "related_documents": ["qm_748"],
            },
            {
                "question": _l("Yangi tug‘ilgan hayvonni qachon ro‘yxatdan o‘tkazish kerak?", "Янги туғилган ҳайвонни қачон рўйхатдан ўтказиш керак?", "Когда нужно зарегистрировать новорожденное животное?", "When should a newborn animal be registered?"),
                "answer": _l("Yangi tug‘ilgan hayvonni belgilangan muddatlarda ro‘yxatdan o‘tkazish lozim. Aniq muddatlar amaldagi qonunchilikka muvofiq belgilanadi.", "Янги туғилган ҳайвонни белгиланган муддатларда рўйхатдан ўтказиш лозим. Аниқ муддатлар амалдаги қонунчиликка мувофиқ белгиланади.", "Новорожденное животное необходимо зарегистрировать в установленные сроки. Конкретные сроки определяются действующим законодательством.", "A newborn animal must be registered within the established time limits. The exact time limits are determined by applicable legislation."),
                "related_documents": ["orq_1079", "qm_748"],
            },
            {
                "question": _l("Hayvon sotilganda nima qilish kerak?", "Ҳайвон сотилганда нима қилиш керак?", "Что делать при продаже животного?", "What should I do when an animal is sold?"),
                "answer": _l("Hayvon sotilganda uning egasi o‘zgarishi amaldagi qonunchilikka muvofiq identifikatsiya tizimida qayd etilishi lozim.", "Ҳайвон сотилганда унинг эгаси ўзгариши амалдаги қонунчиликка мувофиқ идентификация тизимида қайд этилиши лозим.", "При продаже животного смена владельца должна быть зарегистрирована в системе идентификации в соответствии с действующим законодательством.", "When an animal is sold, the change of owner must be recorded in the identification system in accordance with applicable legislation."),
                "related_documents": ["qm_748"],
            },
        ],
    },
    {
        "id": "id_number",
        "title": _l("🏷️ Identifikatsiya raqami va birka", "🏷️ Идентификация рақами ва бирка", "🏷️ Идентификационный номер и бирка", "🏷️ Identification number and ear tag"),
        "questions": [
            {
                "question": _l("Identifikatsiya raqami nima?", "Идентификация рақами нима?", "Что такое идентификационный номер?", "What is an identification number?"),
                "answer": _l("Identifikatsiya raqami — har bir hayvonga beriladigan va uni boshqa hayvonlardan farqlash imkonini beruvchi yagona raqam.", "Идентификация рақами — ҳар бир ҳайвонга бериладиган ва уни бошқа ҳайвонлардан фарқлаш имконини берувчи ягона рақам.", "Идентификационный номер — это уникальный номер, присваиваемый каждому животному и позволяющий отличить его от других животных.", "An identification number is a unique number assigned to each animal that distinguishes it from other animals."),
                "related_documents": ["orq_1079"],
            },
            {
                "question": _l("Identifikatsiya birkasi nima uchun kerak?", "Идентификация биркаси нима учун керак?", "Для чего нужна идентификационная бирка?", "Why is an identification ear tag needed?"),
                "answer": _l("Identifikatsiya birkasi hayvonning identifikatsiya raqamini jismoniy tarzda aks ettirib, uni vizual aniqlash imkonini beradi.", "Идентификация биркаси ҳайвоннинг идентификация рақамини жисмоний тарзда акс эттириб, уни визуал аниқлаш имконини беради.", "Идентификационная бирка физически отображает идентификационный номер животного и позволяет визуально его определить.", "An identification ear tag physically displays the animal’s identification number and allows it to be identified visually."),
                "related_documents": ["qm_748"],
            },
            {
                "question": _l("Birka yo‘qolsa nima qilish kerak?", "Бирка йўқолса нима қилиш керак?", "Что делать, если бирка потеряна?", "What should I do if the ear tag is lost?"),
                "answer": _l("Birka yo‘qolgan taqdirda uni tiklash uchun amaldagi qonunchilikka muvofiq tegishli idoraga murojaat qilish lozim.", "Бирка йўқолган тақдирда уни тиклаш учун амалдаги қонунчиликка мувофиқ тегишли идорага мурожаат қилиш лозим.", "При утрате бирки необходимо обратиться в соответствующий орган для ее восстановления в соответствии с действующим законодательством.", "If an ear tag is lost, the relevant authority should be contacted for replacement in accordance with applicable legislation."),
                "related_documents": ["qm_748"],
            },
            {
                "question": _l("Identifikatsiya raqamini qayerdan bilib olsa bo‘ladi?", "Идентификация рақамини қаердан билиб олса бўлади?", "Где можно узнать идентификационный номер?", "Where can I find the identification number?"),
                "answer": _l("Identifikatsiya raqami hayvonga biriktirilgan birka va tegishli hujjatlarda ko‘rsatiladi.", "Идентификация рақами ҳайвонга бириктирилган бирка ва тегишли ҳужжатларда кўрсатилади.", "Идентификационный номер указан на бирке, закрепленной за животным, и в соответствующих документах.", "The identification number is shown on the animal’s ear tag and in the relevant documents."),
            },
        ],
    },
    {
        "id": "appeals",
        "title": _l("📨 Murojaatlar", "📨 Мурожаатлар", "📨 Обращения", "📨 Appeals"),
        "questions": [
            {
                "question": _l("Murojaatni qanday yuborish mumkin?", "Мурожаатни қандай юбориш мумкин?", "Как отправить обращение?", "How can I submit an appeal?"),
                "answer": _l("Botning asosiy menyusidagi «📨 Murojaat yuborish» bo‘limi orqali yo‘nalishni tanlab, murojaat matnini yozishingiz va zarur bo‘lsa PDF hujjat biriktirishingiz mumkin.", "Ботнинг асосий менюсидаги «📨 Мурожаат юбориш» бўлими орқали йўналишни танлаб, мурожаат матнини ёзишингиз ва зарур бўлса PDF ҳужжат бириктиришингиз мумкин.", "В разделе «📨 Отправить обращение» главного меню выберите направление, напишите текст обращения и при необходимости приложите PDF-документ.", "Use the “📨 Submit an appeal” section in the main menu, choose a category, enter your appeal text, and optionally attach a PDF document."),
            },
            {
                "question": _l("Murojaat raqami nima uchun beriladi?", "Мурожаат рақами нима учун берилади?", "Для чего присваивается номер обращения?", "Why is an appeal number assigned?"),
                "answer": _l("Har bir murojaatga alohida raqam beriladi. Ushbu raqam orqali murojaatni keyinchalik aniqlash va uning holatini nazorat qilish mumkin.", "Ҳар бир мурожаатга алоҳида рақам берилади. Ушбу рақам орқали мурожаатни кейинчалик аниқлаш ва унинг ҳолатини назорат қилиш имконияти яратилади.", "Каждому обращению присваивается отдельный номер. По нему можно идентифицировать обращение и отслеживать его статус.", "Each appeal receives a unique number that can be used to identify it later and track its status."),
            },
            {
                "question": _l("Telefon raqamini qanday kiritish kerak?", "Телефон рақамини қандай киритиш керак?", "Как указать номер телефона?", "How should I provide my phone number?"),
                "answer": _l("Telefon raqamini Telegram orqali «📱 Raqamimni yuborish» tugmasi yordamida yuborishingiz mumkin. Qo‘lda kiritilgan raqam qabul qilinmaydi.", "Телефон рақамини Telegram орқали «📱 Рақамимни юбориш» тугмаси ёрдамида юборишингиз мумкин. Қўлда киритилган рақам қабул қилинмайди.", "Номер телефона нужно отправить через Telegram с помощью кнопки «📱 Отправить мой номер». Введенный вручную номер не принимается.", "Share your phone number through Telegram using the “📱 Share my phone number” button. Manually typed numbers are not accepted."),
            },
            {
                "question": _l("Qaysi hududni tanlash kerak?", "Қайси ҳудудни танлаш керак?", "Какой регион нужно выбрать?", "Which location should I choose?"),
                "answer": _l("Hayvon ro‘yxatdan o‘tkazilgan yoki murojaatga tegishli bo‘lgan viloyat hamda tuman/shaharni tanlang.", "Ҳайвон рўйхатдан ўтказилган ёки мурожаатга тегишли бўлган вилоят ҳамда туман/шаҳарни танланг.", "Выберите область и район/город, где зарегистрировано животное или к которому относится обращение.", "Choose the region and district/city where the animal is registered or that is relevant to the appeal."),
            },
        ],
    },
    {
        "id": "other",
        "title": _l("📞 Boshqa savollar", "📞 Бошқа саволлар", "📞 Другие вопросы", "📞 Other questions"),
        "questions": [
            {
                "question": _l("Bot qanday ishlaydi?", "Бот қандай ишлайди?", "Как работает бот?", "How does the bot work?"),
                "answer": _l("Bot orqali tayyor savol-javoblar bilan tanishish, murojaat va taklif yuborish, shuningdek rasmiy hujjatlarni ko‘rish mumkin.", "Бот орқали тайёр савол-жавоблар билан танишиш, мурожаат ва таклиф юбориш, шунингдек расмий ҳужжатлар билан танишиш мумкин.", "Через бот можно ознакомиться с готовыми вопросами и ответами, отправить обращение или предложение, а также просмотреть официальные документы.", "The bot lets you browse prepared questions and answers, submit appeals and suggestions, and view official documents."),
            },
            {
                "question": _l("Ma’lumotlarim xavfsizmi?", "Маълумотларим хавфсизми?", "Безопасны ли мои данные?", "Is my information secure?"),
                "answer": _l("Siz kiritgan ma’lumotlar xizmat ko‘rsatish maqsadida ishlatiladi va amaldagi qonunchilikka muvofiq himoya qilinadi.", "Сиз киритган маълумотлар хизмат кўрсатиш мақсадида ишлатилади ва амалдаги қонунчиликка мувофиқ ҳимояланади.", "Введенные вами данные используются для оказания услуги и защищаются в соответствии с действующим законодательством.", "The information you provide is used to deliver the service and is protected in accordance with applicable legislation."),
            },
            {
                "question": _l("Murojaatimga qachon javob olaman?", "Мурожаатимга қачон жавоб оламан?", "Когда я получу ответ на обращение?", "When will I receive a response to my appeal?"),
                "answer": _l("Murojaatlar mas’ul xodimlar tomonidan imkon qadar qisqa muddatda ko‘rib chiqiladi.", "Мурожаатлар масъул ходимлар томонидан имкон қадар қисқа муддатда кўриб чиқилади.", "Обращения рассматриваются ответственными сотрудниками в максимально короткие сроки.", "Appeals are reviewed by responsible staff as promptly as possible."),
            },
            {
                "question": _l("Savolimga javob topolmadim, nima qilishim kerak?", "Саволимга жавоб тополмадим, нима қилишим керак?", "Что делать, если я не нашел ответ на свой вопрос?", "What should I do if I cannot find an answer to my question?"),
                "answer": _l("Bunday holatda «📨 Murojaat yuborish» bo‘limi orqali savolingizni yozib yuborishingiz mumkin.", "Бундай ҳолда «📨 Мурожаат юбориш» бўлими орқали саволингизни ёзиб юборишингиз мумкин.", "В таком случае отправьте свой вопрос через раздел «📨 Отправить обращение».", "In that case, send your question through the “📨 Submit an appeal” section."),
            },
        ],
    },
]


def _localized(value: object, language_code: str | None) -> str:
    if not isinstance(value, dict):
        return str(value)
    language = normalize_language(language_code)
    return value.get(language) or value.get(DEFAULT_LANGUAGE) or next(iter(value.values()), "")


def get_category(category_id: str) -> dict | None:
    for category in FAQ_CATEGORIES:
        if category["id"] == category_id:
            return category
    return None


def get_question(category_id: str, question_index: int) -> dict | None:
    category = get_category(category_id)
    if category is None:
        return None
    questions = category["questions"]
    return questions[question_index] if 0 <= question_index < len(questions) else None


def category_title(category: dict, language_code: str | None = None) -> str:
    return _localized(category.get("title", ""), language_code)


def question_text(question: dict, language_code: str | None = None) -> str:
    return _localized(question.get("question", ""), language_code)


def answer_text(question: dict, language_code: str | None = None) -> str:
    return _localized(question.get("answer", ""), language_code)
