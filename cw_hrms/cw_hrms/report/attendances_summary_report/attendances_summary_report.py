# Copyright (c) 2026, Codeware Limited and contributors
import frappe
from frappe import _

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
        # Shift সরিয়ে Total Days যোগ করা হয়েছে
        {"label": _("Total Days"), "fieldname": "total_days", "fieldtype": "Float", "width": 100},
        {"label": _("Working Days"), "fieldname": "working_days", "fieldtype": "Float", "width": 100},
        {"label": _("Absent"), "fieldname": "absent_days", "fieldtype": "Float", "width": 80},
        {"label": _("Late"), "fieldname": "late_days", "fieldtype": "Int", "width": 80},
        {"label": _("Outduty"), "fieldname": "out_duty", "fieldtype": "Int", "width": 80},
        {"label": _("Home Office"), "fieldname": "home_office", "fieldtype": "Int", "width": 100},
        {"label": _("Leave"), "fieldname": "leave_days", "fieldtype": "Float", "width": 80},
        # Stay Time এবং Avg Time এখন Data টাইপ (HH:mm:ss এর জন্য)
        {"label": _("Total Stay Time"), "fieldname": "total_stay", "fieldtype": "Data", "width": 130},
        {"label": _("Avg Time"), "fieldname": "avg_time", "fieldtype": "Data", "width": 120},
    ]

def format_duration(hours):
    """ঘণ্টাকে HH:mm:ss ফরমেটে রূপান্তর করার ফাংশন"""
    if not hours:
        return "00:00:00"
    total_seconds = int(hours * 3600)
    hh = total_seconds // 3600
    mm = (total_seconds % 3600) // 60
    ss = total_seconds % 60
    return f"{hh:02}:{mm:02}:{ss:02}"

def get_report_data(filters):
    conditions = "att.docstatus = 1"
    if filters.get("from_date"): conditions += f" AND att.attendance_date >= '{filters.get('from_date')}'"
    if filters.get("to_date"): conditions += f" AND att.attendance_date <= '{filters.get('to_date')}'"
    if filters.get("employee"): conditions += f" AND att.employee = '{filters.get('employee')}'"
    if filters.get("company"): conditions += f" AND att.company = '{filters.get('company')}'"
    if filters.get("department"): conditions += f" AND att.department = '{filters.get('department')}'"

    raw_data = frappe.db.sql(f"""
        SELECT 
            att.employee, att.employee_name, emp.designation, att.department,
            att.status, att.late_entry, att.working_hours
        FROM `tabAttendance` att
        LEFT JOIN `tabEmployee` emp ON att.employee = emp.name
        WHERE {conditions}
    """, as_dict=1)

    emp_map = {}
    for d in raw_data:
        emp = d.employee
        if emp not in emp_map:
            emp_map[emp] = {
                "employee_name": d.employee_name,
                "employee": d.employee,
                "designation": d.designation, 
                "department": d.department,
                "working_days": 0.0, 
                "absent_days": 0.0,
                "late_days": 0,
                "out_duty": 0, 
                "home_office": 0, 
                "leave_days": 0.0,
                "total_stay_raw": 0.0 # ক্যালকুলেশনের জন্য raw number
            }
        
        row = emp_map[emp]
        
        if d.status == "Present":
            row["working_days"] += 1
        elif d.status == "Absent":
            row["absent_days"] += 1
        elif d.status == "Half Day":
            row["working_days"] += 0.5
        elif d.status == "On Leave":
            row["leave_days"] += 1
        elif d.status == "Work From Home":
            row["home_office"] += 1
            row["working_days"] += 1

        if d.late_entry: 
            row["late_days"] += 1
        
        row["total_stay_raw"] += (d.working_hours or 0)

    report_data = []
    for emp_id, val in emp_map.items():
        # Total Days = Working Days + Absent
        val["total_days"] = val["working_days"] + val["absent_days"]
        
        # Avg Time Raw Calculation
        avg_raw = 0
        if val["working_days"] > 0:
            avg_raw = val["total_stay_raw"] / val["working_days"]
        
        # ফরমেটিং HH:mm:ss
        val["total_stay"] = format_duration(val["total_stay_raw"])
        val["avg_time"] = format_duration(avg_raw)
        
        report_data.append(val)

    return report_data