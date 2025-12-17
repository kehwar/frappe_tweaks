"""Sync Sync Job Type documents from JSON files"""

import os

import frappe
from frappe.modules.import_file import import_file_by_path
from frappe.utils import update_progress_bar


def sync_job_types(app_name=None):
    """
    Sync Sync Job Type documents from JSON files across all apps.
    
    Scans all installed apps (or specific app) for sync_job_type directories
    and imports any JSON files found, similar to how Frappe handles Report doctypes.
    
    Args:
        app_name: Optional app name to sync. If None, syncs all installed apps.
    """
    apps = [app_name] if app_name else frappe.get_installed_apps()
    files_to_import = []
    
    # Collect all sync job type JSON files
    for app in apps:
        try:
            app_modules = frappe.local.app_modules.get(app) or []
            
            for module_name in app_modules:
                try:
                    # Get module path
                    module = frappe.get_module(f"{app}.{module_name}")
                    module_path = os.path.dirname(module.__file__)
                    
                    # Check for sync_job_type directory
                    sync_job_type_path = os.path.join(module_path, "sync_job_type")
                    
                    if os.path.exists(sync_job_type_path) and os.path.isdir(sync_job_type_path):
                        # Scan for sync job type folders
                        for job_type_name in os.listdir(sync_job_type_path):
                            job_type_dir = os.path.join(sync_job_type_path, job_type_name)
                            
                            if os.path.isdir(job_type_dir):
                                # Look for JSON file
                                json_path = os.path.join(job_type_dir, f"{job_type_name}.json")
                                
                                if os.path.exists(json_path):
                                    files_to_import.append(json_path)
                
                except (ImportError, AttributeError) as e:
                    # Module doesn't exist or can't be imported, skip it
                    frappe.log_error(
                        title=f"Error scanning module {module_name} in app {app}",
                        message=str(e)
                    )
                    continue
        
        except Exception as e:
            # App error, log and continue
            frappe.log_error(
                title=f"Error scanning app {app} for Sync Job Types",
                message=str(e)
            )
            continue
    
    # Import collected files
    total = len(files_to_import)
    if total:
        for i, json_path in enumerate(files_to_import):
            try:
                import_file_by_path(
                    json_path,
                    force=False,
                    ignore_version=True,
                    reset_permissions=False
                )
                frappe.db.commit()
                
                # Show progress
                update_progress_bar("Syncing Sync Job Types", i, total)
            
            except Exception as e:
                # Log error but continue with other files
                frappe.log_error(
                    title=f"Error importing Sync Job Type from {json_path}",
                    message=str(e)
                )
                continue
        
        # Print newline after progress bar
        print()
