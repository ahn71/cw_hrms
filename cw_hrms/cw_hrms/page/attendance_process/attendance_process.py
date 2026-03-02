import frappe
import json
# এই মেথডটি সরাসরি অ্যাটেনডেন্স জেনারেট করে যা শিফট টাইপ পেজে ব্যবহৃত হয়
from hrms.hr.doctype.employee_checkin.employee_checkin import mark_attendance_and_link_log

@frappe.whitelist()
def process_attendance_re_sync(employees, from_date, to_date, shift=None):
    if isinstance(employees, str):
        employees = json.loads(employees)

    for emp_id in employees:
        # ১. পুরাতন Submitted (docstatus=1) অ্যাটেনডেন্স ডিলিট
        frappe.db.sql("""
            DELETE FROM `tabAttendance` 
            WHERE employee = %s 
            AND docstatus = 1 
            AND attendance_date BETWEEN %s AND %s
        """, (emp_id, from_date, to_date))

        # ২. মার্ক অ্যাটেনডেন্স লজিক (যা শিফট টাইপ বাটনে কাজ করে)
        # এখানে সরাসরি ফাংশনটি কল করা হয়েছে
        try:
            mark_attendance_and_link_log(
                employee=emp_id,
                from_date=from_date,
                to_date=to_date,
                shift=shift
            )
        except Exception as e:
            # যদি কোন এমপ্লয়ির ডাটাতে সমস্যা থাকে তবে এরর লগ করবে কিন্তু প্রসেস থামবে না
            frappe.log_error(title="Attendance Sync Error", message=frappe.get_traceback())
            continue

    return "Attendance re-synced successfully like Shift Type process."