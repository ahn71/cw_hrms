import frappe

def redirect_user(login_manager):
    # This sends the path back to the JS login_handler you found
    # It populates the "data.home_page" variable automatically
    frappe.local.response["home_page"] = "/app/custom-user-dashboar"