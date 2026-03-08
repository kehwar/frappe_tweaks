# Copyright (c) 2026, Erick W.R. and Contributors
# See license.txt

import frappe
from frappe.model.document import Document


class AsyncTaskType(Document):
    # begin: auto-generated types
    # This code is auto-generated. Do not modify anything in this block.

    from typing import TYPE_CHECKING

    if TYPE_CHECKING:
        from frappe.types import DF

        is_standard: DF.Check
        limit: DF.Int
        method: DF.Data
        priority: DF.Int
    # end: auto-generated types
