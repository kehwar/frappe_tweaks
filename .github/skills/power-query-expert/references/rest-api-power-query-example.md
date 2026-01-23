# REST API Power Query Example

Power Query M code template for fetching all records from Frappe using the REST API with automatic pagination.

## Overview

This template provides a complete solution for fetching all records from any Frappe DocType with:
- **Automatic pagination** - Fetches all records across multiple pages
- **Filters** - Filter records server-side
- **Sorting** - Order results by any field
- **Custom fields** - Select specific fields to return
- **Link expansion** - Optionally expand linked documents

**Use this for datasets < 10,000 records.** For larger datasets or complex queries, use the [long-polling API](long-polling-power-query-example.md) instead.

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
    
    // Edit field list here
    FieldList = {
        "name",
        "party_name",
        "transaction_date",
        "grand_total",
        "status",
        "valid_till"
    },
    
    // Edit filters here: {field, operator, value}
    // Leave empty {} for no filters
    FilterList = {
        {"transaction_date", ">=", "2024-01-01"},
        {"docstatus", "=", "1"}
    },
    
    // Sort: "fieldname asc" or "fieldname desc"
    // Leave as "" for no sorting
    OrderBy = "transaction_date desc",
    
    PageSize = 100,
    // ====================================
    
    // Convert to JSON (don't edit below)
    Fields = "[" & Text.Combine(List.Transform(FieldList, each """" & _ & """"), ", ") & "]",
    Filters = if List.Count(FilterList) > 0 then
        "[" & Text.Combine(
            List.Transform(FilterList, each "[""" & _{0} & """, """ & _{1} & """, """ & _{2} & """]"),
            ", "
        ) & "]"
        else "",
    
    // Function to fetch a single page
    FetchPage = (StartIndex as number) =>
        let
            // Build base URL with fields
            BaseApiUrl = BaseUrl & "/api/resource/" & DocType 
                & "?fields=" & Uri.EscapeDataString(Fields)
                & "&limit_start=" & Number.ToText(StartIndex)
                & "&limit_page_length=" & Number.ToText(PageSize),
            
            // Add filters if provided
            UrlWithFilters = if Filters <> "" then
                BaseApiUrl & "&filters=" & Uri.EscapeDataString(Filters)
                else BaseApiUrl,
            
            // Add sorting if provided
            ApiUrl = if OrderBy <> "" then
                UrlWithFilters & "&order_by=" & Uri.EscapeDataString(OrderBy)
                else UrlWithFilters,
            
            Response = Json.Document(Web.Contents(ApiUrl)),
            
            Data = Response[data]
        in
            Data,
    
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
- Automatically fetches all records across multiple pages
- Supports filters, sorting, and custom fields
- Stops when fewer records than `PageSize` are returned

## How to Use This Template

### 1. Set Your DocType and Fields

Edit the configuration section at the top:

```fsharp
DocType = "Quotation",  // Change to your DocType

FieldList = {
    "name",
    "party_name",
    "transaction_date"
    // Add or remove fields as needed
},
```

### 2. Add Filters (Optional)

Use `{field, operator, value}` format:

```fsharp
FilterList = {
    {"transaction_date", ">=", "2024-01-01"},
    {"status", "=", "Open"}
},

// Or leave empty for no filters:
FilterList = {},
```

**Available operators:** `=`, `!=`, `>`, `<`, `>=`, `<=`, `like`, `in`, `not in`

### 3. Set Sorting (Optional)

```fsharp
OrderBy = "transaction_date desc",  // Sort descending
// or
OrderBy = "party_name asc",         // Sort ascending
// or
OrderBy = "",                        // No sorting
```

## Expanding Link Fields

To fetch full data from linked documents (e.g., expand `customer` to get customer details), add the link field name to your field list with special syntax:

### Example: Expand Customer Link

```fsharp
FieldList = {
    "name",
    "party_name",
    "customer.customer_name",      // Expands customer link
    "customer.customer_group",     // Gets customer's group
    "customer.territory",          // Gets customer's territory
    "transaction_date",
    "grand_total"
},
```

**Syntax:** `"linked_field.field_name"`

This is equivalent to using `expand_links=True` in the API, but gives you control over exactly which linked fields to fetch.

### Multiple Link Expansions

You can expand multiple link fields:

```fsharp
FieldList = {
    "name",
    "party_name",
    "customer.customer_name",
    "customer.territory",
    "sales_person.sales_person_name",  // Expand sales person
    "sales_person.commission_rate",
    "transaction_date",
    "grand_total"
},
```

**Note:** Each expanded field adds to response size and query time. Only expand what you need.

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

**Link fields not expanding:**
- Use dot notation: `"customer.customer_name"`
- Verify the link field exists and is accessible
- Check that linked document has the field you're requesting
