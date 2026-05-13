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

            // --- Rowspan Tracker Logic Start ---
            let row_span_map = {};
            data.forEach((row, idx) => {
                // ইনভয়েস আইডি ফিল্ডটি চেক করুন (সাধারণত 'name', 'voucher_no' বা 'parent_invoice' হয়)
                let inv_id = row.name || row.voucher_no || row.parent_invoice;
                
                if (inv_id && row.posting_date !== "Total") {
                    if (!row_span_map[inv_id]) {
                        row_span_map[inv_id] = { start_idx: idx, count: 0 };
                    }
                    row_span_map[inv_id].count++;
                }
            });
            // --- Rowspan Tracker Logic End ---

            let table_html = `
                <table border="1" cellpadding="5" cellspacing="0"
                    style="width:100%; border-collapse:collapse; font-size:12px; margin-top:15px;">
                    <thead>
                        <tr style="background:#f0f0f0;">
            `;
            columns.forEach(col => {
                table_html += `<th style="text-align:left; padding:6px 8px; border:1px solid #ccc;">${col.label}</th>`;
            });
            table_html += `</tr></thead><tbody>`;

            data.forEach((row, idx) => {
                const is_total = row.posting_date === "Total";
                const row_style = is_total
                    ? `style="font-weight:bold; background:#f0f4ff; border-top:2px solid #5e64ff;"`
                    : "";

                table_html += `<tr ${row_style}>`;
                
                columns.forEach(col => {
                    let val = row[col.fieldname];
                    if (val === null || val === undefined) val = "";
                    
                    // Formatting for Currency and Float
                    if (col.fieldtype === "Currency" && val !== "") {
                        val = frappe.format(val, { fieldtype: "Currency" });
                    }
                    if (col.fieldtype === "Float" && val !== "") {
                        val = frappe.format(val, { fieldtype: "Float" });
                    }

                    // যে কলামগুলো মার্জ করতে চান (যেমন: Date, Invoice ID, Customer)
                    const merge_cols = ["posting_date", "name", "customer", "customer_name", "voucher_no"];
                    let current_inv_id = row.name || row.voucher_no || row.parent_invoice;

                    if (merge_cols.includes(col.fieldname) && !is_total && current_inv_id) {
                        let span_info = row_span_map[current_inv_id];
                        
                        if (span_info && span_info.start_idx === idx) {
                            // শুধুমাত্র প্রথম রো-তে rowspan বসবে এবং টেক্সট মাঝখানে থাকবে
                            table_html += `<td rowspan="${span_info.count}" style="padding:5px 8px; border:1px solid #ccc; text-align:center; vertical-align:middle;">${val}</td>`;
                        } 
                        // যদি এটি গ্রুপিংয়ের মাঝখানের রো হয়, তবে <td> তৈরি হবে না (skip)
                    } else {
                        // নরমাল কলামগুলো (Item, Qty, Rate ইত্যাদি) এবং Total রো-এর জন্য
                        let text_align = (col.fieldtype === "Currency" || col.fieldtype === "Float") ? "right" : "left";
                        table_html += `<td style="padding:5px 8px; border:1px solid #ccc; text-align:${text_align};">${val}</td>`;
                    }
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
            `;

            const print_html = `
                <!DOCTYPE html>
                <html>
                <head>
                    <meta charset="utf-8">
                    <title>Sales Report - ${company}</title>
                    <style>
                        body { font-family: Arial, sans-serif; margin: 20px; }
                        table { page-break-inside: auto; border-collapse: collapse; }
                        tr { page-break-inside: avoid; }
                        th, td { border: 1px solid #ccc; }
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