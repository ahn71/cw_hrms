import frappe
from frappe.utils import nowdate, get_first_day, getdate, add_days, flt

@frappe.whitelist()
def get_user_stats(employee=None):
    user = frappe.session.user
    if not employee:
        employee = frappe.db.get_value("Employee", {"user_id": user}, "name")
    
    employee_doc = frappe.db.get_value("Employee", {"name": employee}, ["name", "company", "holiday_list"], as_dict=True)
    
    if not employee_doc:
        return {"stats": {}, "attendance_details": [], "leave_allocation": [], "leave_history": []}
    
    employee = employee_doc.name
    today = getdate(nowdate())
    yesterday = add_days(today, -1)
    month_start = getdate(get_first_day(today))
    year_start = f"{today.year}-01-01"
    year_end = f"{today.year}-12-31"

    data = {
        "stats": {"present": 0, "absent": 0, "late": 0, "leave": 0, "holiday": 0, "weekend": 0, "home_office": 0},
        "leave_allocation": [],
        "attendance_details": [],
        "leave_history": []
    }

    # ১. এটেনডেন্স ডাটা
    attendance_records = frappe.get_all("Attendance",
        filters={"employee": employee, "attendance_date": ["between", [month_start, yesterday]], "docstatus": 1},
        fields=["attendance_date", "status", "late_entry", "in_time", "out_time", "working_hours"]
    )
    att_dict = {getdate(d.attendance_date): d for d in attendance_records}

    # ২. হলিডে ডাটা
    h_list = employee_doc.holiday_list or frappe.db.get_value("Company", employee_doc.company, "default_holiday_list")
    holiday_dict = {}
    if h_list:
        holidays = frappe.db.sql("""SELECT holiday_date, description, weekly_off FROM `tabHoliday`
                                    WHERE parent = %s AND holiday_date BETWEEN %s AND %s""",
                                 (h_list, month_start, yesterday), as_dict=True)
        holiday_dict = {getdate(h.holiday_date): h for h in holidays}

    # ৩. Working Hours Format
    def format_to_hh_mm_ss(hours_float):
        if not hours_float: return "00:00:00"
        total_seconds = int(flt(hours_float) * 3600)
        hh = total_seconds // 3600
        mm = (total_seconds % 3600) // 60
        ss = total_seconds % 60
        return f"{hh:02d}:{mm:02d}:{ss:02d}"

    # ৪. Attendance Processing Loop
    curr_date = month_start
    temp_details = []

    while curr_date <= yesterday:
        status_to_show, in_t, out_t, work_h = "Absent", None, None, 0

        if curr_date in holiday_dict:
            h_info = holiday_dict[curr_date]
            if curr_date in att_dict and att_dict[curr_date].status == "Present":
                att = att_dict[curr_date]
                in_t, out_t, work_h = att.in_time, att.out_time, att.working_hours
                if att.late_entry:
                    status_to_show = "Late"
                    data["stats"]["present"] += 1
                    data["stats"]["late"] += 1
                else:
                    status_to_show = "Present"
                    data["stats"]["present"] += 1
            else:
                status_to_show = "Weekend" if h_info.weekly_off else (h_info.description or "Holiday")
                data["stats"]["weekend" if h_info.weekly_off else "holiday"] += 1

        elif curr_date in att_dict:
            att = att_dict[curr_date]
            in_t, out_t, work_h = att.in_time, att.out_time, att.working_hours

            if att.status == "Present" and att.late_entry:
                # Late হলে present count এ থাকবে + late আলাদা count
                status_to_show = "Late"
                data["stats"]["present"] += 1
                data["stats"]["late"] += 1
            else:
                status_to_show = att.status
                key = status_to_show.lower().replace(" ", "_")
                if key == "on_leave":
                    key = "leave"
                if key in data["stats"]:
                    data["stats"][key] += 1

        else:
            data["stats"]["absent"] += 1

        temp_details.append({
            "attendance_date": curr_date,
            "status": status_to_show,
            "in_time": str(in_t) if in_t else None,
            "out_time": str(out_t) if out_t else None,
            "working_hours": format_to_hh_mm_ss(work_h)
        })
        curr_date = add_days(curr_date, 1)

    data["attendance_details"] = sorted(temp_details, key=lambda x: x['attendance_date'], reverse=True)

    # ৫. লিভ Allocation & Calculation
    allocations = frappe.get_all("Leave Allocation",
        filters={"employee": employee, "docstatus": 1, "from_date": ["<=", today], "to_date": [">=", today]},
        fields=["leave_type", "total_leaves_allocated"])

    leave_data = []
    for alloc in allocations:
        used_leaves = frappe.db.get_value("Leave Application", {
            "employee": employee,
            "leave_type": alloc.leave_type,
            "status": "Approved",
            "docstatus": 1,
            "from_date": [">=", year_start],
            "to_date": ["<=", year_end]
        }, "sum(total_leave_days)") or 0

        remaining = flt(alloc.total_leaves_allocated) - flt(used_leaves)
        leave_data.append({
            "leave_type": alloc.leave_type,
            "total_allocated": alloc.total_leaves_allocated,
            "unused_leaves": remaining,
            "used_leave": flt(used_leaves)
        })
    data["leave_allocation"] = leave_data

    # ৬. লিভ হিস্ট্রি
    data["leave_history"] = frappe.get_all("Leave Application",
        filters={"employee": employee, "status": "Approved", "docstatus": 1, "from_date": [">=", year_start]},
        fields=["leave_type", "from_date", "to_date", "total_leave_days"],
        order_by="from_date desc")

    return data

@frappe.whitelist()
def get_yearly_attendance(year=None, employee=None):
    user = frappe.session.user

    if not employee:
        employee = frappe.db.get_value("Employee", {"user_id": user}, "name")

    if not employee:
        return []

    if not year:
        year = getdate(nowdate()).year

    year = int(year)
    today = getdate(nowdate())
    yesterday = add_days(today, -1)
    year_start = getdate(f"{year}-01-01")
    year_end = getdate(f"{year}-12-31")

    # Future year হলে সব 0
    if year_start > today:
        return [
            {
                "month": ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"][i],
                "present": 0, "absent": 0, "leave": 0, "late": 0
            }
            for i in range(12)
        ]

    # Employee info আনো
    employee_doc = frappe.db.get_value("Employee", {"name": employee},
        ["company", "holiday_list", "date_of_joining", "relieving_date"], as_dict=True)

    if not employee_doc:
        return []

    # এই employee এর সর্বপ্রথম attendance record কোনদিন
    first_attendance = frappe.db.get_value("Attendance",
        {"employee": employee, "docstatus": 1},
        "min(attendance_date)")

    joining_date = getdate(employee_doc.date_of_joining) if employee_doc.date_of_joining else None
    first_att_date = getdate(first_attendance) if first_attendance else None

    # loop_start নির্ধারণ — তিনটার মধ্যে সবচেয়ে কার্যকর তারিখ
    # joining date আর first attendance date এর মধ্যে যেটা পরে সেটা নাও
    # তারপর সেটা year_start এর সাথে তুলনা করে যেটা পরে সেটা নাও
    if first_att_date and joining_date:
        effective_start = max(joining_date, first_att_date)
    elif first_att_date:
        effective_start = first_att_date
    elif joining_date:
        effective_start = joining_date
    else:
        effective_start = year_start

    loop_start = max(year_start, effective_start)

    # loop_end নির্ধারণ
    relieving_date = getdate(employee_doc.relieving_date) if employee_doc.relieving_date else None
    loop_end = min(yesterday, year_end)
    if relieving_date:
        loop_end = min(loop_end, relieving_date)

    # Selected year এ কোনো কার্যকর দিন নেই
    if loop_start > loop_end:
        return [
            {
                "month": ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"][i],
                "present": 0, "absent": 0, "leave": 0, "late": 0
            }
            for i in range(12)
        ]

    # Attendance আনো
    records = frappe.get_all("Attendance",
        filters={
            "employee": employee,
            "attendance_date": ["between", [loop_start, loop_end]],
            "docstatus": 1
        },
        fields=["attendance_date", "status", "late_entry"]
    )
    att_dict = {getdate(a.attendance_date): a for a in records}

    # Holiday আনো
    h_list = employee_doc.holiday_list or frappe.db.get_value("Company", employee_doc.company, "default_holiday_list")

    holiday_set = set()
    if h_list:
        holidays = frappe.db.sql("""SELECT holiday_date FROM `tabHoliday`
                                    WHERE parent = %s AND holiday_date BETWEEN %s AND %s""",
                                 (h_list, loop_start, loop_end), as_dict=True)
        holiday_set = {getdate(h.holiday_date) for h in holidays}

    monthly = {i: {"present": 0, "absent": 0, "leave": 0, "late": 0} for i in range(12)}

    curr_date = loop_start
    while curr_date <= loop_end:
        m = curr_date.month - 1

        if curr_date in holiday_set:
            if curr_date in att_dict and att_dict[curr_date].status == "Present":
                monthly[m]["present"] += 1
                if att_dict[curr_date].late_entry:
                    monthly[m]["late"] += 1

        elif curr_date in att_dict:
            a = att_dict[curr_date]
            s = (a.status or "").lower().replace(" ", "_")

            if "present" in s:
                monthly[m]["present"] += 1
            elif "absent" in s:
                monthly[m]["absent"] += 1
            elif "leave" in s or "on_leave" in s:
                monthly[m]["leave"] += 1

            if a.late_entry:
                monthly[m]["late"] += 1

        else:
            monthly[m]["absent"] += 1

        curr_date = add_days(curr_date, 1)

    return [
        {
            "month": ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"][i],
            "present": monthly[i]["present"],
            "absent":  monthly[i]["absent"],
            "leave":   monthly[i]["leave"],
            "late":    monthly[i]["late"]
        }
        for i in range(12)
    ]
@frappe.whitelist()
def get_employee_list():
    if "System Manager" not in frappe.get_roles() and "HR Manager" not in frappe.get_roles():
        return []

    return frappe.get_all("Employee",
        filters={"status": "Active"},
        fields=["name", "employee_name"],
        order_by="employee_name asc"
    )