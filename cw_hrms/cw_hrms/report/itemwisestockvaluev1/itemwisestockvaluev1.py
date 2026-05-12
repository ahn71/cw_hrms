import frappe
from frappe import _

def execute(filters=None):
    if not filters:
        filters = {}

    columns = get_columns()
    conditions = get_conditions(filters)
    
    # SQL Query: Added item.item_name
    data = frappe.db.sql(f"""
        SELECT 
            SUBSTRING(bin.item_code, 1, 3) as raw_code,
            bin.item_code as variant,
            item.item_name as item_name,
            bin.actual_qty as qty_in_stock,
            bin.warehouse as warehouse,
            wh.company as company
        FROM 
            `tabBin` bin
        INNER JOIN 
            `tabWarehouse` wh ON bin.warehouse = wh.name
        INNER JOIN
            `tabItem` item ON bin.item_code = item.name
        WHERE 
            bin.actual_qty > 0 {conditions}
        ORDER BY 
            raw_code, variant
    """, filters, as_dict=1)

    result = []
    last_raw = None
    
    total_qty = 0
    total_stock_value = 0

    for d in data:
        selling_price = frappe.db.get_value("Item Price", 
            {"item_code": d.variant, "price_list": "Standard Selling"}, "price_list_rate") or 0
        
        stock_value = d.qty_in_stock * selling_price
        total_qty += d.qty_in_stock
        total_stock_value += stock_value

        # Formatting Raw and Variant to show Name below Code
        # We use \n for a new line. 
        # For 'Raw', we logic check if it's a new group to avoid repeating.
        raw_display = f"{d.raw_code}\n{d.item_name[:10]}..." if d.raw_code != last_raw else ""
        variant_display = f"{d.variant}\n{d.item_name}"
        
        row = {
            "raw_code": raw_display,
            "variant": variant_display,
            "qty_in_stock": d.qty_in_stock,
            "selling_price": selling_price,
            "stock_value": stock_value,
            "warehouse": d.warehouse,
            "company": d.company
        }
        result.append(row)
        last_raw = d.raw_code

    if result:
        result.append({
            "variant": "Total",
            "qty_in_stock": total_qty,
            "stock_value": total_stock_value
        })

    report_summary = [
        {"value": total_qty, "indicator": "Blue", "label": _("Total Quantity"), "datatype": "Float"},
        {"value": total_stock_value, "indicator": "Green", "label": _("Total Stock Value"), "datatype": "Currency", 
         "currency": frappe.get_cached_value('Company', filters.get("company"), "default_currency") if filters.get("company") else "BDT"}
    ]

    return columns, result, None, None, report_summary

def get_conditions(filters):
    conditions = ""
    if filters.get("company"):
        conditions += " AND wh.company = %(company)s"
    if filters.get("warehouse"):
        conditions += " AND bin.warehouse = %(warehouse)s"
    if filters.get("item_code"):
        conditions += " AND bin.item_code LIKE %(item_code)s"
    return conditions

def get_columns():
    return [
        # Note: Changed fieldtype to 'Data' for Variant to allow custom string formatting
        {"label": _("Raw"), "fieldname": "raw_code", "fieldtype": "Data", "width": 120},
        {"label": _("Variant"), "fieldname": "variant", "fieldtype": "Data", "width": 180},
        {"label": _("Qty in Stock"), "fieldname": "qty_in_stock", "fieldtype": "Float", "width": 100},
        {"label": _("Selling Price"), "fieldname": "selling_price", "fieldtype": "Currency", "width": 120},
        {"label": _("Stock Value"), "fieldname": "stock_value", "fieldtype": "Currency", "width": 120},
        {"label": _("Warehouse"), "fieldname": "warehouse", "fieldtype": "Link", "options": "Warehouse", "width": 150},
        {"label": _("Company"), "fieldname": "company", "fieldtype": "Link", "options": "Company", "width": 150}
    ]