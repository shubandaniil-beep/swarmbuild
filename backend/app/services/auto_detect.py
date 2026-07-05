"""Smarter auto-detect (spec-2 §14): type, mode and requires_codebase from the brief."""
from sqlalchemy.orm import Session

from ..models import ProjectType

_DOC_KEYWORDS = ("диплом", "курсов", "реферат", "исследован", "thesis", "research",
                 "доклад", "эссе", "статья")
_BUSINESS_KEYWORDS = ("бизнес-план", "бизнес план", "business plan", "финмодел",
                      "стратеги", "монетизац")
_PITCH_KEYWORDS = ("pitch", "питч", "презентац", "deck", "слайд")
_MARKETING_KEYWORDS = ("маркетинг", "marketing", "реклам", "smm", "брендинг")
_CODE_KEYWORDS = ("бот", "bot", "crm", "сайт", "site", "app", "приложен", "api",
                  "скрипт", "script", "лендинг", "landing", "dashboard", "дашборд",
                  "интеграц", "калькулятор", "calculator", "утилит", "saas", "код")
_NO_CODE_PHRASES = ("без кода", "код не нужен", "не нужен код", "no code",
                    "without code", "не требуется код", "не нужна кодовая база")


def detect(db: Session, brief: str, requested_type: str = "auto",
           requested_mode: str = "auto") -> tuple[str, str, bool]:
    """Return (project_type_key, project_mode, requires_codebase)."""
    b = brief.lower()

    if requested_type != "auto":
        row = db.query(ProjectType).filter(ProjectType.key == requested_type).first()
        requires = row.requires_codebase if row else True
        mode = requested_mode if requested_mode != "auto" else (
            "code" if requires else "document")
        return requested_type, mode, requires

    no_code_requested = any(k in b for k in _NO_CODE_PHRASES)
    has_code = any(k in b for k in _CODE_KEYWORDS) and not no_code_requested
    has_doc = any(k in b for k in _DOC_KEYWORDS)
    has_biz = any(k in b for k in _BUSINESS_KEYWORDS)
    has_pitch = any(k in b for k in _PITCH_KEYWORDS)
    has_mkt = any(k in b for k in _MARKETING_KEYWORDS)

    if requested_mode == "document" or (has_doc and not has_code):
        return ("diploma_or_coursework" if any(k in b for k in ("диплом", "курсов", "thesis"))
                else "document_project"), "document", False
    if requested_mode == "business" or (has_biz and not has_code):
        return "business_project", "business", False
    if has_pitch and not has_code:
        return "pitch_deck", "document", False
    if has_mkt and not has_code:
        return "marketing_pack", "business", False

    # code side: pick a concrete type
    signals = sum([has_code, has_biz, has_pitch, has_doc])
    if has_code and signals >= 2 or requested_mode == "mixed":
        mode = "mixed"
    else:
        mode = "code"

    if any(k in b for k in ("crm", "заявк", "клиентская база", "lead")):
        type_key = "mini_crm"
    elif any(k in b for k in ("telegram", "телеграм", "бот", "bot")):
        type_key = "telegram_bot"
    elif any(k in b for k in ("лендинг", "landing")):
        type_key = "landing_page"
    elif any(k in b for k in ("dashboard", "дашборд")):
        type_key = "dashboard"
    elif any(k in b for k in ("кальку", "calculator", "стоимост", "расчет", "расчёт", "утилит")):
        type_key = "python_utility"
    elif any(k in b for k in ("сайт", "site", "web", "приложен", "app")):
        type_key = "web_app"
    else:
        type_key = "code_project" if has_code else "document_project"

    if not has_code and type_key == "document_project":
        return type_key, "document", False
    return type_key, mode, True
