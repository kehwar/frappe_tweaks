# AC Resource Rules Report

## Overview

This report provides a matrix view of user permissions for a specific AC Resource. It shows which users have access to which AC Rules and what actions they are allowed to perform.

## Features

- **Resource Selection**: Required filter to select the AC Resource to analyze
- **User Filtering**: Optional Query Filter to narrow down which users to display
- **Matrix View**: Shows users as rows and AC Rules as columns
- **Visual Indicators**: Uses emojis to distinguish between Permit (✅) and Forbid (🚫) rules
- **Action Display**: Shows allowed actions as a comma-separated list in each cell

## Usage

1. Navigate to **Reports > AC Resource Rules**
2. Select an **AC Resource** from the dropdown (required)
3. Optionally select a **User Filter** to filter which users are displayed
   - The User Filter must be a Query Filter with reference doctype: User, User Group, Role, or Role Profile
4. Click **Refresh** to generate the report

## Report Structure

### Columns

- **User**: The user's name (linked to User doctype)
- **AC Rule Columns**: One column per AC Rule associated with the selected resource
  - Column names include an emoji (✅ for Permit, 🚫 for Forbid) followed by the rule title
  - Each column shows the actions allowed by that rule for that user

### Rows

- One row per user (filtered by the optional Query Filter if provided)
- Shows which AC Rules apply to each user and what actions are permitted

### Cell Values

- **Empty**: User does not match the principals of that AC Rule
- **Action List**: Comma-separated list of actions (e.g., "Read, Write, Create") if the user matches the rule's principals

## Example

If you have:
- AC Resource: "Customer" 
- AC Rules:
  - "Sales Team Read" (Permit) - allows Read action for sales team users
  - "Manager Full Access" (Permit) - allows Read, Write, Create, Delete for managers
  - "Restrict Archived" (Forbid) - denies access to archived customers

The report will show:
- One column for each rule (✅ Sales Team Read, ✅ Manager Full Access, 🚫 Restrict Archived)
- One row per user
- In each cell, the actions that user has for that rule

## Implementation Details

The report:
1. Loads all AC Rules for the selected resource (excluding disabled rules and rules outside their valid date range)
2. Gets the list of users (all enabled users, or filtered by the Query Filter)
3. For each user and each rule, evaluates the principal filters to determine if the user matches
4. Displays the actions allowed by each rule for users who match the principals

## Notes

- Only enabled AC Rules are shown
- AC Rules must be within their valid date range (valid_from/valid_upto)
- Only enabled users are displayed
- If no Query Filter is selected, all enabled users are shown
- The report respects the AC Rule's principal exception logic (allowed principals minus denied principals)
