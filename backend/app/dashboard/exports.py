"""Real Unicode PDF and text exports from the saved conversation, without AI calls."""
import io
import os
import threading
from datetime import datetime
from pathlib import Path
from xml.sax.saxutils import escape
from zoneinfo import ZoneInfo

from .engine import build_report

FONT_LOCK = threading.Lock()


def local_date(value):
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(ZoneInfo("Europe/Berlin")).strftime("%d.%m.%Y %H:%M %Z")
    except (ValueError, TypeError, AttributeError):
        return str(value or "")


def mode_label(session):
    if session["mode"] == "simple_actor":
        p=session["client_profile_snapshot"]
        return f"OpenAI · simple_actor · профиль {p['id']} v{p['version']} · персона v{p['persona']['version']} · сценарий v{p['scenario']['version']} · без LLM-Verifier"
    if session["mode"] == "demo":
        return "Техническая проверка · без AI-вызовов"
    if any(m.get("source") == "openai_actor_verified" for m in session["messages"]):
        return "OpenAI · разговорная роль клиента и отдельная проверка ответа"
    if any(m["role"] == "customer" and m.get("turn", 0) > 0 for m in session["messages"]):
        return "OpenAI · прежняя версия с готовыми ответами клиента"
    return "OpenAI выбран · сохранённых ответов модели пока нет"


def api_usage_label(session):
    if session["mode"] == "demo":
        return "Обращений к API: 0. Результат технической проверки не оценивает свободную речь."
    count = session.get("live_requests")
    label = "Попыток обращения к API" if session.get("api_count_complete") else "Учтённых попыток API с обновления; ранние обращения неизвестны"
    return (f"{label}: {count}. Включает ошибки; это не расчёт стоимости."
            if count is not None else "Точное число обращений к API в старой версии не записывалось.")


def export_text(session):
    report = session["report"] if session.get("restricted_export") else build_report(session) if session["mode"] == "simple_actor" else session.get("report") or build_report(session)
    scenario = session["scenario_snapshot"]
    company = session["company_snapshot"]
    lines = ["KLARE KI | РАЗБОР КОНСУЛЬТАЦИИ", "", scenario["title"],
             f"Клиент: {scenario['customer_name']}", f"Компания: {company['name']}",
             f"Начало: {local_date(session['created_at'])}", f"Обновлено: {local_date(session['updated_at'])}",
             f"Режим: {mode_label(session)}", api_usage_label(session), f"Сценарий: {scenario['id']} · версия {scenario['revision']}",
             f"Компания: версия {company['revision']}", f"Беседа: {session['id']}", "", "РЕЗУЛЬТАТ", report.get("summary", "")]
    for stage in report.get("stages", []):
        lines.append(f"- {stage['label']}: {stage.get('rating_label') or ('подтверждено' if stage['confirmed'] else 'не подтверждено')}")
    if session["mode"] == "simple_actor":
        lines.extend(["Результат разговора: " + report["commercial_label"], "Соответствие услугам компании: " + report["company_fit_label"]])
    lines.extend(["", "НАБЛЮДЕНИЯ"])
    if not report.get("findings"):
        lines.append("Отдельных событий не зафиксировано. Это не подтверждение качества обучения.")
    for item in report.get("findings", []):
        lines.append(f"Ход {item.get('turn', '—')}: {item.get('detail', '')}")
    if not session.get("restricted_export"):
        lines.extend(["", "СВЕДЕНИЯ СЦЕНАРИЯ (ОТКРЫТЫ ПОСЛЕ ЗАВЕРШЕНИЯ)"])
    for item in report.get("facts", []):
        found = "не оценено автоматически" if session["mode"]=="simple_actor" else "выяснено" if item.get("discovered") else "не выяснено"
        lines.extend([f"{item['label']} — {found}; состояние клиента: {item['status']}", item["value"], ""])
    lines.append("ПОЛНАЯ РАСШИФРОВКА")
    for message in session["messages"]:
        speaker = "Ученик" if message["role"] == "learner" else scenario["customer_name"] + " · клиент"
        lines.extend([f"[{local_date(message.get('at', ''))}] {speaker} | ход {message.get('turn', 0)}", message["text"], ""])
    if session.get("review_note"):
        lines.extend(["ОТЗЫВ НАСТАВНИКА", session["review_note"], ""])
    lines.extend(["ГРАНИЦЫ ЭТОГО РАЗБОРА", *["- " + x for x in report.get("limitations", [])]])
    lines.append("Локальный прототип. Передача наставнику — очередь внутри приложения; внешняя отправка не выполняется.")
    return "\n".join(lines) + "\n"


def _fonts():
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    with FONT_LOCK:
        if "KlareRegular" in pdfmetrics.getRegisteredFontNames():
            return
        candidates = []
        custom = os.environ.get("TRAINER_FONT_PATH")
        if custom:
            candidates.append((custom, os.environ.get("TRAINER_BOLD_FONT_PATH", custom)))
        candidates.extend([
            ("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
            ("/usr/share/fonts/dejavu-sans-fonts/DejaVuSans.ttf", "/usr/share/fonts/dejavu-sans-fonts/DejaVuSans-Bold.ttf"),
            ("/System/Library/Fonts/Supplemental/Arial.ttf", "/System/Library/Fonts/Supplemental/Arial Bold.ttf"),
            ("/Library/Fonts/Arial.ttf", "/Library/Fonts/Arial Bold.ttf"),
            ("C:/Windows/Fonts/arial.ttf", "C:/Windows/Fonts/arialbd.ttf"),
        ])
        for regular, bold in candidates:
            if Path(regular).is_file():
                pdfmetrics.registerFont(TTFont("KlareRegular", regular))
                pdfmetrics.registerFont(TTFont("KlareBold", bold if Path(bold).is_file() else regular))
                pdfmetrics.registerFontFamily("Klare", normal="KlareRegular", bold="KlareBold", italic="KlareRegular", boldItalic="KlareBold")
                return
    raise RuntimeError("Install a Cyrillic TrueType font, e.g. fonts-dejavu-core")


def export_pdf(session):
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_LEFT
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak, Table, TableStyle

    _fonts()
    ink = colors.HexColor("#173B35")
    muted = colors.HexColor("#62746E")
    light = colors.HexColor("#ECF2EF")
    styles = {
        "title": ParagraphStyle("title", fontName="KlareBold", fontSize=23, leading=30, textColor=ink, spaceAfter=15),
        "subtitle": ParagraphStyle("subtitle", fontName="KlareRegular", fontSize=11, leading=17, textColor=muted, spaceAfter=12),
        "heading": ParagraphStyle("heading", fontName="KlareBold", fontSize=13, leading=19, textColor=ink, spaceBefore=19, spaceAfter=8, keepWithNext=True),
        "body": ParagraphStyle("body", fontName="KlareRegular", fontSize=10, leading=15, textColor=ink, spaceAfter=8, splitLongWords=True),
        "meta": ParagraphStyle("meta", fontName="KlareRegular", fontSize=8.5, leading=13, textColor=muted, spaceAfter=6),
        "speaker": ParagraphStyle("speaker", fontName="KlareBold", fontSize=9, leading=14, textColor=ink, spaceBefore=10, spaceAfter=3, keepWithNext=True),
    }
    styles["limitation"] = ParagraphStyle("limitation", parent=styles["meta"], fontSize=7.5, leading=11, spaceAfter=4)
    styles["fact_meta"] = ParagraphStyle("fact_meta", parent=styles["meta"], keepWithNext=True)
    def p(text, kind="body"):
        return Paragraph(escape(str(text)).replace("\n", "<br/>"), styles[kind])

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=46, leftMargin=46, topMargin=66, bottomMargin=52,
                            title="Klare KI — Разбор консультации", author="Klare KI", pageCompression=1)
    report = session["report"] if session.get("restricted_export") else build_report(session) if session["mode"] == "simple_actor" else session.get("report") or build_report(session)
    scenario = session["scenario_snapshot"]
    company = session["company_snapshot"]
    story = [p("Разбор консультации", "title"), p(scenario["title"], "subtitle"),
             p(f"{scenario['customer_name']}  /  {company['name']}", "body"),
             p(f"Начало: {local_date(session['created_at'])}\nРежим: {mode_label(session)}", "meta"),
             p(api_usage_label(session), "meta"),
             p(f"Сценарий {scenario['id']} · версия {scenario['revision']}. Компания · версия {company['revision']}.\nБеседа {session['id']}", "meta"),
             p("Результат", "heading"), p(report.get("summary", ""))]
    rows = [[p("Этап", "speaker"), p("Подтверждение", "speaker")]]
    for stage in report.get("stages", []):
        rows.append([p(stage["label"]), p(stage.get("rating_label") or ("Подтверждено" if stage["confirmed"] else "Не подтверждено"))])
    table = Table(rows, colWidths=[doc.width * .63, doc.width * .37], hAlign="LEFT")
    table.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), light), ("VALIGN", (0, 0), (-1, -1), "TOP"),
                               ("LEFTPADDING", (0, 0), (-1, -1), 10), ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                               ("TOPPADDING", (0, 0), (-1, -1), 5), ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                               ("LINEBELOW", (0, 0), (-1, -1), .5, colors.HexColor("#DDE5E0"))]))
    story.append(table)
    if session["mode"] == "simple_actor":
        story.extend([p("Результат разговора: " + report["commercial_label"]), p("Соответствие услугам компании: " + report["company_fit_label"])])
    story.append(p("Наблюдения по беседе", "heading"))
    if not report.get("findings"):
        story.append(p("Отдельных событий не зафиксировано. Это не подтверждение качества обучения."))
    for finding in report.get("findings", []):
        story.append(p(f"Ход {finding.get('turn', '—')} · {finding.get('detail', '')}"))
    if session.get("review_note"):
        story.extend([p("Отзыв наставника", "heading"), p(session["review_note"])])
    story.append(p("Как читать этот результат", "heading"))
    for item in report.get("limitations", []):
        story.append(p("• " + item, "limitation"))
    story.extend([PageBreak(), p("Расшифровка беседы", "title"), p("Все сообщения в порядке их появления. Текст ученика сохранён без исправлений.", "subtitle")])
    for message in session["messages"]:
        speaker = "Ученик" if message["role"] == "learner" else scenario["customer_name"] + " · клиент"
        story.extend([p(f"{speaker}   /   ход {message.get('turn', 0)}", "speaker"), p(message["text"])])
    if not session.get("restricted_export"):
        story.extend([PageBreak(), p("Основания для разбора", "title"), p("Закрытые сведения этой версии сценария открыты после завершения попытки.", "subtitle")])
    status_names = {"known": "знает", "undecided": "не определился", "does_not_know": "не знает", "refuses_to_disclose": "не раскрывает", "not_applicable": "не относится к ситуации"}
    for fact in report.get("facts", []):
        found = "не оценено автоматически" if session["mode"]=="simple_actor" else "выяснено" if fact.get("discovered") else "не выяснено"
        story.extend([p(fact["label"], "heading"), p(f"{found} · клиент {status_names.get(fact['status'], fact['status'])}", "fact_meta"), p(fact["value"])])
    story.extend([p("Возможности компании", "heading"), p(company["description"])])
    for service in company["services"]:
        story.extend([p(service["title"], "speaker"), p(service["description"]), p(service["conditions"], "meta")])
    story.extend([p("Ограничения", "heading"), p(company["limitations"])])
    if company.get("source_url"):
        story.append(p("Источник, указанный наставником: " + company["source_url"], "meta"))

    def page(canvas, document):
        canvas.saveState()
        canvas.setFont("KlareBold", 10)
        canvas.setFillColor(ink)
        canvas.drawString(46, A4[1] - 34, "KLARE KI")
        canvas.setFont("KlareRegular", 8)
        canvas.setFillColor(muted)
        canvas.drawRightString(A4[0] - 46, A4[1] - 34, "CONSULTATION STUDIO")
        canvas.setStrokeColor(colors.HexColor("#DDE5E0"))
        canvas.line(46, A4[1] - 43, A4[0] - 46, A4[1] - 43)
        canvas.setFont("KlareRegular", 7.5)
        canvas.drawString(46, 30, "Локальный прототип · " + ("Техническая проверка" if session["mode"] == "demo" else "OpenAI"))
        canvas.drawRightString(A4[0] - 46, 30, str(document.page))
        canvas.restoreState()

    doc.build(story, onFirstPage=page, onLaterPages=page)
    return buffer.getvalue()
