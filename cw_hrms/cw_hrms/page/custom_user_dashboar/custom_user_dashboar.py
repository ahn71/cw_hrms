import frappe
from frappe.utils import nowdate, get_first_day, get_last_day, getdate, add_days, flt

@frappe.whitelist()
def get_user_stats():
    user = frappe.session.user
    employee_doc = frappe.db.get_value("Employee", {"user_id": user}, ["name", "company", "holiday_list"], as_dict=True)
    
    if not employee_doc:
        return {"stats": {}, "attendance_details": [], "leave_allocation": [], "leave_history": []}

    employee = employee_doc.name
    today = getdate(nowdate())
    month_start = getdate(get_first_day(today))
    
    # year_start এবং year_end তৈরি করা হলো (এরর ফিক্স)
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
        filters={"employee": employee, "attendance_date": ["between", [month_start, today]], "docstatus": 1},
        fields=["attendance_date", "status", "late_entry", "in_time", "out_time", "working_hours"]
    )
    att_dict = {getdate(d.attendance_date): d for d in attendance_records}

    # ২. হলিডে লিস্ট ডাটা সংগ্রহ
    h_list = employee_doc.holiday_list or frappe.db.get_value("Company", employee_doc.company, "default_holiday_list")
    holiday_dict = {}
    if h_list:
        holidays = frappe.db.sql("""SELECT holiday_date, description, weekly_off FROM `tabHoliday` 
                                    WHERE parent = %s AND holiday_date BETWEEN %s AND %s""", 
                                 (h_list, month_start, today), as_dict=True)
        holiday_dict = {getdate(h.holiday_date): h for h in holidays}

    # ৩. লুপ প্রসেসিং (১ তারিখ থেকে আজ পর্যন্ত)
    curr_date = month_start
    temp_details = []

    while curr_date <= today:
        status_to_show = ""
        in_t, out_t, work_h = None, None, 0
        
        # Priority 1: Holiday List
        if curr_date in holiday_dict:
            h_info = holiday_dict[curr_date]
            if curr_date in att_dict and att_dict[curr_date].status == "Present":
                att = att_dict[curr_date]
                status_to_show = "Present"
                in_t, out_t, work_h = att.in_time, att.out_time, att.working_hours
                data["stats"]["present"] += 1
                if att.late_entry: data["stats"]["late"] += 1
            else:
                if h_info.weekly_off:
                    status_to_show = "Weekend"
                    data["stats"]["weekend"] += 1
                else:
                    status_to_show = h_info.description or "Holiday"
                    data["stats"]["holiday"] += 1 # এখানে ফিক্স করা হয়েছে

        # Priority 2: Attendance Database
        elif curr_date in att_dict:
            att = att_dict[curr_date]
            status_to_show = att.status
            in_t, out_t, work_h = att.in_time, att.out_time, att.working_hours
            
            if status_to_show == "Present": data["stats"]["present"] += 1
            elif status_to_show == "On Leave": data["stats"]["leave"] += 1
            elif status_to_show == "Work From Home": data["stats"]["home_office"] += 1
            elif status_to_show == "Absent": data["stats"]["absent"] += 1
            if att.late_entry: data["stats"]["late"] += 1

        # Priority 3: Absent
        else:
            status_to_show = "Absent"
            data["stats"]["absent"] += 1

        temp_details.append({
            "attendance_date": curr_date,
            "status": status_to_show,
            "in_time": in_t,
            "out_time": out_t,
            "working_hours": work_h
        })
        curr_date = add_days(curr_date, 1)

    data["attendance_details"] = sorted(temp_details, key=lambda x: x['attendance_date'], reverse=True)
    
    # ৪. লিভ ডাটা (Allocation & History)
    # Allocation-এ 'unused_leaves' ও আনা হয়েছে যাতে অবশিষ্ট ছুটি দেখা যায়
    data["leave_allocation"] = frappe.get_all("Leave Allocation",
        filters={"employee": employee, "docstatus": 1, "from_date": ["<=", today], "to_date": [">=", today]},
        fields=["leave_type", "total_leaves_allocated as total", "unused_leaves"])
    
    data["leave_history"] = frappe.get_all("Leave Application",
        filters={"employee": employee, "status": "Approved", "from_date": ["between", [year_start, year_end]]},
        fields=["leave_type", "from_date", "to_date", "total_leave_days"],
        order_by="from_date desc")

    return data