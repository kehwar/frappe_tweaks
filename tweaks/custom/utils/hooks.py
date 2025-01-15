import frappe


def execute_with_hooks(func, before=None, after=None):
    def wrapper(*args, **kwargs):
        # Initialize the state dictionary with the original arguments and the function
        state = {"args": args, "kwargs": kwargs, "func": func, "result": None}

        # Call the before hook if it exists, passing the state dictionary
        if before and callable(before):
            before(state)

        # Only call the main function if state['result'] is not set
        if state["result"] is None:
            state["result"] = func(*state["args"], **state["kwargs"])

        # Call the after hook if it exists, passing the updated state dictionary
        if after and callable(after):
            after(state)

        # Return the result stored in the state dictionary
        return state["result"]

    return wrapper


def join_doc_events(args):
    result = {}
    for doc_events in args:
        for key, value in doc_events.items():
            frappe.append_hook(result, key, value)
    return result
