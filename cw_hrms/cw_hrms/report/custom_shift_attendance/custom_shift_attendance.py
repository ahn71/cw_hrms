# Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from datetime import timedelta
import frappe
from frappe import _
from frappe.utils import cint, flt, format_datetime, format_duration
from erpnext.setup.doctype.holiday_list.holiday_list import is_holiday
from frappe.utils import getdate, nowdate

def execute(filters=None):
    if not filters:
        filters = {}

    columns = get_columns()
    data = get_data(filters)
    chart = get_chart_data(data)
    report_summary = get_report_summary(data)

    # অপ্রয়োজনীয় throw এবং self কল মুছে ফেলা হয়েছে যাতে রিপোর্ট লোড হয়
    return columns, data, None, chart, report_summary

def get_columns():
    return [
        {"label": _("Employee"), "fieldname": "employee", "fieldtype": "Link", "options": "Employee", "width": 220},
        {"fieldname": "employee_name", "fieldtype": "Data", "label": _("Employee Name"), "width": 0, "hidden": 1},
        {"label": _("Shift"), "fieldname": "shift", "fieldtype": "Link", "options": "Shift Type", "width": 120},
        {"label": _("Attendance Date"), "fieldname": "attendance_date", "fieldtype": "Date", "width": 130},
        {"label": _("Status"), "fieldname": "status", "fieldtype": "Data", "width": 80},
        {"label": _("Shift Start Time"), "fieldname": "shift_start", "fieldtype": "Data", "width": 125},
        {"label": _("Shift End Time"), "fieldname": "shift_end", "fieldtype": "Data", "width": 125},
        {"label": _("In Time"), "fieldname": "in_time", "fieldtype": "Data", "width": 120},
        {"label": _("Out Time"), "fieldname": "out_time", "fieldtype": "Data", "width": 120},
        {"label": _("Total Working Hours"), "fieldname": "working_hours", "fieldtype": "Data", "width": 100},
        {"label": _("Late Entry By"), "fieldname": "late_entry_hrs", "fieldtype": "Data", "width": 120},
        {"label": _("Early Exit By"), "fieldname": "early_exit_hrs", "fieldtype": "Data", "width": 120},
        {"label": _("Department"), "fieldname": "department", "fieldtype": "Link", "options": "Department", "width": 150},
        {"label": _("Company"), "fieldname": "company", "fieldtype": "Link", "options": "Company", "width": 150},
        {"label": _("Attendance ID"), "fieldname": "name", "fieldtype": "Link", "options": "Attendance", "width": 150},
    ]

def get_data(filters):
    query = get_query(filters)
    data = query.run(as_dict=True)
    data = update_data(data, filters)
    return data

def get_query(filters):
    attendance = frappe.qb.DocType("Attendance")
    checkin = frappe.qb.DocType("Employee Checkin")
    shift_type = frappe.qb.DocType("Shift Type")
    employee = frappe.qb.DocType("Employee")

    query = (
        frappe.qb.from_(attendance)
        .left_join(checkin).on(checkin.attendance == attendance.name)
        .left_join(shift_type).on(attendance.shift == shift_type.name)
        .left_join(employee).on(attendance.employee == employee.name)
        .select(
            attendance.name, attendance.employee, attendance.employee_name,
            attendance.shift, attendance.attendance_date, attendance.status,
            attendance.in_time, attendance.out_time, attendance.working_hours,
            attendance.late_entry, attendance.early_exit, attendance.department,
            attendance.company, checkin.shift_start, checkin.shift_end,
            shift_type.enable_late_entry_marking, shift_type.late_entry_grace_period,
            shift_type.enable_early_exit_marking, shift_type.early_exit_grace_period,
            employee.holiday_list
        )
        .where(attendance.docstatus == 1)
    )

    # --- ইউজার ভিত্তিক ফিল্টারিং ---
    user_roles = frappe.get_roles(frappe.session.user)
    if "HR Manager" not in user_roles and "System Manager" not in user_roles:
        # লগইন করা ইউজারের সাথে যুক্ত Employee আইডি খুঁজে বের করা
        logged_in_employee = frappe.db.get_value("Employee", {"user_id": frappe.session.user}, "name")
        if logged_in_employee:
            query = query.where(attendance.employee == logged_in_employee)
        else:
            # যদি ইউজারের সাথে কোনো Employee লিংক না থাকে তবে কিছুই দেখাবে না
            query = query.where(attendance.employee == "None")
    # -----------------------------

    # ফিল্টার হ্যান্ডলিং
    if filters.get("from_date"): query = query.where(attendance.attendance_date >= filters.get("from_date"))
    if filters.get("to_date"): query = query.where(attendance.attendance_date <= filters.get("to_date"))
    if filters.get("employee"): query = query.where(attendance.employee == filters.get("employee"))
    if filters.get("company"): query = query.where(attendance.company == filters.get("company"))

    query = query.groupby(attendance.name)
    #frappe.msgprint(f"AttList ID: {query}")
    return query
def update_data(data, filters):
    consider_grace = filters.get("consider_grace_period")
    
    for d in data:
        total_seconds = 0
        if d.in_time and d.out_time:
            diff = d.out_time - d.in_time
            total_seconds = diff.total_seconds()
        
        hms_time = format_seconds_to_hms(total_seconds)
        d.working_hours_float = total_seconds / 3600.0

        d.is_weekend_or_holiday = 0
        # লাইভ সার্ভারের জন্য ক্যাশ এড়িয়ে সরাসরি ভ্যালু নেওয়া
        h_list = d.holiday_list or frappe.db.get_value("Company", d.company, "default_holiday_list")
        
        if h_list and d.attendance_date:
            holiday_record = frappe.db.get_value("Holiday", 
                {"parent": h_list, "holiday_date": d.attendance_date}, 
                ["weekly_off"], as_dict=True)

            if holiday_record:
                d.is_weekend_or_holiday = 1
                if holiday_record.weekly_off:
                    d.status = _("Weekend")
                else:
                    d.status = _("Holiday")
            else:
                original_status = d.get("status") or "Absent"
                if "on leave" in original_status.lower():
                    d.status = _("On Leave")
                else:
                    d.status = f"{original_status} ({hms_time})"

        d.working_hours = hms_time
        update_late_entry(d, consider_grace)
        update_early_exit(d, consider_grace)
        
        # ফরম্যাটিং: এখানে শুধুমাত্র সময় রিটার্ন করবে
        d.in_time, d.out_time = convert_datetime_to_time_for_same_date(d.in_time, d.out_time)
        d.shift_start, d.shift_end = convert_datetime_to_time_for_same_date(d.shift_start, d.shift_end)

    return data

def get_report_summary(data):
    if not data: return []
    #frappe.msgprint(f"AttList ID: {data}")
    t = p = l = a = e = hol = h = leave = 0
    total_seconds = 0.0
    today = getdate(nowdate())

    for d in data:
        # শুধুমাত্র আজ পর্যন্ত হওয়া এটেনডেন্সগুলো প্রসেস হবে
        if getdate(d.get("attendance_date")) <= today:
            t += 1 # Total Count
            
            if d.get("is_weekend_or_holiday"):
                hol += 1
            else:
                status = str(d.get("status") or "").strip().lower()
                
                # গড় কর্মঘণ্টার জন্য সেকেন্ড ক্যালকুলেশন
                wh_seconds = flt(d.get("working_hours_float") or 0) * 3600
                total_seconds += wh_seconds

                if "present" in status:
                    p += 1
                elif "half day" in status:
                    h += 1
                elif "on leave" in status:
                    leave += 1
                elif "absent" in status:
                    a += 1

            if d.get("late_entry"): l += 1
            if d.get("early_exit"): e += 1

    # গড় কর্মঘণ্টা (Avg Wh) বের করা
    working_days = p + h
    avg_wh_hms = format_seconds_to_hms(total_seconds / working_days) if working_days > 0 else "00:00:00"

    return [
        {"value": t, "label": _("Total"), "indicator": "Blue", "datatype": "Int"},
        {"value": p, "label": _("Present"), "indicator": "Green", "datatype": "Int"},
        {"value": l, "label": _("Late"), "indicator": "Red", "datatype": "Int"},
        {"value": a, "label": _("Absent"), "indicator": "Red", "datatype": "Int"},
        {"value": e, "label": _("Early"), "indicator": "Red", "datatype": "Int"},
        {"value": hol, "label": _("Holiday"), "indicator": "Purple", "datatype": "Int"},
        {"value": h, "label": _("Half Day"), "indicator": "Orange", "datatype": "Int"},
        {"value": leave, "label": _("Leave"), "indicator": "Yellow", "datatype": "Int"},
        {"value": avg_wh_hms, "label": _("Avg Wh"), "indicator": "Blue", "datatype": "Data"} 
    ]
def get_chart_data(data):
    if not data: return None
    shifts = {}
    for entry in data:
        s = entry.shift or _("No Shift")
        shifts[s] = shifts.get(s, 0) + 1
    return {
        "data": {"labels": list(shifts.keys()), "datasets": [{"values": list(shifts.values())}]},
        "type": "percentage"
    }

def format_in_out_time(in_time, out_time, attendance_date):
    if not in_time and not out_time: return None, None
    return convert_datetime_to_time_for_same_date(in_time, out_time)

def convert_datetime_to_time_for_same_date(start, end):
    # ইন-টাইম এবং আউট-টাইম যাই হোক না কেন, শুধুমাত্র সময় টুকু নেওয়া হচ্ছে
    formatted_start = start.strftime("%H:%M:%S") if start else None
    formatted_end = end.strftime("%H:%M:%S") if end else None
    
    return formatted_start, formatted_end

def format_float_precision(value):
    precision = cint(frappe.db.get_default("float_precision")) or 2
    return flt(value, precision)

def update_late_entry(entry, consider_grace_period):
    if not entry.in_time or not entry.shift_start: return
    diff = None
    if consider_grace_period:
        grace = entry.late_entry_grace_period if entry.enable_late_entry_marking else 0
        limit = entry.shift_start + timedelta(minutes=cint(grace))
        if entry.in_time > limit: diff = entry.in_time - limit
    elif entry.in_time > entry.shift_start:
        diff = entry.in_time - entry.shift_start
    if diff and diff.total_seconds() > 0:
        entry.late_entry_hrs = format_duration(diff.total_seconds())
        entry.late_entry = 1

def update_early_exit(entry, consider_grace_period):
    if not entry.out_time or not entry.shift_end: return
    diff = None
    if consider_grace_period:
        grace = entry.early_exit_grace_period if entry.enable_early_exit_marking else 0
        limit = entry.shift_end - timedelta(minutes=cint(grace))
        if entry.out_time < limit: diff = limit - entry.out_time
    elif entry.out_time < entry.shift_end:
        diff = entry.shift_end - entry.out_time
    if diff and diff.total_seconds() > 0:
        entry.early_exit_hrs = format_duration(diff.total_seconds())
        entry.early_exit = 1

def format_seconds_to_hms(seconds):
    if not seconds or seconds <= 0:
        return "00:00:00"
    seconds = int(seconds)
    hours, remainder = divmod(seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{hours:02}:{minutes:02}:{seconds:02}"  