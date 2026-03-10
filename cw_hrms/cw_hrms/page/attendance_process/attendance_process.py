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
            # ১. পুরাতন অ্যাটেনডেন্স খুঁজে বের করে ডিলিট করা
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

            # ৩. অত্যন্ত গুরুত্বপূর্ণ: ডাটাবেস কমিট করা
            # এটি না করলে process_auto_attendance আগের লিঙ্ক করা ডেটা দেখতে পাবে
            frappe.db.commit()

            # ৪. শিফট টাইপের অরিজিনাল প্রসেস কল করা
            if shift:
                # যদি নির্দিষ্ট শিফট পাঠানো হয়
                shift_doc = frappe.get_doc("Shift Type", shift)
                
                # এখানে একটি ছোট ট্রিক: process_auto_attendance ফিল্টার হিসেবে 
                # 'process_attendance_after' ব্যবহার করে। সাময়িকভাবে সেটি পরিবর্তন করা।
                original_after_date = shift_doc.process_attendance_after
                shift_doc.process_attendance_after = from_date
                
                # শিফট টাইপের অরিজিনাল মেথড কল
                shift_doc.process_auto_attendance(is_manually_triggered=True)
                
                success_count += 1
            else:
                # যদি শিফট না থাকে, তবে এমপ্লয়ির ডিফল্ট শিফট থেকে প্রসেস করা
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
        "message": _("Success: {0}, Errors: {1}").format(success_count, error_count)
    }