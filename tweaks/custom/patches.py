from tweaks.custom.utils.fixtures import apply_fixtures_patches
from tweaks.custom.utils.safe_exec import apply_safe_exec_patches
from tweaks.tweaks.doctype.event_script.event_script import apply_event_script_patches


def apply_patches():

    apply_event_script_patches()
    apply_fixtures_patches()
    apply_safe_exec_patches()
