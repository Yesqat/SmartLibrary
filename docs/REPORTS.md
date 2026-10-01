# PDF and XLSX reports — PHASE 17

POST `/api/v1/admin/reports` accepts `report_type` (inventory, borrowings, overdue,
reservations), `format` (pdf, xlsx), optional inclusive `date_from`/`date_to`.
ADMIN VIEW_ANALYTICS permission and valid Origin are required. Six generations per
account/minute; the shared maximum period is 3660 days. Response is the actual
binary attachment, Content-Disposition safe ASCII filename and X-Report-Rows.

## Data contract

All four reports share PHASE 16 time boundaries, current-state/overdue predicates
and summary aggregations. SQL joins select explicit safe columns; no ORM secret
serialization. One repeatable-read, read-only snapshot supplies rows and metrics.
Database statement timeout is 15 seconds. Generation is synchronous and bounded
to 5000 rows; more returns REPORT_TOO_LARGE (422), never silently truncates.

- Inventory table: nonarchived copies of nonarchived books added in the period.
  Current collection counts and all period additions are separately labeled.
- Borrowings: issued in the period; current status, due/return/lost timestamps.
- Overdue: currently active overdue loans whose due_at is in the period.
  Current total overdue and selected table count are explicitly distinct.
- Reservations: created in the period; assigned copy, hold dates and current status.
  Summary terminal events use their own completion/cancellation/expiry times.

Current snapshots are not historical reconstructions. Reports say this explicitly.
Names are included where operationally useful; emails, passwords, session/QR
credentials and provider secrets are absent. An empty selection returns a useful
metadata/summary report with an explicit no-records statement.

## Files and safety

ReportLab 4.5.1 builds landscape A4 structured paragraphs/tables, summary, selected
dates/timezone/generated_by, repeated headers and page numbers. Bundled Noto Sans
Regular/Bold include Kazakh/Cyrillic glyphs and their SIL OFL license; source revision
is in backend/app/assets/fonts/README.md. Arbitrary text is escaped before entering
ReportLab markup; no remote images or resources are loaded.

openpyxl 3.1.5 creates Қорытынды and Жазбалар sheets with headers, filters, frozen
row, widths, wrap alignment, numeric cells and actual date/datetime cells. Datetimes
are converted to the named report timezone before removing timezone metadata,
because Excel cannot store it. Strings are forced to string cell type, including
formula-leading characters. No external links/formulas are generated.

Reports exist in response memory, without publicly stored files. Backend checks
live session/role again after generation and audits REPORT_GENERATED with safe
type/format/count. Unexpected failures return REPORT_GENERATION_FAILED (503),
without exception details. Browser blobs are revoked when replaced/unmounted.
The UI shows pending, success, explicit download, no-data and safe error states.

## Verification

Four native renderer tests, ten PostgreSQL report tests and the shared analytics
regression gate execute actual libraries/database queries. All eight type/format
combinations were parsed. PDF tests inspect embedded glyph coverage, escaped markup,
multi-page headers and final-row preservation. XLSX tests inspect numeric/date
types and formula safety. A real Edge flow downloads PDF and XLSX through Nginx.

Additional current-database inspection exported 27 inventory rows, 10 borrowings,
one overdue and 16 reservations. All four XLSX files reopened; seven PDF pages
were rendered by Poppler and visually inspected. Evidence is local/private under
work/report-verification; test data is not production analytics. See PHASE_17_REPORT.md.

Implementation references: [ReportLab Unicode fonts](https://docs.reportlab.com/reportlab/userguide/ch3_fonts/),
[openpyxl date/time storage](https://openpyxl.readthedocs.io/en/stable/datetime.html),
[Noto source](https://github.com/notofonts/noto-fonts/tree/main/hinted/ttf/NotoSans).


PHASE 22 repeated generation/reopening and visual review for every pair/page.
Evidence: work/logs/final-report-generation.txt, final-artifact-checks.txt and
work/final-report-verification/. These are actual development database exports.
