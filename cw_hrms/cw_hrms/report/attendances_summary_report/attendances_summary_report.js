// Copyright (c) 2026, Codeware Limited and contributors
// For license information, please see license.txt

frappe.query_reports["Attendances Summary Report"] = {
    "filters": [
        {
            "fieldname": "company",
            "label": __("Company"),
            "fieldtype": "Link",
            "options": "Company",
            "default": frappe.defaults.get_user_default("Company")
        },
        {
            "fieldname": "from_date",
            "label": __("From Date"),
            "fieldtype": "Date",
            "default": frappe.datetime.month_start(),
            "reqd": 1
        },
{
            "fieldname": "to_date",
            "label": __("To Date"),
            "fieldtype": "Date",
            "reqd": 1,
            // শুধুমাত্র ডিফল্ট হিসেবে ১ দিন কম দেখাবে
            "default": frappe.datetime.add_days(frappe.datetime.get_today(), -1)
        },
        {
            "fieldname": "department",
            "label": __("Department"),
            "fieldtype": "Link",
            "options": "Department"
        },
        {
            "fieldname": "employee",
            "label": __("Employee"),
            "fieldtype": "Link",
            "options": "Employee"
        },
        {
        "fieldname": "employee_status",
        "label": "Employee Status",
        "fieldtype": "Select",
        "options": "\nActive\nInactive\nSuspended\nLeft",
        "default": "Active"
        }
    ],
    onload: function(report) {
        let to_date = report.get_filter_value('to_date');
        let today = frappe.datetime.get_today();
        
        if (to_date === today) {
            report.set_filter_value('to_date', frappe.datetime.add_days(today, -1));
            report.refresh();
        }
    }

};