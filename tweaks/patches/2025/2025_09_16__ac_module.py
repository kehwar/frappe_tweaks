import frappe

from tweaks.custom.doctype.role import apply_role_patches
from tweaks.custom.doctype.user_group import apply_user_group_patches
from tweaks.tweaks.doctype.ac_action.ac_action import insert_standard_actions


def execute():

    insert_standard_actions()
    apply_user_group_patches()
    apply_role_patches()
