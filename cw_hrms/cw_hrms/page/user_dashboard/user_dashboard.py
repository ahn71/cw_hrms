import frappe
from frappe.utils import nowdate, get_first_day, getdate, add_days, flt

@frappe.whitelist()
def get_user_stats(employee=None):
    user = frappe.session.user
    if not employee:
        employee = frappe.db.get_value("Employee", {"user_id": user}, "name")
    # এমপ্লয়ি প্রোফাইল সংগ্রহ
    employee_doc = frappe.db.get_value("Employee", {"user_id": user}, ["name", "company", "holiday_list"], as_dict=True)
    
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

    # ১. এটেনডেন্স ডাটা সংগ্রহ
    attendance_records = frappe.get_all("Attendance", 
        filters={"employee": employee, "attendance_date": ["between", [month_start, yesterday]], "docstatus": 1},
        fields=["attendance_date", "status", "late_entry", "in_time", "out_time", "working_hours"]
    )
    att_dict = {getdate(d.attendance_date): d for d in attendance_records}

    # ২. হলিডে ডাটা সংগ্রহ
    h_list = employee_doc.holiday_list or frappe.db.get_value("Company", employee_doc.company, "default_holiday_list")
    holiday_dict = {}
    if h_list:
        holidays = frappe.db.sql("""SELECT holiday_date, description, weekly_off FROM `tabHoliday` 
                                    WHERE parent = %s AND holiday_date BETWEEN %s AND %s""", 
                                 (h_list, month_start, yesterday), as_dict=True)
        holiday_dict = {getdate(h.holiday_date): h for h in holidays}

    # ৩. Attendance Processing Loop
    def format_to_hh_mm_ss(hours_float):
        if not hours_float: return "00:00:00"
        total_seconds = int(flt(hours_float) * 3600)
        hh, mm, ss = total_seconds // 3600, (total_seconds % 3600) // 60, total_seconds % 60
        return f"{hh:02d}:{mm:02d}:{ss:02d}"

    curr_date = month_start
    temp_details = []
    while curr_date <= yesterday:
        status_to_show, in_t, out_t, work_h = "Absent", None, None, 0
        if curr_date in holiday_dict:
            h_info = holiday_dict[curr_date]
            if curr_date in att_dict and att_dict[curr_date].status == "Present":
                att = att_dict[curr_date]
                status_to_show, in_t, out_t, work_h = "Present", att.in_time, att.out_time, att.working_hours
                data["stats"]["present"] += 1
            else:
                status_to_show = "Weekend" if h_info.weekly_off else (h_info.description or "Holiday")
                data["stats"]["weekend" if h_info.weekly_off else "holiday"] += 1
        elif curr_date in att_dict:
            att = att_dict[curr_date]
            status_to_show, in_t, out_t, work_h = att.status, att.in_time, att.out_time, att.working_hours
            key = status_to_show.lower().replace(" ", "_")
            if key == "on_leave": key = "leave"
            if key in data["stats"]: data["stats"][key] += 1
            if att.late_entry: data["stats"]["late"] += 1
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

    # ৪. লিভ ডাটা (Allocation & Calculation)
    allocations = frappe.get_all("Leave Allocation",
        filters={"employee": employee, "docstatus": 1, "from_date": ["<=", today], "to_date": [">=", today]},
        fields=["leave_type", "total_leaves_allocated"])

    leave_data = []
    for alloc in allocations:
        used_leaves = frappe.db.get_value("Leave Application", {
            "employee": employee, "leave_type": alloc.leave_type, "status": "Approved", "docstatus": 1,
            "from_date": [">=", year_start], "to_date": ["<=", year_end]
        }, "sum(total_leave_days)") or 0
        
        remaining = flt(alloc.total_leaves_allocated) - flt(used_leaves)
        leave_data.append({
            "leave_type": alloc.leave_type,
            "total_allocated": alloc.total_leaves_allocated,
            "unused_leaves": remaining,
            "used_leave":flt(used_leaves)
        })
    data["leave_allocation"] = leave_data
    #frappe.msgprint(str(data["leave_allocation"]))

    # ৫. লিভ হিস্ট্রি সংগ্রহ
    data["leave_history"] = frappe.get_all("Leave Application",
        filters={"employee": employee, "status": "Approved", "docstatus": 1, "from_date": [">=", year_start]},
        fields=["leave_type", "from_date", "to_date", "total_leave_days"],
        order_by="from_date desc")

    return data
@frappe.whitelist()
def get_yearly_attendance(year=None, employee=None):
    user = frappe.session.user
    
    # যদি employee parameter না আসে তাহলে logged in user থেকে বের করো
    if not employee:
        employee = frappe.db.get_value("Employee", {"user_id": user}, "name")
    
    # Admin হলে কিন্তু employee select না করলে খালি return
    if not employee:
        return []

    if not year:
        year = getdate(nowdate()).year

    year = int(year)
    year_start = f"{year}-01-01"
    year_end = f"{year}-12-31"

    records = frappe.get_all("Attendance",
        filters={
            "employee": employee,
            "attendance_date": ["between", [year_start, year_end]],
            "docstatus": 1
        },
        fields=["attendance_date", "status", "late_entry"]
    )

    monthly = {i: {"present": 0, "absent": 0, "leave": 0, "late": 0} for i in range(12)}

    for a in records:
        m = getdate(a.attendance_date).month - 1
        s = (a.status or "").lower().replace(" ", "_")
        if "present" in s:
            monthly[m]["present"] += 1
        elif "absent" in s:
            monthly[m]["absent"] += 1
        elif "leave" in s:
            monthly[m]["leave"] += 1
        if a.late_entry:
            monthly[m]["late"] += 1

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
    # শুধু System Manager বা HR Manager দেখতে পাবে
    if "System Manager" not in frappe.get_roles() and "HR Manager" not in frappe.get_roles():
        return []
    
    return frappe.get_all("Employee",
        filters={"status": "Active"},
        fields=["name", "employee_name"],
        order_by="employee_name asc"
    )