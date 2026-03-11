import frappe
import json
from frappe import _
from frappe.utils import getdate

@frappe.whitelist()
def process_attendance_re_sync(employees, from_date, to_date, shift=None):
    if isinstance(employees, str):
        employees = json.loads(employees)

    success_count = 0
    error_count = 0

    for emp_id in employees:
        try:
            # ১. পুরাতন অ্যাটেনডেন্স ডিলিট করা
            attendances = frappe.get_all("Attendance", filters={
                "employee": emp_id,
                "attendance_date": ["between", [from_date, to_date]],
                "docstatus": ["<", 2]
            })

            for att in attendances:
                doc = frappe.get_doc("Attendance", att.name)
                if doc.docstatus == 1:
                    doc.cancel()
                doc.delete()

            # ২. Employee Checkin আনলিঙ্ক করা
            frappe.db.sql("""
                UPDATE `tabEmployee Checkin`
                SET attendance = NULL
                WHERE employee = %s 
                AND DATE(time) BETWEEN %s AND %s
            """, (emp_id, from_date, to_date))

            # ৩. ডাটাবেস কমিট (যাতে প্রসেস ক্লীন ডাটা পায়)
            frappe.db.commit()

            # ৪. চেক-ইন টেবিল থেকে ওই এমপ্লয়ির নির্দিষ্ট ডেট রেঞ্জের শিফটগুলো খুঁজে বের করা
            checkin_shifts = frappe.get_all("Employee Checkin", 
                filters={
                    "employee": emp_id,
                    "time": ["between", [from_date, to_date]],
                    "shift": ["is", "set"]
                }, 
                fields=["shift"],
                distinct=1 # ইউনিক শিফট গুলো নেবে
            )

            if checkin_shifts:
                for row in checkin_shifts:
                    current_shift = row.shift
                    shift_doc = frappe.get_doc("Shift Type", current_shift)
                    
                    # সাময়িকভাবে process_attendance_after সেট করা
                    shift_doc.process_attendance_after = from_date
                    
                    # ওই নির্দিষ্ট শিফটের জন্য অটো অ্যাটেনডেন্স কল করা
                    shift_doc.process_auto_attendance(is_manually_triggered=True)
                
                success_count += 1
            else:
                # যদি চেক-ইন টেবিলে কোনো শিফট না থাকে, তবে ব্যাকআপ হিসেবে ডিফল্ট শিফট
                default_shift = frappe.db.get_value("Employee", emp_id, "default_shift")
                if default_shift:
                    shift_doc = frappe.get_doc("Shift Type", default_shift)
                    shift_doc.process_attendance_after = from_date
                    shift_doc.process_auto_attendance(is_manually_triggered=True)
                    success_count += 1

        except Exception as e:
            frappe.db.rollback()
            frappe.log_error(title="Attendance Process Error", message=frappe.get_traceback())
            error_count += 1

    return {
        "status": "success",
        "message": _("Processed {0} employees. Success: {1}, Errors: {2}").format(
            len(employees), success_count, error_count
        )
    }