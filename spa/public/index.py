import frappe


def get_context(context):
    context.safe_render = False
    return context
