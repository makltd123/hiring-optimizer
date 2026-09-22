from io import BytesIO
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, HRFlowable
from reportlab.pdfgen import canvas as pdfcanvas

PAGE_W, PAGE_H = A4
BLUE = colors.HexColor("#1d4ed8")
BLUE_LIGHT = colors.HexColor("#eff6ff")
RED = colors.HexColor("#dc2626")
GRAY = colors.HexColor("#64748b")
GRAY_LIGHT = colors.HexColor("#f8fafc")
BORDER = colors.HexColor("#e2e8f0")


def _make_page_template(org_name: str, total_pages_ref: list):
    """Возвращает функцию-callback для нижнего колонтитула каждой страницы."""
    def draw_footer(canvas, doc):
        canvas.saveState()
        canvas.setFont("Helvetica", 7)
        canvas.setFillColor(GRAY)
        y = 1.2 * cm
        canvas.drawString(2 * cm, y, org_name)
        canvas.drawCentredString(PAGE_W / 2, y, "Сформировано автоматически — Оптимизатор найма")
        canvas.drawRightString(PAGE_W - 2 * cm, y, f"Стр. {doc.page}")
        canvas.setStrokeColor(BORDER)
        canvas.setLineWidth(0.5)
        canvas.line(2 * cm, y + 0.35 * cm, PAGE_W - 2 * cm, y + 0.35 * cm)
        canvas.restoreState()
    return draw_footer


def generate_report_pdf(
    project,
    result,
    skill_gap_data: dict,
    reserve_data: dict,
    org_info: dict | None = None,
    branding: dict | None = None,
) -> bytes:
    """
    org_info: { org_name, dept_name, prepared_by }
    branding: { logo_url, brand_color, report_footer }
    """
    _branding = branding or {}
    if _branding.get("brand_color"):
        try:
            global BLUE
            BLUE = colors.HexColor(_branding["brand_color"])
        except Exception:
            pass

    org_name = (org_info or {}).get("org_name", "")
    dept_name = (org_info or {}).get("dept_name", "")
    prepared_by = (org_info or {}).get("prepared_by", "")
    report_no = f"HIRE-{project.id}-{datetime.now().strftime('%Y%m%d')}"

    buffer = BytesIO()
    footer_cb = _make_page_template(org_name or "Оптимизатор найма", [])
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=2 * cm,
        rightMargin=2 * cm,
        topMargin=2 * cm,
        bottomMargin=2.5 * cm,
        onFirstPage=footer_cb,
        onLaterPages=footer_cb,
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle("title", parent=styles["Title"], fontSize=18, spaceAfter=4,
                                 textColor=BLUE)
    h2_style = ParagraphStyle("h2", parent=styles["Heading2"], fontSize=12,
                              spaceBefore=14, spaceAfter=6, textColor=BLUE)
    normal = styles["Normal"]
    small = ParagraphStyle("small", parent=normal, fontSize=8, textColor=GRAY)
    bold = ParagraphStyle("bold", parent=normal, fontName="Helvetica-Bold")
    sign_label = ParagraphStyle("sign_label", parent=small, fontSize=8, textColor=GRAY)

    elements = []

    # ── Корпоративная шапка ──────────────────────────────────────────────────
    if org_name:
        header_data = [[
            Paragraph(f"<b>{org_name}</b>", ParagraphStyle("oh", parent=normal,
                      fontSize=13, textColor=BLUE, fontName="Helvetica-Bold")),
            Paragraph('<font color="#dc2626"><b>КОНФИДЕНЦИАЛЬНО</b></font>',
                      ParagraphStyle("conf", parent=normal, fontSize=9,
                                     alignment=2)),  # 2 = right
        ]]
        if dept_name:
            header_data.append([
                Paragraph(dept_name, small),
                Paragraph(f"№ {report_no}", ParagraphStyle("rno", parent=small, alignment=2)),
            ])
        ht = Table(header_data, colWidths=[12 * cm, 5 * cm])
        ht.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
            ("TOPPADDING", (0, 0), (-1, -1), 2),
        ]))
        elements.append(ht)
        elements.append(HRFlowable(width="100%", thickness=1.5, color=BLUE, spaceAfter=8))
    else:
        elements.append(Paragraph(f"№ {report_no}", small))

    # ── Заголовок отчёта ─────────────────────────────────────────────────────
    elements.append(Paragraph("Отчёт по подбору команды", title_style))
    elements.append(Paragraph(f"Проект: <b>{project.title}</b>", normal))

    meta_parts = [f"Дата формирования: {datetime.now().strftime('%d.%m.%Y %H:%M')}"]
    if prepared_by:
        meta_parts.append(f"Подготовил: {prepared_by}")
    if project.fot_limit:
        meta_parts.append(f"Лимит ФОТ: {int(project.fot_limit):,} ₽".replace(",", " "))
    if getattr(project, "deadline", None):
        meta_parts.append(f"Дедлайн: {project.deadline.strftime('%d.%m.%Y')}")
    elements.append(Paragraph(" · ".join(meta_parts), small))
    elements.append(Spacer(1, 0.4 * cm))

    # ── Итоговый состав команды ──────────────────────────────────────────────
    elements.append(Paragraph("Итоговый состав команды", h2_style))

    cand_by_id = {c.id: c for c in project.candidates}
    vac_by_id = {v.id: v for v in project.vacancies}

    assignment_rows = [["Роль", "Кандидат", "Соответствие", "Зарплата"]]
    for vac_id_str, cand_id in result.assignment.items():
        vac = vac_by_id.get(int(vac_id_str))
        if not vac:
            continue
        cand = cand_by_id.get(cand_id) if cand_id is not None else None
        score = result.match_scores.get(vac_id_str, {}).get(str(cand_id), 0) if cand else 0
        assignment_rows.append([
            vac.title,
            cand.display_name if cand else "Не закрыта",
            f"{round(score * 100)}%" if cand else "—",
            f"{int(cand.salary_expectation):,} ₽".replace(",", " ")
            if cand and cand.salary_expectation else "—",
        ])

    t = Table(assignment_rows, colWidths=[5 * cm, 5 * cm, 3 * cm, 4 * cm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), BLUE),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, GRAY_LIGHT]),
        ("GRID", (0, 0), (-1, -1), 0.5, BORDER),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    elements.append(t)
    elements.append(Spacer(1, 0.3 * cm))

    if result.total_cost:
        total_vacancies = len(project.vacancies)
        covered = sum(1 for v in result.assignment.values() if v is not None)
        coverage_pct = round(covered / total_vacancies * 100) if total_vacancies else 0
        elements.append(Paragraph(
            f"Покрытие команды: <b>{coverage_pct}%</b>   ·   "
            f"Суммарный ФОТ: <b>{int(result.total_cost):,} ₽</b>".replace(",", " "),
            normal,
        ))

    # ── Дефицит скиллов ──────────────────────────────────────────────────────
    gaps = skill_gap_data.get("gaps", [])
    if gaps:
        elements.append(Paragraph("Дефицит скиллов", h2_style))
        gap_rows = [["Скилл", "Покрытие", "Требуется", "Покрыто"]]
        for g in gaps:
            gap_rows.append([
                g["skill"],
                f"{round(g['coverage'] * 100)}%",
                str(g["required"]),
                str(g["covered"]),
            ])
        gt = Table(gap_rows, colWidths=[6 * cm, 3 * cm, 3 * cm, 3 * cm])
        gt.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), RED),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#fef2f2")]),
            ("GRID", (0, 0), (-1, -1), 0.5, BORDER),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]))
        elements.append(gt)

    fully = skill_gap_data.get("fully_covered", [])
    if fully:
        elements.append(Spacer(1, 0.2 * cm))
        elements.append(Paragraph(f"Полностью покрыты: {', '.join(fully)}", small))

    # ── Резервный список ─────────────────────────────────────────────────────
    reserve_list = reserve_data.get("reserve", [])
    if reserve_list:
        elements.append(Paragraph("Резервный список", h2_style))
        res_rows = [["#", "Кандидат", "Лучшая вакансия", "Score", "Причина"]]
        for item in reserve_list:
            res_rows.append([
                str(item["rank"]),
                item["display_name"],
                item["best_vacancy_title"],
                f"{round(item['best_score'] * 100)}%",
                item["rejection_reason"],
            ])
        rt = Table(res_rows, colWidths=[1 * cm, 4 * cm, 4 * cm, 2 * cm, 6 * cm])
        rt.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), GRAY),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, GRAY_LIGHT]),
            ("GRID", (0, 0), (-1, -1), 0.5, BORDER),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("WORDWRAP", (4, 1), (4, -1), True),
        ]))
        elements.append(rt)

    # ── Блок подписей ────────────────────────────────────────────────────────
    elements.append(Spacer(1, 1 * cm))
    elements.append(HRFlowable(width="100%", thickness=0.5, color=BORDER, spaceAfter=6))

    sign_data = [
        [
            Paragraph("Отчёт подготовлен:", sign_label),
            Paragraph("Согласовано:", sign_label),
            Paragraph("Утверждено:", sign_label),
        ],
        [
            Paragraph(prepared_by or "_______________________", bold),
            Paragraph("_______________________", bold),
            Paragraph("_______________________", bold),
        ],
        [
            Paragraph("подпись / дата", sign_label),
            Paragraph("подпись / дата", sign_label),
            Paragraph("подпись / дата", sign_label),
        ],
    ]
    st = Table(sign_data, colWidths=[5.67 * cm, 5.67 * cm, 5.66 * cm])
    st.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    elements.append(st)

    doc.build(elements)
    return buffer.getvalue()
