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
        },
        {
            "fieldname": "item",
            "label": __("Item"),
            "fieldtype": "Data",
            "wildcard_filter": 1
        }
    ],

    "formatter": function(value, row, column, data, default_formatter) {

        // Total row - bold + blue top border
        if (data && data.posting_date === "Total") {
            value = default_formatter(value, row, column, data);
            return `<span style="font-weight:bold; color:#1f272e; display:block; border-top:2px solid #5e64ff;">${value || ""}</span>`;
        }

        // নতুন invoice এর প্রথম row - grey top border
        const is_new_invoice = data && data.posting_date !== null && data.posting_date !== undefined;
        if (is_new_invoice) {
            const all_data = frappe.query_report.data;
            if (all_data) {
                const current_index = all_data.indexOf(data);
                if (current_index > 0) {
                    value = default_formatter(value, row, column, data);
                    return `<span style="display:block; border-top:2px solid #d1d5db; margin-top:-1px;">${value}</span>`;
                }
            }
        }

        return default_formatter(value, row, column, data);
    },

    "onload": function(report) {
    report.page.add_inner_button(__("Custom Print"), function() {

        const filters = report.get_values();
        const company = filters.company;

        frappe.db.get_doc("Letter Head", "AgronyInfo").then(function(lh) {

            let header_html    = lh.content || `<h2 style="text-align:center;">${company}</h2>`;
            let footer_content = lh.footer  || "";

            const columns = frappe.query_report.columns;
            const data    = frappe.query_report.data;

            let table_html = `
                <table border="1" cellpadding="5" cellspacing="0"
                    style="width:100%; border-collapse:collapse; font-size:12px; margin-top:15px;">
                    <thead>
                        <tr style="background:#f0f0f0;">
            `;
            columns.forEach(col => {
                table_html += `<th style="text-align:left; padding:6px 8px;">${col.label}</th>`;
            });
            table_html += `</tr></thead><tbody>`;

            data.forEach(row => {
                const is_total = row.posting_date === "Total";
                const row_style = is_total
                    ? `style="font-weight:bold; background:#f0f4ff; border-top:2px solid #5e64ff;"`
                    : "";

                table_html += `<tr ${row_style}>`;
                columns.forEach(col => {
                    let val = row[col.fieldname];
                    if (val === null || val === undefined) val = "";
                    if (col.fieldtype === "Currency" && val !== "") {
                        val = frappe.format(val, { fieldtype: "Currency" });
                    }
                    if (col.fieldtype === "Float" && val !== "") {
                        val = frappe.format(val, { fieldtype: "Float" });
                    }
                    table_html += `<td style="padding:5px 8px;">${val}</td>`;
                });
                table_html += `</tr>`;
            });
            table_html += `</tbody></table>`;

            const from_date = frappe.datetime.str_to_user(filters.from_date);
            const to_date   = frappe.datetime.str_to_user(filters.to_date);

            const signature_html = `
                <div style="margin-top:60px; display:flex; justify-content:space-between; padding:0 20px;">
                    <div style="text-align:center;">
                        <div style="border-top:1px solid #333; width:180px; margin:0 auto;"></div>
                        <p style="margin:5px 0; font-size:12px;">Prepared by</p>
                    </div>
                    <div style="text-align:center;">
                        <div style="border-top:1px solid #333; width:180px; margin:0 auto;"></div>
                        <p style="margin:5px 0; font-size:12px;">Authorized by</p>
                    </div>
                </div>
                <div style="margin-top:20px; text-align:right; font-size:11px; color:#666;">
                    Date: ${frappe.datetime.str_to_user(frappe.datetime.get_today())}
                </div>
            `;

            const print_html = `
                <!DOCTYPE html>
                <html>
                <head>
                    <meta charset="utf-8">
                    <title>Sales Report - ${company}</title>
                    <style>
                        body { font-family: Arial, sans-serif; margin: 20px; }
                        table { page-break-inside: auto; }
                        tr { page-break-inside: avoid; }
                        @media print { body { margin: 10px; } }
                    </style>
                </head>
                <body>
                    ${header_html}
                    <div style="text-align:center; margin:15px 0 5px;">
                        <h3 style="margin:0;">Sales Report (Item Wise)</h3>
                        <p style="margin:4px 0; font-size:12px; color:#555;">
                            Period: ${from_date} to ${to_date}
                        </p>
                    </div>
                    ${table_html}
                    ${footer_content}
                    ${signature_html}
                </body>
                </html>
            `;

            const w = window.open("", "_blank");
            w.document.write(print_html);
            w.document.close();
            w.focus();
            setTimeout(() => { w.print(); }, 800);
        });
    });
}
};