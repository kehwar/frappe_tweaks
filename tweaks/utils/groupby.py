from collections import defaultdict
from typing import Any, Callable, Dict, List, Optional, Tuple

import frappe

Number = (int, float)


def get_nested_value(obj: Dict[str, Any], path: str) -> Any:
    """
    Get nested value from dict using dot notation.
    Example: get_nested_value({"user": {"name": "John"}}, "user.name") -> "John"
    """
    if "." not in path:
        return obj.get(path)

    keys = path.split(".")
    current = obj

    for key in keys:
        if isinstance(current, dict) and key in current:
            current = current[key]
        else:
            return None

    return current


@frappe.whitelist()
def group_aggregate(
    rows: List[Dict[str, Any]],
    group_fields: List[str],
    aggregations: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Group and aggregate a list of dict rows.

    Params:
      rows: list of dicts
      group_fields: ordered list of fields to group by (e.g., ["country", "city", "user.name"])
        - Supports dot notation for nested fields (e.g., "user.profile.name")
      aggregations: list of { "op": "sum|count|average", "field": <str or None>, "name": <optional str> }
        - For "count", "field" may be None. Count is number of rows in the group.
        - "name" optional; default uses the field name.
        - Fields support dot notation for nested properties (e.g., "sales.amount")

    Returns:
      A dict with:
        {
          "group": [],  # root level has empty group
          "aggregations": [ [name, value], ... ],
          "level": int,  # depth level in the grouping hierarchy (0 = root)
          "index_in_parent": int,  # 0-based index of this node among its siblings
          "count_in_parent": int,  # total count of siblings at this level
          "groups": [ ... ] or "rows": [...]
        }
    """

    def aggr_name(spec: Dict[str, Any]) -> str:
        if "name" in spec and spec["name"]:
            return spec["name"]
        return spec.get("field")

    def compute_aggrs(group_rows: List[Dict[str, Any]]) -> List[Tuple[str, Any]]:
        out: List[Tuple[str, Any]] = []
        # Precompute counts to support avg
        n = len(group_rows)
        for spec in aggregations:
            op = spec["op"]
            field = spec.get("field")
            name = aggr_name(spec)

            if op == "count":
                # If a field is provided, you could choose to count non-null values.
                # Here we count all rows for simplicity.
                value = n
            elif op == "sum":
                if field is None:
                    raise ValueError("sum requires 'field'")
                total = 0.0
                for r in group_rows:
                    v = get_nested_value(r, field)
                    if isinstance(v, Number):
                        total += float(v)
                value = total
            elif op == "average":
                if field is None:
                    raise ValueError("average requires 'field'")
                total = 0.0
                count = 0
                for r in group_rows:
                    v = get_nested_value(r, field)
                    if isinstance(v, Number):
                        total += float(v)
                        count += 1
                value = (total / count) if count > 0 else None
            else:
                raise ValueError(f"Unsupported op: {op}")
            out.append((name, value))
        return out

    def recurse(
        level: int,
        parent_group_vals: List[Any],
        subset: List[Dict[str, Any]],
        index_in_parent: int = 0,
        count_in_parent: int = 1,
    ) -> Dict[str, Any]:
        node = {
            "group": parent_group_vals,
            "aggregations": compute_aggrs(subset),
            "level": level,
            "index_in_parent": index_in_parent,
            "count_in_parent": count_in_parent,
        }

        if level >= len(group_fields):
            node["rows"] = subset
            return node

        key = group_fields[level]
        buckets: Dict[Any, List[Dict[str, Any]]] = defaultdict(list)
        for r in subset:
            buckets[get_nested_value(r, key)].append(r)

        # Keep stable order by sorting on the key if it’s sortable; otherwise leave insertion order
        try:
            keys_sorted = sorted(buckets.keys(), key=lambda x: (x is None, x))
        except TypeError:
            # Mixed incomparable types; fallback to insertion order
            keys_sorted = list(buckets.keys())

        child_count = len(keys_sorted)
        node["groups"] = [
            recurse(level + 1, parent_group_vals + [k], buckets[k], idx, child_count)
            for idx, k in enumerate(keys_sorted)
        ]
        return node

    return recurse(0, [], rows)
