// Users without module/role access (only Employee / basic roles) should never
// land on the default desk home — send them to the custom User Dashboard instead.
// Explicitly opened workspaces (e.g. /app/employee-desk) still work normally.
(function () {
	const DASHBOARD = "user-dashboard";

	function is_dashboard_only_user() {
		return !!(frappe.boot && frappe.boot.cw_dashboard_only_user);
	}

	function is_bare_home() {
		// "/app" (or logo / Home click) — no specific workspace requested
		const route = frappe.router.current_route || frappe.get_route() || [];
		return !route.length || !route[0];
	}

	function redirect_home_to_dashboard() {
		if (!is_dashboard_only_user() || !is_bare_home()) return false;
		frappe.route_flags.replace_route = true;
		frappe.set_route(DASHBOARD);
		return true;
	}

	// Workspace view picks a default workspace when route is bare "/app".
	// Intercept only that case; explicit workspace routes go through untouched.
	if (frappe.views && frappe.views.Workspace) {
		const original_show = frappe.views.Workspace.prototype.show;
		frappe.views.Workspace.prototype.show = function () {
			if (redirect_home_to_dashboard()) return;
			return original_show.apply(this, arguments);
		};
	}
})();
