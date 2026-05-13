frappe.query_reports["SalesReportItemWise"] = {
    "filters": [
        {
            "fieldname": "company",
            "label": __("Company"),
            "fieldtype": "Link",
            "options": "Company",
            "default": frappe.defaults.get_user_default("Company"),
            "reqd": 1
        },
        {
            "fieldname": "from_date",
            "label": __("From Date"),
            "fieldtype": "Date",
            "default": frappe.datetime.add_months(frappe.datetime.get_today(), -1),
            "reqd": 1
        },
        {
            "fieldname": "to_date",
            "label": __("To Date"),
            "fieldtype": "Date",
            "default": frappe.datetime.get_today(),
            "reqd": 1
        }
    ],

    "formatter": function(value, row, column, data, default_formatter) {

        // ✅ Total row - bold + background
        if (data && data.posting_date === "মোট") {
            value = default_formatter(value, row, column, data);
            return `<span style="font-weight: bold; color: #1f272e;">${value || ""}</span>`;
        }

        // নতুন invoice এর প্রথম row চেনা
        const is_new_invoice = data && data.posting_date !== null && data.posting_date !== undefined;

        if (is_new_invoice) {
            const all_data = frappe.query_report.data;
            if (all_data) {
                const current_index = all_data.indexOf(data);
                if (current_index > 0) {
                    value = default_formatter(value, row, column, data);
                    return `<span style="display:block; border-top: 2px solid #d1d5db; margin-top:-1px;">${value}</span>`;
                }
            }
        }

        return default_formatter(value, row, column, data);
    }
};