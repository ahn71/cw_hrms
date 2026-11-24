"""
Login redirect for "self-service" users.

A user who has no module / role access beyond the basic self-service roles
lands on the custom User Dashboard page (/app/user-dashboard) after login
instead of the empty desk home. Users with any other role (System Manager,
HR Manager, Accounts User, ...) keep the normal ERPNext behaviour.
"""

import frappe

DASHBOARD_ROUTE = "/app/user-dashboard"

# Roles that do NOT count as real module access.
# If a user has only these roles, they are redirected to the dashboard.
BASIC_ROLES = {
	"All",
	"Guest",
	"Desk User",
	"Employee",
	"Employee Self Service",
	"Employee Desk",
}


def is_dashboard_only_user(user=None):
	user = user or frappe.session.user
	if user in ("Administrator", "Guest"):
		return False

	if frappe.get_cached_value("User", user, "user_type") != "System User":
		return False

	roles = set(frappe.get_roles(user))
	return not (roles - BASIC_ROLES)


def on_login(login_manager):
	"""Hook: on_login. Frappe's login response picks up `redirect_after_login`."""
	user = login_manager.user
	if is_dashboard_only_user(user):
		frappe.cache.hset("redirect_after_login", user, DASHBOARD_ROUTE)


def boot_session(bootinfo):
	"""Hook: boot_session. Lets the desk JS know whether to redirect home → dashboard."""
	bootinfo.cw_dashboard_only_user = is_dashboard_only_user()
