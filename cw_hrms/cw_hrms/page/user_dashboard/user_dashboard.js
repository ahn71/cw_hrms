frappe.pages['user-dashboard'].on_page_load = function (wrapper) {
	let page = frappe.ui.make_app_page({
		parent: wrapper,
		title: __('User Dashboard'),
		single_column: false
	});

	create_workspace_sidebar(page);

	frappe.call({
		method: 'cw_hrms.cw_hrms.page.user_dashboard.user_dashboard.get_user_stats',
		callback: function (r) {
			if (r.message) {
				render_dashboard_html(page, r.message);
			}
		}
	});
};

function create_workspace_sidebar(page) {
	// Create the workspace sidebar structure
	let list_sidebar = $(`
		<div class="list-sidebar overlay-sidebar hidden-xs hidden-sm">
			<div class="desk-sidebar list-unstyled sidebar-menu"></div>
		</div>
	`).appendTo(page.sidebar);

	let sidebar = list_sidebar.find('.desk-sidebar');

	// Get workspace sidebar items
	frappe.xcall('frappe.desk.desktop.get_workspace_sidebar_items').then((data) => {
		if (!data || !data.pages) return;

		let public_pages = data.pages.filter(p => p.public);
		let private_pages = data.pages.filter(p => !p.public);

		// Build Public section
		if (public_pages.length > 0) {
			build_sidebar_section(sidebar, 'Public', public_pages, true);
		}

		// Build Personal section
		if (private_pages.length > 0) {
			build_sidebar_section(sidebar, 'Personal', private_pages, false);
		}
	});
}

function build_sidebar_section(sidebar, title, pages, is_public) {
	let root_pages = pages.filter(p => !p.parent_page);

	let section = $(`
		<div class="standard-sidebar-section nested-container" data-title="${title}">
			<button class="btn-reset standard-sidebar-label" aria-label="Toggle Section: ${title}" aria-expanded="true">
				<span>${frappe.utils.icon('es-line-down', 'xs')}</span>
				<span class="section-title">${__(title)}</span>
			</button>
		</div>
	`).appendTo(sidebar);

	let $title = section.find('.standard-sidebar-label');
	$title.on('click', (e) => {
		const $e = $(e.currentTarget);
		const href = $e.find('span use').attr('href');
		const isCollapsed = href === '#es-line-down';
		let icon = isCollapsed ? '#es-line-right-chevron' : '#es-line-down';
		$e.find('span use').attr('href', icon);
		section.find('> .sidebar-item-container').toggleClass('hidden');
		$e.attr('aria-expanded', String(!isCollapsed));
	});

	root_pages.forEach(page => {
		append_sidebar_item(section, page, pages, is_public);
	});
}

function append_sidebar_item(container, item, all_pages, is_public) {
	let route = is_public ? frappe.router.slug(item.title) : 'private/' + frappe.router.slug(item.title);
	let is_current = frappe.get_route_str().includes(frappe.router.slug(item.title));

	let $item = $(`
		<div class="sidebar-item-container" item-name="${item.title}" item-public="${is_public ? 1 : 0}">
			<div class="desk-sidebar-item standard-sidebar-item ${is_current ? 'selected' : ''}">
				<a href="/app/${route}" class="item-anchor" title="${__(item.title)}">
					<span class="sidebar-item-icon">
						${is_public ? frappe.utils.icon(item.icon || 'folder-normal', 'md') : `<span class="indicator ${item.indicator_color || 'blue'}"></span>`}
					</span>
					<span class="sidebar-item-label">${__(item.title)}</span>
				</a>
			</div>
			<div class="sidebar-child-item nested-container hidden"></div>
		</div>
	`).appendTo(container);

	// Add child items
	let child_items = all_pages.filter(p => p.parent_page == item.title);
	if (child_items.length > 0) {
		let child_container = $item.find('.sidebar-child-item');
		child_items.forEach(child => {
			append_sidebar_item(child_container, child, all_pages, is_public);
		});
		child_container.removeClass('hidden');
	}
}
function render_dashboard_html(page, data) {
    let stats = data.stats || {};
	let total_used_leaves = 0;

    // ২. লুপ চালিয়ে ডাটাগুলো যোগ করুন
    if (data.leave_allocation) {
        data.leave_allocation.forEach(l => {
            total_used_leaves += (l.used_leave || 0);
        });
    }
    let html = `
    <style>
        .dash-container { padding: 15px; background: #f8f9fc; font-family: sans-serif; }
        .stat-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(130px, 1fr)); gap: 15px; margin-bottom: 20px; }
        .s-card { background: white; padding: 15px; border-radius: 8px; border-bottom: 4px solid; text-align: center; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
        .s-value { font-size: 20px; font-weight: 800; }
        
        .main-grid { display: grid; grid-template-columns: 1.2fr 0.8fr; gap: 20px; }
        .section { background: white; padding: 15px; border-radius: 10px; box-shadow: 0 2px 8px rgba(0,0,0,0.05); margin-bottom: 20px; }
        .sec-title { font-size: 14px; font-weight: 700; margin-bottom: 12px; border-bottom: 1px solid #eee; padding-bottom: 5px; }
        
        /* Attendance Scroll Setting */
        .attendance-scroll { max-height: 400px; overflow-y: auto; }
        
        .m-table { width: 100%; border-collapse: collapse; }
        .m-table th { position: sticky; top: 0; background: white; text-align: left; font-size: 11px; color: #777; padding: 8px; border-bottom: 2px solid #f4f4f4; z-index: 1; }
        .m-table td { padding: 8px; font-size: 12px; border-bottom: 1px solid #f4f4f4; vertical-align: middle; }
        
        .date-cell { white-space: nowrap; font-weight: 700; color: #333; min-width: 100px; }
        .badge { padding: 3px 7px; border-radius: 10px; font-size: 10px; font-weight: 600; white-space: nowrap; }
        .bg-present { background: #e6fffa; color: #38a169; }
        .bg-absent { background: #fff5f5; color: #e53e3e; }
        
        @media (max-width: 992px) { .main-grid { grid-template-columns: 1fr; } }
    </style>

    <div class="dash-container">
        <div class="stat-grid">
            ${createStatCard("Present", stats.present, "#38a169")}
            ${createStatCard("Absent", stats.absent, "#e53e3e")}
            ${createStatCard("Late", stats.late, "#d69e2e")}
            ${createStatCard("Leave", total_used_leaves, "#3182ce")}
            ${createStatCard("Holiday", (stats.weekend || 0) + (stats.holiday || 0), "#805ad5")}
        </div>

        <div class="main-grid">
            <div class="section">
                <div class="sec-title">📅 Monthly Attendance Summary</div>
                <div class="attendance-scroll">
                    <table class="m-table">
                        <thead>
                            <tr>
                                <th>Date</th>
                                <th>In Time</th>
                                <th>Out Time</th>
                                <th>Stay Time</th>
                                <th>Status</th>
                            </tr>
                        </thead>
                        <tbody>
                            ${data.attendance_details.map(a => {
                                let in_t = a.in_time ? a.in_time.split(' ')[1].substring(0,8) : '--:--:--';
                                let out_t = a.out_time ? a.out_time.split(' ')[1].substring(0,8) : '--:--:--';
                                let formatted_date = frappe.datetime.str_to_user(a.attendance_date);
                                return `
                                    <tr>
                                        <td class="date-cell">${formatted_date}</td>
                                        <td>${in_t}</td>
                                        <td>${out_t}</td>
                                        <td><strong>${a.working_hours}</strong></td>
                                        <td><span class="badge bg-${a.status.toLowerCase().replace(/ /g, '-')}">${a.status}</span></td>
                                    </tr>
                                `;
                            }).join('')}
                        </tbody>
                    </table>
                </div>
            </div>

            <div class="leave-column">
                <div class="section">
                    <div class="sec-title">📊 Leave Balance</div>
                    <table class="m-table">
                        <tbody>
                            ${data.leave_allocation.map(l => `
                                <tr>
                                    <td>${l.leave_type}</td>
                                    <td align="right"><strong>${l.unused_leaves}</strong> / ${l.total_allocated}</td>
                                </tr>
                            `).join('')}
                        </tbody>
                    </table>
                </div>

                <div class="section">
                    <div class="sec-title">🗓️ Leave History</div>
                    <table class="m-table">
                        <thead>
                            <tr>
                                <th>From</th>
                                <th>Days</th>
                                <th>Type</th>
                            </tr>
                        </thead>
                        <tbody>
                            ${(data.leave_history && data.leave_history.length) ? data.leave_history.map(l => `
                                <tr>
                                    <td>${frappe.datetime.str_to_user(l.from_date)}</td>
                                    <td><strong>${l.total_leave_days}</strong></td>
                                    <td><span class="badge" style="background:#e2e5ff; color:#4e73df;">${l.leave_type}</span></td>
                                </tr>
                            `).join('') : '<tr><td colspan="3" align="center">No records</td></tr>'}
                        </tbody>
                    </table>
                </div>
            </div> </div> </div>
    `;
    page.main.html(html);
}

function createStatCard(label, val, color) {
    return `<div class="s-card" style="border-bottom-color: ${color}">
        <div class="s-label" style="font-size: 11px; color: #888; font-weight: 600;">${label}</div>
        <div class="s-value" style="color: ${color}">${val || 0}</div>
    </div>`;
}