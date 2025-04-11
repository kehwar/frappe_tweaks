from tweaks.custom.doctype.client_script import apply_client_script_patches
from tweaks.custom.doctype.document import apply_document_patches
from tweaks.custom.doctype.server_script_customization import (
    apply_server_script_patches,
)
from tweaks.custom.doctype.workflow import apply_workflow_patches
from tweaks.custom.utils.db_query import apply_db_query_patches
from tweaks.custom.utils.fixtures import apply_fixtures_patches
from tweaks.custom.utils.safe_exec import apply_safe_exec_patches
from tweaks.custom.utils.authentication import apply_authentication_patches


def apply_patches():

    apply_authentication_patches()
    apply_client_script_patches()
    apply_db_query_patches()
    apply_document_patches()
    apply_fixtures_patches()
    apply_safe_exec_patches()
    apply_server_script_patches()
    apply_workflow_patches()
