from datetime import date, datetime
from io import BytesIO
from pathlib import Path
from threading import Lock
from typing import Any
from xml.sax.saxutils import escape
from zoneinfo import ZoneInfo

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen.canvas import Canvas
from reportlab.platypus import LongTable, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from app.services.reports.data import TITLES, ReportData, Value

FONT_DIRECTORY = Path(__file__).resolve().parents[2] / "assets" / "fonts"
_font_lock = Lock()
EMPTY = "Таңдалған кезеңде осы шарттарға сәйкес жазба жоқ."


def plain(value: str) -> str:
    # Excel XML/PDF markup cannot accept arbitrary control characters.
    return "".join(
        c for c in value if c in "\n\t" or (ord(c) >= 32 and ord(c) not in {127, 65534, 65535})
    )


def local(value: Value, report: ReportData) -> Value:
    if isinstance(value, datetime):
        return value.astimezone(ZoneInfo(report.window.meta.timezone)).replace(tzinfo=None)
    return plain(value) if isinstance(value, str) else value


def metadata(report: ReportData) -> list[tuple[str, Value]]:
    period = report.window.meta
    return [
        ("Жүйе", "SmartLibrary"),
        ("Есеп", TITLES[report.kind]),
        ("Басталу күні", period.date_from),
        ("Аяқталу күні", period.date_to),
        ("Жасалған уақыт", period.generated_at),
        ("Уақыт белдеуі", period.timezone),
        ("Дайындаған", report.generated_by),
        ("Түсіндірме", report.note),
    ]


def spreadsheet(report: ReportData) -> bytes:
    workbook = Workbook()
    workbook.remove(workbook.active)
    sections: list[tuple[str, list[str], Any]] = [
        ("Қорытынды", ["Көрсеткіш", "Мәні"], [*metadata(report), *report.summary]),
        ("Жазбалар", report.headers, report.rows),
    ]
    for title, headers, rows in sections:
        sheet = workbook.create_sheet(title)
        for row_index, row in enumerate([headers, *rows], start=1):
            for col_index, value in enumerate(row, start=1):
                cell = sheet.cell(row_index, col_index)
                cell.value = local(value, report)
                if isinstance(cell.value, str):
                    # Explicit strings, including =/+/-/@, can never become formulas.
                    cell.data_type = "s"
                if isinstance(cell.value, datetime):
                    cell.number_format = "yyyy-mm-dd hh:mm"
                elif isinstance(cell.value, date):
                    cell.number_format = "yyyy-mm-dd"
                elif isinstance(cell.value, float):
                    cell.number_format = "0.00"
                cell.alignment = Alignment(vertical="top", wrap_text=True)
                if row_index == 1:
                    cell.font = Font(bold=True, color="FFFFFF")
                    cell.fill = PatternFill("solid", fgColor="065F46")
        if title == "Жазбалар" and not rows:
            sheet.cell(2, 1, EMPTY)
        sheet.freeze_panes = "A2"
        sheet.auto_filter.ref = sheet.dimensions
        for index in range(1, len(headers) + 1):
            sheet.column_dimensions[get_column_letter(index)].width = (
                45 if title == "Қорытынды" else max(18, report.widths[index - 1] * 1.8)
            )
        sheet.sheet_properties.pageSetUpPr.fitToPage = True
        sheet.page_setup.orientation = "landscape"
        sheet.page_setup.paperSize = sheet.PAPERSIZE_A4
        sheet.page_setup.fitToWidth = 1
        sheet.page_setup.fitToHeight = 0
        sheet.print_title_rows = "1:1"
    output = BytesIO()
    workbook.save(output)
    return output.getvalue()


def pdf(report: ReportData) -> bytes:
    with _font_lock:
        for name, file in [
            ("Library", "NotoSans-Regular.ttf"),
            ("LibraryBold", "NotoSans-Bold.ttf"),
        ]:
            if name not in pdfmetrics.getRegisteredFontNames():
                pdfmetrics.registerFont(TTFont(name, str(FONT_DIRECTORY / file)))
    body = ParagraphStyle("body", fontName="Library", fontSize=8, leading=11, spaceAfter=5)
    heading = ParagraphStyle(
        "heading", parent=body, fontName="LibraryBold", fontSize=19, leading=24, spaceAfter=12
    )
    header = ParagraphStyle("header", parent=body, fontName="LibraryBold", textColor=colors.white)

    def paragraph(value: Value, style: ParagraphStyle = body) -> Any:
        value = local(value, report)
        if isinstance(value, datetime):
            value = value.strftime("%Y-%m-%d %H:%M")
        elif isinstance(value, date):
            value = value.isoformat()
        elif value is None:
            value = "-"
        return Paragraph(escape(plain(str(value))).replace("\n", "<br/>"), style)

    page = landscape(A4)
    width = page[0] - 64
    output = BytesIO()
    document = SimpleDocTemplate(
        output,
        pagesize=page,
        leftMargin=32,
        rightMargin=32,
        topMargin=32,
        bottomMargin=36,
        title=TITLES[report.kind],
        author="SmartLibrary",
        pageCompression=1,
    )
    story: list[Any] = [paragraph("SmartLibrary", heading), paragraph(TITLES[report.kind], heading)]
    story.extend(
        paragraph(f"{label}: {local(value, report)}") for label, value in metadata(report)[2:-1]
    )
    story.extend([paragraph(report.note), Spacer(1, 8)])
    summary = Table(
        [[paragraph(label), paragraph(value)] for label, value in report.summary],
        colWidths=[width * 0.7, width * 0.3],
        hAlign="LEFT",
    )
    summary.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#ecfdf5")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    story.extend([summary, Spacer(1, 16)])
    if not report.rows:
        story.append(paragraph(EMPTY))
    else:
        table = LongTable(
            [
                [paragraph(item, header) for item in report.headers],
                *[[paragraph(item) for item in row] for row in report.rows],
            ],
            colWidths=[width * part / 100 for part in report.widths],
            repeatRows=1,
            hAlign="LEFT",
            splitByRow=1,
            splitInRow=1,
        )
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#065f46")),
                    (
                        "ROWBACKGROUNDS",
                        (0, 1),
                        (-1, -1),
                        [colors.white, colors.HexColor("#f4f7f6")],
                    ),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("LINEBELOW", (0, 0), (-1, -1), 0.25, colors.HexColor("#cbd5e1")),
                    ("TOPPADDING", (0, 0), (-1, -1), 6),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ]
            )
        )
        story.append(table)

    def footer(canvas: Canvas, doc: Any) -> None:
        canvas.saveState()
        canvas.setFont("Library", 8)
        canvas.setFillColor(colors.HexColor("#475569"))
        canvas.drawString(32, 19, "SmartLibrary | " + TITLES[report.kind])
        canvas.drawRightString(page[0] - 32, 19, f"Бет {doc.page}")
        canvas.restoreState()

    document.build(story, onFirstPage=footer, onLaterPages=footer)
    return output.getvalue()
