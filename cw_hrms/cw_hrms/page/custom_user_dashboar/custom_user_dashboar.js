frappe.pages['custom-user-dashboar'].on_page_load = function(wrapper) {
    let page = frappe.ui.make_app_page({
        parent: wrapper,
        title: __('User Dashboard'),
        single_column: false // সাইডবার মেনু দেখানোর জন্য এটি অবশ্যই false হবে
    });

    // বাম পাশে মডিউল লিস্ট বা সাইডবার মেনু রেন্ডার করা
    // এটি ইউজারের পারমিশন অনুযায়ী মডিউলগুলো দেখাবে
    wrapper.page.sidebar.html('<div class="module-sidebar-nav standard-sidebar"></div>');
    
    // ফ্রাপ্পের ডিফল্ট সাইডবার বিল্ডারকে ফোর্স করা
    if (frappe.boot.navbar_settings.enable_side_bar) {
        frappe.utils.make_navbar(); 
    }

    frappe.call({
        method: 'cw_hrms.cw_hrms.page.custom_user_dashboar.custom_user_dashboar.get_user_stats',
        callback: function(r) {
            if (r.message) {
                render_dashboard_html(page, r.message);
            }
        }
    });
};

function render_dashboard_html(page, data) {
    let stats = data.stats;
    let html = `
    <div class="p-4">
        <div class="row mb-4">
            ${createCard("Present", stats.present, "green")}
            ${createCard("Absent", stats.absent, "red")}
            ${createCard("Late", stats.late, "orange")}
            ${createCard("Holiday", stats.holiday, "blue")}
            ${createCard("On Leave", stats.leave, "purple")}
        </div>

        <div class="card mb-4 shadow-sm">
            <div class="card-header font-weight-bold">Leave Summary (Annual)</div>
            <table class="table table-bordered m-0">
                <thead class="bg-light text-center">
                    <tr><th>Leave Type</th><th>Allocation</th><th>Taken</th><th>Balance</th></tr>
                </thead>
                <tbody class="text-center">
                    ${data.leave_summary.length ? data.leave_summary.map(l => `
                        <tr>
                            <td>${l.leave_type}</td>
                            <td>${l.total_allocated}</td>
                            <td class="text-danger">${l.leaves_taken}</td>
                            <td class="font-weight-bold text-success">${l.remaining}</td>
                        </tr>
                    `).join('') : '<tr><td colspan="4">No leave data found</td></tr>'}
                </tbody>
            </table>
        </div>

        <div class="card shadow-sm">
            <div class="card-header font-weight-bold">Attendance Details (Current Month)</div>
            <table class="table table-hover m-0">
                <thead class="bg-light">
                    <tr><th>Date</th><th>In Time</th><th>Out Time</th><th>Stay Time</th><th>Status</th></tr>
                </thead>
                <tbody>
                    ${data.attendance_details.length ? data.attendance_details.map(a => `
                        <tr>
                            <td>${frappe.datetime.str_to_user(a.attendance_date)}</td>
                            <td>${a.in_time ? frappe.datetime.get_time(a.in_time) : '--'}</td>
                            <td>${a.out_time ? frappe.datetime.get_time(a.out_time) : '--'}</td>
                            <td>${a.working_hours ? flt(a.working_hours).toFixed(2) + 'h' : '0'}</td>
                            <td><span class="badge badge-${a.status=='Present'?'success':'secondary'}">${a.status}</span></td>
                        </tr>
                    `).join('') : '<tr><td colspan="5" class="text-center">No attendance found</td></tr>'}
                </tbody>
            </table>
        </div>
    </div>`;

    page.main.html(html);
}

function createCard(label, val, color) {
    return `
    <div class="col-md-2">
        <div class="card p-3 text-center shadow-sm" style="border-bottom: 4px solid ${color}">
            <div class="text-muted small">${label}</div>
            <div class="h3 font-weight-bold" style="color: ${color}">${val}</div>
        </div>
    </div>`;
}