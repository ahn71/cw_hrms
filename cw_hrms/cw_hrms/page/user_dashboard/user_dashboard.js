frappe.pages['user-dashboard'].on_page_load = function (wrapper) {
    let page = frappe.ui.make_app_page({
        parent: wrapper,
        title: __('User Dashboard'),
        single_column: false
    });

    create_workspace_sidebar(page);
    
    // শুরুতেই ইউজারের নিজস্ব এমপ্লয়ি আইডি খুঁজে বের করা
    frappe.db.get_value('Employee', { user_id: frappe.session.user }, 'name', (r) => {
        let current_user_employee = r ? r.name : null;
        setup_dashboard(page, current_user_employee);
    });
};

function setup_dashboard(page, current_user_employee) {
    // ১. ফিল্টার তৈরি
    page.employee_filter = frappe.ui.form.make_control({
        parent: page.wrapper.find('.page-actions'),
        df: {
            fieldtype: 'Link',
            options: 'Employee',
            fieldname: 'employee',
            placeholder: __('Select Employee'),
            get_query: () => {
                if (!frappe.user_roles.includes('HR Manager') && !frappe.user_roles.includes('HR User')) {
                    return {
                        filters: [
                            ['Employee', 'reports_to', '=', current_user_employee, 'or'],
                            ['Employee', 'name', '=', current_user_employee]
                        ]
                    };
                }
            }
        },
        render_input: true,
    });

    // ২. ইভেন্ট লিসেনার সেট করা (on_change মাঝে মাঝে ঝামেলা করলে এটি ১০০% কাজ করবে)
    page.employee_filter.$input.on('change', function() {
        let selected = page.employee_filter.get_value();
        console.log("Change Detected! Selected:", selected); // এটি কনসোলে চেক করবেন
        if (selected) {
            refresh_dashboard(page, selected);
        }
    });

    // ৩. ডিফল্ট সেট এবং প্রথমবার কল
    if (current_user_employee) {
        page.employee_filter.set_value(current_user_employee);
        refresh_dashboard(page, current_user_employee);
    }
}

function refresh_dashboard(page, employee) {
    console.log("Calling Server for Employee:", employee); // চেক করুন এটি প্রিন্ট হয় কি না
    
    frappe.call({
        method: 'cw_hrms.cw_hrms.page.user_dashboard.user_dashboard.get_user_stats',
        args: { employee: employee },
        callback: function (r) {
            console.log("Data Received:", r.message);
            render_dashboard_html(page, r.message || {}, employee);
        }
    });
}
function render_dashboard_html(page, data, selected_employee) {
    let stats = data.stats || {};
    let leave_alloc = data.leave_allocation || [];
    let leave_hist = data.leave_history || [];
    
    let total_used_leaves = 0;
    leave_alloc.forEach(l => {
        total_used_leaves += flt(l.used_leave || 0);
    });

    let html = `
    <style>
        .dash-container { padding: 15px; background: #f8f9fc; }
        .stat-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(130px, 1fr)); gap: 15px; margin-bottom: 20px; }
        .s-card { background: white; padding: 15px; border-radius: 8px; border-bottom: 4px solid; text-align: center; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
        .s-value { font-size: 20px; font-weight: 800; }
        .main-grid { display: grid; grid-template-columns: 1.2fr 0.8fr; gap: 20px; }
        .section { background: white; padding: 15px; border-radius: 10px; box-shadow: 0 2px 8px rgba(0,0,0,0.05); margin-bottom: 20px; }
        .sec-title { font-size: 14px; font-weight: 700; margin-bottom: 12px; border-bottom: 1px solid #eee; padding-bottom: 5px; }
        .m-table { width: 100%; border-collapse: collapse; }
        .m-table td, .m-table th { padding: 8px; font-size: 12px; border-bottom: 1px solid #f4f4f4; text-align: left; }
        .badge { padding: 3px 7px; border-radius: 10px; font-size: 10px; font-weight: 600; }
        .bg-present { background: #e6fffa; color: #38a169; }
        .bg-absent { background: #fff5f5; color: #e53e3e; }
    </style>

    <div class="dash-container">
        <div class="stat-grid">
            ${createStatCard("Present", stats.present, "#38a169")}
            ${createStatCard("Absent", stats.absent, "#e53e3e")}
            ${createStatCard("Late", stats.late, "#d69e2e")}
            ${createStatCard("Leave", total_used_leaves, "#3182ce")}
            ${createStatCard("Holiday", (flt(stats.weekend) + flt(stats.holiday)), "#805ad5")}
        </div>

        <div class="main-grid">
            <div class="section">
                <div class="sec-title">📅 Monthly Attendance Summary</div>
                <div style="max-height: 350px; overflow-y: auto;">
                    <table class="m-table">
                        <thead><tr><th>Date</th><th>In/Out</th><th>Status</th></tr></thead>
                        <tbody>
                            ${(data.attendance_details || []).map(a => `
                                <tr>
                                    <td><b>${frappe.datetime.str_to_user(a.attendance_date)}</b></td>
                                    <td>${(a.in_time || '').split(' ')[1] || '--'} - ${(a.out_time || '').split(' ')[1] || '--'}</td>
                                    <td><span class="badge ${a.status == 'Present' ? 'bg-present' : 'bg-absent'}">${a.status}</span></td>
                                </tr>
                            `).join('')}
                        </tbody>
                    </table>
                </div>
            </div>

            <div>
                <div class="section">
                    <div class="sec-title">📊 Leave Balance (Unused / Total)</div>
                    <table class="m-table">
                        <tbody>
                            ${leave_alloc.map(l => `
                                <tr>
                                    <td>${l.leave_type}</td>
                                    <td align="right"><strong>${l.unused_leaves}</strong> / ${l.total_allocated}</td>
                                </tr>
                            `).join('')}
                        </tbody>
                    </table>
                </div>

                <div class="section">
                    <div class="sec-title">🗓️ Recent Leave History</div>
                    <table class="m-table">
                        <tbody>
                            ${leave_hist.length ? leave_hist.map(l => `
                                <tr>
                                    <td>${frappe.datetime.str_to_user(l.from_date)}</td>
                                    <td><strong>${l.total_leave_days} d</strong></td>
                                    <td><span class="badge" style="background:#e2e5ff;">${l.leave_type}</span></td>
                                </tr>
                            `).join('') : '<tr><td colspan="3" align="center">No Records</td></tr>'}
                        </tbody>
                    </table>
                </div>
            </div>
        </div>

        <div class="section">
            <div class="sec-title">📈 Attendance Yearly Chart</div>
            <div style="height:280px;"><canvas id="attBarChart"></canvas></div>
        </div>
    </div>`;

    page.main.html(html);

    frappe.require('https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.js', function() {
        render_chart(selected_employee);
    });
}

function render_chart(employee) {
    frappe.call({
        method: 'cw_hrms.cw_hrms.page.user_dashboard.user_dashboard.get_yearly_attendance',
        args: { year: 2026, employee: employee },
        callback: function(r) {
            let rows = r.message || [];
            let ctx = document.getElementById('attBarChart').getContext('2d');
            if (window.dashboardChart) window.dashboardChart.destroy();
            window.dashboardChart = new Chart(ctx, {
                type: 'bar',
                data: {
                    labels: rows.map(d => d.month),
                    datasets: [
                        { label: 'Present', data: rows.map(d => d.present), backgroundColor: '#38a169', stack: 's' },
                        { label: 'Absent', data: rows.map(d => d.absent), backgroundColor: '#e53e3e', stack: 's' },
                        { label: 'Late', data: rows.map(d => d.late), backgroundColor: '#d69e2e', stack: 's' },
                        { label: 'Leave', data: rows.map(d => d.leave), backgroundColor: '#3182ce', stack: 's' }
                    ]
                },
                options: { 
                    responsive: true, 
                    maintainAspectRatio: false, 
                    scales: { x: { stacked: true }, y: { stacked: true } } 
                }
            });
        }
    });
}

function createStatCard(label, val, color) {
    return `<div class="s-card" style="border-bottom-color: ${color}">
        <div style="font-size: 11px; color: #888;">${__(label)}</div>
        <div class="s-value" style="color: ${color}">${val || 0}</div>
    </div>`;
}
// সাইডবার ফাংশন (অপরিবর্তিত)
function create_workspace_sidebar(page) {
    let list_sidebar = $(`
        <div class="list-sidebar overlay-sidebar hidden-xs hidden-sm">
            <div class="desk-sidebar list-unstyled sidebar-menu"></div>
        </div>
    `).appendTo(page.sidebar);

    let sidebar = list_sidebar.find('.desk-sidebar');

    frappe.xcall('frappe.desk.desktop.get_workspace_sidebar_items').then((data) => {
        if (!data || !data.pages) return;
        let public_pages = data.pages.filter(p => p.public);
        let private_pages = data.pages.filter(p => !p.public);

        if (public_pages.length > 0) build_sidebar_section(sidebar, 'Public', public_pages, true);
        if (private_pages.length > 0) build_sidebar_section(sidebar, 'Personal', private_pages, false);
    });
}

function build_sidebar_section(sidebar, title, pages, is_public) {
    let root_pages = pages.filter(p => !p.parent_page);
    let section = $(`
        <div class="standard-sidebar-section nested-container" data-title="${title}">
            <button class="btn-reset standard-sidebar-label">
                <span>${frappe.utils.icon('es-line-down', 'xs')}</span>
                <span class="section-title">${__(title)}</span>
            </button>
        </div>
    `).appendTo(sidebar);

    root_pages.forEach(page => {
        append_sidebar_item(section, page, pages, is_public);
    });
}

function append_sidebar_item(container, item, all_pages, is_public) {
    let route = is_public ? frappe.router.slug(item.title) : 'private/' + frappe.router.slug(item.title);
    let $item = $(`
        <div class="sidebar-item-container" item-name="${item.title}">
            <div class="desk-sidebar-item standard-sidebar-item">
                <a href="/app/${route}" class="item-anchor">
                    <span class="sidebar-item-icon">
                        ${is_public ? frappe.utils.icon(item.icon || 'folder-normal', 'md') : `<span class="indicator ${item.indicator_color || 'blue'}"></span>`}
                    </span>
                    <span class="sidebar-item-label">${__(item.title)}</span>
                </a>
            </div>
            <div class="sidebar-child-item nested-container hidden"></div>
        </div>
    `).appendTo(container);

    let child_items = all_pages.filter(p => p.parent_page == item.title);
    if (child_items.length > 0) {
        let child_container = $item.find('.sidebar-child-item');
        child_items.forEach(child => append_sidebar_item(child_container, child, all_pages, is_public));
        child_container.removeClass('hidden');
    }
}