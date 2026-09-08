import frappe
from frappe import _

def execute(filters=None):
    columns = get_columns()
    data = []

    if not filters:
        filters = {}

    conditions = get_conditions(filters)

    # Fetch Employee Checkins EXCEPT device logs (Device ID is empty/NULL)
    checkins = frappe.db.sql(f"""
        SELECT 
            emp.name as employee,
            emp.employee_name,
            emp.department,
            emp.company,
            DATE(chk.creation) as application_date,
            chk.time as checkin_time,
            chk.log_type,
            chk.workflow_state
        FROM `tabEmployee Checkin` chk
        INNER JOIN `tabEmployee` emp ON chk.employee = emp.name
        WHERE {conditions}
          AND (chk.device_id IS NULL OR chk.device_id = '')
        ORDER BY chk.creation DESC
    """, filters, as_dict=True)

    if not checkins:
        return columns, data

    # 1. Summary Calculations for Manual Requests
    total_applications = len(checkins)
    in_miss_count = sum(1 for d in checkins if d.log_type == 'IN')
    out_miss_count = sum(1 for d in checkins if d.log_type == 'OUT')

    # Determining Most Missed Punch
    most_missed_punch = "N/A"
    if in_miss_count > out_miss_count:
        most_missed_punch = f"IN Punch ({in_miss_count} times)"
    elif out_miss_count > in_miss_count:
        most_missed_punch = f"OUT Punch ({out_miss_count} times)"
    elif in_miss_count > 0 and in_miss_count == out_miss_count:
        most_missed_punch = f"Equal (IN: {in_miss_count}, OUT: {out_miss_count})"

    # Summary Row at the Top
    data.append({
        "employee_name": f"<b>Total Manual Requests: {total_applications}</b>",
        "department": f"<b>IN Requests: {in_miss_count} | OUT Requests: {out_miss_count}</b>",
        "log_type": f"<b>Most Missed: {most_missed_punch}</b>"
    })

    # Separator Row
    data.append({})

    # 2. Detail Rows
    for row in checkins:
        data.append({
            "employee": row.employee,
            "employee_name": row.employee_name,
            "department": row.department,
            "company": row.company,
            "application_date": row.application_date,
            "checkin_time": row.checkin_time,
            "log_type": row.log_type,
            "workflow_state": row.workflow_state or "Submitted"
        })

    return columns, data


def get_conditions(filters):
    conditions = ["1=1"]

    if filters.get("company"):
        conditions.append("emp.company = %(company)s")

    if filters.get("employee"):
        conditions.append("emp.name = %(employee)s")

    if filters.get("department"):
        conditions.append("emp.department = %(department)s")

    if filters.get("from_date"):
        conditions.append("DATE(chk.creation) >= %(from_date)s")

    if filters.get("to_date"):
        conditions.append("DATE(chk.creation) <= %(to_date)s")

    return " AND ".join(conditions)


def get_columns():
    return [
        {
            "fieldname": "employee",
            "label": _("Employee ID"),
            "fieldtype": "Link",
            "options": "Employee",
            "width": 120
        },
        {
            "fieldname": "employee_name",
            "label": _("Employee Name"),
            "fieldtype": "Data",
            "width": 160
        },
        {
            "fieldname": "department",
            "label": _("Department"),
            "fieldtype": "Link",
            "options": "Department",
            "width": 140
        },
        {
            "fieldname": "company",
            "label": _("Company"),
            "fieldtype": "Link",
            "options": "Company",
            "width": 130
        },
        {
            "fieldname": "application_date",
            "label": _("Applied Date"),
            "fieldtype": "Date",
            "width": 120
        },
        {
            "fieldname": "checkin_time",
            "label": _("Punch Log Time"),
            "fieldtype": "Datetime",
            "width": 160
        },
        {
            "fieldname": "log_type",
            "label": _("Punch Type (IN/OUT)"),
            "fieldtype": "Data",
            "width": 140
        },
        {
            "fieldname": "workflow_state",
            "label": _("Workflow Status"),
            "fieldtype": "Data",
            "width": 130
        }
    ]