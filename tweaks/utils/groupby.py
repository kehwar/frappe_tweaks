from collections import defaultdict
from typing import Any, Callable, Dict, List, Optional, Tuple

import frappe

Number = (int, float)


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
      group_fields: ordered list of fields to group by (e.g., ["country", "city"])
      aggregations: list of { "op": "sum|count|avg", "field": <str or None>, "name": <optional str> }
        - For "count", "field" may be None. Count is number of rows in the group.
        - "name" optional; default generated as "<op>(<field>)" or "count(*)".

    Returns:
      A dict with:
        {
          "group": [],  # root level has empty group
          "aggregations": [ [name, value], ... ],
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
                    v = r.get(field)
                    if isinstance(v, Number):
                        total += float(v)
                value = total
            elif op == "average":
                if field is None:
                    raise ValueError("average requires 'field'")
                total = 0.0
                count = 0
                for r in group_rows:
                    v = r.get(field)
                    if isinstance(v, Number):
                        total += float(v)
                        count += 1
                value = (total / count) if count > 0 else None
            else:
                raise ValueError(f"Unsupported op: {op}")
            out.append((name, value))
        return out

    def recurse(
        level: int, parent_group_vals: List[Any], subset: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        node = {
            "group": parent_group_vals,
            "aggregations": compute_aggrs(subset),
        }

        if level >= len(group_fields):
            node["rows"] = subset
            return node

        key = group_fields[level]
        buckets: Dict[Any, List[Dict[str, Any]]] = defaultdict(list)
        for r in subset:
            buckets[r.get(key)].append(r)

        # Keep stable order by sorting on the key if it’s sortable; otherwise leave insertion order
        try:
            keys_sorted = sorted(buckets.keys(), key=lambda x: (x is None, x))
        except TypeError:
            # Mixed incomparable types; fallback to insertion order
            keys_sorted = list(buckets.keys())

        node["groups"] = [
            recurse(level + 1, parent_group_vals + [k], buckets[k]) for k in keys_sorted
        ]
        return node

    return recurse(0, [], rows)
