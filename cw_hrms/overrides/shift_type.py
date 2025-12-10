import frappe
from hrms.hr.doctype.shift_type.shift_type import ShiftType

class CustomShiftType(ShiftType):
    # def validate(self):
    #     """
    #     This method executes before the Shift Type is saved (inserted or updated).
    #     It will show a message and then block the save operation using frappe.throw().
    #     """
    #     custom_message = "You press Save Button and your custom method is work fine"
        
    #     # 1. Show a green message box (msgprint)
    #     frappe.msgprint(custom_message, title="Custom Validation Check", indicator="green")
        
    #     # 2. Block the saving process using frappe.throw()
    #     # The text inside frappe.throw will appear as the official validation error.
    #     # This is the mechanism that prevents the data from being written to the database.
    #     frappe.throw(custom_message)
    @frappe.whitelist()    
    def process_auto_attendance(self):
        """
        Custom logic to override Shift Type's Mark Attendance (process_auto_attendance).
        """
        
        # ------------------------------------------------------------
        # STEP 1: ADD YOUR CUSTOM LOGIC HERE
        # e.g., Add special handling for specific employee groups or shifts
        # ------------------------------------------------------------
        frappe.logger("cw_hrms").info(f"Custom Shift Type Override called for: {self.name}")
        print("This is Custom method override process_auto_attendance")
        custom_message = "This is Custom method override process_auto_attendance"
        frappe.msgprint(custom_message, title="Custom Validation Check", indicator="green")
        frappe.throw(custom_message)
        
        # If you want to RUN the standard HRMS logic and THEN add your own checks:
        # super().process_auto_attendance()
        
        # If you want to COMPLETELY REPLACE the standard logic:
        # 1. Comment out or remove the super() call above.
        # 2. Implement the full new logic here.
        # ------------------------------------------------------------

        # Example replacement logic (Placeholder)
        # from frappe.utils import nowdate
        # frappe.db.set_value("Attendance", 
        #   {"employee": "EMP/001", "attendance_date": nowdate()}, 
        #   "status", "Present - Overridden"
        # )

        pass
