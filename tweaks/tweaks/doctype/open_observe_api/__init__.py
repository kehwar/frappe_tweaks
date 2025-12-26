# Copyright (c) 2025, Erick W.R. and contributors
# For license information, please see license.txt

from .open_observe_api import OpenObserveAPI, search_logs, send_logs, test_connection

__all__ = ["OpenObserveAPI", "send_logs", "search_logs", "test_connection"]
