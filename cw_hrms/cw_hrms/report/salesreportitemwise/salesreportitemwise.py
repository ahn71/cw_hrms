import frappe
from frappe import _  # এখানে একটি underscore হবে

def execute(filters=None):
    columns = get_columns()
    data = get_data(filters)
    return columns, data

def get_columns():
    return [
        {"label": _("Item Name"), "fieldname": "item_name", "fieldtype": "Link", "options": "Item", "width": 150},
        {"label": _("Warehouse"), "fieldname": "warehouse", "fieldtype": "Link", "options": "Warehouse", "width": 120},
        {"label": _("Company"), "fieldname": "company", "fieldtype": "Data", "width": 120},
        {"label": _("Sales Date"), "fieldname": "posting_date", "fieldtype": "Date", "width": 100},
        {"label": _("Sales Qty"), "fieldname": "qty", "fieldtype": "Float", "width": 100},
        {"label": _("Standard Selling Price"), "fieldname": "standard_selling_price", "fieldtype": "Currency", "width": 150},
        {"label": _("Total Sell Price"), "fieldname": "total_sell_price", "fieldtype": "Currency", "width": 130},
        {"label": _("Discount Amount"), "fieldname": "discount_amount", "fieldtype": "Currency", "width": 120},
        {"label": _("Paid"), "fieldname": "paid_amount", "fieldtype": "Currency", "width": 100},
        {"label": _("Outstanding"), "fieldname": "outstanding_amount", "fieldtype": "Currency", "width": 120},
    ]

def get_data(filters):
    conditions = get_conditions(filters)
    
    # Query to fetch sales invoice items with standard selling price join
    raw_data = frappe.db.sql(f"""
        SELECT 
            sii.item_name, 
            sii.warehouse, 
            si.company, 
            si.posting_date, 
            sii.qty, 
            sii.base_amount as total_sell_price, 
            sii.discount_amount, 
            si.paid_amount, 
            si.outstanding_amount,
            item_price.price_list_rate as std_rate
        FROM `tabSales Invoice` si
        JOIN `tabSales Invoice Item` sii ON si.name = sii.parent
        LEFT JOIN `tabItem Price` item_price ON item_price.item_code = sii.item_code 
            AND item_price.price_list = 'Standard Selling'
        WHERE si.docstatus = 1 {conditions}
        ORDER BY si.posting_date DESC
    """, filters, as_dict=1)

    return raw_data

def get_conditions(filters):
    conditions = ""
    if filters.get("company"): conditions += " AND si.company = %(company)s"
    if filters.get("from_date"): conditions += " AND si.posting_date >= %(from_date)s"
    if filters.get("to_date"): conditions += " AND si.posting_date <= %(to_date)s"
    if filters.get("item_code"): conditions += " AND sii.item_code = %(item_code)s"
    if filters.get("warehouse"): conditions += " AND sii.warehouse = %(warehouse)s"
    return conditions