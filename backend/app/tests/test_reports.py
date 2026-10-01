from datetime import UTC, date, datetime
from io import BytesIO

from openpyxl import load_workbook
from pypdf import PdfReader
from reportlab.pdfbase import pdfmetrics

from app.schemas.analytics import AnalyticsDates
from app.services.analytics.definitions import period
from app.services.reports.data import ReportData
from app.services.reports.render import EMPTY, pdf, spreadsheet


def sample(rows=None):
    return ReportData(
        "inventory",
        period(
            AnalyticsDates(date_from=date(2025, 1, 1), date_to=date(2025, 1, 2)), "Asia/Qyzylorda"
        ),
        "Әкімші",
        "Нақты дерек тексеруі",
        ["Кітап", "Саны", "Уақыты"],
        [50, 15, 35],
        rows
        if rows is not None
        else [["Әә Ғғ Ққ Ңң Өө Ұұ Үү Һһ Іі Қазақша Русский", 7, datetime(2025, 1, 1, tzinfo=UTC)]],
        [("Саны", 7), ("Үлес", None)],
    )


def test_pdf_embeds_kazakh_glyphs_and_escapes_untrusted_markup():
    report = sample()
    report.rows.append(['<img src="https://invalid.example/private"/> & =1+1', 0, None])
    result = pdf(report)
    document = PdfReader(BytesIO(result))
    content = "\n".join(page.extract_text() for page in document.pages)
    assert "Әә Ғғ Ққ Ңң Өө Ұұ Үү Һһ Іі" in content
    assert '<img src="https://invalid.example/private"/> & =1+1' in content
    assert "Бет 1" in content and "Әкімші" in content and "Asia/Qyzylorda" in content
    font = pdfmetrics.getFont("Library")
    assert all(ord(letter) in font.face.charToGlyph for letter in "ӘәҒғҚқҢңӨөҰұҮүҺһІі")
    assert any(
        "/FontFile2" in item.get_object().get("/FontDescriptor", {}).get_object()
        for item in document.pages[0]["/Resources"]["/Font"].values()
        if "/FontDescriptor" in item.get_object()
    )


def test_xlsx_numeric_dates_timezone_and_formula_injection():
    report = sample()
    for text in [
        '=HYPERLINK("https://invalid.example")',
        "+1+1",
        "-1+1",
        "@SUM(A1)",
        "safe\x00text",
    ]:
        report.rows.append([text, 3.5, date(2025, 1, 2)])
    book = load_workbook(BytesIO(spreadsheet(report)), data_only=False)
    assert book.sheetnames == ["Қорытынды", "Жазбалар"]
    sheet = book["Жазбалар"]
    assert sheet["B2"].value == 7 and sheet["B2"].data_type == "n"
    assert sheet["C2"].value == datetime(2025, 1, 1, 5)
    assert sheet["C2"].is_date and sheet["C3"].is_date
    assert sheet["A3"].value.startswith("=HYPERLINK") and sheet["A3"].data_type == "s"
    assert all(cell.data_type != "f" for row in sheet for cell in row)
    assert sheet["A7"].value == "safetext"
    assert sheet.freeze_panes == "A2" and sheet.auto_filter.ref


def test_no_data_reports_contain_explicit_metadata_and_empty_statement():
    report = sample([])
    assert EMPTY in PdfReader(BytesIO(pdf(report))).pages[0].extract_text()
    book = load_workbook(BytesIO(spreadsheet(report)))
    assert book["Жазбалар"]["A2"].value == EMPTY
    assert book["Қорытынды"].max_row > 8


def test_pdf_repeats_headers_and_numbers_multiple_pages_without_truncating_rows():
    report = sample([[f"Қазақша ұзын атау {i} " + "мәтін " * 20, i, None] for i in range(70)])
    document = PdfReader(BytesIO(pdf(report)))
    assert len(document.pages) > 2
    for index, page in enumerate(document.pages):
        text = page.extract_text()
        assert f"Бет {index + 1}" in text
        if index > 0:
            assert "Кітап" in text and "Уақыты" in text
    assert "Қазақша ұзын атау 69" in document.pages[-1].extract_text()
