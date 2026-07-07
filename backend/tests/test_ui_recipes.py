"""UI recipe retrieval: the weak-UI model must receive vetted, on-brand recipes
(the 'constructor') for a web brief — and NOTHING for backend/CLI builds — while
the injected block never blows the 3000-token builder-input ceiling."""
from app.services import ui_retrieval as ui


def _top(brief, ptype="web_app"):
    picks = ui.select_recipes(brief, ptype, "builder")
    return picks[0]["id"] if picks else None


# --------------------------------------------------------------------------- #
# routing: the right page recipe for a brief (incl. Russian inflection)         #
# --------------------------------------------------------------------------- #

def test_page_routing_ru():
    assert _top("интернет-магазин одежды, зелёный минимализм") == "green-minimal-ecommerce"
    assert _top("тёмный лендинг saas стартапа", "landing_page") == "dark-saas-landing"
    assert _top("сайт ресторана с меню и бронированием") == "warm-editorial-restaurant"
    assert _top("админ-панель с аналитикой", "dashboard") == "admin-dashboard"
    assert _top("сайт киберспортивной команды") == "gaming-neon"
    assert _top("портал документации для разработчиков") == "docs-site"


def test_backend_and_cli_get_no_ui():
    # code_project is generic code (APIs/CLIs/libs) — must not receive UI recipes
    assert ui.build_ui_context("build a rest api for payments", "code_project", "builder") == ""
    assert ui.build_ui_context("rest api платежей", "code_project", "builder") == ""
    # non-UI mandates skip retrieval even for a web project
    assert ui.select_recipes("магазин одежды", "web_app", "reviewer") == []


def test_short_tokens_do_not_false_match():
    # 2-letter 'ии'/'sport' must not fire inside конференции / esports
    assert _top("лендинг конференции со спикерами и билетами", "landing_page") == "event-conference"


# --------------------------------------------------------------------------- #
# token budget: the whole injected block stays within the ceiling              #
# --------------------------------------------------------------------------- #

def test_injection_within_budget():
    briefs = [
        ("интернет-магазин одежды с формой обратной связи и FAQ", "web_app"),
        ("тёмный лендинг saas с тарифами, отзывами и мобильным меню", "landing_page"),
        ("портфолио дизайнера с модальным окном", "web_app"),
    ]
    for brief, ptype in briefs:
        block = ui.build_ui_context(brief, ptype, "builder")
        assert block, brief
        assert ui.est_tokens(block) <= ui.UI_TOKEN_BUDGET, brief


def test_every_recipe_fits_alone():
    # each page recipe body must fit under budget so it can be injected on its own
    for entry in ui._load_index():
        if entry.get("kind", "page") == "page":
            body = ui.recipe_body(entry["file"])
            assert body, entry["id"]
            assert ui.est_tokens(body) <= ui.UI_TOKEN_BUDGET, entry["id"]


# --------------------------------------------------------------------------- #
# interactive components + framework directive                                 #
# --------------------------------------------------------------------------- #

def test_components_triggered_by_brief():
    comps = {c["id"] for c in ui.select_components("форма обратной связи с FAQ")}
    assert "form-validation" in comps
    assert "accordion-faq" in comps
    # an unrelated brief pulls no components
    assert ui.select_components("люксовый бренд часов") == []


def test_framework_directive_only_when_requested():
    react = ui.build_ui_context("сайт магазина одежды на react", "web_app", "builder")
    assert "FRAMEWORK: React" in react
    plain = ui.build_ui_context("сайт магазина одежды", "web_app", "builder")
    assert "FRAMEWORK" not in plain
