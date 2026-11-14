import io
from openpyxl import Workbook
from openpyxl.styles import Font
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


def export_report_pdf(report_data: dict) -> bytes:
    """Render a custom date range report as a formatted PDF document (FR19, FR20)."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, title="Expense & Budget Report")
    styles = getSampleStyleSheet()
    elements = []

    elements.append(Paragraph("Smart Expense & Budget Report", styles["Title"]))
    elements.append(
        Paragraph(
            f"Period: {report_data['start_date']} to {report_data['end_date']}",
            styles["Normal"],
        )
    )
    elements.append(Spacer(1, 12))

    # Summary Statistics
    elements.append(Paragraph("Summary Statistics", styles["Heading2"]))
    summary = report_data["summary"]
    summary_table = Table(
        [
            ["Total Spend", "Transactions", "Average Spend"],
            [
                summary["total_spend"],
                str(summary["transaction_count"]),
                summary["average_spend"],
            ],
        ]
    )
    summary_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1e293b")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ]
        )
    )
    elements.append(summary_table)
    elements.append(Spacer(1, 14))

    # Category Breakdown
    elements.append(Paragraph("Category Breakdown", styles["Heading2"]))
    cat_rows = [["Category", "Total Amount", "Transactions", "Share (%)"]]
    for cat in report_data["category_breakdown"]:
        cat_rows.append(
            [
                cat["category_name"],
                cat["total_amount"],
                str(cat["transaction_count"]),
                f"{cat['percentage']}%",
            ]
        )
    if len(cat_rows) == 1:
        cat_rows.append(["No expenses in range", "0.00", "0", "0%"])

    cat_table = Table(cat_rows)
    cat_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#334155")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ]
        )
    )
    elements.append(cat_table)
    elements.append(Spacer(1, 14))

    # Budget vs Actual
    elements.append(Paragraph("Budget vs. Actual", styles["Heading2"]))
    bva_rows = [["Budget", "Category", "Limit", "Actual", "Remaining", "Utilization"]]
    for item in report_data["budget_vs_actual"]:
        bva_rows.append(
            [
                item["name"],
                item["category_name"],
                item["limit_amount"],
                item["actual_spent"],
                item["remaining_amount"],
                f"{item['utilization_percentage']}%",
            ]
        )
    if len(bva_rows) == 1:
        bva_rows.append(["No budgets in range", "-", "-", "-", "-", "-"])

    bva_table = Table(bva_rows)
    bva_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#334155")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ]
        )
    )
    elements.append(bva_table)

    doc.build(elements)
    return buffer.getvalue()


def export_report_excel(report_data: dict) -> bytes:
    """Render a custom date range report as an Excel (.xlsx) workbook (FR19, FR20)."""
    wb = Workbook()

    # Sheet 1: Summary
    ws_summary = wb.active
    ws_summary.title = "Summary"
    ws_summary.append(["Smart Expense & Budget Report"])
    ws_summary["A1"].font = Font(bold=True, size=14)
    ws_summary.append(["Period", f"{report_data['start_date']} to {report_data['end_date']}"])
    ws_summary.append([])
    ws_summary.append(["Total Spend", "Transactions", "Average Spend"])
    for cell in ws_summary[4]:
        cell.font = Font(bold=True)
    summary = report_data["summary"]
    ws_summary.append([summary["total_spend"], summary["transaction_count"], summary["average_spend"]])

    # Sheet 2: Category Breakdown
    ws_cat = wb.create_sheet(title="Category Breakdown")
    ws_cat.append(["Category", "Total Amount", "Transactions", "Share (%)"])
    for cell in ws_cat[1]:
        cell.font = Font(bold=True)
    for cat in report_data["category_breakdown"]:
        ws_cat.append(
            [cat["category_name"], cat["total_amount"], cat["transaction_count"], cat["percentage"]]
        )

    # Sheet 3: Budget vs Actual
    ws_bva = wb.create_sheet(title="Budget vs Actual")
    ws_bva.append(["Budget", "Category", "Period", "Limit", "Actual Spent", "Remaining", "Utilization (%)"])
    for cell in ws_bva[1]:
        cell.font = Font(bold=True)
    for item in report_data["budget_vs_actual"]:
        ws_bva.append(
            [
                item["name"],
                item["category_name"],
                item["period"],
                item["limit_amount"],
                item["actual_spent"],
                item["remaining_amount"],
                item["utilization_percentage"],
            ]
        )

    buffer = io.BytesIO()
    wb.save(buffer)
    return buffer.getvalue()
