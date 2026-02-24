frappe.pages['attendance-process'].on_page_load = function(wrapper) {
    let page = frappe.ui.make_app_page({
        parent: wrapper,
        title: 'Attendance Processing Panel',
        single_column: true
    });

    // ১. ফিল্টার তৈরি করা
    let emp_filter = page.add_field({
        label: 'Employee',
        fieldname: 'employee',
        fieldtype: 'Link',
        options: 'Employee'
    });
    
    let date_filter = page.add_field({
        label: 'Date',
        fieldname: 'date',
        fieldtype: 'Date'
    });

    // ২. এপ্রুভ বাটন এবং অ্যাকশন
    page.set_primary_action('Approve & Sync', () => {
        // টেবিল থেকে চেক করা আইডিগুলো নেওয়ার ফাংশন
        let selected_items = [];
        $(wrapper).find('.row-check:checked').each(function() {
            selected_items.push($(this).data('id'));
        });

        if(selected_items.length == 0) return frappe.msgprint("Please select rows to approve.");

        frappe.confirm('Are you sure you want to approve and re-sync these check-ins?', () => {
            frappe.call({
                method: "cw_hrms.cw_hrms.page.attendance_process.attendance_process.get_attendance_status",
                args: {
                    checkin_ids: selected_items
                },
                callback: function(r) {
                    if(r.message) {
                        frappe.show_alert({message: __("Attendance Processed Successfully"), indicator: 'green'});
                        // প্রসেস শেষে পেজ রিলোড বা ডাটা রিফ্রেশ
                        location.reload(); 
                    }
                }
            });
        });
    });
}