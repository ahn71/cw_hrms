frappe.query_reports["ItemWiseStockValueV1"] = {
    "filters": [
        {
            "fieldname": "company",
            "label": __("Company"),
            "fieldtype": "Link",
            "options": "Company",
            "default": frappe.defaults.get_user_default("Company")
        },
        {
            "fieldname": "warehouse",
            "label": __("Warehouse"),
            "fieldtype": "Link",
            "options": "Warehouse"
        },
        {
            "fieldname": "item_code",
            "label": __("Item"),
            "fieldtype": "Link",
            "options": "Item"
        }
    ],
    "show_total_row": true,

    // ডাটা কমানো ছাড়া চেকবক্স অ্যাড করার সঠিক নিয়ম
    "get_datatable_options": function(options) {
        return Object.assign(options, {
            checkboxColumn: true,
        });
    },

    "onload": function(report) {
        // ১. পেজ টোটাল বাটন (আপনার আগের লজিক অনুযায়ী)
        report.page.add_inner_button(__("Calculate Page Total"), function() {
            let total_qty = 0;
            let total_value = 0;

            const visible_rows = report.datatable.rowmanager.getRows();
            
            visible_rows.forEach(row => {
                // ইনডেক্স ৩ এ Qty এবং ৫ এ Value (যেহেতু চেকবক্স একটা কলাম দখল করে নিয়েছে)
                total_qty += flt(row[3].content); 
                total_value += flt(row[5].content);
            });

            frappe.msgprint(__('<b>Current Page Summary:</b> <br> Total Qty: {0} <br> Total Value: {1}', [total_qty, total_value]));
        });

        // ২. আপনার চাহিদামত সিলেক্টেড রো এক্সপোর্ট করার বাটন
        report.page.add_inner_button(__("Export Selected"), function() {
            const datatable = report.datatable;
            const selected_indices = datatable.rowmanager.getSelectedRowIndices();
            
            if (selected_indices.length === 0) {
                frappe.msgprint(__("দয়া করে বামপাশের চেকবক্স থেকে আইটেম সিলেক্ট করুন।"));
                return;
            }

            let export_data = [];
            // হেডার অ্যাড করা
            export_data.push(["Raw", "Variant", "Qty in Stock", "Selling Price", "Stock Value", "Warehouse", "Company"]);

            selected_indices.forEach(idx => {
                let d = report.data[idx];
                if (d) {
                    export_data.push([
                        d.raw_code, d.variant, d.qty_in_stock, 
                        d.selling_price, d.stock_value, d.warehouse, d.company
                    ]);
                }
            });

            // CSV ডাউনলোড
            frappe.tools.downloadify(export_data, null, "Selected_Stock_Report");
        });
    },

    "after_datatable_render": function(datatable) {
        // টোটাল ক্যালকুলেশন আগের মতোই থাকবে
        let qty_sum = 0;
        let value_sum = 0;

        datatable.data.forEach(row => {
            qty_sum += flt(row.qty_in_stock);
            value_sum += flt(row.stock_value);
        });
    }
};