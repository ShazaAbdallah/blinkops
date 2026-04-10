# TicketForge CLI

A command-line interface for managing tickets with TicketForge, a lightweight project management tool. This application allows you to create, list, update, and delete tickets directly from your terminal.

## Features

### Core Functionality
- ✅ **Setup**: Configure your TicketForge connection with credentials  
- ✅ **Login**: Test connectivity to TicketForge server
- ✅ **List Tickets**: View all your tickets with pagination support
- ✅ **Get Ticket**: Retrieve details of a specific ticket
- ✅ **Create Tickets**: Create new tickets via API
- ✅ **Update Tickets**: Modify ticket properties (title, description, stage, custom fields)
- ✅ **Delete Tickets**: Remove tickets via API
- ✅ **Custom Fields**: Create and manage custom fields, add values to tickets
- ✅ **Dependencies**: Set dependencies between tickets

### Enhancements Beyond Core Requirements
- 🎨 **Colored Output**: Beautiful ANSI color formatting for better readability
- 📊 **Multiple Output Formats**: Table view and JSON output options
- 📄 **Pagination Support**: `--limit` and `--skip` parameters for managing large lists
- 💾 **Config Persistence**: Save credentials locally for convenience (stored in `~/.ticketforge/config.json`)
- 📋 **Formatted Tickets**: Well-structured display of ticket information
- ⚠️ **Error Handling**: Clear error messages for API failures
- 🔄 **Rate Limit Handling**: Respects API rate limits (50 requests/minute)
- 🧪 **Unit Tests**: Comprehensive test suite for core functionality
- 🔗 **Dependency Management**: Set and manage ticket dependencies

## Installation

### Prerequisites
- Python 3.8 or higher
- pip (Python package manager)

### Setup Steps

1. **Clone or download the project**:
```bash
cd /path/to/ticketforge
```

2. **Create a virtual environment** (recommended):
```bash
python3 -m venv venv
source venv/bin/activate  # On macOS/Linux
# or
venv\Scripts\activate  # On Windows
```

3. **Install dependencies**:
```bash
pip install requests
```

## Usage

### Initial Setup

#### Option 1: Create a new account
Register a new user account:
```bash
python3 ticketforge.py register --username newuser --password mypassword
```

Then configure the CLI with your credentials:
```bash
python3 ticketforge.py setup --base-url https://integrations-assignment-ticketforge.vercel.app --username newuser --password mypassword
```

#### Option 2: Use existing credentials
Configure with existing account:
```bash
python3 ticketforge.py setup \
  --base-url https://integrations-assignment-ticketforge.vercel.app \
  --username user1 \
  --password qwe123
```

After setup, credentials are saved locally and you don't need to provide them again.

### Command Reference

#### 1. Register a New Account
Create a new user account:
```bash
python3 ticketforge.py register --username newuser --password mypassword
```

**Output:**
```
✓ User registered successfully!
Username: newuser
User ID: cmnsz2tfi000m8axk63ilr3li
Created: 2026-04-10T13:59:34.783Z

You can now login with these credentials:
  python3 ticketforge.py setup --base-url https://integrations-assignment-ticketforge.vercel.app --username newuser --password mypassword
```

#### 2. Test Connection
Verify that your credentials work:
```bash
python3 ticketforge.py login
```

**Output:**
```
✓ Connected successfully to TicketForge
```

#### 2. List Tickets
View all your tickets:
```bash
python3 ticketforge.py list
```

With pagination:
```bash
python3 ticketforge.py list --limit 10 --skip 5
```

JSON output:
```bash
python3 ticketforge.py list --format json
```

#### 3. Get Ticket Details
Retrieve a specific ticket:
```bash
python3 ticketforge.py get TF-244
```

As JSON:
```bash
python3 ticketforge.py get TF-244 --format json
```

#### 4. Create a Ticket
Create a new ticket:
```bash
python3 ticketforge.py create --title "Bug in login flow" --description "Users cannot log in with special characters"
```

Create a ticket with custom fields:
```bash
python3 ticketforge.py create --title "Critical Bug" --description "Needs urgent fix" --custom priority=High status=Urgent
```

Create a ticket with dependencies:
```bash
python3 ticketforge.py create --title "Feature Task" --description "Implement new feature" --depends-on TF-244 TF-245
```

Create a ticket with all options:
```bash
python3 ticketforge.py create --title "Complex Task" --description "Full example" --depends-on TF-240 --custom priority=High
```

#### 5. Update a Ticket
Update an existing ticket:
```bash
python3 ticketforge.py update TF-244 --title "Updated Title" --stage closed
```

Update custom field values:
```bash
python3 ticketforge.py update TF-244 --title "Updated Title" --custom priority=Medium
```

#### 6. Delete a Ticket
Remove a ticket:
```bash
python3 ticketforge.py delete TF-244
```

#### 7. Manage Custom Fields
List all custom fields defined for your account:
```bash
python3 ticketforge.py fields list
```

Create a new custom field:
```bash
python3 ticketforge.py fields create --name priority --label "Priority" --type text
```

Update a custom field label:
```bash
python3 ticketforge.py fields update priority --label "Task Priority"
```

Delete a custom field:
```bash
python3 ticketforge.py fields delete priority
```

### Using Different Credentials

Override saved credentials at any time:
```bash
python3 ticketforge.py --username otheruser --password pass123 list
```

Or override just the base URL:
```bash
python3 ticketforge.py --base-url https://custom-url.com login
```

## Output Examples

### List Tickets (Table Format)
```
Your Tickets:

Ref    | Title        | Stage 
------------------------------
TF-244 | first ticket | open  
TF-243 | assignment 2 | review
TF-242 | assignment 1 | open  

Total: 3 ticket(s)
```

### Get Ticket Details
```
Ref: TF-244
Title: first ticket
Stage: open
Description: jgjah
Created: 2026-04-10T12:16:10.707Z
Updated: 2026-04-10T12:16:42.826Z
```

### Create Ticket Response
```
✓ Ticket created successfully!
Ticket Ref: TF-246

{
  "ref": "TF-246",
  "title": "CLI Test Ticket #2",
  "description": "Testing create with updated endpoint",
  "stage": "open",
  "created": "2026-04-10T13:45:29.262Z",
  "customFields": {
    "priority": "4"
  }
}
```

### Update Ticket Response
```
✓ Ticket updated successfully!

{
  "ref": "TF-246",
  "title": "Updated Title - Modified via API",
  "description": "Updated description from CLI",
  "stage": "review",
  "created": "2026-04-10T13:45:29.262Z",
  "updated": "2026-04-10T13:45:41.059Z",
  "dependsOn": ["TF-244"],
  "customFields": {"priority": "3"}
}
```

### Delete Ticket Response
```
✓ Ticket deleted successfully!
```

## API Endpoints Discovered

Through reverse engineering the web application using browser network inspection (HAR analysis), the following REST API endpoints were discovered and tested:

**Ticket Operations:**
- `GET /api/tforge/workitems/mine` - List user's tickets (with pagination)
- `GET /api/tforge/workitem/{ref}?view=deep` - Get specific ticket details
- `POST /api/tforge/workitem/publish` - Create a new ticket
- `PUT /api/tforge/workitem/{ref}` - Update an existing ticket
- `DELETE /api/tforge/workitem/{ref}` - Delete a ticket

**Custom Fields:**
- `GET /api/tforge/custom-fields` - List all custom field definitions
- `POST /api/tforge/custom-fields` - Create a new custom field definition
- `DELETE /api/tforge/custom-fields/{id}` - Delete a custom field definition

**User Operations:**
- `POST /api/tforge/user/register` - Register a new user account

**Rate Limiting:**
- 50 requests per minute per API
- Returns `x-ratelimit-limit`, `x-ratelimit-remaining`, and `x-ratelimit-reset` headers

## Configuration

Credentials are stored in `~/.ticketforge/config.json`:

```json
{
  "base_url": "https://integrations-assignment-ticketforge.vercel.app",
  "username": "user1",
  "password": "qwe123"
}
```

You can delete this file to reset your configuration.

## Error Handling

The application handles common errors gracefully:

- **Connection Errors**: Displays network failure messages
- **Authentication Errors**: Shows 401/403 status with details
- **Invalid Requests**: Provides the error message from the server
- **Timeouts**: Defaults to 15-second timeout; can be configured

## Testing

Run the test suite:
```bash
python3 -m pytest test_ticketforge.py -v
```

Test coverage:
```bash
python3 -m pytest test_ticketforge.py --cov=ticketforge
```

## Limitations & Assumptions

1. **Authentication**: Uses HTTP Basic Authentication (username/password)
2. **API Discovery Method**: Reverse-engineered from browser network inspection (HAR file analysis)
3. **Pagination**: Implemented via `limit` and `skip` parameters
4. **Stage Values**: Valid values include "open", "in_progress", "review", "closed"
5. **Ticket References**: Identified by reference codes (e.g., TF-244) provided by the server
6. **JSON Output**: All responses are returned as JSON
7. **Concurrent Requests**: This CLI is single-threaded; not designed for concurrent operations
8. **Rate Limiting**: API enforces 50 requests per minute (headers: x-ratelimit-*)
9. **Dependencies**: Dependencies between tickets can be set via the `dependsOn` field
10. **Available Fields**: Tickets contain `ref`, `title`, `description`, `stage`, `created`, `updated`, `dependsOn`, and `customFields` fields
11. **Custom Fields**: Fields must be created first before adding values to tickets; custom field values are stored per-user

## Troubleshooting

### "Connection refused" error
- Verify the base URL is correct
- Check your internet connection
- Ensure the TicketForge server is running

### "Unauthorized" error
- Verify username and password are correct
- Run `python3 ticketforge.py setup` to reconfigure
- Check that credentials haven't changed on the server

### "Invalid JSON" error
- The server may have returned HTML (e.g., error page)
- Verify the base URL is correct
- Check server status

### Slow Response Times
- The default timeout is 15 seconds
- Network latency may cause delays
- Try again if server is under high load

## AI Disclosure

**Tools Used**: GitHub Copilot was used to assist with:
- Initial code structure and best practices
- Type hints and dataclass implementation
- Error handling patterns
- ANSI color formatting code
- README documentation template

**Manual Work**:
- API endpoint discovery and reverse engineering
- Feature design and enhancement decisions
- Test suite implementation
- Integration and edge case handling
- Command-line interface design

## License

This project was created as a take-home assignment for an Integration Developer role.

## Support

For issues or questions, please refer to the error messages in the CLI output. They provide detailed information about what went wrong.

---

**Version**: 1.0.0  
**Last Updated**: April 10, 2024
