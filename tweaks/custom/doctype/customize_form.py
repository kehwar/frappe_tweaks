import frappe


def set_property_setters_for_actions_and_links(
    doctype, actions=[], links=[], states=[]
):
    """
    Updates doctype using Customize Form controller.

    Args:
        doctype (str): The doctype which is being customized.
        actions (list of dict): A list of action dictionaries, each containing:
            - "label" (str): The display label for the action.
            - "action_type" (str): The type of action ("Server Action" or "Route").
            - "action" (str): The action content.
            - "group" (str, optional): Grouping category for the action.
            - "hidden" (int, optional): 1 if hidden, 0 otherwise.

        links (list of dict): A list of link dictionaries, each containing:
            - "link_doctype" (str): The target doctype being linked.
            - "link_fieldname" (str): The fieldname that holds the link.
            - "table_fieldname" (str, optional): The fieldname of the table field holding the link.
            - "group" (str, optional): Grouping category for the link.
            - "hidden" (int, optional): 1 if hidden, 0 otherwise.

        states (list of dict): A list of state dictionaries, each containing:
            - "title" (str): The name of the state.
            - "color" (str, optional): The color associated with the state.

    Behavior:
    - Loads the "Customize Form" controller for the specified doctype.
    - Checks for existing actions, links, and states and appends only the new ones.
    - Calls `set_property_setters_for_actions_and_links` to apply the updates.

    Returns:
        None
    """
    cf = frappe.new_doc("Customize Form")
    cf.doc_type = doctype
    cf.doc_type_meta = frappe.get_meta(cf.doc_type, cached=False)
    cf.load_properties(cf.doc_type_meta)

    current_links = [(line.link_doctype, line.link_fieldname) for line in cf.links]
    links_to_append = [
        link
        for link in links
        if (link.get("link_doctype"), link.get("link_fieldname")) not in current_links
    ]
    for link in links_to_append:
        cf.append("links", link)

    current_actions = [
        (line.label, line.action_type, line.action) for line in cf.actions
    ]
    actions_to_append = [
        action
        for action in actions
        if (action.get("label"), action.get("action_type"), action.get("action"))
        not in current_actions
    ]
    for action in actions_to_append:
        cf.append("actions", action)

    current_states = [line.title for line in cf.states]
    states_to_append = [
        state for state in states if state["title"] not in current_states
    ]
    for state in states_to_append:
        cf.append("states", state)

    cf.set_property_setters_for_actions_and_links(cf.doc_type_meta)
