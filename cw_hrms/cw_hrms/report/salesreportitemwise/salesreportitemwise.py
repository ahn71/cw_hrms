import frappe
from frappe import _


def execute(filters=None):
    columns = get_columns()
    data = get_data(filters)
    return columns, data


def get_columns():
    return [
        {"label": _("Date"), "fieldname": "posting_date", "fieldtype": "Date", "width": 110},
        {"label": _("Invoice ID"), "fieldname": "invoice_id", "fieldtype": "Link", "options": "Sales Invoice", "width": 140},
        {"label": _("Customer"), "fieldname": "customer", "fieldtype": "Link", "options": "Customer", "width": 150},
        {"label": _("Item Name"), "fieldname": "item_name", "fieldtype": "Link", "options": "Item", "width": 150},
        {"label": _("Qty"), "fieldname": "qty", "fieldtype": "Float", "width": 80},
        {"label": _("Selling Rate"), "fieldname": "selling_rate", "fieldtype": "Currency", "width": 110},
        {"label": _("Item Total"), "fieldname": "item_total", "fieldtype": "Currency", "width": 110},
        {"label": _("Total"), "fieldname": "total", "fieldtype": "Currency", "width": 110},
        {"label": _("Discount"), "fieldname": "additional_discount", "fieldtype": "Currency", "width": 110},
        {"label": _("Net Total"), "fieldname": "grand_total", "fieldtype": "Currency", "width": 120},
        {"label": _("Paid Amount"), "fieldname": "paid_amount", "fieldtype": "Currency", "width": 110},
        {"label": _("Outstanding"), "fieldname": "outstanding_amount", "fieldtype": "Currency", "width": 110},
    ]

def get_data(filters):
    conditions = get_conditions(filters)

    if filters.get("item"):
        filters["item"] = f"%{filters['item']}%"

    raw_data = frappe.db.sql(f"""
        SELECT
            si.posting_date,
            si.name as invoice_id,
            si.customer,
            sii.item_name,
            sii.qty,
            sii.rate as selling_rate,
            sii.base_amount as item_total,
            si.base_total as invoice_total,
            si.discount_amount as invoice_discount,
            si.base_grand_total as invoice_grand_total,
            (si.base_grand_total - si.outstanding_amount) as invoice_paid,
            si.outstanding_amount as invoice_outstanding
        FROM `tabSales Invoice` si
        JOIN `tabSales Invoice Item` sii ON si.name = sii.parent
        WHERE si.docstatus = 1 {conditions}
        ORDER BY si.posting_date DESC, si.name ASC, sii.idx ASC
    """, filters, as_dict=1)

    final_data    = []
    seen_invoices = set()

    total_qty         = 0
    total_item_total  = 0
    total_total       = 0
    total_discount    = 0
    total_grand_total = 0
    total_paid        = 0
    total_outstanding = 0

    for row in raw_data:
        is_first = row.invoice_id not in seen_invoices
        seen_invoices.add(row.invoice_id)

        total_qty        += row.qty or 0
        total_item_total += row.item_total or 0

        if is_first:
            total_total       += row.invoice_total or 0
            total_discount    += row.invoice_discount or 0
            total_grand_total += row.invoice_grand_total or 0
            total_paid        += (row.invoice_grand_total - row.invoice_outstanding) or 0
            total_outstanding += row.invoice_outstanding or 0

        final_data.append({
            "posting_date":        row.posting_date        if is_first else None,
            "invoice_id":          row.invoice_id          if is_first else None,
            "customer":            row.customer            if is_first else None,
            "total":               row.invoice_total       if is_first else None,
            "additional_discount": row.invoice_discount    if is_first else None,
            "grand_total":         row.invoice_grand_total if is_first else None,
            "paid_amount":         row.invoice_paid        if is_first else None,
            "outstanding_amount":  row.invoice_outstanding if is_first else None,
            "item_name":           row.item_name,
            "qty":                 row.qty,
            "selling_rate":        row.selling_rate,
            "item_total":          row.item_total,
        })

    final_data.append({
        "posting_date":        "Total",
        "invoice_id":          None,
        "customer":            None,
        "item_name":           None,
        "selling_rate":        None,
        "qty":                 total_qty,
        "item_total":          total_item_total,
        "total":               total_total,
        "additional_discount": total_discount,
        "grand_total":         total_grand_total,
        "paid_amount":         total_paid,
        "outstanding_amount":  total_outstanding,
        "is_total_row":        1,
    })

    return final_data

def get_conditions(filters):
    conditions = ""
    if filters.get("company"):   conditions += " AND si.company = %(company)s"
    if filters.get("from_date"): conditions += " AND si.posting_date >= %(from_date)s"
    if filters.get("to_date"):   conditions += " AND si.posting_date <= %(to_date)s"
    if filters.get("item"):      conditions += " AND (sii.item_code LIKE %(item)s OR sii.item_name LIKE %(item)s)"
    return conditions