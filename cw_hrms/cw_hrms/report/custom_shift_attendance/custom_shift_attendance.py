# Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from datetime import timedelta
import frappe
from frappe import _
from frappe.utils import cint, flt, format_datetime, format_duration, getdate, nowdate

def execute(filters=None):
    if not filters:
        filters = {}

    columns = get_columns()
    data = get_data(filters)
    chart = get_chart_data(data)
    report_summary = get_report_summary(data)

    return columns, data, None, chart, report_summary

def get_columns():
    return [
        {"label": _("Employee"), "fieldname": "employee", "fieldtype": "Link", "options": "Employee", "width": 220},
        {"label": _("Shift"), "fieldname": "shift", "fieldtype": "Link", "options": "Shift Type", "width": 120},
        {"label": _("Attendance Date"), "fieldname": "attendance_date", "fieldtype": "Date", "width": 130},
        {"label": _("Status"), "fieldname": "status", "fieldtype": "Data", "width": 100},
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
    # ১. এটেনডেন্স ডাটা সংগ্রহ
    query = get_query(filters)
    data = query.run(as_dict=True)
    
    # --- ডিবাগিং অংশ: এমপ্লয়ী এবং তাদের হলিডে লিস্ট প্রিন্ট করা ---
    if data:
        debug_msg = "<b>Employee vs Holiday List Matching:</b><br><table border='1' style='border-collapse: collapse; width: 100%;'>"
        debug_msg += "<tr><th style='padding:5px;'>Employee</th><th style='padding:5px;'>Holiday List from Profile</th></tr>"
        
        # ডুপ্লিকেট এড়াতে সেট ব্যবহার করছি
        seen_employees = set()
        for d in data:
            if d.employee not in seen_employees:
                debug_msg += f"<tr><td style='padding:5px;'>{d.employee}</td><td style='padding:5px; color:blue;'>{d.holiday_list or '<i>None (Will use Company Default)</i>'}</td></tr>"
                seen_employees.add(d.employee)
        
        debug_msg += "</table>"
        frappe.msgprint(debug_msg, title="Debug: Holiday List Check", wide=True)
    # --- ডিবাগিং শেষ ---

    # ২. হলিডে ম্যাপ তৈরি
    holiday_map = get_holiday_map(filters)
    
    # ৩. ডাটা প্রসেসিং
    data = update_data(data, filters, holiday_map)
    return data

def get_holiday_map(filters):
    from_date = filters.get("from_date") or "2000-01-01"
    to_date = filters.get("to_date") or "2099-12-31"
    
    holidays = frappe.db.sql("""
        SELECT parent, holiday_date, description, weekly_off 
        FROM `tabHoliday` 
        WHERE holiday_date BETWEEN %s AND %s
    """, (from_date, to_date), as_dict=True)
    
    holiday_map = {}
    for h in holidays:
        # তারিখকে স্ট্যান্ডার্ড স্ট্রিং ফরম্যাটে (YYYY-MM-DD) রূপান্তর করছি
        h_date_str = str(getdate(h.holiday_date))
        # Key: "Holiday List Name|2026-01-01"
        key = f"{h.parent}|{h_date_str}"
        holiday_map[key] = h
    return holiday_map

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

    user_roles = frappe.get_roles(frappe.session.user)
    if "HR Manager" not in user_roles and "System Manager" not in user_roles:
        emp = frappe.db.get_value("Employee", {"user_id": frappe.session.user}, "name")
        query = query.where(attendance.employee == (emp or "None"))

    if filters.get("from_date"): query = query.where(attendance.attendance_date >= filters.get("from_date"))
    if filters.get("to_date"): query = query.where(attendance.attendance_date <= filters.get("to_date"))
    if filters.get("employee"): query = query.where(attendance.employee == filters.get("employee"))
    if filters.get("company"): query = query.where(attendance.company == filters.get("company"))

    return query.groupby(attendance.name)


def update_data(data, filters, holiday_map):
    consider_grace = filters.get("consider_grace_period")
    company_holiday_lists = {}
    
    # ম্যাপে আসলে কয়টি কি (Key) আছে তা একবার দেখে নেওয়া
    map_keys = list(holiday_map.keys()) if holiday_map else []

    for d in data:
        # ১. এমপ্লয়ীর লিস্ট নির্ধারণ (ক্লিন করে নেওয়া)
        h_list = str(d.holiday_list or "").strip()
        if not h_list:
            if d.company not in company_holiday_lists:
                company_holiday_lists[d.company] = str(frappe.db.get_value("Company", d.company, "default_holiday_list") or "").strip()
            h_list = company_holiday_lists[d.company]

        # ২. তারিখ এবং কী (Key) তৈরি
        att_date_str = str(getdate(d.attendance_date))
        holiday_key = f"{h_list}|{att_date_str}"
        
        # ৩. ডাটা খোঁজা
        holiday_info = holiday_map.get(holiday_key)

        # --- এই অংশটিই আপনার সমস্যার সমাধান এবং ডিবাগিং ---
        d.is_weekend_or_holiday = 0
        if holiday_info:
            d.is_weekend_or_holiday = 1
            if holiday_info.weekly_off:
                d.status = _("Weekend")
            else:
                d.status = _(holiday_info.description or "Holiday")
        else:
            # যদি সরাসরি না মেলে, তবে অন্য কোনো লিস্টে এই তারিখে ছুটি আছে কি না চেক করা (Fallback)
            for k in map_keys:
                if att_date_str in k: # তারিখটি অন্তত ম্যাপের অন্য কোনো কি-তে আছে কি না
                    holiday_info = holiday_map[k]
                    d.is_weekend_or_holiday = 1
                    d.status = _("Weekend") if holiday_info.weekly_off else _(holiday_info.description or "Holiday")
                    break
            
            # যদি এরপরেও না পাওয়া যায়, তবেই কেবল এবসেন্ট বা ডাটাবেস স্ট্যাটাস
            if not holiday_info:
                d.status = _(d.status or "Absent")

        # ৪. ক্যালকুলেশন ও টাইম ফরম্যাটিং
        total_seconds = 0
        if d.in_time and d.out_time:
            try:
                diff = d.out_time - d.in_time
                total_seconds = diff.total_seconds()
            except: pass
        
        d.working_hours_float = total_seconds / 3600.0
        d.working_hours = format_seconds_to_hms(total_seconds)
        update_late_entry(d, consider_grace)
        update_early_exit(d, consider_grace)
        d.in_time, d.out_time = convert_datetime_to_time_for_same_date(d.in_time, d.out_time)
        d.shift_start, d.shift_end = convert_datetime_to_time_for_same_date(d.shift_start, d.shift_end)
    
    return data


def get_report_summary(data):
    if not data: return []
    t = p = l = a = e = hol = h = leave = 0
    total_seconds = 0.0
    today = getdate(nowdate())

    for d in data:
        att_date = getdate(d.get("attendance_date"))
        if att_date <= today:
            t += 1
            # --- ডিবাগিং: সামারিতে হলিডে কাউন্ট হচ্ছে কি না দেখা ---
            if d.get("is_weekend_or_holiday") == 1:
                hol += 1
            else:
                status = str(d.get("status") or "").lower()
                wh_seconds = flt(d.get("working_hours_float") or 0) * 3600
                total_seconds += wh_seconds

                if "present" in status: p += 1
                elif "half day" in status: h += 1
                elif "on leave" in status: leave += 1
                elif "absent" in status: a += 1

            if d.get("late_entry"): l += 1
            if d.get("early_exit"): e += 1

    # --- ফাইনাল কাউন্ট চেক ---
    if hol == 0 and t > 0:
        frappe.msgprint("<b>Summary Error:</b> Weekend/Holiday count is 0. Check 'is_weekend_or_holiday' flag in update_data loop.", alert=True)

    working_days = p + h
    avg_wh = format_seconds_to_hms(total_seconds / working_days) if working_days > 0 else "00:00:00"

    return [
        {"value": t, "label": _("Total"), "indicator": "Blue", "datatype": "Int"},
        {"value": p, "label": _("Present"), "indicator": "Green", "datatype": "Int"},
        {"value": l, "label": _("Late"), "indicator": "Red", "datatype": "Int"},
        {"value": a, "label": _("Absent"), "indicator": "Red", "datatype": "Int"},
        {"value": e, "label": _("Early"), "indicator": "Red", "datatype": "Int"},
        {"value": hol, "label": _("Holiday"), "indicator": "Purple", "datatype": "Int"},
        {"value": h, "label": _("Half Day"), "indicator": "Orange", "datatype": "Int"},
        {"value": leave, "label": _("Leave"), "indicator": "Yellow", "datatype": "Int"},
        {"value": avg_wh, "label": _("Avg Wh"), "indicator": "Blue", "datatype": "Data"}
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
def convert_datetime_to_time_for_same_date(start, end):
    try:
        f_start = start.strftime("%H:%M:%S") if start else None
        f_end = end.strftime("%H:%M:%S") if end else None
        return f_start, f_end
    except:
        return str(start), str(end)

def update_late_entry(entry, consider_grace):
    if not entry.in_time or not entry.shift_start: return
    diff = None
    try:
        if consider_grace:
            grace = entry.late_entry_grace_period if entry.enable_late_entry_marking else 0
            limit = entry.shift_start + timedelta(minutes=cint(grace))
            if entry.in_time > limit: diff = entry.in_time - limit
        elif entry.in_time > entry.shift_start:
            diff = entry.in_time - entry.shift_start
        
        if diff and diff.total_seconds() > 0:
            entry.late_entry_hrs = format_duration(diff.total_seconds())
            entry.late_entry = 1
    except:
        pass

def update_early_exit(entry, consider_grace):
    if not entry.out_time or not entry.shift_end: return
    diff = None
    try:
        if consider_grace:
            grace = entry.early_exit_grace_period if entry.enable_early_exit_marking else 0
            limit = entry.shift_end - timedelta(minutes=cint(grace))
            if entry.out_time < limit: diff = limit - entry.out_time
        elif entry.out_time < entry.shift_end:
            diff = entry.shift_end - entry.out_time
        
        if diff and diff.total_seconds() > 0:
            entry.early_exit_hrs = format_duration(diff.total_seconds())
            entry.early_exit = 1
    except:
        pass

def format_seconds_to_hms(seconds):
    if not seconds or seconds <= 0: return "00:00:00"
    seconds = int(seconds)
    hours, remainder = divmod(seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{hours:02}:{minutes:02}:{seconds:02}"