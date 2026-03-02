frappe.pages['attendance-process'].on_page_load = function(wrapper) {
    let page = frappe.ui.make_app_page({
        parent: wrapper,
        title: 'Attendance Processing Panel',
        single_column: true
    });

    // --- ১. Main Section এ Filter HTML Inject করা ---
    let $main = $(wrapper).find('.layout-main-section');

    $main.empty().append(`
        <!-- Filter Section -->
        <div class="filter-section" style="display:flex; gap:15px; flex-wrap:wrap; margin-bottom:20px; padding:15px; background:#f4f5f6; border-radius:6px;">
            <div id="filter-company" style="min-width:200px;"></div>
            <div id="filter-employee" style="min-width:200px;"></div>
            <div id="filter-shift" style="min-width:200px;"></div>
            <div id="filter-from-date" style="min-width:160px;"></div>
            <div id="filter-to-date" style="min-width:160px;"></div>
        </div>

        <!-- Table Section -->
        <div style="overflow-x:auto;">
            <table class="table table-bordered table-hover" id="attendance-table">
                <thead style="background:#f0f0f0;">
                    <tr>
                        <th style="width:40px; text-align:center;">
                            <input type="checkbox" id="select-all-rows" title="Select All">
                        </th>
                        <th>Employee Name</th>
                        <th>Employee ID</th>
                        <th>Company</th>
                        <th>Department</th>
                        <th>Designation</th>
                        <th>Default Shift</th>
                    </tr>
                </thead>
                <tbody id="table-body">
                    <tr>
                        <td colspan="7" style="text-align:center; color:#888;">
                            Initializing...
                        </td>
                    </tr>
                </tbody>
            </table>
        </div>
    `);

    // --- ২. frappe.ui.form.make_control দিয়ে Filter তৈরি ---
    let company_filter = frappe.ui.form.make_control({
        parent: wrapper.querySelector('#filter-company'),
        df: {
            label: 'Company',
            fieldname: 'company',
            fieldtype: 'Link',
            options: 'Company',
            placeholder: 'All Companies'
        },
        render_input: true
    });

    let emp_filter = frappe.ui.form.make_control({
        parent: wrapper.querySelector('#filter-employee'),
        df: {
            label: 'Employee',
            fieldname: 'employee',
            fieldtype: 'Link',
            options: 'Employee',
            placeholder: 'All Employees'
        },
        render_input: true
    });

    let shift_filter = frappe.ui.form.make_control({
        parent: wrapper.querySelector('#filter-shift'),
        df: {
            label: 'Shift',
            fieldname: 'shift',
            fieldtype: 'Link',
            options: 'Shift Type',
            placeholder: 'All Shifts'
        },
        render_input: true
    });

    let from_date = frappe.ui.form.make_control({
        parent: wrapper.querySelector('#filter-from-date'),
        df: {
            label: 'From Date',
            fieldname: 'from_date',
            fieldtype: 'Date'
        },
        render_input: true
    });

    let to_date = frappe.ui.form.make_control({
        parent: wrapper.querySelector('#filter-to-date'),
        df: {
            label: 'To Date',
            fieldname: 'to_date',
            fieldtype: 'Date'
        },
        render_input: true
    });

    // --- ৩. Auto Filter Events ---

    // Link fields (Company, Employee, Shift)
    [company_filter, emp_filter, shift_filter].forEach(f => {
        // autocomplete থেকে select করলে
        f.$input.on('awesomplete-selectcomplete', () => {
            setTimeout(() => refresh_table_data(), 100);
        });
        // manually clear করলে
        f.$input.on('input', function() {
            if ($(this).val() === '') {
                setTimeout(() => refresh_table_data(), 300);
            }
        });
    });

    // Date fields
    [from_date, to_date].forEach(f => {
        f.$input.on('change dp.change blur', () => {
            setTimeout(() => refresh_table_data(), 100);
        });
    });

    // --- ৪. ডেটা লোড ফাংশন ---
    function refresh_table_data() {
        let filters = { 'status': 'Active' };

        let company = company_filter.get_value();
        let emp     = emp_filter.get_value();
        let shift   = shift_filter.get_value();

        if (company) filters.company       = company;
        if (emp)     filters.name          = emp;
        if (shift)   filters.default_shift = shift;

        frappe.call({
            method: 'frappe.client.get_list',
            args: {
                doctype: 'Employee',
                filters: filters,
                fields: ['name', 'employee_name', 'company', 'department', 'designation', 'default_shift'],
                limit_page_length: 500
            },
            callback: function(r) {
                let $tbody = $('#table-body');
                $tbody.empty();

                if (r.message && r.message.length > 0) {
                    r.message.forEach(row => {
                        $tbody.append(`
                            <tr>
                                <td style="text-align:center;">
                                    <input type="checkbox" class="row-check" data-id="${row.name}">
                                </td>
                                <td>${row.employee_name || '-'}</td>
                                <td>${row.name || '-'}</td>
                                <td>${row.company || '-'}</td>
                                <td>${row.department || '-'}</td>
                                <td>${row.designation || '-'}</td>
                                <td>${row.default_shift || '-'}</td>
                            </tr>
                        `);
                    });
                } else {
                    $tbody.append(`
                        <tr>
                            <td colspan="7" style="text-align:center; color:#888;">
                                No employees found.
                            </td>
                        </tr>
                    `);
                }
            }
        });
    }

    // --- ৫. Select All Checkbox লজিক ---
    $(wrapper).on('change', '#select-all-rows', function() {
        $('.row-check').prop('checked', $(this).prop('checked'));
    });

    // --- ৬. Primary Action Button ---
    page.set_primary_action('Approve & Sync', () => {
        let selected_employees = [];

        $(wrapper).find('.row-check:checked').each(function() {
            selected_employees.push($(this).data('id'));
        });

        let fd = from_date.get_value();
        let td = to_date.get_value();

        if (!selected_employees.length) {
            return frappe.msgprint({
                title: __('Warning'),
                indicator: 'orange',
                message: __('Please select at least one employee.')
            });
        }

        if (!fd || !td) {
            return frappe.msgprint({
                title: __('Warning'),
                indicator: 'orange',
                message: __('Please select From Date and To Date.')
            });
        }

        frappe.confirm(
            `<b>${selected_employees.length}</b> জন Employee-এর জন্য <b>${fd}</b> থেকে <b>${td}</b> পর্যন্ত attendance sync করবেন?<br><br>
            <span style="color:red;">⚠️ পুরাতন ডাটা ডিলিট হয়ে যাবে।</span>`,
            () => {
                frappe.dom.freeze('Processing...');
                const callArgs = {
                    employees: selected_employees,
                    from_date: fd,
                    to_date: td,
                    shift: shift_filter.get_value()
                };
                console.log("Request Args:", callArgs);
                frappe.call({
                    method: 'cw_hrms.cw_hrms.page.attendance_process.attendance_process.process_attendance_re_sync',
                    args: callArgs,
                    callback: function(r) {
                        frappe.dom.unfreeze();

                        if (!r.exc) {
                            frappe.show_alert({
                                message: __('Attendance synced successfully!'),
                                indicator: 'green'
                            }, 5);
                            refresh_table_data();
                        }
                    },
                    error: function() {
                        frappe.dom.unfreeze();
                        frappe.msgprint({
                            title: __('Error'),
                            indicator: 'red',
                            message: __('Something went wrong. Please check the error log.')
                        });
                    }
                });
            }
        );
    });

    // --- ৭. Page Load হওয়ার সাথে সাথে ডেটা লোড ---
    company_filter.set_value('Codeware Limited');
    setTimeout(() => refresh_table_data(), 200);
    refresh_table_data();
};