from frappe.model.db_query import DatabaseQuery


def apply_db_query_patches():

    DatabaseQuery.build_match_conditions = build_match_conditions(
        DatabaseQuery.build_match_conditions
    )
    DatabaseQuery.get_permission_query_conditions = get_permission_query_conditions(
        DatabaseQuery.get_permission_query_conditions
    )


def build_match_conditions(_build_match_conditions):
    """
    Patch the db_query.build_match_conditions method to include shared documents when permission query conditions are present.

    Args:
        _build_match_conditions: Original build_match_conditions function from frappe.

    Returns:
        build_match_conditions: Patched build_match_conditions function.
    """

    def build_match_conditions(self, as_condition=True) -> str | list:
        """
        Patched version of build_match_conditions to account for shared documents.

        Args:
            as_condition: Boolean indicating whether to return result as a single SQL condition or a list.

        Returns:
            str | list: Conditions for the query.
        """
        # Retrieve permission query conditions if present
        doctype_conditions = self.get_permission_query_conditions()
        if doctype_conditions:
            # Fetch shared documents if conditions are present
            self._fetch_shared_documents = True

        return _build_match_conditions(self, as_condition)

    return build_match_conditions


def get_permission_query_conditions(_get_permission_query_conditions):

    def get_permission_query_conditions(self):

        if not self._get_permission_query_conditions:

            self._get_permission_query_conditions = _get_permission_query_conditions(
                self
            )

        return self._get_permission_query_conditions

    return get_permission_query_conditions
