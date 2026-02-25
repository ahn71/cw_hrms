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

        // ১. লেট এন্ট্রি এবং আর্লি এক্সিট এর জন্য লাল রঙ
        if (
            (column.fieldname === "in_time" && data.late_entry) ||
            (column.fieldname === "out_time" && data.early_exit)
        ) {
            value = `<span style='color:red!important; font-weight:bold;'>${value}</span>`;
        }
		console.log("Hello Codware",column);
        // ২. আপনার রিপোর্টের কলাম নাম অনুযায়ী (Total Working Hours)
        if (column.fieldname === "working_hours") {
            console.log("working_hours Codware");
			console.log("Data Codware",data);
            // শিফট স্টার্ট এবং এন্ড টাইম থাকলে তুলনা শুরু হবে
            if (data.shift_start && data.shift_end && value) {
                console.log("shift_start_time Codware");
                // সময়কে সেকেন্ডে রূপান্তর করার ফাংশন (HH:MM:SS ফরম্যাটের জন্য)
                const get_seconds = (time_str) => {
                    if (!time_str) return 0;
                    let parts = time_str.split(':');
                    return (parseInt(parts[0]) * 3600) + (parseInt(parts[1]) * 60) + parseInt(parts[2] || 0);
                };

			let shift_start_sec = get_seconds(data.shift_start);
            console.log("Shift Start:", data.shift_start, "-> Seconds:", shift_start_sec);

            let shift_end_sec = get_seconds(data.shift_end);
            console.log("Shift End:", data.shift_end, "-> Seconds:", shift_end_sec);

            let shift_duration_sec = shift_end_sec - shift_start_sec;
            console.log("Total Shift Duration (Seconds):", shift_duration_sec);

            let actual_working_val = data.working_hours;
            let actual_working_sec = get_seconds(actual_working_val);
            console.log("Actual Working Time:", actual_working_val, "-> Seconds:", actual_working_sec);
			if (actual_working_sec < shift_duration_sec) {
                console.log("%c Result: LESS THAN SHIFT TIME - Applying Red Color", "color: red; font-weight: bold;");
                value = `<span style='color:red!important; font-weight:bold;'>${value}</span>`;
            }
            }
        }
		if ((column.fieldname === "in_time" && data.late_entry) || (column.fieldname === "out_time" && data.early_exit)) {
				value = `<span style='color:red!important; font-weight:bold;'>${value}</span>`;
			}

    	return value;
        
    },
};
