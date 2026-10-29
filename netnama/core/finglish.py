"""Suggest a domain label from Persian text.

Short vowels are not written in Persian, so the Latin form is a suggestion.
Callers keep the original text and let the user edit the label.
"""

import re
import unicodedata

_DIACRITICS = re.compile(r"[\u064b-\u0652\u0670\u0640]")
_LATIN_WORD = re.compile(r"[A-Za-z][A-Za-z0-9-]*$")
_VOWEL_LETTERS = set("اآوی")
_CONSONANTS = {
    "ب": "b",
    "پ": "p",
    "ت": "t",
    "ث": "s",
    "ج": "j",
    "چ": "ch",
    "ح": "h",
    "خ": "kh",
    "د": "d",
    "ذ": "z",
    "ر": "r",
    "ز": "z",
    "ژ": "zh",
    "س": "s",
    "ش": "sh",
    "ص": "s",
    "ض": "z",
    "ط": "t",
    "ظ": "z",
    "غ": "gh",
    "ف": "f",
    "ق": "q",
    "ک": "k",
    "گ": "g",
    "ل": "l",
    "م": "m",
    "ن": "n",
    "ه": "h",
}

# Readings that the letter-by-letter rules miss. Keys are normalized Persian.
LEXICON = {
    "نگین": "negin",
    "آرمین": "armin",
    "آرمیتا": "armita",
    "آرمینا": "armina",
    "آرمان": "arman",
    "آراد": "arad",
    "آرتین": "artin",
    "آریا": "arya",
    "آریو": "ario",
    "آریانا": "ariana",
    "آرش": "arash",
    "آوا": "ava",
    "آناهیتا": "anahita",
    "آنیتا": "anita",
    "آنوش": "anoush",
    "اسکندر": "eskandar",
    "اشکان": "ashkan",
    "افشین": "afshin",
    "امید": "omid",
    "امین": "amin",
    "امیر": "amir",
    "امیرعلی": "amirali",
    "ایلیا": "ilia",
    "بابک": "babak",
    "باران": "baran",
    "بردیا": "bardia",
    "بهار": "bahar",
    "بهاره": "bahareh",
    "بهرام": "bahram",
    "بهروز": "behrouz",
    "بهمن": "bahman",
    "بهنام": "behnam",
    "بهناز": "behnaz",
    "بهنوش": "behnoosh",
    "بیتا": "bita",
    "بیژن": "bijan",
    "بنفشه": "banafsheh",
    "پانیذ": "paniz",
    "پانتهآ": "pantea",
    "پارسا": "parsa",
    "پردیس": "pardis",
    "پروانه": "parvaneh",
    "پروین": "parvin",
    "پگاه": "pegah",
    "پویا": "pouya",
    "پیمان": "peyman",
    "ترانه": "taraneh",
    "ترنم": "taranom",
    "تارا": "tara",
    "تینا": "tina",
    "جمشید": "jamshid",
    "جواد": "javad",
    "حامد": "hamed",
    "حسام": "hesam",
    "حسین": "hossein",
    "حمید": "hamid",
    "حمیدرضا": "hamidreza",
    "خدیجه": "khadijeh",
    "خسرو": "khosrow",
    "داریوش": "dariush",
    "دانیال": "danial",
    "داوود": "davood",
    "درسا": "dorsa",
    "درنا": "dorna",
    "دریا": "darya",
    "دنیا": "donya",
    "دیبا": "diba",
    "دینا": "dina",
    "رادین": "radin",
    "راحله": "raheleh",
    "رامین": "ramin",
    "رضا": "reza",
    "رستم": "rostam",
    "رقیه": "roghayeh",
    "رها": "raha",
    "رهام": "roham",
    "روزبه": "roozbeh",
    "روشنک": "roshanak",
    "ریحانه": "reyhaneh",
    "زادین": "zadin",
    "زرین": "zarrin",
    "زهره": "zohreh",
    "زهرا": "zahra",
    "زیبا": "ziba",
    "زینب": "zeinab",
    "ژاله": "zhaleh",
    "ژیلا": "zhila",
    "ساحل": "sahel",
    "سارا": "sara",
    "سارنا": "sarina",
    "سارینا": "sarina",
    "سام": "sam",
    "سامان": "saman",
    "ساناز": "sanaz",
    "سپهر": "sepehr",
    "سپیده": "sepideh",
    "ستاره": "setareh",
    "سجاد": "sajjad",
    "سعید": "saeid",
    "سلما": "salma",
    "سمیرا": "samira",
    "سمیه": "somayeh",
    "سهراب": "sohrab",
    "سهند": "sahand",
    "سهیل": "soheil",
    "سوگند": "sogand",
    "سیاوش": "siavash",
    "سیما": "sima",
    "سیمین": "simin",
    "سینا": "sina",
    "شادی": "shadi",
    "شبنم": "shabnam",
    "شروین": "shervin",
    "شهرزاد": "shahrzad",
    "شهریار": "shahriar",
    "شهره": "shohreh",
    "شیدا": "sheyda",
    "شیرین": "shirin",
    "شیوا": "shiva",
    "شایان": "shayan",
    "صادق": "sadegh",
    "صابر": "saber",
    "طه": "taha",
    "عرفان": "erfan",
    "علی": "ali",
    "علیرضا": "alireza",
    "عماد": "emad",
    "غزل": "ghazal",
    "فاطمه": "fatemeh",
    "فرزاد": "farzad",
    "فرشته": "fereshteh",
    "فرزانه": "farzaneh",
    "فرهاد": "farhad",
    "فرید": "farid",
    "فریدون": "fereydoun",
    "فریبا": "fariba",
    "فروغ": "forough",
    "کتایون": "katayoun",
    "کوروش": "kourosh",
    "کوثر": "kowsar",
    "کاوه": "kaveh",
    "کامران": "kamran",
    "کامبیز": "kambiz",
    "کیمیا": "kimia",
    "کیان": "kian",
    "کیانوش": "kianoosh",
    "کیا": "kia",
    "کیارش": "kiarash",
    "گلنار": "golnar",
    "گلناز": "golnaz",
    "گلرخ": "golrokh",
    "گلشیفته": "golshifteh",
    "گیسو": "gisu",
    "گیتا": "gita",
    "لادن": "ladan",
    "لاله": "laleh",
    "لیلا": "leila",
    "لیان": "lian",
    "مائده": "maedeh",
    "مانا": "mana",
    "ماندانا": "mandana",
    "ماهان": "mahan",
    "ماهور": "mahour",
    "مبینا": "mobina",
    "مجتبی": "mojtaba",
    "محدثه": "mohadeseh",
    "محسن": "mohsen",
    "محمد": "mohammad",
    "محمدرضا": "mohammadreza",
    "محمدحسین": "mohammadhossein",
    "مرجان": "marjan",
    "مرضیه": "marzieh",
    "مریم": "maryam",
    "مروارید": "morvarid",
    "مسعود": "masoud",
    "معصومه": "masoumeh",
    "ملیکا": "melika",
    "ملینا": "melina",
    "مهدی": "mahdi",
    "مهرنوش": "mehrnoosh",
    "مهرناز": "mehrnaz",
    "مهسا": "mahsa",
    "مهتاب": "mahtab",
    "مهیا": "mahya",
    "میترا": "mitra",
    "میلاد": "milad",
    "مینا": "mina",
    "مینو": "minoo",
    "نازگل": "nazgol",
    "نازنین": "nazanin",
    "نازلی": "nazli",
    "ناهید": "nahid",
    "نجمه": "najmeh",
    "ندا": "neda",
    "نرگس": "narges",
    "نسرین": "nasrin",
    "نگار": "negar",
    "نیلوفر": "niloufar",
    "نیما": "nima",
    "نیکو": "nikoo",
    "نوشین": "noushin",
    "هادی": "hadi",
    "هستی": "hasti",
    "هلما": "helma",
    "هلیا": "helia",
    "هومن": "hooman",
    "وحید": "vahid",
    "ویانا": "viana",
    "یاسر": "yaser",
    "یاشار": "yashar",
    "یاسمین": "yasamin",
    "یلدا": "yalda",
    "یوسف": "yousef",
    "یسنا": "yasna",
    "یکتا": "yekta",
    "ابراهیم": "ebrahim",
    "احمد": "ahmad",
    "حسن": "hasan",
    "حدیث": "hadis",
    "سحر": "sahar",
    "الناز": "elnaz",
    "الهام": "elham",
    "الینا": "elina",
    "آیسان": "aysan",
    "پریسا": "parisa",
    "تهران": "tehran",
    "تبریز": "tabriz",
    "کاشان": "kashan",
    "اصفهان": "esfahan",
    "شیراز": "shiraz",
    "یزد": "yazd",
    "مشهد": "mashhad",
    "کرمان": "kerman",
    "قم": "qom",
    "رشت": "rasht",
    "اهواز": "ahvaz",
    "همدان": "hamedan",
    "زنجان": "zanjan",
    "سمنان": "semnan",
    "کرج": "karaj",
    "قزوین": "qazvin",
    "اردبیل": "ardabil",
    "بوشهر": "bushehr",
    "کرمانشاه": "kermanshah",
    "سنندج": "sanandaj",
    "گرگان": "gorgan",
    "ساری": "sari",
    "بابل": "babol",
    "نیشابور": "neyshabur",
    "کیش": "kish",
    "قشم": "qeshm",
    "ارومیه": "urmia",
    "زاهدان": "zahedan",
    "بندرعباس": "bandarabbas",
    "رفسنجان": "rafsanjan",
    "کاشمر": "kashmar",
    "بیرجند": "birjand",
    "ایلام": "ilam",
    "خرمآباد": "khorramabad",
    "اراک": "arak",
    "ساوه": "saveh",
    "ملایر": "malayer",
    "بروجرد": "borujerd",
    "دزفول": "dezful",
    "آبادان": "abadan",
    "خرمشهر": "khorramshahr",
    "یاسوج": "yasuj",
    "شهرکرد": "shahrekord",
    "زابل": "zabol",
    "چابهار": "chabahar",
    "بجنورد": "bojnord",
    "آمل": "amol",
    "قائمشهر": "qaemshahr",
    "ورامین": "varamin",
    "اسلامشهر": "eslamshahr",
    "ری": "rey",
    "خوی": "khoy",
    "سبزوار": "sabzevar",
    "شاهرود": "shahroud",
    "مراغه": "maragheh",
    "ایران": "iran",
    "فرش": "farsh",
    "قالی": "ghali",
    "گلیم": "gelim",
    "طلا": "tala",
    "نقره": "noghre",
    "جواهر": "javaher",
    "گالری": "gallery",
    "فروشگاه": "forushgah",
    "فروش": "forush",
    "خرید": "kharid",
    "خانه": "khane",
    "بازار": "bazar",
    "بازرگانی": "bazargani",
    "تجارت": "tejarat",
    "شرکت": "sherkat",
    "گروه": "goruh",
    "صنعت": "sanat",
    "صنایع": "sanaye",
    "پخش": "pakhsh",
    "خدمات": "khadamat",
    "مشاوره": "moshavere",
    "طراحی": "tarahi",
    "معماری": "memari",
    "ساختمان": "sakhteman",
    "املاک": "amlak",
    "مسکن": "maskan",
    "خودرو": "khodro",
    "ابزار": "abzar",
    "کشاورزی": "keshavarzi",
    "گل": "gol",
    "گلخانه": "golkhane",
    "کتاب": "ketab",
    "چاپ": "chap",
    "آموزش": "amoozesh",
    "زبان": "zaban",
    "هنر": "honar",
    "چرم": "charm",
    "کفش": "kafsh",
    "پوشاک": "pooshak",
    "لباس": "lebas",
    "پارچه": "parche",
    "ابریشم": "abrisham",
    "رستوران": "restaurant",
    "کافه": "cafe",
    "شیرینی": "shirini",
    "دیجیتال": "digital",
    "موبایل": "mobile",
    "نرمافزار": "narmafzar",
    "هوشمند": "hooshmand",
    "نوین": "novin",
    "مدرن": "modern",
    "سنتی": "sonati",
    "اصیل": "asil",
    "سبز": "sabz",
    "الماس": "almas",
    "یاقوت": "yaghut",
    "زمرد": "zomorrod",
    "فیروزه": "firuze",
    "عطر": "atr",
    "آرایش": "arayesh",
    "زیبایی": "zibaei",
    "سالن": "salon",
    "پزشکی": "pezeshki",
    "درمان": "darman",
    "سلامت": "salamat",
    "ورزش": "varzesh",
    "باشگاه": "bashgah",
    "سفر": "safar",
    "گردشگری": "gardeshgari",
    "هتل": "hotel",
    "مرکز": "markaz",
    "شهر": "shahr",
    "دستباف": "dastbaf",
    "ایرانی": "irani",
    "پارسی": "parsi",
    "پارس": "pars",
    "پرشیا": "persia",
    "پرشین": "persian",
    "برتر": "bartar",
    "ویژه": "vizhe",
    "کلاسیک": "classic",
    "لوکس": "lux",
}

PLACES = {
    "تهران",
    "تبریز",
    "کاشان",
    "اصفهان",
    "شیراز",
    "یزد",
    "مشهد",
    "کرمان",
    "قم",
    "رشت",
    "اهواز",
    "همدان",
    "زنجان",
    "سمنان",
    "کرج",
    "قزوین",
    "اردبیل",
    "بوشهر",
    "کرمانشاه",
    "سنندج",
    "گرگان",
    "ساری",
    "بابل",
    "نیشابور",
    "کیش",
    "قشم",
    "ارومیه",
    "زاهدان",
    "بندرعباس",
    "رفسنجان",
    "کاشمر",
    "بیرجند",
    "ایلام",
    "خرمآباد",
    "اراک",
    "ساوه",
    "ملایر",
    "بروجرد",
    "دزفول",
    "آبادان",
    "خرمشهر",
    "یاسوج",
    "شهرکرد",
    "زابل",
    "چابهار",
    "بجنورد",
    "آمل",
    "قائمشهر",
    "ورامین",
    "اسلامشهر",
    "ری",
    "خوی",
    "سبزوار",
    "شاهرود",
    "مراغه",
    "ایران",
}


def normalize_fa(text):
    text = unicodedata.normalize("NFKC", str(text))
    text = text.replace("\u200c", "").replace("\u200d", "")
    text = _DIACRITICS.sub("", text)
    text = (
        text.replace("ي", "ی")
        .replace("ك", "ک")
        .replace("ة", "ه")
        .replace("ۀ", "ه")
        .replace("أ", "ا")
        .replace("إ", "ا")
        .replace("ؤ", "و")
        .replace("ئ", "ی")
    )
    return " ".join(text.split())


def _needs_vowel(chars, index):
    if index + 2 >= len(chars):
        return False
    nxt = chars[index + 1]
    if nxt in _VOWEL_LETTERS or nxt == "و":
        return False
    if nxt not in _CONSONANTS and nxt != "ع":
        return False
    return chars[index + 2] not in _VOWEL_LETTERS and chars[index + 2] != "و"


def _convert_token(token):
    if token in LEXICON:
        return LEXICON[token]
    chars = list(token)
    out = []
    index = 0
    count = len(chars)
    while index < count:
        char = chars[index]
        nxt = chars[index + 1] if index + 1 < count else ""
        if char in "اآ":
            if not out or out[-1] not in "aeiou":
                out.append("a")
            elif out[-1] != "a":
                out.append("a")
            index += 1
            continue
        if char == "ع":
            if not out or out[-1] not in "aeiou":
                out.append("a")
            index += 1
            continue
        if char == "و":
            if nxt in "یي":
                out.append("v")
            elif nxt == "ا":
                out.append("v")
            elif index == 0 and nxt and nxt not in _VOWEL_LETTERS:
                out.append("va")
            elif nxt == "و":
                out.append("u")
                index += 2
                continue
            else:
                out.append("o")
            index += 1
            continue
        if char in "یي":
            if index == 0 or nxt == "ا":
                out.append("y")
            else:
                out.append("i")
            index += 1
            continue
        if char == "ه" and index == count - 1:
            if not out or out[-1] not in "aeiou":
                out.append("e")
            index += 1
            continue
        mapped = _CONSONANTS.get(char)
        if mapped:
            out.append(mapped)
            if _needs_vowel(chars, index):
                out.append("a")
            index += 1
            continue
        if char.isascii() and char.isalnum():
            out.append(char.lower())
        index += 1
    return re.sub(r"[^a-z0-9]", "", "".join(out))


def transliterate(text):
    """Return a lowercase domain label, without separators."""
    cleaned = normalize_fa(text)
    if not cleaned:
        return ""
    parts = []
    for part in re.split(r"[\s_\-]+", cleaned):
        if not part:
            continue
        if _LATIN_WORD.fullmatch(part):
            parts.append(re.sub(r"[^a-z0-9]", "", part.lower()))
        else:
            parts.append(_convert_token(part))
    return "".join(parts)[:63]
