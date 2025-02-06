import frappe
from frappe.query_builder import DocType
from frappe.utils import cint


def setseries(key, current, digits=None):
    # series created ?
    # Using frappe.qb as frappe.get_values does not allow order_by=None
    series = DocType("Series")
    exists = (
        frappe.qb.from_(series).where(series.name == key).for_update().select("current")
    ).run()
    current = cint(current)

    if exists and exists[0][0] is not None:
        # yes, set it
        frappe.db.sql(
            "UPDATE `tabSeries` SET `current` = %s WHERE `name` = %s", (current, key)
        )
    else:
        # no, create it
        frappe.db.sql(
            "INSERT INTO `tabSeries` (`name`, `current`) VALUES (%s, %s)",
            (key, current),
        )
    if digits:
        return ("%0" + str(digits) + "d") % current
    else:
        return str(current)
