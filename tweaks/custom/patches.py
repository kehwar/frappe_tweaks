from tweaks.custom.doctype.document import apply_document_patches
from tweaks.custom.doctype.server_script_customization import (
    apply_server_script_patches,
)
from tweaks.custom.doctype.workflow import apply_workflow_patches


def apply_patches():

    apply_document_patches()
    apply_server_script_patches()
    apply_workflow_patches()
