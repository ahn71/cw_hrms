# Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from datetime import datetime, timedelta, time
import frappe
from frappe import _
from frappe.utils import cint, flt, format_duration, getdate, add_days, nowdate


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
    raw_data = get_attendance_data(filters)
    holiday_map = get_holiday_map(filters)
    return update_data(raw_data, filters, holiday_map)


def get_attendance_data(filters):
    attendance = frappe.qb.DocType("Attendance")
    shift_type = frappe.qb.DocType("Shift Type")
    employee = frappe.qb.DocType("Employee")

    # Shift Type ???? start_time ??? end_time ?????? ??????? ??? ?????
    query = (
        frappe.qb.from_(attendance)
        .left_join(shift_type).on(attendance.shift == shift_type.name)
        .left_join(employee).on(attendance.employee == employee.name)
        .select(
            attendance.name, attendance.employee, attendance.employee_name, attendance.attendance_request,
            attendance.shift, attendance.attendance_date, attendance.status,
            attendance.in_time, attendance.out_time, attendance.working_hours,
            attendance.late_entry, attendance.early_exit, attendance.department,
            attendance.company, 
            shift_type.start_time.as_("shift_start_time"),
            shift_type.end_time.as_("shift_end_time"),
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

    return query.run(as_dict=True)


def get_holiday_map(filters):
    from_date = filters.get("from_date")
    to_date = filters.get("to_date")

    if not from_date or not to_date:
        return {}

    holidays = frappe.db.sql("""
        SELECT parent as holiday_list, holiday_date, description, weekly_off 
        FROM `tabHoliday` 
        WHERE holiday_date BETWEEN %s AND %s
    """, (from_date, to_date), as_dict=True)

    holiday_dict = {}
    for h in holidays:
        key = (h.holiday_list, getdate(h.holiday_date))
        holiday_dict[key] = h

    return holiday_dict


def update_data(data, filters, holiday_map):
    consider_grace = filters.get("consider_grace_period")
    from_date = getdate(filters.get("from_date"))
    to_date = getdate(filters.get("to_date"))

    emp_info_map = {}
    for d in data:
        if d.employee not in emp_info_map:
            emp_info_map[d.employee] = {
                "employee_name": d.get("employee_name"),
                "shift": d.get("shift"),
                "department": d.get("department"),
                "company": d.get("company"),
                "holiday_list": d.get("holiday_list"),
                "shift_start_time": d.get("shift_start_time"),
                "shift_end_time": d.get("shift_end_time"),
                "enable_late_entry_marking": d.get("enable_late_entry_marking"),
                "late_entry_grace_period": d.get("late_entry_grace_period"),
                "enable_early_exit_marking": d.get("enable_early_exit_marking"),
                "early_exit_grace_period": d.get("early_exit_grace_period")
            }

    if filters.get("employee"):
        employees = [filters.get("employee")]
    else:
        employees = list(emp_info_map.keys())

    attendance_map = {(d.employee, getdate(d.attendance_date)): d for d in data}
    final_data = []

    for emp in employees:
        info = emp_info_map.get(emp, {})
        emp_holiday_list = info.get("holiday_list")
        
        curr_date = from_date
        while curr_date <= to_date:
            key = (emp, curr_date)

            if key in attendance_map:
                d = attendance_map[key]
            else:
                d = frappe._dict({
                    "attendance_date": curr_date,
                    "status": None,
                    "employee": emp,
                    "employee_name": info.get("employee_name"),
                    "shift": info.get("shift"),
                    "department": info.get("department"),
                    "company": info.get("company"),
                    "holiday_list": emp_holiday_list,
                    "shift_start_time": info.get("shift_start_time"),
                    "shift_end_time": info.get("shift_end_time"),
                    "enable_late_entry_marking": info.get("enable_late_entry_marking"),
                    "late_entry_grace_period": info.get("late_entry_grace_period"),
                    "enable_early_exit_marking": info.get("enable_early_exit_marking"),
                    "early_exit_grace_period": info.get("early_exit_grace_period"),
                    "working_hours": 0,
                    "in_time": None,
                    "out_time": None
                })

            d.is_weekend_or_holiday = 0
            h_key = (emp_holiday_list, curr_date)
            
            if h_key in holiday_map:
                h_info = holiday_map[h_key]
                if d.status == "Present":
                    d.is_weekend_or_holiday = 0
                    d.status = _("Present")
                else:
                    d.is_weekend_or_holiday = 1
                    d.status = _("Weekend") if h_info.weekly_off else _(h_info.description or "Holiday")
            else:
                if not d.status:
                    d.status = _("Absent")
                else:
                    d.status = _(str(d.status))

            # ???????? ??????? ?????
            total_seconds = 0
            if d.working_hours and flt(d.working_hours) > 0:
                total_seconds = flt(d.working_hours) * 3600
            elif d.in_time and d.out_time:
                try:
                    diff = d.out_time - d.in_time
                    total_seconds = diff.total_seconds()
                except Exception:
                    total_seconds = 0

            d.working_hours_float = total_seconds / 3600.0
            d.working_hours = format_seconds_to_hms(total_seconds)

            # ??? ??????? ? ????? ?????? ?????
            update_late_entry(d, consider_grace)
            update_early_exit(d, consider_grace)

            # ??????? ?????????
            d.shift_start = format_time_str(d.get("shift_start_time"))
            d.shift_end = format_time_str(d.get("shift_end_time"))
            
            if isinstance(d.in_time, datetime):
                d.in_time = d.in_time.strftime("%H:%M:%S")
            if isinstance(d.out_time, datetime):
                d.out_time = d.out_time.strftime("%H:%M:%S")

            final_data.append(d)
            curr_date = add_days(curr_date, 1)

    return final_data


def update_late_entry(entry, consider_grace):
    if not entry.in_time or not entry.shift_start_time or not entry.attendance_date:
        return

    try:
        in_datetime = entry.in_time if isinstance(entry.in_time, datetime) else None
        if not in_datetime:
            return

        att_date = getdate(entry.attendance_date)
        shift_start_td = entry.shift_start_time
        
        # Shift Time-?? Datetime-? ????????
        shift_start_dt = datetime.combine(att_date, (datetime.min + shift_start_td).time())

        grace = 0
        if consider_grace and entry.enable_late_entry_marking:
            grace = cint(entry.late_entry_grace_period or 0)

        limit_dt = shift_start_dt + timedelta(minutes=grace)

        if in_datetime > limit_dt:
            diff = in_datetime - shift_start_dt
            if diff.total_seconds() > 0:
                entry.late_entry_hrs = format_duration(diff.total_seconds())
                entry.late_entry = 1
    except Exception:
        pass


def update_early_exit(entry, consider_grace):
    if not entry.out_time or not entry.shift_end_time or not entry.attendance_date:
        return

    try:
        out_datetime = entry.out_time if isinstance(entry.out_time, datetime) else None
        if not out_datetime:
            return

        att_date = getdate(entry.attendance_date)
        shift_end_td = entry.shift_end_time
        
        # Shift Time-?? Datetime-? ????????
        shift_end_dt = datetime.combine(att_date, (datetime.min + shift_end_td).time())

        grace = 0
        if consider_grace and entry.enable_early_exit_marking:
            grace = cint(entry.early_exit_grace_period or 0)

        limit_dt = shift_end_dt - timedelta(minutes=grace)

        if out_datetime < limit_dt:
            diff = shift_end_dt - out_datetime
            if diff.total_seconds() > 0:
                entry.early_exit_hrs = format_duration(diff.total_seconds())
                entry.early_exit = 1
    except Exception:
        pass


def format_time_str(val):
    if not val:
        return ""
    if isinstance(val, timedelta):
        total_seconds = int(val.total_seconds())
        hours, remainder = divmod(total_seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        return f"{hours:02}:{minutes:02}:{seconds:02}"
    return str(val)


def get_report_summary(data):
    if not data: return []
    t = p = l = a = e = hol = h = leave = wfh = od = 0
    total_seconds = 0.0
    today = getdate(nowdate())

    for d in data:
        att_date = getdate(d.get("attendance_date"))
        if att_date <= today:
            t += 1
            if d.get("is_weekend_or_holiday") == 1:
                hol += 1
            else:
                status = str(d.get("status") or "").lower()
                att_req = d.get("attendance_request")
                
                wh_seconds = flt(d.get("working_hours_float") or 0) * 3600
                total_seconds += wh_seconds

                if "present" in status:
                    p += 1
                    if att_req:
                        od += 1
                elif "half day" in status: h += 1
                elif "on leave" in status: leave += 1
                elif "absent" in status: a += 1
                elif "work from home" in status: wfh += 1

            if d.get("late_entry") and str(d.get("status")).lower() != "half day": l += 1
            if d.get("early_exit"): e += 1

    working_days = float(p) + (float(h) * 0.5) - float(od)
    avg_wh = format_seconds_to_hms(total_seconds / working_days) if working_days > 0 else "00:00:00"

    return [
        {"value": t, "label": _("Total"), "indicator": "Blue", "datatype": "Int"},
        {"value": p, "label": _("Present"), "indicator": "Green", "datatype": "Int"},
        {"value": wfh, "label": _("Home Office"), "indicator": "Green", "datatype": "Int"},
        {"value": l, "label": _("Late"), "indicator": "Red", "datatype": "Int"},
        {"value": a, "label": _("Absent"), "indicator": "Red", "datatype": "Int"},
        {"value": e, "label": _("Early"), "indicator": "Red", "datatype": "Int"},
        {"value": hol, "label": _("Holiday"), "indicator": "Purple", "datatype": "Int"},
        {"value": h, "label": _("Half Day"), "indicator": "Orange", "datatype": "Int"},
        {"value": leave, "label": _("Leave"), "indicator": "Yellow", "datatype": "Int"},
        {"value": avg_wh, "label": _("Avg Wh"), "indicator": "Blue", "datatype": "Data"},
        {"value": od, "label": _("Out Duty"), "indicator": "Blue", "datatype": "Data"}
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


def format_seconds_to_hms(seconds):
    if not seconds or seconds <= 0: return "00:00:00"
    seconds = int(seconds)
    hours, remainder = divmod(seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{hours:02}:{minutes:02}:{seconds:02}"