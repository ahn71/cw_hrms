# Copyright (c) 2026, Codeware Limited and contributors
import frappe
from frappe import _
from frappe.utils import getdate, add_days,date_diff


def execute(filters=None):
    if not filters:
        filters = {}

    columns = get_columns()
    data = get_report_data(filters)
    
    return columns, data

def get_columns():
    return [
        {"label": _("Employee Name"), "fieldname": "employee_name", "fieldtype": "Data", "width": 150},
        {"label": _("Emp ID"), "fieldname": "employee", "fieldtype": "Link", "options": "Employee", "width": 120},
        {"label": _("Designation"), "fieldname": "designation", "fieldtype": "Data", "width": 120},
        {"label": _("Department"), "fieldname": "department", "fieldtype": "Data", "width": 120},
        {"label": _("Total Days"), "fieldname": "total_days", "fieldtype": "Float", "width": 100},
        {"label": _("Working Days"), "fieldname": "working_days", "fieldtype": "Float", "width": 100},
        {"label": _("Holiday/Weekend"), "fieldname": "holidays", "fieldtype": "Float", "width": 120}, # নতুন কলাম
        {"label": _("Absent"), "fieldname": "absent_days", "fieldtype": "Float", "width": 80},
        {"label": _("Late"), "fieldname": "late_days", "fieldtype": "Int", "width": 80},
        {"label": _("Home Office"), "fieldname": "home_office", "fieldtype": "Int", "width": 100},
        {"label": _("Leave"), "fieldname": "leave_days", "fieldtype": "Float", "width": 80},
        {"label": _("Total Stay Time"), "fieldname": "total_stay", "fieldtype": "Data", "width": 130},
        {"label": _("Avg Time"), "fieldname": "avg_time", "fieldtype": "Data", "width": 120},
    ]

def format_duration(hours):
    if not hours: return "00:00:00"
    total_seconds = int(hours * 3600)
    hh = total_seconds // 3600
    mm = (total_seconds % 3600) // 60
    ss = total_seconds % 60
    return f"{hh:02}:{mm:02}:{ss:02}"

def get_employee_holiday_count(holiday_list, filters):
    """নির্দিষ্ট Holiday List এর আন্ডারে কতগুলো ছুটি আছে তা বের করা"""
    if not holiday_list:
        return 0
        
    from_date = filters.get("from_date")
    to_date = filters.get("to_date")
    
    # tabHoliday টেবিল থেকে নির্দিষ্ট লিস্টের জন্য কাউন্ট
    count = frappe.db.sql("""
        SELECT COUNT(name) 
        FROM `tabHoliday` 
        WHERE parent = %s AND holiday_date BETWEEN %s AND %s
    """, (holiday_list, from_date, to_date))
    
    return count[0][0] if count else 0

def get_report_data(filters):

    conditions = "att.docstatus = 1"

    if filters.get("from_date"):
        conditions += f" AND att.attendance_date >= '{filters.get('from_date')}'"

    if filters.get("to_date"):
        conditions += f" AND att.attendance_date <= '{filters.get('to_date')}'"

    if filters.get("employee"):
        conditions += f" AND att.employee = '{filters.get('employee')}'"

    if filters.get("company"):
        conditions += f" AND att.company = '{filters.get('company')}'"

    if filters.get("department"):
        conditions += f" AND att.department = '{filters.get('department')}'"

    if filters.get("employee_status"):
        conditions += f" AND emp.status = '{filters.get('employee_status')}'"

    raw_data = frappe.db.sql(f"""
        SELECT 
            att.employee,
            att.employee_name,
            emp.designation,
            att.department,
            att.status,
            att.late_entry,
            att.working_hours,
            att.attendance_request,
            emp.holiday_list,
            att.attendance_date

        FROM `tabAttendance` att

        LEFT JOIN `tabEmployee` emp
            ON att.employee = emp.name

        WHERE {conditions}

    """, as_dict=1)

    holiday_count_cache = {}
    holiday_days_cache = {}

    emp_map = {}

    for d in raw_data:

        emp = d.employee
        h_list = d.holiday_list

        # Holiday cache
        if h_list not in holiday_days_cache:

            holidays = frappe.db.get_all(
                "Holiday",
                filters={
                    "parent": h_list,
                    "holiday_date": [
                        "between",
                        [filters.get("from_date"), filters.get("to_date")]
                    ]
                },
                fields=["holiday_date"]
            )

            holiday_days_cache[h_list] = [
                str(h.holiday_date) for h in holidays
            ]

            holiday_count_cache[h_list] = len(holidays)

        # Employee initialize
        if emp not in emp_map:

            emp_map[emp] = {
                "employee_name": d.employee_name,
                "employee": d.employee,
                "designation": d.designation,
                "department": d.department,

                "working_days": 0.0,
                "absent_days": 0.0,
                "late_days": 0,
                "home_office": 0,
                "leave_days": 0.0,
                "od_days": 0,

                "holidays": holiday_count_cache[h_list],

                "total_stay_raw": 0.0
            }

        row = emp_map[emp]

        curr_date = str(d.attendance_date)

        # Holiday check
        is_holiday = curr_date in holiday_days_cache.get(h_list, [])

        # Present
        if d.status == "Present":

            row["working_days"] += 1

            # OD day detect
            if d.attendance_request:
                row["od_days"] += 1

        # Absent
        elif d.status == "Absent":

            if not is_holiday:
                row["absent_days"] += 1

        # Half Day
        elif d.status == "Half Day":

            row["working_days"] += 0.5

        # Leave
        elif d.status == "On Leave":

            row["leave_days"] += 1

        # Work From Home
        elif d.status == "Work From Home":

            row["home_office"] += 1
            row["working_days"] += 1

        # Late count
        if d.late_entry and d.status != "Half Day":
            row["late_days"] += 1

        # Total working hour add
        row["total_stay_raw"] += (d.working_hours or 0)

    report_data = []

    total_period_days = (
        date_diff(filters.get("to_date"), filters.get("from_date")) + 1
    )

    for emp_id, val in emp_map.items():

        val["total_days"] = total_period_days

        # OD bad diye avg calculation
        actual_working_days = (
            val["working_days"] - val["od_days"]-val["home_office"]
        )

        avg_raw = (
            val["total_stay_raw"] / actual_working_days
            if actual_working_days > 0 else 0
        )

        val["total_stay"] = format_duration(
            val["total_stay_raw"]
        )

        val["avg_time"] = format_duration(
            avg_raw
        )

        report_data.append(val)

    return report_data