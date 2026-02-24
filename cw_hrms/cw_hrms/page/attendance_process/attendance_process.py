import frappe
from frappe.utils import getdate
import json

@frappe.whitelist()
def get_attendance_status(checkin_ids):
    # ফ্রন্ট-এন্ড থেকে আসা স্ট্রিং বা লিস্টকে প্রসেস করা
    if isinstance(checkin_ids, str):
        ids = json.loads(checkin_ids)
    else:
        ids = checkin_ids

    if not ids:
        return False

    for name in ids:
        # ১. Employee Checkin ডকুমেন্টটি নিয়ে আসা
        doc = frappe.get_doc("Employee Checkin", name)
        
        # ২. স্ট্যাটাস আপডেট এবং Skip বক্স আন-টিক করা
        doc.status = "Approved"
        doc.skip_auto_attendance = 0
        doc.save(ignore_permissions=True)
        
        attendance_date = getdate(doc.time)
        employee = doc.employee

        # ৩. ওই দিনের বিদ্যমান (Existing) Attendance রেকর্ড ডিলিট করা
        # যাতে নতুন পাঞ্চ সহ ফ্রেশ রিপোর্ট তৈরি হতে পারে
        frappe.db.sql("""
            DELETE FROM `tabAttendance` 
            WHERE employee = %s AND attendance_date = %s
        """, (employee, attendance_date))
        
        # ৪. ওই দিনের সকল পাঞ্চের সাথে আগের অ্যাটেন্ডেন্সের লিঙ্ক মুছে ফেলা
        frappe.db.sql("""
            UPDATE `tabEmployee Checkin` 
            SET attendance = NULL 
            WHERE employee = %s AND DATE(time) = %s
        """, (employee, attendance_date))
        
        # ডাটাবেজ কমিট করা যাতে স্ট্যান্ডার্ড ফাংশন ক্লিন ডাটা পায়
        frappe.db.commit()

        # ৫. ERPNext-এর কোর ফাংশন কল করা যা পাঞ্চগুলো প্রসেস করে অ্যাটেন্ডেন্স বানাবে
        from erpnext.hr.doctype.employee_checkin.employee_checkin import mark_attendance_and_link_log
        mark_attendance_and_link_log(employee, attendance_date)
        
    # ক্যাশ ক্লিয়ার করা যাতে রিপোর্টে তাৎক্ষণিক পরিবর্তন দেখা যায়
    frappe.clear_cache(doctype="Attendance")
    
    return True