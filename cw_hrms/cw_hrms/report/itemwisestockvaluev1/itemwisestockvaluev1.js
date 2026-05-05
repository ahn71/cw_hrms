frappe.query_reports["itemwisestockvaluev1"] = {
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

	"onload": function(report) {

		// ✅ report.refresh original function কে wrap করা
		const original_refresh = report.refresh.bind(report);
		report.refresh = function() {
			original_refresh();
			setTimeout(() => inject_checkboxes(), 1500);
		};

		// ✅ Export Selected
		report.page.add_inner_button(__("Export Selected"), function() {
			const checked = document.querySelectorAll('.row-cb:checked');

			if (checked.length === 0) {
				frappe.msgprint(__("কোনো row সিলেক্ট করা হয়নি।"));
				return;
			}

			const real_data = (report.data || []).filter(r => r.variant !== "Total");
			let export_data = [
				["Raw", "Variant", "Qty in Stock", "Selling Price", "Stock Value", "Warehouse", "Company"]
			];

			checked.forEach(cb => {
				const idx = parseInt(cb.getAttribute('data-idx'));
				const d = real_data[idx];
				if (d) {
					export_data.push([
						d.raw_code, d.variant, d.qty_in_stock,
						d.selling_price, d.stock_value,
						d.warehouse, d.company
					]);
				}
			});

			frappe.tools.downloadify(export_data, null, "Selected_Stock_Report");
		});

		// ✅ Manual inject button (test এর জন্য)
		report.page.add_inner_button(__("Add Checkboxes"), function() {
			inject_checkboxes();
		});
	}
};

function inject_checkboxes() {
	// Header
	const header_col0 = document.querySelector('.dt-cell--header.dt-cell--col-0 .dt-cell__content');
	if (header_col0) {
		header_col0.innerHTML = `
			<input type="checkbox" class="select-all-cb" 
			style="width:15px;height:15px;cursor:pointer;display:block;margin:auto;">
		`;
		header_col0.querySelector('.select-all-cb').addEventListener('change', function() {
			document.querySelectorAll('.row-cb').forEach(cb => {
				cb.checked = this.checked;
				cb.closest('.dt-row').style.background = this.checked ? '#e8f4fd' : '';
			});
		});
	}

	// Rows
	document.querySelectorAll('.dt-scrollable .dt-row').forEach((row, idx) => {
		const col0 = row.querySelector('.dt-cell--col-0 .dt-cell__content');
		if (col0) {
			col0.innerHTML = `
				<input type="checkbox" class="row-cb" data-idx="${idx}"
				style="width:15px;height:15px;cursor:pointer;display:block;margin:auto;">
			`;
			col0.querySelector('.row-cb').addEventListener('change', function() {
				this.closest('.dt-row').style.background = this.checked ? '#e8f4fd' : '';
			});
		}
	});

	console.log("✅ Checkboxes injected:", document.querySelectorAll('.row-cb').length);
}