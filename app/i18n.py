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
    "menu.my_appeals": {
        "uz_latn": "📂 Mening murojaatlarim",
        "uz_cyrl": "📂 Менинг мурожаатларим",
        "ru": "📂 Мои обращения",
        "en": "📂 My appeals",
    },
    "menu.settings": {
        "uz_latn": "⚙️ Sozlamalar",
        "uz_cyrl": "⚙️ Созламалар",
        "ru": "⚙️ Настройки",
        "en": "⚙️ Settings",
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
    "button.previous": {
        "uz_latn": "⬅️ Oldingi",
        "uz_cyrl": "⬅️ Олдинги",
        "ru": "⬅️ Назад",
        "en": "⬅️ Previous",
    },
    "button.next": {
        "uz_latn": "Keyingi ➡️",
        "uz_cyrl": "Кейинги ➡️",
        "ru": "Вперёд ➡️",
        "en": "Next ➡️",
    },
    "button.official_source": {
        "uz_latn": "🔗 Rasmiy manba",
        "uz_cyrl": "🔗 Расмий манба",
        "ru": "🔗 Официальный источник",
        "en": "🔗 Official source",
    },
    "appeal.category_prompt": {
        "uz_latn": "Murojaat yo‘nalishini tanlang:",
        "uz_cyrl": "Мурожаат йўналишини танланг:",
        "ru": "Выберите категорию обращения:",
        "en": "Select an appeal category:",
    },
    "appeal.category.identification": {
        "uz_latn": "🐄 Hayvonlarni identifikatsiya qilish",
        "uz_cyrl": "🐄 Ҳайвонларни идентификация қилиш",
        "ru": "🐄 Идентификация животных",
        "en": "🐄 Animal identification",
    },
    "appeal.category.tag": {
        "uz_latn": "🏷 Birka / identifikatsiya raqami",
        "uz_cyrl": "🏷 Бирка / идентификация рақами",
        "ru": "🏷 Бирка / идентификационный номер",
        "en": "🏷 Tag / identification number",
    },
    "appeal.category.registration": {
        "uz_latn": "📝 Ro‘yxatga olish",
        "uz_cyrl": "📝 Рўйхатга олиш",
        "ru": "📝 Регистрация",
        "en": "📝 Registration",
    },
    "appeal.category.deregistration": {
        "uz_latn": "📤 Hisobdan chiqarish",
        "uz_cyrl": "📤 Ҳисобдан чиқариш",
        "ru": "📤 Снятие с учёта",
        "en": "📤 Deregistration",
    },
    "appeal.category.database": {
        "uz_latn": "💾 Elektron baza",
        "uz_cyrl": "💾 Электрон база",
        "ru": "💾 Электронная база",
        "en": "💾 Electronic database",
    },
    "appeal.category.technical": {
        "uz_latn": "🛠 Texnik muammo",
        "uz_cyrl": "🛠 Техник муаммо",
        "ru": "🛠 Техническая проблема",
        "en": "🛠 Technical issue",
    },
    "appeal.category.legislation": {
        "uz_latn": "⚖️ Qonunchilik bo‘yicha savol",
        "uz_cyrl": "⚖️ Қонунчилик бўйича савол",
        "ru": "⚖️ Вопрос по законодательству",
        "en": "⚖️ Legislation question",
    },
    "appeal.category.other": {
        "uz_latn": "📌 Boshqa",
        "uz_cyrl": "📌 Бошқа",
        "ru": "📌 Другое",
        "en": "📌 Other",
    },
    "appeal.subject_prompt": {
        "uz_latn": "Murojaat mavzusini qisqacha yozing (3–200 ta belgi):",
        "uz_cyrl": "Мурожаат мавзусини қисқача ёзинг (3–200 та белги):",
        "ru": "Кратко укажите тему обращения (3–200 символов):",
        "en": "Enter a short subject for the appeal (3–200 characters):",
    },
    "appeal.subject_invalid": {
        "uz_latn": "Mavzu noto‘g‘ri. 3–200 ta belgi kiriting.",
        "uz_cyrl": "Мавзу нотўғри. 3–200 та белги киритинг.",
        "ru": "Некорректная тема. Введите от 3 до 200 символов.",
        "en": "Invalid subject. Enter 3–200 characters.",
    },
    "appeal.text_prompt": {
        "uz_latn": "Endi murojaat mazmunini batafsil yozing (5–4000 ta belgi):",
        "uz_cyrl": "Энди мурожаат мазмунини батафсил ёзинг (5–4000 та белги):",
        "ru": "Теперь подробно опишите обращение (5–4000 символов):",
        "en": "Now describe your appeal in detail (5–4000 characters):",
    },
    "appeal.attachment_prompt": {
        "uz_latn": "📎 Zarur bo‘lsa bitta foto yoki PDF yuboring. Ilova kerak bo‘lmasa «O‘tkazib yuborish»ni bosing.",
        "uz_cyrl": "📎 Зарур бўлса битта фото ёки PDF юборинг. Илова керак бўлмаса «Ўтказиб юбориш»ни босинг.",
        "ru": "📎 При необходимости отправьте одно фото или PDF. Если файл не нужен, нажмите «Пропустить».",
        "en": "📎 Optionally send one photo or PDF. If no attachment is needed, tap “Skip”.",
    },
    "appeal.attachment_invalid": {
        "uz_latn": "Faqat bitta foto yoki PDF fayl qabul qilinadi.",
        "uz_cyrl": "Фақат битта фото ёки PDF файл қабул қилинади.",
        "ru": "Принимается только одно фото или PDF-файл.",
        "en": "Only one photo or PDF file is accepted.",
    },
    "appeal.attachment_too_large": {
        "uz_latn": "Fayl hajmi juda katta. Foto 10 MB, PDF 20 MB gacha bo‘lishi mumkin.",
        "uz_cyrl": "Файл ҳажми жуда катта. Фото 10 MB, PDF 20 MB гача бўлиши мумкин.",
        "ru": "Файл слишком большой. Фото — до 10 МБ, PDF — до 20 МБ.",
        "en": "The file is too large. Photos may be up to 10 MB and PDFs up to 20 MB.",
    },
    "appeal.attachment.none": {
        "uz_latn": "Yo‘q", "uz_cyrl": "Йўқ", "ru": "Нет", "en": "None",
    },
    "appeal.attachment.photo": {
        "uz_latn": "Foto", "uz_cyrl": "Фото", "ru": "Фото", "en": "Photo",
    },
    "appeal.attachment.pdf": {
        "uz_latn": "PDF hujjat", "uz_cyrl": "PDF ҳужжат", "ru": "PDF-документ", "en": "PDF document",
    },
    "appeal.confirmation": {
        "uz_latn": "✅ Murojaatni tekshiring:\n\nYo‘nalish: {category}\nMavzu: {subject}\nIlova: {attachment}\n\nMurojaat matni:\n{appeal_text}\n\nMa’lumotlar to‘g‘ri bo‘lsa, tasdiqlang.",
        "uz_cyrl": "✅ Мурожаатни текширинг:\n\nЙўналиш: {category}\nМавзу: {subject}\nИлова: {attachment}\n\nМурожаат матни:\n{appeal_text}\n\nМаълумотлар тўғри бўлса, тасдиқланг.",
        "ru": "✅ Проверьте обращение:\n\nКатегория: {category}\nТема: {subject}\nВложение: {attachment}\n\nТекст обращения:\n{appeal_text}\n\nЕсли всё верно, подтвердите отправку.",
        "en": "✅ Review your appeal:\n\nCategory: {category}\nSubject: {subject}\nAttachment: {attachment}\n\nAppeal text:\n{appeal_text}\n\nIf everything is correct, confirm submission.",
    },
    "appeal.confirm": {
        "uz_latn": "✅ Tasdiqlash va yuborish",
        "uz_cyrl": "✅ Тасдиқлаш ва юбориш",
        "ru": "✅ Подтвердить и отправить",
        "en": "✅ Confirm and send",
    },
    "appeal.cancel": {
        "uz_latn": "❌ Bekor qilish",
        "uz_cyrl": "❌ Бекор қилиш",
        "ru": "❌ Отменить",
        "en": "❌ Cancel",
    },
    "appeal.skip_attachment": {
        "uz_latn": "⏭ O‘tkazib yuborish",
        "uz_cyrl": "⏭ Ўтказиб юбориш",
        "ru": "⏭ Пропустить",
        "en": "⏭ Skip",
    },
    "appeal.cancelled": {
        "uz_latn": "Murojaat yuborish bekor qilindi.",
        "uz_cyrl": "Мурожаат юбориш бекор қилинди.",
        "ru": "Отправка обращения отменена.",
        "en": "Appeal submission cancelled.",
    },
    "appeal.success_v2": {
        "uz_latn": "✅ Murojaatingiz qabul qilindi.\n\nMurojaat raqami: {appeal_number}\nHolat: Yangi\n\nMurojaatingiz mas’ul xodimlar tomonidan ko‘rib chiqiladi.",
        "uz_cyrl": "✅ Мурожаатингиз қабул қилинди.\n\nМурожаат рақами: {appeal_number}\nҲолат: Янги\n\nМурожаатингиз масъул ходимлар томонидан кўриб чиқилади.",
        "ru": "✅ Ваше обращение принято.\n\nНомер обращения: {appeal_number}\nСтатус: Новое\n\nОбращение будет рассмотрено ответственными сотрудниками.",
        "en": "✅ Your appeal has been accepted.\n\nAppeal number: {appeal_number}\nStatus: New\n\nIt will be reviewed by responsible staff.",
    },
    "appeal.status_changed": {
        "uz_latn": "📌 {appeal_number} murojaatingiz holati yangilandi: {status}",
        "uz_cyrl": "📌 {appeal_number} мурожаатингиз ҳолати янгиланди: {status}",
        "ru": "📌 Статус обращения {appeal_number} обновлён: {status}",
        "en": "📌 Appeal {appeal_number} status updated: {status}",
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
        "uz_latn": "📩 <b>Murojaatingiz bo‘yicha javob</b>\n\n🆔 <b>Murojaat raqami:</b> {appeal_number}\n\n📝 <b>Javob:</b>\n\n{admin_answer}\n\n✅ <b>Holat:</b> Yakunlangan\n\nMurojaatingiz ko‘rib chiqildi. Rahmat!",
        "uz_cyrl": "📩 <b>Мурожаатингиз бўйича жавоб</b>\n\n🆔 <b>Мурожаат рақами:</b> {appeal_number}\n\n📝 <b>Жавоб:</b>\n\n{admin_answer}\n\n✅ <b>Ҳолат:</b> Якунланган\n\nМурожаатингиз кўриб чиқилди. Раҳмат!",
        "ru": "📩 <b>Ответ по вашему обращению</b>\n\n🆔 <b>Номер обращения:</b> {appeal_number}\n\n📝 <b>Ответ:</b>\n\n{admin_answer}\n\n✅ <b>Статус:</b> Завершено\n\nВаше обращение рассмотрено. Спасибо!",
        "en": "📩 <b>Response to your appeal</b>\n\n🆔 <b>Appeal number:</b> {appeal_number}\n\n📝 <b>Response:</b>\n\n{admin_answer}\n\n✅ <b>Status:</b> Completed\n\nYour appeal has been reviewed. Thank you!",
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
    "common.invalid_action": {
        "uz_latn": "Noto‘g‘ri amal. Iltimos, menyudan qayta tanlang.",
        "uz_cyrl": "Нотўғри амал. Илтимос, менюдан қайта танланг.",
        "ru": "Некорректное действие. Пожалуйста, выберите пункт меню заново.",
        "en": "Invalid action. Please choose again from the menu.",
    },
    "my_appeals.title": {
        "uz_latn": "📂 Mening murojaatlarim\n\nJami: {total} ta\nSahifa: {current_page}/{total_pages}\n\nKo‘rish uchun murojaat raqamini tanlang:",
        "uz_cyrl": "📂 Менинг мурожаатларим\n\nЖами: {total} та\nСаҳифа: {current_page}/{total_pages}\n\nКўриш учун мурожаат рақамини танланг:",
        "ru": "📂 Мои обращения\n\nВсего: {total}\nСтраница: {current_page}/{total_pages}\n\nВыберите номер обращения:",
        "en": "📂 My appeals\n\nTotal: {total}\nPage: {current_page}/{total_pages}\n\nSelect an appeal number to view it:",
    },
    "my_appeals.empty": {
        "uz_latn": "📂 Sizda hozircha yuborilgan murojaatlar yo‘q.",
        "uz_cyrl": "📂 Сизда ҳозирча юборилган мурожаатлар йўқ.",
        "ru": "📂 У вас пока нет отправленных обращений.",
        "en": "📂 You have not submitted any appeals yet.",
    },
    "my_appeals.empty_short": {
        "uz_latn": "Murojaatlar topilmadi.",
        "uz_cyrl": "Мурожаатлар топилмади.",
        "ru": "Обращения не найдены.",
        "en": "No appeals found.",
    },
    "my_appeals.not_found": {
        "uz_latn": "Bu murojaat topilmadi yoki sizga tegishli emas.",
        "uz_cyrl": "Бу мурожаат топилмади ёки сизга тегишли эмас.",
        "ru": "Обращение не найдено или не принадлежит вам.",
        "en": "This appeal was not found or does not belong to you.",
    },
    "my_appeals.no_answer": {
        "uz_latn": "Hozircha javob berilmagan.",
        "uz_cyrl": "Ҳозирча жавоб берилмаган.",
        "ru": "Ответ пока не предоставлен.",
        "en": "No response has been provided yet.",
    },
    "my_appeals.detail": {
        "uz_latn": "📄 Murojaat tafsilotlari\n\n🆔 Raqam: {appeal_number}\n📅 Sana: {created_at}\n📌 Holat: {status}\n🗂 Yo‘nalish: {category}\n📋 Mavzu: {subject}\n📎 Ilova: {attachment}\n\n📝 Murojaat matni:\n{appeal_text}\n\n💬 Admin javobi:\n{admin_answer}",
        "uz_cyrl": "📄 Мурожаат тафсилотлари\n\n🆔 Рақам: {appeal_number}\n📅 Сана: {created_at}\n📌 Ҳолат: {status}\n🗂 Йўналиш: {category}\n📋 Мавзу: {subject}\n📎 Илова: {attachment}\n\n📝 Мурожаат матни:\n{appeal_text}\n\n💬 Админ жавоби:\n{admin_answer}",
        "ru": "📄 Детали обращения\n\n🆔 Номер: {appeal_number}\n📅 Дата: {created_at}\n📌 Статус: {status}\n🗂 Категория: {category}\n📋 Тема: {subject}\n📎 Вложение: {attachment}\n\n📝 Текст обращения:\n{appeal_text}\n\n💬 Ответ администратора:\n{admin_answer}",
        "en": "📄 Appeal details\n\n🆔 Number: {appeal_number}\n📅 Date: {created_at}\n📌 Status: {status}\n🗂 Category: {category}\n📋 Subject: {subject}\n📎 Attachment: {attachment}\n\n📝 Appeal text:\n{appeal_text}\n\n💬 Administrator response:\n{admin_answer}",
    },
    "status.new": {
        "uz_latn": "Yangi", "uz_cyrl": "Янги", "ru": "Новое", "en": "New",
    },
    "status.in_progress": {
        "uz_latn": "Ko‘rib chiqilmoqda", "uz_cyrl": "Кўриб чиқилмоқда", "ru": "На рассмотрении", "en": "In progress",
    },
    "status.waiting_for_user": {
        "uz_latn": "Foydalanuvchi javobi kutilmoqda", "uz_cyrl": "Фойдаланувчи жавоби кутилмоқда", "ru": "Ожидается ответ пользователя", "en": "Waiting for user",
    },
    "status.completed": {
        "uz_latn": "Yakunlangan", "uz_cyrl": "Якунланган", "ru": "Завершено", "en": "Completed",
    },
    "status.rejected": {
        "uz_latn": "Rad etilgan", "uz_cyrl": "Рад этилган", "ru": "Отклонено", "en": "Rejected",
    },
    "status.unknown": {
        "uz_latn": "Noma’lum", "uz_cyrl": "Номаълум", "ru": "Неизвестно", "en": "Unknown",
    },
    "settings.title": {
        "uz_latn": "⚙️ Sozlamalar\n\nKerakli bo‘limni tanlang:",
        "uz_cyrl": "⚙️ Созламалар\n\nКеракли бўлимни танланг:",
        "ru": "⚙️ Настройки\n\nВыберите раздел:",
        "en": "⚙️ Settings\n\nChoose a section:",
    },
    "settings.profile": {
        "uz_latn": "👤 Profil", "uz_cyrl": "👤 Профил", "ru": "👤 Профиль", "en": "👤 Profile",
    },
    "settings.language": {
        "uz_latn": "🌐 Tilni o‘zgartirish", "uz_cyrl": "🌐 Тилни ўзгартириш", "ru": "🌐 Изменить язык", "en": "🌐 Change language",
    },
    "settings.phone": {
        "uz_latn": "📱 Telefon raqamini yangilash", "uz_cyrl": "📱 Телефон рақамини янгилаш", "ru": "📱 Обновить номер телефона", "en": "📱 Update phone number",
    },
    "settings.profile_text": {
        "uz_latn": "👤 Profil\n\nF.I.Sh.: {full_name}\nTelefon: {phone}\nTelefon tasdiqlangan: {verified}\nViloyat: {region}\nTuman/shahar: {district}\nTil: {language}",
        "uz_cyrl": "👤 Профил\n\nФ.И.Ш.: {full_name}\nТелефон: {phone}\nТелефон тасдиқланган: {verified}\nВилоят: {region}\nТуман/шаҳар: {district}\nТил: {language}",
        "ru": "👤 Профиль\n\nФ.И.О.: {full_name}\nТелефон: {phone}\nТелефон подтверждён: {verified}\nОбласть: {region}\nРайон/город: {district}\nЯзык: {language}",
        "en": "👤 Profile\n\nFull name: {full_name}\nPhone: {phone}\nPhone verified: {verified}\nRegion: {region}\nDistrict/city: {district}\nLanguage: {language}",
    },
    "settings.yes": {
        "uz_latn": "Ha", "uz_cyrl": "Ҳа", "ru": "Да", "en": "Yes",
    },
    "settings.no": {
        "uz_latn": "Yo‘q", "uz_cyrl": "Йўқ", "ru": "Нет", "en": "No",
    },
    "settings.profile_not_found": {
        "uz_latn": "Profil topilmadi. /start orqali qayta kiring.",
        "uz_cyrl": "Профил топилмади. /start орқали қайта киринг.",
        "ru": "Профиль не найден. Запустите /start повторно.",
        "en": "Profile not found. Please run /start again.",
    },
    "settings.language_choose": {
        "uz_latn": "🌐 Yangi tilni tanlang:",
        "uz_cyrl": "🌐 Янги тилни танланг:",
        "ru": "🌐 Выберите новый язык:",
        "en": "🌐 Choose a new language:",
    },
    "settings.language_changed": {
        "uz_latn": "✅ Til muvaffaqiyatli o‘zgartirildi.",
        "uz_cyrl": "✅ Тил муваффақиятли ўзгартирилди.",
        "ru": "✅ Язык успешно изменён.",
        "en": "✅ Language changed successfully.",
    },
    "settings.phone_prompt": {
        "uz_latn": "📱 Yangi telefon raqamingizni quyidagi tugma orqali yuboring. Faqat o‘zingizning Telegram raqamingiz qabul qilinadi:",
        "uz_cyrl": "📱 Янги телефон рақамингизни қуйидаги тугма орқали юборинг. Фақат ўзингизнинг Telegram рақамингиз қабул қилинади:",
        "ru": "📱 Отправьте новый номер кнопкой ниже. Принимается только номер вашего Telegram-аккаунта:",
        "en": "📱 Share your new number using the button below. Only the number linked to your Telegram account is accepted:",
    },
    "settings.phone_changed": {
        "uz_latn": "✅ Telefon raqamingiz yangilandi va Telegram orqali tasdiqlandi.",
        "uz_cyrl": "✅ Телефон рақамингиз янгиланди ва Telegram орқали тасдиқланди.",
        "ru": "✅ Номер телефона обновлён и подтверждён через Telegram.",
        "en": "✅ Your phone number was updated and verified through Telegram.",
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


_APPEAL_CATEGORY_KEYS: Final[dict[str, str]] = {
    "IDENTIFICATION": "appeal.category.identification",
    "TAG": "appeal.category.tag",
    "REGISTRATION": "appeal.category.registration",
    "DEREGISTRATION": "appeal.category.deregistration",
    "DATABASE": "appeal.category.database",
    "TECHNICAL": "appeal.category.technical",
    "LEGISLATION": "appeal.category.legislation",
    "OTHER": "appeal.category.other",
}

_APPEAL_STATUS_KEYS: Final[dict[str, str]] = {
    "NEW": "status.new",
    "IN_PROGRESS": "status.in_progress",
    "WAITING_FOR_USER": "status.waiting_for_user",
    "COMPLETED": "status.completed",
    "REJECTED": "status.rejected",
}


def appeal_category_text(category_code: str | None, language_code: str | None = None) -> str:
    key = _APPEAL_CATEGORY_KEYS.get(category_code or "OTHER", "appeal.category.other")
    return t(key, language_code)


def appeal_status_text(status: str | None, language_code: str | None = None) -> str:
    key = _APPEAL_STATUS_KEYS.get(status or "")
    return t(key, language_code) if key else t("status.unknown", language_code)


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
