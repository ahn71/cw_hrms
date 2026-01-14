frappe.pages['custom-user-dashboar'].on_page_load = function(wrapper) {
    let page = frappe.ui.make_app_page({
        parent: wrapper,
        title: __('User Dashboard'),
        single_column: true
    });

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
    // stats অবজেক্ট বা ডিফল্ট খালি অবজেক্ট
    let stats = data.stats || {};
    
    let html = `
    <div class="container-fluid p-4" style="background-color: #f8f9fa;">
        <div class="row">
            <div class="col-md-8">
                <div class="row">
                    ${createCard("Present", stats.present, "#28a745")}
                    ${createCard("Absent", stats.absent, "#dc3545")}
                    ${createCard("Late", stats.late, "#ffc107")}
                </div>
                <div class="row mt-3">
                    ${createCard("Leave", stats.leave, "#6f42c1")}
                    ${createCard("Weekend/Holiday", stats.weekend || stats.holiday, "#17a2b8")}
                    ${createCard("Home Office", stats.home_office, "#fd7e14")}
                </div>
            </div>

            <div class="col-md-4">
                <div class="card shadow-sm mb-3 border-0">
                    <div class="card-header bg-white font-weight-bold">Leave Allocation</div>
                    <div class="p-2">
                        ${(data.leave_allocation && data.leave_allocation.length) ? data.leave_allocation.map(l => `
                            <div class="d-flex justify-content-between p-2 border-bottom">
                                <span class="text-muted">${l.leave_type}</span>
                                <span class="badge badge-primary badge-pill">${l.total}</span>
                            </div>
                        `).join('') : '<p class="text-center p-2 text-muted">No Allocation</p>'}
                    </div>
                </div>

                <div class="card shadow-sm border-0">
                    <div class="card-header bg-white font-weight-bold">Quick Links</div>
                    <div class="card-body p-2">
                        <button class="btn btn-outline-primary btn-sm btn-block mb-2" onclick="frappe.set_route('List', 'Leave Application', 'List')">Leave Application</button>
                        <button class="btn btn-outline-secondary btn-sm btn-block" onclick="frappe.set_route('List', 'Employee Checkin', 'List')">Employee Checkin</button>
                    </div>
                </div>
            </div>
        </div>

        <div class="row mt-5">
            <div class="col-md-6">
                <div class="card shadow-sm border-0">
                    <div class="card-header font-weight-bold bg-white border-0">Attendance Summary (Monthly)</div>
                    <div class="table-responsive" style="max-height: 400px;">
                        <table class="table table-sm table-hover text-center mb-0">
                            <thead class="bg-light text-muted">
                                <tr><th>SL</th><th>Date</th><th>In</th><th>Out</th><th>Stay</th><th>Status</th></tr>
                            </thead>
                            <tbody>
                                ${data.attendance_details.map((a, i) => {
                                    // স্ট্যাটাস অনুযায়ী ব্যাজ কালার নির্ধারণ
                                    let badge_class = "secondary";
                                    if(a.status === "Present") badge_class = "success";
                                    else if(a.status === "Absent") badge_class = "danger";
                                    else if(a.status === "Weekend" || a.status === "Holiday") badge_class = "info";
                                    else if(a.status === "Work From Home") badge_class = "warning";
                                    else if(a.status === "On Leave") badge_class = "primary";

                                    return `
                                    <tr>
                                        <td>${i+1}</td>
                                        <td>${frappe.datetime.str_to_user(a.attendance_date)}</td>
                                        <td>${a.in_time ? frappe.datetime.get_time(a.in_time) : '--'}</td>
                                        <td>${a.out_time ? frappe.datetime.get_time(a.out_time) : '--'}</td>
                                        <td>${a.working_hours ? flt(a.working_hours).toFixed(2) : '0'}h</td>
                                        <td><span class="badge badge-${badge_class}">${a.status}</span></td>
                                    </tr>`;
                                }).join('')}
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>

            <div class="col-md-6">
                <div class="card shadow-sm border-0">
                    <div class="card-header font-weight-bold bg-white border-0">Leave Summary (Yearly)</div>
                    <div class="table-responsive" style="max-height: 400px;">
                        <table class="table table-sm table-hover text-center mb-0">
                            <thead class="bg-light text-muted">
                                <tr><th>SL</th><th>From</th><th>To</th><th>Days</th><th>Type</th></tr>
                            </thead>
                            <tbody>
                                ${(data.leave_history && data.leave_history.length) ? data.leave_history.map((l, i) => `
                                    <tr>
                                        <td>${i+1}</td>
                                        <td>${frappe.datetime.str_to_user(l.from_date)}</td>
                                        <td>${frappe.datetime.str_to_user(l.to_date)}</td>
                                        <td>${l.total_leave_days}</td>
                                        <td><span class="badge badge-info">${l.leave_type}</span></td>
                                    </tr>
                                `).join('') : '<tr><td colspan="5" class="p-3 text-muted">No records found</td></tr>'}
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>
        </div>
    </div>`;

    page.main.html(html);
}

// কার্ড তৈরির ফাংশন (N/A হ্যান্ডেল করা হয়েছে)
function createCard(label, val, color) {
    let display_val = (val === undefined || val === null || val === 0) ? "N/A" : val;
    
    return `
    <div class="col-md-4">
        <div class="card p-3 text-center shadow-sm border-0" style="border-top: 4px solid ${color}; border-radius: 8px;">
            <div class="text-muted small font-weight-bold uppercase" style="letter-spacing: 0.5px;">${label}</div>
            <div class="h3 font-weight-bold mt-2" style="color: ${color}">${display_val}</div>
        </div>
    </div>`;
}
