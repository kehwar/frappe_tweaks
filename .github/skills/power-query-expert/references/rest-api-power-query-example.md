# REST API Power Query Example

Power Query M code template for fetching all records from Frappe using the Report View API with automatic pagination.

## Overview

This template provides a complete solution for fetching all records from any Frappe DocType with:
- **Automatic pagination** - Fetches all records across multiple pages
- **Filters** - Filter records server-side
- **Sorting** - Order results by any field
- **Custom fields** - Select specific fields to return
- **Child table fields** - Access child table data directly in results
- **Link expansion** - Optionally expand linked documents

**Use this for datasets < 10,000 records.** For larger datasets or complex queries, use the [long-polling API](long-polling-power-query-example.md) instead.

**Note:** This uses `frappe.desk.reportview.get` which returns a compressed format (`keys` and `values`). The M code automatically expands this into a proper table.

## Authentication

Authentication is handled automatically by Excel and Power BI through their built-in authentication forms:

- **Username/Password**: Use your Frappe account credentials
- **API Key/Token**: Enter API Key as username, API Secret as password

Excel/Power BI automatically adds the `Authorization` header using **HTTP Basic Authentication** format: `Authorization: Basic base64(username:password)`. Frappe's API accepts this format alongside its native token format.

**Do not include authentication headers in your M code** - they are added automatically by Excel/Power BI.

### Create API Keys in Frappe

1. Go to User → API Access
2. Click "Generate Keys"
3. Copy API Key and Secret
4. When Excel/Power BI prompts for credentials, enter:
   - **Username**: Your API Key
   - **Password**: Your API Secret
5. Complete Template: Fetch

## Fetching All Records with Pagination

```fsharp
let
    // ========== CONFIGURATION ==========
    BaseUrl = "https://your-site.frappe.cloud",
    DocType = "Quotation",
    
    // OPTIONAL: Set if you want to include child table fields
    // Leave as "" to only query parent fields
    ChildDocType = "Quotation Item",
    
    // Fields: {DocType or ChildDocType, FieldName}
    FieldList = {
        {DocType, "name"},
        {DocType, "party_name"},
        {DocType, "transaction_date"},
        {DocType, "grand_total"},
        {DocType, "status"},
        {DocType, "valid_till"},
        // Child table fields (optional - only if ChildDocType is set)
        {ChildDocType, "item_code"},
        {ChildDocType, "qty"},
        {ChildDocType, "rate"},
        {ChildDocType, "amount"}
    },
    
    // Filters: {DocType, Field, Operator, Value}
    // Use DocType for parent, ChildDocType for child fields
    // Leave empty {} for no filters
    FilterList = {
        {DocType, "transaction_date", ">=", "2026-01-15"},
        {DocType, "docstatus", "=", "1"}
        // Filter by child field:
        // {ChildDocType, "item_code", "=", "ITEM-001"}
    },
    
    // Sort: List of {DocType or ChildDocType, FieldName, "asc" or "desc"}
    // Leave as {} for no sorting
    OrderByList = {
        {DocType, "transaction_date", "desc"}
        // Add more sort fields if needed:
        // {DocType, "name", "asc"}
    },
    
    PageSize = 100,
    // ====================================
    
    // Format OrderBy clauses
    OrderByClause = if List.Count(OrderByList) > 0 then
        Text.Combine(
            List.Transform(
                OrderByList,
                each "`tab" & _{0} & "`.`" & _{1} & "` " & _{2}
            ),
            ", "
        )
        else "",
    
    // Helper function to format field with backticks and alias
    FormatField = (fieldDef as list) as text =>
        let
            doctype = fieldDef{0},
            fieldname = fieldDef{1},
            
            // Format: `tabDocType`.`fieldname`
            fullField = "`tab" & doctype & "`.`" & fieldname & "`",
            
            // Add alias for child tables
            withAlias = if doctype <> DocType then
                fullField & " as '" & doctype & ":" & fieldname & "'"
                else fullField
        in
            withAlias,
    
    // Convert fields to JSON array
    Fields = "[" & Text.Combine(
        List.Transform(FieldList, each """" & FormatField(_) & """"),
        ", "
    ) & "]",
    
    // Convert filters to JSON array
    Filters = if List.Count(FilterList) > 0 then
        "[" & Text.Combine(
            List.Transform(FilterList, 
                each "[""" & _{0} & """, """ & _{1} & """, """ & _{2} & """, """ & Text.From(_{3}) & """]"
            ),
            ", "
        ) & "]"
        else "[]",
    
    // Function to fetch a single page using reportview.get
    FetchPage = (StartIndex as number) =>
        let
            // Build API URL for frappe.desk.reportview.get
            ApiUrl = BaseUrl & "/api/method/frappe.desk.reportview.get"
                & "?doctype=" & Uri.EscapeDataString(DocType)
                & "&fields=" & Uri.EscapeDataString(Fields)
                & "&filters=" & Uri.EscapeDataString(Filters)
                & "&start=" & Number.ToText(StartIndex)
                & "&page_length=" & Number.ToText(PageSize)
                & "&view=Report"
                & (if OrderByClause <> "" then "&order_by=" & Uri.EscapeDataString(OrderByClause) else ""),
            
            Response = Json.Document(Web.Contents(ApiUrl)),
            
            // Handle compressed response format
            Message = Response[message],
            Keys = Message[keys],
            Values = Message[values],
            
            // Convert compressed format to records
            Records = List.Transform(
                Values,
                each Record.FromList(_, Keys)
            )
        in
            Records,
    
    // Fetch all pages recursively
    FetchAllPages = (StartIndex as number) as list =>
        let
            CurrentPage = FetchPage(StartIndex),
            NextPages = if List.Count(CurrentPage) = PageSize 
                then @FetchAllPages(StartIndex + PageSize) 
                else {}
        in
            List.Combine({CurrentPage, NextPages}),
    
    AllData = FetchAllPages(0),
    Table = Table.FromRecords(AllData)
in
    Table
```

**How it works:**
- Uses `frappe.desk.reportview.get` which supports child table fields
- Properly formats fields with backticks: `` `tabDocType`.`fieldname` ``
- Adds aliases for child table fields to match Frappe's format
- Automatically decompresses the response format (`keys` + `values` → records)
- Fetches all records across multiple pages
- Stops when fewer records than `PageSize` are returned

## How to Use This Template

### 1. Set Your DocType and Fields

Edit the configuration section at the top:

```fsharp
DocType = "Quotation",  // Change to your DocType

// OPTIONAL: Set only if you want child table fields
ChildDocType = "Quotation Item",  // Or "" to skip child table

// Fields: {DocType or ChildDocType, FieldName}
FieldList = {
    {DocType, "name"},
    {DocType, "party_name"},
    {DocType, "transaction_date"},
    {DocType, "grand_total"},
    // Child table fields (optional)
    {ChildDocType, "item_code"},
    {ChildDocType, "qty"},
    {ChildDocType, "rate"}
},
```

**Note:** When including child table fields, you'll get one row per child record. For example, a Quotation with 3 items will return 3 rows with the parent data duplicated.

### 2. Add Filters (Optional)

Use `{DocType, field, operator, value}` format. Use `DocType` for parent fields or `ChildDocType` for child fields:

```fsharp
FilterList = {
    {DocType, "transaction_date", ">=", "2024-01-01"},
    {DocType, "status", "=", "Open"},
    // Filter by child table field
    {ChildDocType, "item_code", "=", "ITEM-001"}
},

// Or leave empty for no filters:
FilterList = {},
```

**Filter Format:** `{DocType or ChildDocType, FieldName, Operator, Value}`

**Available operators:** `=`, `!=`, `>`, `<`, `>=`, `<=`, `like`, `in`, `not in`

### 3. Set Sorting (Optional)

Use a list of `{DocType or ChildDocType, FieldName, "asc" or "desc"}` tuples. You can specify multiple sort fields:

```fsharp
OrderByList = {
    {DocType, "transaction_date", "desc"},     // Primary sort
    {DocType, "name", "asc"}                    // Secondary sort
},
// or single sort:
OrderByList = {
    {ChildDocType, "qty", "asc"}
},
// or no sorting:
OrderByList = {},
```

**Sort Format:** `{DocType or ChildDocType, FieldName, Direction}`

**Direction:** `"asc"` (ascending) or `"desc"` (descending)

**Multiple sorts:** Add multiple tuples to sort by multiple fields. First tuple is primary sort, second is secondary, etc.

## Accessing Child Table Fields

To include child table fields, set `ChildDocType` and add field names to `ChildFields`.

### Example: Sales Order with Items

```fsharp
DocType = "Sales Order",
ChildDocType = "Sales Order Item",

FieldList = {
    {DocType, "name"},
    {DocType, "customer"},
    {DocType, "transaction_date"},
    {DocType, "grand_total"},
    {ChildDocType, "item_code"},
    {ChildDocType, "qty"},
    {ChildDocType, "rate"},
    {ChildDocType, "amount"}
},
```

**Important:** When you include child table fields:
- You get **one row per child record**
- A Sales Order with 3 items returns **3 rows**
- Parent fields are duplicated across rows
- This is a LEFT JOIN, so orders with no items return 1 row with null child values

### Filtering by Child Table Fields

Use `ChildDocType` in your filters:

```fsharp
FilterList = {
    {DocType, "transaction_date", ">=", "2024-01-01"},
    {ChildDocType, "item_code", "=", "ITEM-001"}  // Filter by child field
},
```

### Querying Only Parent Fields

To query without child tables, just set `ChildDocType = ""` and only use `DocType` in your field list:

```fsharp
DocType = "Sales Order",
ChildDocType = "",  // No child table

FieldList = {
    {DocType, "name"},
    {DocType, "customer"},
    {DocType, "transaction_date"},
    {DocType, "grand_total"}
    // No ChildDocType fields
},
```

## Expanding Link Fields

To fetch data from linked documents, you need to use the Link doctype and its fields.

### Example: Expand Customer Link

```fsharp
FieldList = {
    {"Quotation", "name", null},
    {"Quotation", "party_name", null},
    {"Quotation", "customer", null},           // Link field itself
    {"Customer", "customer_name", "Customer Name"},  // Expanded field
    {"Customer", "customer_group", "Customer Group"},
    {"Customer", "territory", "Territory"},
    {"Quotation", "transaction_date", null},
    {"Quotation", "grand_total", null}
},
```

**Note:** The link field (e.g., `customer`) must exist in the parent DocType's schema for the expansion to work.

### Combining Child Tables and Link Expansion

You can use both child table fields and link expansion together:

```fsharp
FieldList = {
    // Parent fields
    {"Quotation", "name", null},
    {"Quotation", "customer", null},
    
    // Expand parent link
    {"Customer", "customer_name", "Customer Name"},
    {"Customer", "territory", "Territory"},
    
    // Child table fields
    {"Quotation Item", "item_code", "Item Code"},
    {"Quotation Item", "qty", "Qty"},
    {"Quotation Item", "rate", "Rate"},
    
    // Expand link in child table
    {"Item", "item_name", "Item Name"},
    {"Item", "item_group", "Item Group"}
},
```

**Note:** Each expanded field and child table join adds to response size and query time. Only include what you need.

## Performance Tips

1. **Limit Fields**: Only request fields you need - this significantly reduces data transfer and improves speed

2. **Use Filters**: Filter on the server, not in Power Query - this reduces the number of records fetched

3. **Adjust PageSize**: 
   - Smaller pages (50-100): Better for slower connections
   - Larger pages (200-500): Faster for good connections, but may timeout on slow queries

4. **Avoid Over-Expansion**: Expanding many link fields increases query complexity - only expand what you need

5. **For Large Datasets**: If you have > 10,000 records, consider using the [long-polling API](long-polling-power-query-example.md) instead

## Troubleshooting

**Query times out:**
- Reduce `PageSize` to 50 or lower
- Add more specific filters to reduce total records
- Consider using long-polling API for heavy queries

**Missing data:**
- Verify field names match exactly (case-sensitive)
- Check filter syntax: `{field, operator, value}`
- Ensure you have permission to access the DocType

**Child table fields not showing:**
- Make sure `ChildDocType` is set correctly
- Use `{ChildDocType, "field_name"}` format in `FieldList`
- Remember: Including child fields returns one row per child record
- Verify the child table field exists and is accessible

**Link fields not expanding:**
- Specify the linked DocType: `{"Customer", "customer_name", "Customer Name"}`
- The link field itself must exist in the main DocType
- Check that linked document has the field you're requesting

**Getting error "Invalid field name":**
- Check for typos in field names (case-sensitive)
- Ensure you're using the correct DocType name
- Verify you have read permission on the fields you're requesting

**Sort not working:**
- Use format: `{DocType, "fieldname", "asc"}` or `{DocType, "fieldname", "desc"}`
- Example: `OrderByList = {{DocType, "transaction_date", "desc"}}`
- Make sure direction is `"asc"` or `"desc"` (lowercase, in quotes)
- For multiple sorts, add more tuples: `{{DocType, "date", "desc"}, {DocType, "name", "asc"}}`
