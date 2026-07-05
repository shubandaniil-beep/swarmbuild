"""Seed demo projects across all project modes and run them through the swarm.

Usage:  PYTHONPATH=. .venv/bin/python scripts/seed_demo.py
Idempotent: skips seeding when the demo user already has projects.
"""
from app.database import SessionLocal, init_db
from app.lib.security import hash_password
from app.models import Project, User
from app.services.phase_orchestrator import run_project
from app.services.project_intake import create_project

DEMOS = [
    ("Car Wash Suite",
     "У меня автомойка. Нужен сайт, мини-CRM, Telegram-бот для записи клиентов, "
     "калькулятор стоимости услуг, бизнес-план и презентация.",
     100, ["mvp", "docs", "business_plan", "pitch_outline"], "auto", "auto"),
    ("Ветклиника «Кабан»",
     "Ветеринарная клиника: система записи, CRM для пациентов и документы для персонала.",
     100, ["mvp", "docs", "user_manual"], "mini_crm", "code"),
    ("Диплом: ИИ и рынок труда",
     "Сделай диплом про влияние ИИ на рынок труда, с презентацией для защиты.",
     40, ["research_report", "presentation_structure"], "auto", "document"),
    ("Startup Pitch Pack",
     "Стартап: доставка кофе дронами. Нужен бизнес-план, pitch deck и финмодель.",
     40, ["business_plan", "pitch_outline", "financial_model"], "auto", "business"),
    ("Telegram Booking Bot",
     "Сделай Telegram-бота для записи клиентов барбершопа.",
     20, ["mvp", "docs"], "telegram_bot", "code"),
    ("Small Business CRM",
     "Мини-CRM для заявок цветочного магазина с лендингом и pitch deck для франшизы.",
     200, ["mvp", "docs", "pitch_outline", "roadmap"], "auto", "mixed"),
]


def main() -> None:
    init_db()
    db = SessionLocal()
    try:
        demo = db.query(User).filter(User.email == "demo@swarmbuild.ai").first()
        if not demo:
            demo = User(email="demo@swarmbuild.ai",
                        password_hash=hash_password("demo12345"))
            db.add(demo)
            db.commit()
        if db.query(Project).filter(Project.user_id == demo.id).count() > 0:
            print("demo user already has projects — nothing to do")
            return
        for title, brief, budget, outputs, ptype, mode in DEMOS:
            project = create_project(db, title, brief, budget, outputs,
                                     project_type=ptype, project_mode=mode,
                                     user_id=demo.id)
            print(f"→ {title}: mode={project.project_mode} "
                  f"code={project.requires_codebase} swarm={project.swarm_size}")
            run_project(db, project.id)
            db.refresh(project)
            print(f"  done: {project.status}")
        print("\nDemo login: demo@swarmbuild.ai / demo12345")
    finally:
        db.close()


if __name__ == "__main__":
    main()
