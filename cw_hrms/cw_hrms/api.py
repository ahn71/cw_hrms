# cw_hrms/cw_hrms/api.py
import frappe
from frappe import _
from datetime import datetime, timedelta

@frappe.whitelist()
def get_employee_attendance_summary(employee, from_date, to_date):
    """Get employee attendance summary for a date range"""
    
    # Get attendance records
    attendance_records = frappe.db.sql("""
        SELECT status, COUNT(*) as count
        FROM `tabAttendance`
        WHERE employee = %s 
        AND attendance_date BETWEEN %s AND %s
        AND docstatus = 1
        GROUP BY status
    """, (employee, from_date, to_date), as_dict=1)
    
    # Get late entries (assuming you have a 'late_entry' field)
    late_count = frappe.db.sql("""
        SELECT COUNT(*) as count
        FROM `tabAttendance`
        WHERE employee = %s 
        AND attendance_date BETWEEN %s AND %s
        AND late_entry = 1
        AND docstatus = 1
    """, (employee, from_date, to_date))[0][0]
    
    # Initialize counts
    summary = {
        'present': 0,
        'absent': 0,
        'late': int(late_count) if late_count else 0,
        'leave': 0
    }
    
    # Map attendance records
    for record in attendance_records:
        if record.status == 'Present':
            summary['present'] = record.count
        elif record.status == 'Absent':
            summary['absent'] = record.count
        elif record.status == 'On Leave':
            summary['leave'] = record.count
    
    return summary

@frappe.whitelist()
def get_employee_leave_balance(employee):
    """Get employee leave balance summary"""
    
    # Get allocation records
    allocations = frappe.db.sql("""
        SELECT 
            la.leave_type,
            la.total_leaves_allocated as total_leaves,
            COALESCE(
                (SELECT SUM(leave_days) 
                 FROM `tabLeave Application` 
                 WHERE employee = %s 
                 AND leave_type = la.leave_type 
                 AND status = 'Approved'
                 AND docstatus = 1), 0
            ) as leaves_taken
        FROM `tabLeave Allocation` la
        WHERE la.employee = %s 
        AND la.docstatus = 1
        AND %s BETWEEN la.from_date AND la.to_date
    """, (employee, employee, frappe.utils.today()), as_dict=1)
    
    # Calculate balance
    for alloc in allocations:
        alloc['balance_leaves'] = alloc['total_leaves'] - alloc['leaves_taken']
        alloc['balance_leaves'] = round(alloc['balance_leaves'], 2)
    
    return allocations

@frappe.whitelist()
def get_employee_todays_punch(employee, date):
    """Get today's RFID punch records"""
    
    # Check if Employee Checkin doctype exists (v15+)
    punches = []
    
    if frappe.db.exists('DocType', 'Employee Checkin'):
        # For Frappe HR / ERPNext v15+
        checkins = frappe.db.sql("""
            SELECT 
                time,
                log_type,
                device_id as gate,
                'Success' as status
            FROM `tabEmployee Checkin`
            WHERE employee = %s 
            AND DATE(time) = %s
            ORDER BY time
        """, (employee, date), as_dict=1)
        
        punches = checkins
    
    elif frappe.db.exists('DocType', 'Employee Checkin'):
        # Fallback to old method if different structure
        # You might need to adjust this based on your actual doctype structure
        pass
    
    # If no punches found, try to get from Attendance Check
    if not punches and frappe.db.exists('DocType', 'Attendance'):
        # Try to get check-in/out times from attendance
        attendance = frappe.db.get_value('Attendance', {
            'employee': employee,
            'attendance_date': date,
            'docstatus': 1
        }, ['in_time', 'out_time'], as_dict=1)
        
        if attendance and attendance.in_time:
            punches.append({
                'time': frappe.utils.format_time(attendance.in_time),
                'log_type': 'IN',
                'gate': 'Attendance',
                'status': 'Success'
            })
        
        if attendance and attendance.out_time:
            punches.append({
                'time': frappe.utils.format_time(attendance.out_time),
                'log_type': 'OUT',
                'gate': 'Attendance',
                'status': 'Success'
            })
    
    return {
        'punches': punches,
        'total_punches': len(punches)
    }