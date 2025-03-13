import frappe
from frappe.automation.doctype.reminder.reminder import Reminder
from frappe.desk.doctype.notification_log.notification_log import (
    send_notification_email,
)
from frappe.desk.doctype.notification_settings.notification_settings import (
    is_email_notifications_enabled,
)


class TweaksReminder(Reminder):

    def send_reminder(self):
        if self.notified:
            return

        self.db_set("notified", 1, update_modified=False)

        try:
            notification = frappe.new_doc("Notification Log")
            notification.for_user = self.user
            notification.set("type", "Alert")
            notification.document_type = self.reminder_doctype
            notification.document_name = self.reminder_docname
            notification.subject = self.description
            notification.insert()
            if is_email_notifications_enabled(self.user):
                notification.type = "Default"
                send_notification_email(notification)
        except Exception:
            self.log_error("Failed to send reminder")
