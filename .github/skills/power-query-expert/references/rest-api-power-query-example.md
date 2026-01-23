# REST API Power Query Example

Power Query M code examples for accessing Frappe document data using the REST API.

## Overview

Frappe's REST API provides direct access to DocType data without needing background jobs. Use this for:
- **Small datasets** (< 1000 records)
- **Single document reads**
- **Simple queries** with basic filters
- **Real-time data** that doesn't require heavy processing

For large or slow queries, use the [long-polling API](long-polling-power-query-example.md) instead.

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
5. Excel/Power BI will create header: `Authorization: Basic base64(api_key:api_secret)`

## Read Single Document

Fetch a single document by DocType and name.

**API Endpoint:** `GET /api/resource/:doctype/:name`

```fsharp
let
    BaseUrl = "https://your-site.frappe.cloud",
    DocType = "Item",
    DocumentName = "ITEM-001",
    
    ApiUrl = BaseUrl & "/api/resource/" & DocType & "/" & Uri.EscapeDataString(DocumentName),
    
    Response = Json.Document(Web.Contents(ApiUrl)),
    
    Data = Response[data],
    Table = Record.ToTable(Data)
in
    Table
```

**Result:** Two-column table with field names and values from the document.

### Expand Link Fields

Expand linked documents by adding `expand_links=True`:

```fsharp
let
    BaseUrl = "https://your-site.frappe.cloud",
    DocType = "Sales Order",
    DocumentName = "SO-00001",
    
    ApiUrl = BaseUrl & "/api/resource/" & DocType & "/" & Uri.EscapeDataString(DocumentName) & "?expand_links=True",
    
    Response = Json.Document(Web.Contents(ApiUrl)),
    
    Data = Response[data]
in
    Data
```

**Result:** Record with expanded link fields showing full linked document data.

## List Documents

Query multiple documents with filters, sorting, and pagination.

**API Endpoint:** `GET /api/resource/:doctype`

### Basic List

```fsharp
let
    BaseUrl = "https://your-site.frappe.cloud",
    DocType = "Item",
    
    ApiUrl = BaseUrl & "/api/resource/" & DocType,
    
    Response = Json.Document(Web.Contents(ApiUrl)),
    
    Data = Response[data],
    Table = Table.FromRecords(Data)
in
    Table
```

**Result:** Table with first 20 documents (only `name` field by default).

### Specify Fields

Select specific fields to return:

```fsharp
let
    BaseUrl = "https://your-site.frappe.cloud",
    DocType = "Item",
    
    // Specify fields as JSON array
    Fields = "[""item_code"", ""item_name"", ""item_group"", ""standard_rate""]",
    
    ApiUrl = BaseUrl & "/api/resource/" & DocType & "?fields=" & Uri.EscapeDataString(Fields),
    
    Response = Json.Document(Web.Contents(ApiUrl)),
    
    Data = Response[data],
    Table = Table.FromRecords(Data)
in
    Table
```
    Table = Table.FromRecords(Data)
in
    Table
```

**Result:** Table with specified fields only.

### Apply Filters

Filter records using Frappe's filter syntax: `[field, operator, value]`

```fsharp
let
    BaseUrl = "https://your-site.frappe.cloud",
    DocType = "Sales Invoice",
    
    Fields = "[""name"", ""customer"", ""posting_date"", ""grand_total"", ""status""]",
    
    // Filters: posting_date >= 2024-01-01 AND status = "Paid"
    Filters = "[[""posting_date"", "">="", ""2024-01-01""], [""status"", ""="", ""Paid""]]",
    
    ApiUrl = BaseUrl & "/api/resource/" & DocType 
        & "?fields=" & Uri.EscapeDataString(Fields)
        & "&filters=" & Uri.EscapeDataString(Filters),
    
    Response = Json.Document(Web.Contents(ApiUrl)),
    
    Data = Response[data],
    Table = Table.FromRecords(Data)
in
    Table
```

**Filter operators:**
- `=` - equals
- `!=` - not equals
- `>` - greater than
- `<` - less than
- `>=` - greater than or equal
- `<=` - less than or equal
- `like` - SQL LIKE pattern
- `in` - in list
- `not in` - not in list

### OR Filters

Use `or_filters` for OR logic:

```fsharp
let
    BaseUrl = "https://your-site.frappe.cloud",
    DocType = "Item",
    
    Fields = "[""item_code"", ""item_name"", ""item_group""]",
    
    // item_group = "Products" OR item_group = "Raw Materials"
    OrFilters = "[[""item_group"", ""="", ""Products""], [""item_group"", ""="", ""Raw Materials""]]",
    
    ApiUrl = BaseUrl & "/api/resource/" & DocType 
        & "?fields=" & Uri.EscapeDataString(Fields)
        & "&or_filters=" & Uri.EscapeDataString(OrFilters),
    
    Response = Json.Document(Web.Contents(ApiUrl)),
    
    Data = Response[data],
    Table = Table.FromRecords(Data)
in
    Table
```

### Sorting

Sort results with `order_by`:

```fsharp
let
    BaseUrl = "https://your-site.frappe.cloud",
    DocType = "Item",
    
    Fields = "[""item_code"", ""item_name"", ""standard_rate""]",
    
    // Sort by standard_rate descending
    OrderBy = "standard_rate desc",
    
    ApiUrl = BaseUrl & "/api/resource/" & DocType 
        & "?fields=" & Uri.EscapeDataString(Fields)
        & "&order_by=" & Uri.EscapeDataString(OrderBy),
    
    Response = Json.Document(Web.Contents(ApiUrl)),
    
    Data = Response[data],
    Table = Table.FromRecords(Data)
in
    Table
```

### Pagination

Use `limit_start` and `limit_page_length` for pagination:

```fsharp
let
    BaseUrl = "https://your-site.frappe.cloud",
    DocType = "Customer",
    
    Fields = "[""name"", ""customer_name"", ""customer_group""]",
    
    LimitStart = "0",      // Start at record 0
    LimitLength = "100",    // Fetch 100 records
    
    ApiUrl = BaseUrl & "/api/resource/" & DocType 
        & "?fields=" & Uri.EscapeDataString(Fields)
        & "&limit_start=" & LimitStart
        & "&limit_page_length=" & LimitLength,
    
    Response = Json.Document(Web.Contents(ApiUrl)),
    
    Data = Response[data],
    Table = Table.FromRecords(Data)
in
    Table
```

### Complete Example with All Parameters

```fsharp
let
    // Configuration
    BaseUrl = "https://your-site.frappe.cloud",
    DocType = "Sales Invoice",
    
    // Query parameters
    Fields = "[""name"", ""customer"", ""posting_date"", ""grand_total"", ""status""]",
    Filters = "[[""posting_date"", "">="", ""2024-01-01""], [""docstatus"", ""="", ""1""]]",
    OrderBy = "posting_date desc",
    LimitStart = "0",
    LimitLength = "500",
    
    // Build URL
    ApiUrl = BaseUrl & "/api/resource/" & DocType 
        & "?fields=" & Uri.EscapeDataString(Fields)
        & "&filters=" & Uri.EscapeDataString(Filters)
        & "&order_by=" & Uri.EscapeDataString(OrderBy)
        & "&limit_start=" & LimitStart
        & "&limit_page_length=" & LimitLength,
    
    // Make request (auth handled automatically by Excel/Power BI)
    Response = Json.Document(Web.Contents(ApiUrl)),
    
    // Extract data
    Data = Response[data],
    Table = Table.FromRecords(Data),
    
    // Apply column types
    TypedTable = Table.TransformColumnTypes(
        Table,
        {
            {"name", type text},
            {"customer", type text},
            {"posting_date", type date},
            {"grand_total", Currency.Type},
            {"status", type text}
        }
    )
in
    TypedTable
```

## Fetching All Records with Pagination

For DocTypes with many records, use pagination to fetch all data:

```fsharp
let
    BaseUrl = "https://your-site.frappe.cloud",
    DocType = "Item",
    Fields = "[""item_code"", ""item_name"", ""item_group""]",
    PageSize = 100,
    
    // Function to fetch a single page
    FetchPage = (StartIndex as number) =>
        let
            ApiUrl = BaseUrl & "/api/resource/" & DocType 
                & "?fields=" & Uri.EscapeDataString(Fields)
                & "&limit_start=" & Number.ToText(StartIndex)
                & "&limit_page_length=" & Number.ToText(PageSize),
            
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

**Note:** This recursive approach works for moderate datasets. For very large datasets (> 10,000 records), consider using the long-polling API instead.

## Child Table Data

Frappe doesn't provide direct REST endpoints for child tables. To fetch child table data:

**Option 1: Read parent document with expand**

```fsharp
// Fetches parent with all child tables included
GET /api/resource/Sales Order/SO-00001?expand_links=True
```

**Option 2: Use a custom whitelisted method**

Create a custom Python method to return child table data and call it via `/api/method/`.

## Comparison: REST API vs Long-Polling API

| Feature | REST API | Long-Polling API |
|---------|----------|------------------|
| **Best for** | < 1000 records, < 30s | > 1000 records, heavy queries |
| **Timeout risk** | High for large datasets | None (background execution) |
| **Real-time** | Immediate response | Polling delay (seconds) |
| **Column metadata** | No automatic metadata | Yes, includes field types |
| **Complexity** | Simple, direct calls | More complex (3-step workflow) |
| **Filters** | Basic (field operators) | Full report filter support |
| **Background workers** | Not required | Required |

**Rule of thumb:**
- REST API: Quick lookups, small lists, single documents
- Long-Polling API: Reports, large exports, complex aggregations

## Error Handling

```fsharp
let
    BaseUrl = "https://your-site.frappe.cloud",
    DocType = "Item",
    
    ApiUrl = BaseUrl & "/api/resource/" & DocType,
    
    Response = try 
        Json.Document(Web.Contents(ApiUrl))
    otherwise null,
    
    Data = if Response <> null and Record.HasFields(Response, "data") 
        then Response[data] 
        else [],
    
    Table = if List.Count(Data) > 0 
        then Table.FromRecords(Data) 
        else #table({"name"}, {})
in
    Table
```

## Best Practices

### 1. Limit Fields
Only request fields you need to reduce response size and improve performance:
```fsharp
Fields = "[""name"", ""item_code"", ""item_name""]"  // Good
Fields = "[]"  // Fetches all fields - avoid unless needed
```

### 2. Use Filters Server-Side
Filter on the server rather than in Power Query:
```fsharp
// Good - filters on server
Filters = "[[""item_group"", ""="", ""Products""]]"

// Bad - fetches everything then filters in Power Query
```

### 3. Page Large Datasets
Don't fetch thousands of records in one call:
```fsharp
limit_page_length = "100"  // Good for most cases
limit_page_length = "10000"  // May timeout or consume too much memory
```

### 4. Cache-Bust When Needed
For data that changes frequently, add timestamps:
```fsharp
ApiUrl & "&_ts=" & Number.ToText(DateTime.LocalNow())
```

### 5. Credentials Are Managed by Excel/Power BI
Excel and Power BI handle authentication through their built-in forms - no need to hardcode credentials in M code.

## Resources

- **Frappe REST API Docs**: https://docs.frappe.io/framework/user/en/api/rest
- **Long-Polling API**: [long-polling-power-query-example.md](long-polling-power-query-example.md)
- **Troubleshooting**: [troubleshooting.md](troubleshooting.md)
