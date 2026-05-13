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

            // --- ১. ডাটা প্রসেসিং (ফাঁকা ঘর পূরণ এবং গ্রুপিং) ---
            let processed_data = JSON.parse(JSON.stringify(data));
            let last_inv_id = "";
            let row_span_map = {};

            processed_data.forEach((row, idx) => {
                if (row.posting_date === "Total") return;

                // যদি ইনভয়েস আইডি ফাঁকা থাকে, আগের আইডি ব্যবহার করো
                let current_id = row.name || row.voucher_no || row.parent_invoice;
                if (!current_id || current_id === "") {
                    row._is_merged_row = true; // এটি একটি অতিরিক্ত রো
                    current_id = last_inv_id;
                } else {
                    last_inv_id = current_id;
                }

                // ম্যাপে কাউন্ট বাড়াও
                if (!row_span_map[current_id]) {
                    row_span_map[current_id] = { start_idx: idx, count: 0 };
                }
                row_span_map[current_id].count++;
                row._inv_group_id = current_id; // গ্রুপ ট্র্যাকিংয়ের জন্য
            });

            let table_html = `
                <table border="1" cellpadding="5" cellspacing="0"
                    style="width:100%; border-collapse:collapse; font-size:11px; margin-top:15px;">
                    <thead>
                        <tr style="background:#f5f5f5;">
            `;
            columns.forEach(col => {
                table_html += `<th style="padding:6px; border:1px solid #999; text-align:center;">${col.label}</th>`;
            });
            table_html += `</tr></thead><tbody>`;

            processed_data.forEach((row, idx) => {
                const is_total = row.posting_date === "Total";
                const row_style = is_total ? `style="font-weight:bold; background:#f0f4ff;"` : "";

                table_html += `<tr ${row_style}>`;
                
                columns.forEach(col => {
                    let val = row[col.fieldname];
                    if (val === null || val === undefined) val = "";
                    
                    // Formatting
                    if ((col.fieldtype === "Currency" || col.fieldtype === "Float") && val !== "") {
                        val = frappe.format(val, { fieldtype: col.fieldtype });
                    }

                    // --- ২. স্পেশাল মার্জিং লজিক ---
                    const merge_cols = [
                        "posting_date", "name", "customer", "customer_name", "voucher_no",
                        "total", "grand_total", "paid_amount", "outstanding_amount", "outstanding"
                    ];
                    
                    let group_id = row._inv_group_id;

                    if (merge_cols.includes(col.fieldname) && !is_total && group_id) {
                        let span_info = row_span_map[group_id];
                        
                        if (span_info && span_info.start_idx === idx) {
                            // প্রথম রো-তে rowspan বসবে
                            table_html += `<td rowspan="${span_info.count}" style="padding:5px; border:1px solid #999; text-align:center; vertical-align:middle;">${val}</td>`;
                        }
                        // বাকি রোগুলোতে এই কলামের জন্য <td> তৈরি হবে না
                    } else {
                        // আইটেম ডিটেইলস (Qty, Rate, Item Name) মার্জ হবে না
                        let align = (col.fieldtype === "Currency" || col.fieldtype === "Float") ? "right" : "left";
                        table_html += `<td style="padding:5px; border:1px solid #999; text-align:${align};">${val}</td>`;
                    }
                });
                table_html += `</tr>`;
            });
            
            table_html += `</tbody></table>`;

            // --- ৩. প্রিন্ট উইন্ডো ---
            const from_date = frappe.datetime.str_to_user(filters.from_date);
            const to_date   = frappe.datetime.str_to_user(filters.to_date);
            const print_html = `
                <html>
                <head>
                    <style>
                        body { font-family: sans-serif; margin: 20px; }
                        table { width: 100%; border-collapse: collapse; }
                        th, td { border: 1px solid #999; }
                    </style>
                </head>
                <body>
                    ${header_html}
                    <div style="text-align:center; margin-bottom:20px;">
                        <h3>Sales Report (Item Wise)</h3>
                        <p>Period: ${from_date} to ${to_date}</p>
                    </div>
                    ${table_html}
                    ${footer_content}
                </body>
                </html>
            `;

            const w = window.open("", "_blank");
            w.document.write(print_html);
            w.document.close();
            setTimeout(() => { w.print(); }, 1000);
        });
    });
}
};