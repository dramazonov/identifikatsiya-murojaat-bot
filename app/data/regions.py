"""Static administrative hierarchy of the Republic of Uzbekistan.

Kept locally (no external APIs / scraping) as required for Stage 3.

``REGIONS_DATA`` is an ordered list of (region_name, [district/city names]).
Region and district indexes (their position in these lists) are used as
compact callback_data identifiers instead of the raw Cyrillic names.
"""

from __future__ import annotations

REGIONS_DATA: list[tuple[str, list[str]]] = [
    (
        "Қорақалпоғистон Республикаси",
        [
            "Нукус шаҳри",
            "Амударё тумани",
            "Беруний тумани",
            "Бўзатов тумани",
            "Кегейли тумани",
            "Мўйноқ тумани",
            "Нукус тумани",
            "Қанлиқўл тумани",
            "Қораўзак тумани",
            "Қўнғирот тумани",
            "Тахтакўпир тумани",
            "Тўрткўл тумани",
            "Хўжайли тумани",
            "Чимбой тумани",
            "Шуманай тумани",
            "Элликқалъа тумани",
        ],
    ),
    (
        "Андижон вилояти",
        [
            "Андижон шаҳри",
            "Хонобод шаҳри",
            "Андижон тумани",
            "Асака тумани",
            "Балиқчи тумани",
            "Булоқбоши тумани",
            "Бўз тумани",
            "Жалақудуқ тумани",
            "Избоскан тумани",
            "Қорадарё тумани",
            "Қўрғонтепа тумани",
            "Марҳамат тумани",
            "Олтинкўл тумани",
            "Пахтаобод тумани",
            "Улуғнор тумани",
            "Хўжаобод тумани",
            "Шаҳрихон тумани",
        ],
    ),
    (
        "Бухоро вилояти",
        [
            "Бухоро шаҳри",
            "Когон шаҳри",
            "Бухоро тумани",
            "Вобкент тумани",
            "Ғиждувон тумани",
            "Жондор тумани",
            "Когон тумани",
            "Олот тумани",
            "Пешку тумани",
            "Қоракўл тумани",
            "Қоровулбозор тумани",
            "Ромитан тумани",
            "Шофиркон тумани",
        ],
    ),
    (
        "Жиззах вилояти",
        [
            "Жиззах шаҳри",
            "Арнасой тумани",
            "Бахмал тумани",
            "Ғаллаорол тумани",
            "Дўстлик тумани",
            "Зафаробод тумани",
            "Зарбдор тумани",
            "Зомин тумани",
            "Мирзачўл тумани",
            "Пахтакор тумани",
            "Фориш тумани",
            "Шароф Рашидов тумани",
            "Янгиобод тумани",
        ],
    ),
    (
        "Қашқадарё вилояти",
        [
            "Қарши шаҳри",
            "Шаҳрисабз шаҳри",
            "Ғузор тумани",
            "Дехқонобод тумани",
            "Камаши тумани",
            "Касби тумани",
            "Китоб тумани",
            "Косон тумани",
            "Миришкор тумани",
            "Муборак тумани",
            "Нишон тумани",
            "Қамаши тумани",
            "Қарши тумани",
            "Чироқчи тумани",
            "Шаҳрисабз тумани",
            "Яккабоғ тумани",
        ],
    ),
    (
        "Навоий вилояти",
        [
            "Навоий шаҳри",
            "Зарафшон шаҳри",
            "Учқудуқ шаҳри",
            "Ғазли шаҳри",
            "Қизилтепа тумани",
            "Конимех тумани",
            "Кармана тумани",
            "Навбаҳор тумани",
            "Нурота тумани",
            "Томди тумани",
            "Учқудуқ тумани",
            "Хатирчи тумани",
        ],
    ),
    (
        "Наманган вилояти",
        [
            "Наманган шаҳри",
            "Косонсой тумани",
            "Минг булоқ тумани",
            "Норин тумани",
            "Поп тумани",
            "Тўрақўрғон тумани",
            "Уйчи тумани",
            "Учқўрғон тумани",
            "Чортоқ тумани",
            "Чуст тумани",
            "Янгиқўрғон тумани",
            "Наманган тумани",
        ],
    ),
    (
        "Самарқанд вилояти",
        [
            "Самарқанд шаҳри",
            "Каттақўрғон шаҳри",
            "Булунғур тумани",
            "Иштихон тумани",
            "Жомбой тумани",
            "Каттақўрғон тумани",
            "Қўшработ тумани",
            "Нарпай тумани",
            "Нуробод тумани",
            "Оқдарё тумани",
            "Пайариқ тумани",
            "Пастдарғом тумани",
            "Пахтачи тумани",
            "Самарқанд тумани",
            "Тайлоқ тумани",
            "Ургут тумани",
        ],
    ),
    (
        "Сурхондарё вилояти",
        [
            "Термиз шаҳри",
            "Ангор тумани",
            "Бандихон тумани",
            "Бойсун тумани",
            "Денов тумани",
            "Жарқўрғон тумани",
            "Музработ тумани",
            "Олтинсой тумани",
            "Сариосиё тумани",
            "Термиз тумани",
            "Узун тумани",
            "Шеробод тумани",
            "Шўрчи тумани",
            "Қизириқ тумани",
            "Қумқўрғон тумани",
        ],
    ),
    (
        "Сирдарё вилояти",
        [
            "Гулистон шаҳри",
            "Ширин шаҳри",
            "Ёнгиер шаҳри",
            "Боёвут тумани",
            "Гулистон тумани",
            "Мирзаобод тумани",
            "Оқолтин тумани",
            "Сайхунобод тумани",
            "Сирдарё тумани",
            "Хавос тумани",
            "Ширин тумани",
        ],
    ),
    (
        "Тошкент вилояти",
        [
            "Ангрен шаҳри",
            "Бекобод шаҳри",
            "Олмалиқ шаҳри",
            "Чирчиқ шаҳри",
            "Янгийўл шаҳри",
            "Охангарон тумани",
            "Бекобод тумани",
            "Бўка тумани",
            "Бўстонлиқ тумани",
            "Зангиота тумани",
            "Қибрай тумани",
            "Қуйичирчиқ тумани",
            "Оққўрғон тумани",
            "Паркент тумани",
            "Пскент тумани",
            "Тошкент тумани",
            "Ўрта Чирчиқ тумани",
            "Чиноз тумани",
            "Юқори Чирчиқ тумани",
        ],
    ),
    (
        "Фарғона вилояти",
        [
            "Фарғона шаҳри",
            "Қўқон шаҳри",
            "Қувасой шаҳри",
            "Марғилон шаҳри",
            "Олтиариқ тумани",
            "Бағдод тумани",
            "Бешариқ тумани",
            "Бувайда тумани",
            "Данғара тумани",
            "Дўстлик тумани",
            "Қува тумани",
            "Қувасой тумани",
            "Риштон тумани",
            "Сўх тумани",
            "Тошлоқ тумани",
            "Ўзбекистон тумани",
            "Учкўприк тумани",
            "Фарғона тумани",
            "Фурқат тумани",
            "Ясши тумани",
        ],
    ),
    (
        "Хоразм вилояти",
        [
            "Урганч шаҳри",
            "Хива шаҳри",
            "Боғот тумани",
            "Гурлан тумани",
            "Хазорасп тумани",
            "Хива тумани",
            "Хонқа тумани",
            "Қўшкўпир тумани",
            "Шовот тумани",
            "Урганч тумани",
            "Янгиариқ тумани",
            "Янгибозор тумани",
        ],
    ),
    (
        "Тошкент шаҳри",
        [
            "Бектемир тумани",
            "Мирзо Улуғбек тумани",
            "Миробод тумани",
            "Олмазор тумани",
            "Сирғали тумани",
            "Учтепа тумани",
            "Чилонзор тумани",
            "Шайхонтоҳур тумани",
            "Юнусобод тумани",
            "Яккасарой тумани",
            "Яшнобод тумани",
        ],
    ),
]

# Ordered list of region names (index == region_id used in callback_data).
REGIONS: list[str] = [name for name, _ in REGIONS_DATA]

# region_id -> list of district/city names (index == district_id).
DISTRICTS: dict[int, list[str]] = {idx: districts for idx, (_, districts) in enumerate(REGIONS_DATA)}

# Citizen-facing localization -------------------------------------------------
# Canonical database values remain the Uzbek-Cyrillic names above for backward
# compatibility.  Only labels shown to the user are localized.

_REGION_LABELS: dict[str, dict[str, str]] = {
    "Қорақалпоғистон Республикаси": {"uz_latn": "Qoraqalpog‘iston Respublikasi", "uz_cyrl": "Қорақалпоғистон Республикаси", "ru": "Республика Каракалпакстан", "en": "Republic of Karakalpakstan"},
    "Андижон вилояти": {"uz_latn": "Andijon viloyati", "uz_cyrl": "Андижон вилояти", "ru": "Андижанская область", "en": "Andijan Region"},
    "Бухоро вилояти": {"uz_latn": "Buxoro viloyati", "uz_cyrl": "Бухоро вилояти", "ru": "Бухарская область", "en": "Bukhara Region"},
    "Жиззах вилояти": {"uz_latn": "Jizzax viloyati", "uz_cyrl": "Жиззах вилояти", "ru": "Джизакская область", "en": "Jizzakh Region"},
    "Қашқадарё вилояти": {"uz_latn": "Qashqadaryo viloyati", "uz_cyrl": "Қашқадарё вилояти", "ru": "Кашкадарьинская область", "en": "Kashkadarya Region"},
    "Навоий вилояти": {"uz_latn": "Navoiy viloyati", "uz_cyrl": "Навоий вилояти", "ru": "Навоийская область", "en": "Navoi Region"},
    "Наманган вилояти": {"uz_latn": "Namangan viloyati", "uz_cyrl": "Наманган вилояти", "ru": "Наманганская область", "en": "Namangan Region"},
    "Самарқанд вилояти": {"uz_latn": "Samarqand viloyati", "uz_cyrl": "Самарқанд вилояти", "ru": "Самаркандская область", "en": "Samarkand Region"},
    "Сурхондарё вилояти": {"uz_latn": "Surxondaryo viloyati", "uz_cyrl": "Сурхондарё вилояти", "ru": "Сурхандарьинская область", "en": "Surkhandarya Region"},
    "Сирдарё вилояти": {"uz_latn": "Sirdaryo viloyati", "uz_cyrl": "Сирдарё вилояти", "ru": "Сырдарьинская область", "en": "Syrdarya Region"},
    "Тошкент вилояти": {"uz_latn": "Toshkent viloyati", "uz_cyrl": "Тошкент вилояти", "ru": "Ташкентская область", "en": "Tashkent Region"},
    "Фарғона вилояти": {"uz_latn": "Farg‘ona viloyati", "uz_cyrl": "Фарғона вилояти", "ru": "Ферганская область", "en": "Fergana Region"},
    "Хоразм вилояти": {"uz_latn": "Xorazm viloyati", "uz_cyrl": "Хоразм вилояти", "ru": "Хорезмская область", "en": "Khorezm Region"},
    "Тошкент шаҳри": {"uz_latn": "Toshkent shahri", "uz_cyrl": "Тошкент шаҳри", "ru": "город Ташкент", "en": "Tashkent City"},
}

_CYR_TO_LAT = {
    "А":"A","а":"a","Б":"B","б":"b","В":"V","в":"v","Г":"G","г":"g",
    "Д":"D","д":"d","Е":"E","е":"e","Ё":"Yo","ё":"yo","Ж":"J","ж":"j",
    "З":"Z","з":"z","И":"I","и":"i","Й":"Y","й":"y","К":"K","к":"k",
    "Л":"L","л":"l","М":"M","м":"m","Н":"N","н":"n","О":"O","о":"o",
    "П":"P","п":"p","Р":"R","р":"r","С":"S","с":"s","Т":"T","т":"t",
    "У":"U","у":"u","Ф":"F","ф":"f","Х":"X","х":"x","Ц":"S","ц":"s",
    "Ч":"Ch","ч":"ch","Ш":"Sh","ш":"sh","Ъ":"’","ъ":"’","Ь":"","ь":"",
    "Э":"E","э":"e","Ю":"Yu","ю":"yu","Я":"Ya","я":"ya","Ў":"O‘","ў":"o‘",
    "Қ":"Q","қ":"q","Ғ":"G‘","ғ":"g‘","Ҳ":"H","ҳ":"h",
}

_RU_REPLACEMENTS = (
    ("Тошкент", "Ташкент"), ("Андижон", "Андижан"), ("Бухоро", "Бухара"),
    ("Жиззах", "Джизак"), ("Қашқадарё", "Кашкадарья"), ("Самарқанд", "Самарканд"),
    ("Сурхондарё", "Сурхандарья"), ("Сирдарё", "Сырдарья"), ("Фарғона", "Фергана"),
    ("Хоразм", "Хорезм"), ("Юнусобод", "Юнусабад"), ("Чилонзор", "Чиланзар"),
    ("Мирзо Улуғбек", "Мирзо-Улугбек"), ("Шайхонтоҳур", "Шайхантахур"),
    ("Олмазор", "Алмазар"), ("Яшнобод", "Яшнабад"), ("Яккасарой", "Яккасарай"),
)


def _uz_cyr_to_latn(text: str) -> str:
    return "".join(_CYR_TO_LAT.get(ch, ch) for ch in text)


def _ru_proper(text: str) -> str:
    for old, new in _RU_REPLACEMENTS:
        text = text.replace(old, new)
    return (text.replace("Қ", "К").replace("қ", "к").replace("Ғ", "Г").replace("ғ", "г")
                .replace("Ў", "У").replace("ў", "у").replace("Ҳ", "Х").replace("ҳ", "х"))


def localize_region_name(canonical_name: str, language_code: str | None = None) -> str:
    language = language_code if language_code in {"uz_latn", "uz_cyrl", "ru", "en"} else "uz_cyrl"
    labels = _REGION_LABELS.get(canonical_name)
    if labels:
        return labels[language]
    return canonical_name if language == "uz_cyrl" else _uz_cyr_to_latn(canonical_name)


def localize_district_name(canonical_name: str, language_code: str | None = None) -> str:
    language = language_code if language_code in {"uz_latn", "uz_cyrl", "ru", "en"} else "uz_cyrl"
    if language == "uz_cyrl":
        return canonical_name
    if canonical_name.endswith(" шаҳри"):
        stem = canonical_name[:-6]
        if language == "uz_latn":
            return f"{_uz_cyr_to_latn(stem)} shahri"
        if language == "en":
            return f"{_uz_cyr_to_latn(stem)} City"
        return f"город {_ru_proper(stem)}"
    if canonical_name.endswith(" тумани"):
        stem = canonical_name[:-7]
        if language == "uz_latn":
            return f"{_uz_cyr_to_latn(stem)} tumani"
        if language == "en":
            return f"{_uz_cyr_to_latn(stem)} District"
        return f"район {_ru_proper(stem)}"
    if language == "ru":
        return _ru_proper(canonical_name)
    return _uz_cyr_to_latn(canonical_name)


def region_label(region_id: int, language_code: str | None = None) -> str:
    return localize_region_name(REGIONS[region_id], language_code)


def district_label(region_id: int, district_id: int, language_code: str | None = None) -> str:
    return localize_district_name(DISTRICTS[region_id][district_id], language_code)


def localize_location_value(canonical_name: str | None, language_code: str | None = None) -> str:
    if not canonical_name:
        return "—"
    if canonical_name in REGIONS:
        return localize_region_name(canonical_name, language_code)
    for districts in DISTRICTS.values():
        if canonical_name in districts:
            return localize_district_name(canonical_name, language_code)
    return canonical_name
