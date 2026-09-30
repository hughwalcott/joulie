"""Which language Joulie answers in (JTBD-03).

Pure logic — no model imports — so the policy is testable without Whisper or
XTTS. The session starts in English, because the greeting is spoken before the
visitor has said anything, and each turn's Whisper detection is run through
choose_language to decide whether to switch.
"""

from dataclasses import dataclass
from typing import Iterable, Optional

from joulie import config


@dataclass(frozen=True)
class Language:
    code: str                  # Whisper's code for it
    name: str                  # English name, used in the fallback notice
    xtts_code: Optional[str]   # None when XTTS-v2 cannot voice it
    # Rides on the current user message, never in the system prompt or history
    # — see Agent._build_messages. Empty for English, so an English turn's
    # prompt is byte-identical to what it was before languages existed.
    reply_directive: str = ""
    error_line: str = "Sorry, I had trouble thinking just then. Please try again."
    # Shown above config.DISCLAIMER, which stays on screen for everyone else.
    disclaimer: str = ""
    # On-screen language badge, in the language itself. Empty for English.
    badge: str = ""
    # How audio.sanitize_for_speech says kWh, MWh and kW, and "NZ". XTTS expands
    # numbers itself but leaves units as letters, so without these a German
    # answer says "kilowatt hours" mid-sentence.
    units: tuple[str, str, str] = ("kilowatt hours", "megawatt hours", "kilowatts")
    country: str = "New Zealand"
    # False until a native speaker has checked error_line and disclaimer, which
    # are spoken and shown verbatim. SessionCore logs the unreviewed ones at
    # startup so a deployment can't ship them unnoticed.
    reviewed: bool = False
    # Qwen2.5 tokens per English-equivalent token of text, measured by having
    # the model copy each language's disclaimer verbatim (they all say the same
    # thing). Scales LLM_NUM_PREDICT, which was sized on English answers — at
    # 260 tokens a Hindi answer stopped mid-word.
    token_factor: float = 1.0


# Tool and publisher names stay in English, in Latin letters, so
# tools.detect_tool still matches them and the QR panel appears — in Hindi,
# Qwen otherwise wrote "Billy" as बिल्ली, which also means "cat". It also priced
# a heat pump in rupees; every amount Joulie quotes is New Zealand dollars.
_KEEP_NAMES = (
    "Keep tool and publisher names in English, in Latin letters, exactly as "
    "written: Billy, EECA, Electricity Authority, Rewiring Aotearoa, NIWA "
    "SolarView, Warmer Kiwi Homes. All money is New Zealand dollars: write "
    "amounts with $, never another currency. Use simple, everyday words."
)


def _directive(language_name: str) -> str:
    return (f"Reply in {language_name}, even though earlier instructions say "
            f"English. {_KEEP_NAMES}")


LANGUAGES: dict[str, Language] = {
    "en": Language(code="en", name="English", xtts_code="en", reviewed=True),
    "zh": Language(
        code="zh",
        name="Mandarin Chinese",
        xtts_code="zh-cn",
        reply_directive=_directive("Simplified Chinese (简体中文)"),
        error_line="抱歉，我刚才没想明白。请再试一次。",
        badge="中文",
        disclaimer=(
            "Joulie 提供有关新西兰家庭和企业电气化的信息。"
            "回答仅供参考，可能不完整。如需做决定，请咨询合格的专业人士。"
        ),
        units=("千瓦时", "兆瓦时", "千瓦"),
        country="新西兰",
        token_factor=1.0,
    ),
    "hi": Language(
        code="hi",
        name="Hindi",
        xtts_code="hi",
        # Named explicitly: without it the model drifts into romanised Hindi or
        # Hinglish, which XTTS's Hindi voice cannot read.
        reply_directive=_directive("Hindi, written in Devanagari script"),
        error_line="माफ़ कीजिए, मुझे अभी सोचने में दिक्कत हुई। कृपया फिर से पूछिए।",
        badge="हिन्दी",
        disclaimer=(
            "Joulie न्यूज़ीलैंड में घरों और व्यवसायों के विद्युतीकरण के बारे में जानकारी देती है। "
            "उत्तर केवल जानकारी के लिए हैं और अधूरे हो सकते हैं। "
            "निर्णय लेने के लिए कृपया किसी योग्य विशेषज्ञ से सलाह लें।"
        ),
        units=("किलोवाट घंटे", "मेगावाट घंटे", "किलोवाट"),
        country="न्यूज़ीलैंड",
        token_factor=5.6,
    ),
    "es": Language(
        code="es", name="Spanish", xtts_code="es",
        reply_directive=_directive("Spanish"),
        error_line="Lo siento, tuve un problema al pensar. Por favor, inténtelo de nuevo.",
        badge="Español",
        disclaimer=(
            "Joulie ofrece información sobre la electrificación de hogares y empresas "
            "en Nueva Zelanda. Las respuestas son solo informativas y pueden estar "
            "incompletas. Para tomar decisiones, consulte a un profesional cualificado."
        ),
        units=("kilovatios hora", "megavatios hora", "kilovatios"),
        country="Nueva Zelanda",
        token_factor=1.5,
    ),
    "fr": Language(
        code="fr", name="French", xtts_code="fr",
        reply_directive=_directive("French"),
        error_line="Désolée, j'ai eu du mal à réfléchir. Veuillez réessayer.",
        badge="Français",
        disclaimer=(
            "Joulie fournit des informations sur l'électrification des logements et "
            "des entreprises en Nouvelle-Zélande. Les réponses sont données à titre "
            "informatif et peuvent être incomplètes. Pour toute décision, veuillez "
            "consulter un professionnel qualifié."
        ),
        units=("kilowattheures", "mégawattheures", "kilowatts"),
        country="Nouvelle-Zélande",
        token_factor=1.8,
    ),
    "de": Language(
        code="de", name="German", xtts_code="de",
        reply_directive=_directive("German"),
        error_line="Entschuldigung, da hatte ich gerade Schwierigkeiten. Bitte versuchen Sie es noch einmal.",
        badge="Deutsch",
        disclaimer=(
            "Joulie informiert über die Elektrifizierung von Haushalten und Unternehmen "
            "in Neuseeland. Die Antworten dienen nur der Information und können "
            "unvollständig sein. Für Entscheidungen wenden Sie sich bitte an eine "
            "qualifizierte Fachkraft."
        ),
        units=("Kilowattstunden", "Megawattstunden", "Kilowatt"),
        country="Neuseeland",
        token_factor=1.8,
    ),
    "it": Language(
        code="it", name="Italian", xtts_code="it",
        reply_directive=_directive("Italian"),
        error_line="Mi scusi, ho avuto un problema a pensare. Per favore, riprovi.",
        badge="Italiano",
        disclaimer=(
            "Joulie fornisce informazioni sull'elettrificazione di case e aziende in "
            "Nuova Zelanda. Le risposte hanno scopo puramente informativo e potrebbero "
            "essere incomplete. Per prendere decisioni, si rivolga a un professionista "
            "qualificato."
        ),
        units=("chilowattora", "megawattora", "chilowatt"),
        country="Nuova Zelanda",
        token_factor=1.9,
    ),
    "pt": Language(
        code="pt", name="Portuguese", xtts_code="pt",
        reply_directive=_directive("Portuguese"),
        error_line="Desculpe, tive um problema a pensar. Por favor, tente novamente.",
        badge="Português",
        disclaimer=(
            "A Joulie partilha informação sobre a eletrificação de casas e empresas na "
            "Nova Zelândia. As respostas são apenas informativas e podem estar "
            "incompletas. Para tomar decisões, consulte um profissional qualificado."
        ),
        units=("quilowatts-hora", "megawatts-hora", "quilowatts"),
        country="Nova Zelândia",
        token_factor=1.6,
    ),
    "nl": Language(
        code="nl", name="Dutch", xtts_code="nl",
        reply_directive=_directive("Dutch"),
        error_line="Sorry, ik had even moeite met nadenken. Probeer het nog eens.",
        badge="Nederlands",
        disclaimer=(
            "Joulie geeft informatie over het elektrificeren van woningen en bedrijven "
            "in Nieuw-Zeeland. De antwoorden zijn alleen ter informatie en kunnen "
            "onvolledig zijn. Raadpleeg voor beslissingen een gekwalificeerde vakman."
        ),
        units=("kilowattuur", "megawattuur", "kilowatt"),
        country="Nieuw-Zeeland",
        token_factor=1.9,
    ),
    "pl": Language(
        code="pl", name="Polish", xtts_code="pl",
        reply_directive=_directive("Polish"),
        error_line="Przepraszam, miałam problem z odpowiedzią. Proszę spróbować ponownie.",
        badge="Polski",
        disclaimer=(
            "Joulie udziela informacji o elektryfikacji domów i firm w Nowej Zelandii. "
            "Odpowiedzi mają charakter wyłącznie informacyjny i mogą być niepełne. "
            "Przed podjęciem decyzji prosimy skonsultować się z wykwalifikowanym "
            "specjalistą."
        ),
        units=("kilowatogodzin", "megawatogodzin", "kilowatów"),
        country="Nowa Zelandia",
        token_factor=2.2,
    ),
    "ru": Language(
        code="ru", name="Russian", xtts_code="ru",
        reply_directive=_directive("Russian"),
        error_line="Извините, у меня возникла проблема. Пожалуйста, попробуйте ещё раз.",
        badge="Русский",
        disclaimer=(
            "Joulie предоставляет информацию об электрификации домов и предприятий в "
            "Новой Зеландии. Ответы носят исключительно информационный характер и "
            "могут быть неполными. Для принятия решений, пожалуйста, обратитесь к "
            "квалифицированному специалисту."
        ),
        units=("киловатт-часов", "мегаватт-часов", "киловатт"),
        country="Новая Зеландия",
        token_factor=2.3,
    ),
    "cs": Language(
        code="cs", name="Czech", xtts_code="cs",
        reply_directive=_directive("Czech"),
        error_line="Promiňte, měla jsem potíž s odpovědí. Zkuste to prosím znovu.",
        badge="Čeština",
        disclaimer=(
            "Joulie poskytuje informace o elektrifikaci domácností a firem na Novém "
            "Zélandu. Odpovědi mají pouze informativní charakter a nemusí být úplné. "
            "Před rozhodnutím se prosím poraďte s kvalifikovaným odborníkem."
        ),
        units=("kilowatthodin", "megawatthodin", "kilowattů"),
        country="Nový Zéland",
        token_factor=2.6,
    ),
    "hu": Language(
        code="hu", name="Hungarian", xtts_code="hu",
        reply_directive=_directive("Hungarian"),
        error_line="Elnézést, gond volt a válasszal. Kérem, próbálja újra.",
        badge="Magyar",
        disclaimer=(
            "Joulie tájékoztatást nyújt az új-zélandi otthonok és vállalkozások "
            "villamosításáról. A válaszok csak tájékoztató jellegűek, és hiányosak "
            "lehetnek. Döntések előtt kérjük, forduljon képzett szakemberhez."
        ),
        units=("kilowattóra", "megawattóra", "kilowatt"),
        country="Új-Zéland",
        token_factor=2.6,
    ),
    "tr": Language(
        code="tr", name="Turkish", xtts_code="tr",
        reply_directive=_directive("Turkish"),
        error_line="Üzgünüm, az önce bir sorun yaşadım. Lütfen tekrar deneyin.",
        badge="Türkçe",
        disclaimer=(
            "Joulie, Yeni Zelanda'daki evlerin ve işletmelerin elektrifikasyonu hakkında "
            "bilgi verir. Yanıtlar yalnızca bilgilendirme amaçlıdır ve eksik olabilir. "
            "Karar vermeden önce lütfen yetkin bir uzmana danışın."
        ),
        units=("kilovatsaat", "megavatsaat", "kilovat"),
        country="Yeni Zelanda",
        token_factor=2.2,
    ),
    # Text-only until a te reo voice has been evaluated with a speaker: enable
    # with JOULIE_TEXT_ONLY_LANGUAGES=mi. Whisper's te reo recognition and
    # Qwen's te reo writing both need checking before that.
    "mi": Language(
        code="mi",
        name="te reo Māori",
        xtts_code=None,
        badge="te reo Māori",
        reply_directive=_directive("te reo Māori"),
        # Unmeasured — macrons and long vowel runs tokenise poorly; measure
        # before enabling.
        token_factor=2.5,
    ),
}

# Whisper splits spoken Hindustani between Hindi and Urdu almost at random — the
# spoken languages are close to identical, the scripts are not. Urdu's
# probability is credited to Hindi so an Urdu or Hindi speaker isn't left in
# English because neither half cleared the threshold; the answer is spoken, and
# spoken Hindi is intelligible to both.
ALIASES: dict[str, str] = {"ur": "hi"}

DEFAULT = "en"


def active_codes() -> frozenset[str]:
    """Languages a session may switch into: voiced plus text-only."""
    codes = set(config.LANGUAGES) | set(config.TEXT_ONLY_LANGUAGES)
    return frozenset(c for c in codes if c in LANGUAGES) | {DEFAULT}


def get(code: str) -> Language:
    return LANGUAGES.get(code, LANGUAGES[DEFAULT])


def reply_directive(code: str) -> str:
    return get(code).reply_directive


def is_text_only(code: str) -> bool:
    return code in config.TEXT_ONLY_LANGUAGES or get(code).xtts_code is None


def unreviewed() -> list[str]:
    """Active languages whose shown and spoken text no native speaker has checked."""
    return sorted(c for c in active_codes() if not LANGUAGES[c].reviewed)


def fallback_notice(code: str) -> str:
    """Spoken in English when the answer is on screen in a language Joulie
    cannot voice."""
    return (f"I've put my answer on the screen in {get(code).name}. "
            f"I can't speak {get(code).name} aloud yet.")


def choose_language(
    session_lang: str,
    all_probs: Optional[Iterable[tuple[str, float]]],
    duration_s: float,
    *,
    allowed: Optional[frozenset[str]] = None,
    min_prob: Optional[float] = None,
    min_seconds: Optional[float] = None,
) -> str:
    """The session's language after this utterance.

    Whisper's probabilities are restricted to the languages Joulie supports
    before picking the best, so Kiwi-accented English that Whisper half-hears as
    Welsh still reads as English. A switch then needs both a confident detection
    — Whisper's own probability, not renormalised, which would turn a 55%
    guess into certainty once the other candidates are dropped — and an
    utterance long enough to be worth trusting — a short "yeah" or "ok" in
    the middle of a Mandarin conversation leaves it in Mandarin, which is what
    scenario A3 asks for ("continues ... until she hangs up").
    """
    allowed = active_codes() if allowed is None else allowed
    min_prob = config.LANG_SWITCH_MIN_PROB if min_prob is None else min_prob
    min_seconds = config.LANG_SWITCH_MIN_SECONDS if min_seconds is None else min_seconds

    probs: dict[str, float] = {}
    for code, p in all_probs or ():
        code = ALIASES.get(code, code)
        if code in allowed:
            probs[code] = probs.get(code, 0.0) + p
    if not probs:
        return session_lang
    best = max(probs, key=probs.get)
    if best == session_lang:
        return session_lang
    if duration_s < min_seconds or probs[best] < min_prob:
        return session_lang
    return best
