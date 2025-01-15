from tweaks.custom.utils.fixtures import apply_fixtures_patches
from tweaks.custom.utils.safe_exec import apply_safe_exec_patches


def apply_patches():

    apply_fixtures_patches()
    apply_safe_exec_patches()
