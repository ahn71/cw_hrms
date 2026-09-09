import frappe
from frappe import _

def execute(filters=None):
    columns = get_columns()
    data = []

    if not filters:
        filters = {}

    conditions = get_conditions(filters)

    # Fetch Employee Checkins EXCEPT device logs
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

    # Aggregate counts for summary columns
    total_applications = len(checkins)
    in_miss_count = sum(1 for d in checkins if d.log_type == 'IN')
    out_miss_count = sum(1 for d in checkins if d.log_type == 'OUT')

    # Determine overall most missed punch type
    if in_miss_count > out_miss_count:
        most_missed = f"IN ({in_miss_count})"
    elif out_miss_count > in_miss_count:
        most_missed = f"OUT ({out_miss_count})"
    elif in_miss_count > 0:
        most_missed = f"Equal (IN:{in_miss_count}/OUT:{out_miss_count})"
    else:
        most_missed = "N/A"

    # Populate table rows with summary appended as the last columns
    for row in checkins:
        data.append({
            "employee": row.employee,
            "employee_name": row.employee_name,
            "department": row.department,
            "company": row.company,
            "application_date": row.application_date,
            "checkin_time": row.checkin_time,
            "log_type": row.log_type,
            "workflow_state": row.workflow_state or "Submitted",
            "total_requests": total_applications,
            "in_out_summary": f"IN: {in_miss_count} | OUT: {out_miss_count}",
            "most_missed_punch": most_missed
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
            "width": 110
        },
        {
            "fieldname": "employee_name",
            "label": _("Employee Name"),
            "fieldtype": "Data",
            "width": 150
        },
        {
            "fieldname": "department",
            "label": _("Department"),
            "fieldtype": "Link",
            "options": "Department",
            "width": 130
        },
        {
            "fieldname": "company",
            "label": _("Company"),
            "fieldtype": "Link",
            "options": "Company",
            "width": 120
        },
        {
            "fieldname": "application_date",
            "label": _("Applied Date"),
            "fieldtype": "Date",
            "width": 110
        },
        {
            "fieldname": "checkin_time",
            "label": _("Punch Log Time"),
            "fieldtype": "Datetime",
            "width": 150
        },
        {
            "fieldname": "log_type",
            "label": _("Punch Type"),
            "fieldtype": "Data",
            "width": 100
        },
        {
            "fieldname": "workflow_state",
            "label": _("Status"),
            "fieldtype": "Data",
            "width": 110
        },
        {
            "fieldname": "total_requests",
            "label": _("Total Applications"),
            "fieldtype": "Int",
            "width": 130
        },
        {
            "fieldname": "in_out_summary",
            "label": _("IN / OUT Count"),
            "fieldtype": "Data",
            "width": 140
        },
        {
            "fieldname": "most_missed_punch",
            "label": _("Most Missed"),
            "fieldtype": "Data",
            "width": 130
        }
    ]