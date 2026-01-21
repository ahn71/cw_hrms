frappe.pages['user-dashboard'].on_page_load = function(wrapper) {
	let page = frappe.ui.make_app_page({
		parent: wrapper,
		title: __('User Dashboard'),
		single_column: false
	});

	frappe.call({
		method: 'cw_hrms.cw_hrms.page.user_dashboard.user_dashboard.get_user_stats',
		callback: function(r) {
			if (r.message) {
				render_dashboard_html(page, r.message);
			}
		}
	});
};

function render_dashboard_html(page, data) {
	let stats = data.stats || {};
	
	let html = `
		<style>
			.user-dashboard-container {
				padding: 20px;
				background: #f8f9fa;
				min-height: 100vh;
			}
			
			.stats-grid {
				display: grid;
				grid-template-columns: repeat(3, 1fr);
				gap: 20px;
				margin-bottom: 30px;
			}
			
			.top-row-grid {
				display: grid;
				grid-template-columns: 1fr 1fr;
				gap: 20px;
				margin-bottom: 24px;
			}
			
			.left-cards-grid {
				display: grid;
				grid-template-columns: repeat(3, 1fr);
				gap: 20px;
			}
			
			.bottom-tables-grid {
				display: grid;
				grid-template-columns: 1fr 1fr;
				gap: 20px;
			}
			
			.stat-card {
				background: white;
				border-radius: 10px;
				padding: 16px 20px;
				box-shadow: 0 2px 8px rgba(0,0,0,0.08);
				transition: all 0.3s ease;
				border-left: 4px solid;
				position: relative;
				overflow: hidden;
			}
			
			.stat-card::before {
				content: '';
				position: absolute;
				top: 0;
				right: 0;
				width: 80px;
				height: 80px;
				border-radius: 50%;
				opacity: 0.1;
				transform: translate(30%, -30%);
			}
			
			.stat-card:hover {
				transform: translateY(-5px);
				box-shadow: 0 8px 20px rgba(0,0,0,0.12);
			}
			
			.stat-label {
				font-size: 11px;
				font-weight: 600;
				color: #6c757d;
				text-transform: uppercase;
				letter-spacing: 0.5px;
				margin-bottom: 6px;
			}
			
			.stat-value {
				font-size: 26px;
				font-weight: 700;
				line-height: 1;
				margin-top: 6px;
			}
			
			.dashboard-section {
				background: white;
				border-radius: 10px;
				padding: 18px 20px;
				margin-bottom: 24px;
				box-shadow: 0 2px 8px rgba(0,0,0,0.08);
			}
			
			.section-title {
				font-size: 16px;
				font-weight: 700;
				color: #2c3e50;
				margin-bottom: 16px;
				padding-bottom: 10px;
				border-bottom: 2px solid #e9ecef;
				display: flex;
				align-items: center;
				gap: 8px;
			}
			
			.section-title::before {
				content: '';
				width: 3px;
				height: 20px;
				background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
				border-radius: 2px;
			}
			
			.leave-allocation-grid {
				display: grid;
				grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
				gap: 16px;
			}
			
			.leave-item {
				background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
				color: white;
				padding: 20px;
				border-radius: 10px;
				text-align: center;
				box-shadow: 0 4px 12px rgba(102, 126, 234, 0.3);
				transition: all 0.3s ease;
			}
			
			.leave-item:hover {
				transform: translateY(-3px);
				box-shadow: 0 6px 16px rgba(102, 126, 234, 0.4);
			}
			
			.leave-type {
				font-size: 13px;
				font-weight: 600;
				opacity: 0.95;
				margin-bottom: 8px;
			}
			
			.leave-count {
				font-size: 28px;
				font-weight: 700;
			}
			
			.quick-links-grid {
				display: grid;
				grid-template-columns: 1fr;
				gap: 16px;
			}
			
			.quick-link-btn {
				display: flex;
				align-items: center;
				justify-content: center;
				gap: 10px;
				padding: 16px;
				background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
				color: white;
				text-decoration: none;
				border-radius: 8px;
				font-weight: 600;
				transition: all 0.3s ease;
				box-shadow: 0 4px 12px rgba(245, 87, 108, 0.3);
				font-size: 13px;
			}
			
			.quick-link-btn:hover {
				transform: translateY(-3px);
				box-shadow: 0 6px 16px rgba(245, 87, 108, 0.4);
				color: white;
				text-decoration: none;
			}
			
			.quick-link-btn:nth-child(1) {
				background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
				box-shadow: 0 4px 12px rgba(102, 126, 234, 0.3);
			}
			
			.quick-link-btn:nth-child(2) {
				background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
				box-shadow: 0 4px 12px rgba(245, 87, 108, 0.3);
			}
			
			.quick-link-icon {
				font-size: 18px;
			}
			
			.table-responsive {
				overflow-x: auto;
				margin-top: 16px;
			}
			
			.modern-table {
				width: 100%;
				border-collapse: separate;
				border-spacing: 0;
			}
			
			.modern-table thead th {
				background: #f8f9fa;
				color: #495057;
				font-weight: 600;
				font-size: 12px;
				text-transform: uppercase;
				letter-spacing: 0.5px;
				padding: 10px 12px;
				border-bottom: 2px solid #dee2e6;
				text-align: left;
			}
			
			.modern-table tbody td {
				padding: 10px 12px;
				border-bottom: 1px solid #f1f3f5;
				font-size: 13px;
				color: #495057;
			}
			
			.modern-table tbody tr {
				transition: all 0.2s ease;
			}
			
			.modern-table tbody tr:hover {
				background: #f8f9fa;
			}
			
			.badge-custom {
				padding: 4px 10px;
				border-radius: 5px;
				font-size: 11px;
				font-weight: 600;
				display: inline-block;
			}
			
			.badge-success { background: #d4edda; color: #155724; }
			.badge-danger { background: #f8d7da; color: #721c24; }
			.badge-info { background: #d1ecf1; color: #0c5460; }
			.badge-warning { background: #fff3cd; color: #856404; }
			.badge-primary { background: #cce5ff; color: #004085; }
			.badge-secondary { background: #e2e3e5; color: #383d41; }
			
			.no-data {
				text-align: center;
				padding: 40px;
				color: #6c757d;
				font-size: 14px;
			}
			
			@media (max-width: 768px) {
				.stats-grid {
					grid-template-columns: repeat(2, 1fr);
				}
				
				.top-row-grid {
					grid-template-columns: 1fr;
				}
				
				.left-cards-grid {
					grid-template-columns: repeat(2, 1fr);
				}
				
				.bottom-tables-grid {
					grid-template-columns: 1fr;
				}
				
				.quick-links-grid {
					grid-template-columns: 1fr;
				}
			}
		</style>
		
		<div class="user-dashboard-container">
			<!-- First Row: 3 Cards + Leave Allocation Table -->
			<div class="top-row-grid">
				<div class="left-cards-grid">
					${createCard("Present", stats.present, "#28a745")}
					${createCard("Absent", stats.absent, "#dc3545")}
					${createCard("Late", stats.late, "#ffc107")}
				</div>
				
				<div class="dashboard-section" style="margin-bottom: 0;">
					<div class="section-title">
						📊 Leave Allocation
					</div>
					<div class="table-responsive">
						<table class="modern-table">
							<thead>
								<tr>
									<th>Leave Type</th>
									<th style="text-align: center;">Allocation</th>
								</tr>
							</thead>
							<tbody>
								${(data.leave_allocation && data.leave_allocation.length) ? 
									data.leave_allocation.map(l => `
										<tr>
											<td><strong>${l.leave_type}</strong></td>
											<td style="text-align: center;">
												<span class="badge-custom badge-primary">${l.total}</span>
											</td>
										</tr>
									`).join('') : 
									'<tr><td colspan="2" class="no-data">No allocation found</td></tr>'
								}
							</tbody>
						</table>
					</div>
				</div>
			</div>
			
			<!-- Second Row: 3 Cards + Quick Access -->
			<div class="top-row-grid">
				<div class="left-cards-grid">
					${createCard("Leave", stats.leave, "#6f42c1")}
					${createCard("Weekend/Holiday", stats.weekend || stats.holiday, "#17a2b8")}
					${createCard("Home Office", stats.home_office, "#fd7e14")}
				</div>
				
				<div class="dashboard-section" style="margin-bottom: 0;">
					<div class="section-title">
						⚡ Quick Access
					</div>
					<div class="quick-links-grid">
						<a href="/app/leave-application" class="quick-link-btn">
							<span class="quick-link-icon">📝</span>
							<span>Leave Application</span>
						</a>
						<a href="/app/employee-checkin" class="quick-link-btn">
							<span class="quick-link-icon">✓</span>
							<span>Employee Checkin</span>
						</a>
					</div>
				</div>
			</div>
			
			<!-- Bottom Row: Two Tables Side by Side -->
			<div class="bottom-tables-grid">
				<div class="dashboard-section" style="margin-bottom: 0;">
					<div class="section-title">
						📅 Attendance Summary
					</div>
					<div class="table-responsive">
						<table class="modern-table">
							<thead>
								<tr>
									<th style="width: 40px;">SL</th>
									<th>Date</th>
									<th>In</th>
									<th>Out</th>
									<th>Hours</th>
									<th>Status</th>
								</tr>
							</thead>
							<tbody>
								${data.attendance_details.map((a, i) => {
									let badge_class = "secondary";
									if(a.status === "Present") badge_class = "success";
									else if(a.status === "Absent") badge_class = "danger";
									else if(a.status === "Weekend" || a.status === "Holiday") badge_class = "info";
									else if(a.status === "Work From Home") badge_class = "warning";
									else if(a.status === "On Leave") badge_class = "primary";
									
									return `
										<tr>
											<td>${i+1}</td>
											<td><strong>${frappe.datetime.str_to_user(a.attendance_date)}</strong></td>
											<td>${a.in_time ? frappe.datetime.get_time(a.in_time) : '--'}</td>
											<td>${a.out_time ? frappe.datetime.get_time(a.out_time) : '--'}</td>
											<td>${a.working_hours ? flt(a.working_hours).toFixed(2) : '0'}h</td>
											<td><span class="badge-custom badge-${badge_class}">${a.status}</span></td>
										</tr>
									`;
								}).join('')}
							</tbody>
						</table>
					</div>
				</div>
				
				<div class="dashboard-section" style="margin-bottom: 0;">
					<div class="section-title">
						🗓️ Leave Summary
					</div>
					<div class="table-responsive">
						<table class="modern-table">
							<thead>
								<tr>
									<th style="width: 40px;">SL</th>
									<th>From</th>
									<th>To</th>
									<th>Days</th>
									<th>Type</th>
								</tr>
							</thead>
							<tbody>
								${(data.leave_history && data.leave_history.length) ? 
									data.leave_history.map((l, i) => `
										<tr>
											<td>${i+1}</td>
											<td>${frappe.datetime.str_to_user(l.from_date)}</td>
											<td>${frappe.datetime.str_to_user(l.to_date)}</td>
											<td><strong>${l.total_leave_days}</strong></td>
											<td><span class="badge-custom badge-primary">${l.leave_type}</span></td>
										</tr>
									`).join('') : 
									'<tr><td colspan="5" class="no-data">No records found</td></tr>'
								}
							</tbody>
						</table>
					</div>
				</div>
			</div>
		</div>
	`;
	
	page.main.html(html);
}

function createCard(label, val, color) {
	let display_val = (val === undefined || val === null || val === 0) ? "N/A" : val;
	return `
		<div class="stat-card" style="border-left-color: ${color};">
			<div class="stat-label">${label}</div>
			<div class="stat-value" style="color: ${color};">${display_val}</div>
			<div style="background: ${color};" class="stat-card::before"></div>
		</div>
	`;
}