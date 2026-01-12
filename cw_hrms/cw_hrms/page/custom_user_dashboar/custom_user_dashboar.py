import frappe
from frappe.utils import nowdate, get_first_day, get_last_day, getdate

@frappe.whitelist()
def get_user_stats():
    user = frappe.session.user
    employee = frappe.db.get_value("Employee", {"user_id": user}, "name")
    
    # পপ-আপ মেসেজ: ইউজার ও এমপ্লয়ি লিস্ট
    user_list = frappe.db.sql("""
        SELECT u.name as user_id, e.name as employee_id 
        FROM `tabUser` u 
        LEFT JOIN `tabEmployee` e ON u.name = e.user_id 
        WHERE u.enabled = 1 AND u.user_type = 'System User'
    """, as_dict=True)

    msg = "<b>User & Employee List:</b><br><table class='table table-bordered'>"
    msg += "<thead><tr><th>User ID</th><th>Employee ID</th></tr></thead><tbody>"
    for u in user_list:
        msg += f"<tr><td>{u.user_id}</td><td>{u.employee_id or 'N/A'}</td></tr>"
    msg += "</tbody></table>"
    frappe.msgprint(msg, title="Active User Info")

    # তারিখ নির্ধারণ
    today = nowdate()
    year_start = today[:4] + "-01-01"
    year_end = today[:4] + "-12-31"
    month_start = get_first_day(today)
    month_end = get_last_day(today)

    data = {
        "stats": {"present": 0, "absent": 0, "weekend": 0, "holiday": 0, "late": 0, "leave": 0},
        "leave_summary": [],
        "attendance_details": []
    }

    if employee:
        # ১. বর্তমান মাসের এটেন্ডেন্স স্ট্যাটাস (কার্ডের জন্য)
        att_month = frappe.get_all("Attendance", 
            filters={"employee": employee, "attendance_date": ["between", [month_start, month_end]]},
            fields=["status", "late_entry"]
        )
        for a in att_month:
            if a.status == "Present": data["stats"]["present"] += 1
            elif a.status == "Absent": data["stats"]["absent"] += 1
            elif a.status == "Weekly Off": data["stats"]["weekend"] += 1
            elif a.status == "Holiday": data["stats"]["holiday"] += 1
            elif a.status == "On Leave": data["stats"]["leave"] += 1
            if a.late_entry: data["stats"]["late"] += 1

        # ২. লিভ সামারি (এটেন্ডেন্স টেবিল থেকে কাউন্ট করে)
        # এক বছরের মধ্যে কতগুলো 'On Leave' আছে তার হিসাব
        leave_allocations = frappe.get_all("Leave Allocation",
            filters={"employee": employee, "docstatus": 1, "from_date": ["<=", today], "to_date": [">=", today]},
            fields=["leave_type", "total_leaves_allocated"]
        )

        for alloc in leave_allocations:
            # এটেন্ডেন্স টেবিল থেকে এই লিভ টাইপের বিপরীতে কয়টি লিভ নিয়েছে তা বের করা
            # দ্রষ্টব্য: এখানে সাধারণত Leave Application এর সাথে লিঙ্ক থাকে, সহজ করার জন্য আমরা সরাসরি কাউন্ট করছি
            taken = frappe.db.count("Attendance", filters={
                "employee": employee,
                "status": "On Leave",
                "attendance_date": ["between", [year_start, year_end]]
                # প্রয়োজনে এখানে নির্দিষ্ট leave_type দিয়ে ফিল্টার করা যেতে পারে যদি Attendance এ কলাম থাকে
            })

            data["leave_summary"].append({
                "leave_type": alloc.leave_type,
                "total_allocated": alloc.total_leaves_allocated,
                "leaves_taken": taken,
                "remaining": alloc.total_leaves_allocated - taken
            })

        # ৩. এটেন্ডেন্স ডিটেইলস (টেবিলের জন্য)
        data["attendance_details"] = frappe.get_all("Attendance",
            filters={"employee": employee, "attendance_date": ["between", [month_start, month_end]]},
            fields=["attendance_date", "in_time", "out_time", "working_hours", "status"],
            order_by="attendance_date desc"
        )

    return data