// Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.query_reports["Custom Shift Attendance"] = {
	filters: [
		{
			fieldname: "from_date",
			label: __("From Date"),
			fieldtype: "Date",
			reqd: 1,
			default: frappe.datetime.month_start(),
		},
		{
			fieldname: "to_date",
			label: __("To Date"),
			fieldtype: "Date",
			reqd: 1,
			default: frappe.datetime.month_end(),
		},
		{
			fieldname: "employee",
			label: __("Employee"),
			fieldtype: "Link",
			options: "Employee",
		},
		{
			fieldname: "shift",
			label: __("Shift Type"),
			fieldtype: "Link",
			options: "Shift Type",
		},
		{
			fieldname: "department",
			label: __("Department"),
			fieldtype: "Link",
			options: "Department",
		},
		{
			fieldname: "company",
			label: __("Company"),
			fieldtype: "Link",
			options: "Company",
			reqd: 1,
			default: frappe.defaults.get_user_default("Company"),
		},
		{
			fieldname: "late_entry",
			label: __("Late Entry"),
			fieldtype: "Check",
		},
		{
			fieldname: "early_exit",
			label: __("Early Exit"),
			fieldtype: "Check",
		},
		{
			fieldname: "consider_grace_period",
			label: __("Consider Grace Period"),
			fieldtype: "Check",
			default: 1,
		},
	],
	formatter: (value, row, column, data, default_formatter) => {
        value = default_formatter(value, row, column, data);

        // ১. লেট এন্ট্রি এবং আর্লি এক্সিট এর জন্য লাল রঙ (আপনার আগের লজিক)
        if (
            (column.fieldname === "in_time" && data.late_entry) ||
            (column.fieldname === "out_time" && data.early_exit)
        ) {
            value = `<span style='color:red!important; font-weight:bold;'>${value}</span>`;
        }

        // ২. ওয়ার্কিং আওয়ার কম হলে লাল রঙ করার লজিক
        if (column.fieldname === "working_hours" || column.fieldname === "total_working_hours") {
            
            // শিফট অনুযায়ী কতটুকু কাজ করার কথা (Shift Duration)
            // ধরে নিচ্ছি আপনার ডাটাতে shift_start এবং shift_end আছে
            if (data.shift_start && data.shift_end && data.working_hours) {
                
                let start = frappe.datetime.str_to_obj(data.shift_start);
                let end = frappe.datetime.str_to_obj(data.shift_end);
                
                // শিফট ডিউরেশন বের করা (ঘন্টায়)
                let shift_duration = (end - start) / (1000 * 60 * 60); 
                
                // অ্যাকচুয়াল ওয়ার্কিং আওয়ার (ডাটা থেকে পাওয়া)
                let actual_working_hours = parseFloat(data.working_hours);

                // যদি শিফট ডিউরেশনের চেয়ে কাজের সময় কম হয়
                if (actual_working_hours < shift_duration) {
                    value = `<span style='color:red!important; font-weight:bold;'>${value}</span>`;
                }
            }
        }

        return value;
    },
};
