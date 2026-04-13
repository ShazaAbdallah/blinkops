import argparse
import json
import requests
import sys
import os
from dataclasses import dataclass
from typing import Any, Optional
from datetime import datetime

# ANSI color codes for better formatting
class Colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'


class TicketForgeError(Exception):
    pass


class TicketForgeLoginError(TicketForgeError):
    pass


@dataclass
class TicketForgeClient:
    base_url: str
    username: str
    password: str
    timeout: int = 15

    def __post_init__(self) -> None:
        self.base_url = self.base_url.rstrip("/")
        self.session = requests.Session()
        self.session.auth = (self.username, self.password)
        self.session.headers.update(
            {
                "Accept": "*/*",
                "User-Agent": "TicketForge-CLI/1.0",
                "Content-Type": "application/json",
            }
        )

    def _request(self, method: str, path: str, **kwargs: Any) -> dict[str, Any]:
        url = f"{self.base_url}{path}"
        try:
            response = self.session.request(method, url, timeout=self.timeout, **kwargs)
            response.raise_for_status()
            return response.json() if response.text else {}
        except requests.HTTPError as e:
            status = e.response.status_code if e.response is not None else "unknown"
            text = e.response.text if e.response is not None else str(e)
            raise TicketForgeError(f"{method} {path} failed [{status}]: {text}") from e
        except requests.RequestException as e:
            raise TicketForgeError(f"{method} {path} request failed: {e}") from e
        except ValueError as e:
            raise TicketForgeError(f"{method} {path} returned invalid JSON") from e

    def login(self) -> dict[str, Any]:
        """Test login/connectivity by fetching user's tickets"""
        return self.list_tickets(limit=1)

    def list_tickets(self, limit: Optional[int] = None, skip: int = 0) -> dict[str, Any]:
        """List tickets with optional pagination support"""
        path = "/api/tforge/workitems/mine"
        params = {}
        if limit is not None:
            params["limit"] = limit
        if skip > 0:
            params["skip"] = skip

        return self._request("GET", path, params=params)

    def get_ticket(self, ticket_ref: str) -> dict[str, Any]:
        """Get a specific ticket by reference (e.g., TF-244)"""
        path = f"/api/tforge/workitem/{ticket_ref}?view=deep"
        result = self._request("GET", path)
        # API returns wrapper, extract workitem
        return result.get("workitem", result)

    def create_ticket(self, title: str, description: str = "", custom_fields: Optional[dict] = None, depends_on: Optional[list] = None) -> dict[str, Any]:
        """Create a new ticket via publish endpoint"""
        path = "/api/tforge/workitem/publish"
        payload = {
            "title": title,
            "description": description,
            "dependsOn": depends_on,
        }
        if custom_fields:
            payload["customFields"] = custom_fields
        result = self._request("POST", path, json=payload)
        # API returns wrapper with workitem
        return result.get("workitem", result)

    def update_ticket(self, ticket_ref: str, title: Optional[str] = None, 
                     description: Optional[str] = None, stage: Optional[str] = None,
                     custom_fields: Optional[dict] = None, depends_on: Optional[list] = None) -> dict[str, Any]:
        """Update an existing ticket"""
        path = f"/api/tforge/workitem/{ticket_ref}"
        payload = {}
        if title is not None:
            payload["title"] = title
        if description is not None:
            payload["description"] = description
        if stage is not None:
            payload["stage"] = stage
        if depends_on is not None:
            payload["dependsOn"] = depends_on
        if custom_fields:
            payload["customFields"] = custom_fields
        
        # If we have customFields or depends_on, we need to fetch current state to get stage
        # because the API requires stage to be set
        if (custom_fields or depends_on) and stage is None and title is None:
            current = self.get_ticket(ticket_ref)
            if "stage" in current:
                payload["stage"] = current["stage"]
            if "title" in current and title is None:
                payload["title"] = current["title"]
        
        result = self._request("PUT", path, json=payload)
        # API returns wrapper with workitem
        return result.get("workitem", result)

    def delete_ticket(self, ticket_ref: str) -> dict[str, Any]:
        """Delete a ticket"""
        path = f"/api/tforge/workitem/{ticket_ref}"
        return self._request("DELETE", path)

    def list_custom_fields(self) -> dict[str, Any]:
        """Get all custom field definitions for this user"""
        path = "/api/tforge/custom-fields"
        return self._request("GET", path)

    def create_custom_field(self, name: str, label: str, field_type: str = "text") -> dict[str, Any]:
        """Create a new custom field definition"""
        path = "/api/tforge/custom-fields"
        payload = {
            "name": name,
            "label": label,
            "type": field_type,
        }
        result = self._request("POST", path, json=payload)
        # API returns wrapper with customField
        return result.get("customField", result)

    def delete_custom_field(self, field_name: str) -> dict[str, Any]:
        """Delete a custom field definition by name
        
        Args:
            field_name: The field name to delete (e.g., 'priority')
        """
        # List all fields and find the one with matching name
        fields_result = self.list_custom_fields()
        fields = fields_result.get("customFields", [])
        
        field_id = None
        for field in fields:
            if field.get("name") == field_name:
                field_id = field.get("id")
                break
        
        if not field_id:
            raise TicketForgeError(f"Custom field '{field_name}' not found")
        
        path = f"/api/tforge/custom-fields/{field_id}"
        return self._request("DELETE", path)

    def update_custom_field(self, field_name: str, label: Optional[str] = None) -> dict[str, Any]:
        """Update a custom field definition by name
        
        Args:
            field_name: The field name to update (e.g., 'priority')
            label: New label for the field (optional)
        """
        # List all fields and find the one with matching name
        fields_result = self.list_custom_fields()
        fields = fields_result.get("customFields", [])
        
        field_id = None
        for field in fields:
            if field.get("name") == field_name:
                field_id = field.get("id")
                break
        
        if not field_id:
            raise TicketForgeError(f"Custom field '{field_name}' not found")
        
        payload = {}
        if label:
            payload["label"] = label
        
        if not payload:
            raise TicketForgeError("No fields to update provided")
        
        path = f"/api/tforge/custom-fields/{field_id}"
        result = self._request("PUT", path, json=payload)
        # API returns wrapper with customField
        return result.get("customField", result)

    @staticmethod
    def register_user(base_url: str, username: str, password: str) -> dict[str, Any]:
        """Register a new user (static method - doesn't require authentication)"""
        path = "/api/tforge/user/register"
        url = f"{base_url.rstrip('/')}{path}"
        try:
            response = requests.post(
                url,
                json={"username": username, "password": password},
                timeout=15
            )
            response.raise_for_status()
            return response.json()
        except requests.HTTPError as e:
            status = e.response.status_code if e.response is not None else "unknown"
            text = e.response.text if e.response is not None else str(e)
            raise TicketForgeError(f"POST {path} failed [{status}]: {text}") from e
        except requests.RequestException as e:
            raise TicketForgeError(f"POST {path} request failed: {e}") from e
        except ValueError as e:
            raise TicketForgeError(f"POST {path} returned invalid JSON") from e


def format_ticket(ticket: dict[str, Any]) -> str:
    """Format a single ticket for display, showing only fields that exist"""
    output = ""
    
    # Standard fields in order, only show if present
    if "ref" in ticket:
        output += f"{Colors.BOLD}Ref:{Colors.ENDC} {ticket['ref']}\n"
    if "title" in ticket:
        output += f"{Colors.BOLD}Title:{Colors.ENDC} {ticket['title']}\n"
    if "stage" in ticket:
        stage = ticket['stage']
        stage_color = Colors.OKGREEN if stage == "open" else Colors.WARNING
        output += f"{Colors.BOLD}Stage:{Colors.ENDC} {stage_color}{stage}{Colors.ENDC}\n"
    if "description" in ticket and ticket['description']:
        output += f"{Colors.BOLD}Description:{Colors.ENDC} {ticket['description']}\n"
    if "created" in ticket:
        output += f"{Colors.BOLD}Created:{Colors.ENDC} {ticket['created']}\n"
    if "updated" in ticket:
        output += f"{Colors.BOLD}Updated:{Colors.ENDC} {ticket['updated']}\n"
    if "dependsOn" in ticket and ticket['dependsOn']:
        output += f"{Colors.BOLD}Depends On:{Colors.ENDC} {', '.join(ticket['dependsOn'])}\n"
    if "customFields" in ticket and ticket['customFields']:
        output += f"{Colors.BOLD}Custom Fields:{Colors.ENDC} {json.dumps(ticket['customFields'])}\n"
    
    return output


def format_ticket_table(tickets: list[dict[str, Any]]) -> str:
    """Format multiple tickets as a table"""
    if not tickets:
        return "No tickets found."
    
    # Calculate column widths
    ref_width = max(len("Ref"), max(len(str(t.get("ref", ""))) for t in tickets))
    title_width = max(len("Title"), max(len(str(t.get("title", ""))) for t in tickets))
    stage_width = max(len("Stage"), max(len(str(t.get("stage", ""))) for t in tickets))
    
    # Create header
    header = f"{Colors.BOLD}{Colors.HEADER}"
    header += f"{'Ref':<{ref_width}} | {'Title':<{title_width}} | {'Stage':<{stage_width}}"
    header += f"{Colors.ENDC}\n"
    header += "-" * (ref_width + title_width + stage_width + 6) + "\n"
    
    # Add rows
    rows = ""
    for ticket in tickets:
        ticket_ref = str(ticket.get("ref", ""))
        title = str(ticket.get("title", ""))
        stage = ticket.get("stage", "")
        
        stage_color = Colors.OKGREEN if stage == "open" else Colors.WARNING
        rows += f"{ticket_ref:<{ref_width}} | {title:<{title_width}} | {stage_color}{stage:<{stage_width}}{Colors.ENDC}\n"
    
    return header + rows


def save_config(base_url: str, username: str, password: str) -> None:
    """Save configuration to a config file"""
    config_dir = os.path.expanduser("~/.ticketforge")
    os.makedirs(config_dir, exist_ok=True)
    
    config_file = os.path.join(config_dir, "config.json")
    config = {
        "base_url": base_url,
        "username": username,
        "password": password,
    }
    
    with open(config_file, "w") as f:
        json.dump(config, f, indent=2)
    
    print(f"{Colors.OKGREEN}Configuration saved to {config_file}{Colors.ENDC}")

def delete_config() -> None:
    """Delete saved configuration (logout)"""
    config_file = os.path.expanduser("~/.ticketforge/config.json")
    if os.path.exists(config_file):
        os.remove(config_file)
        print(f"{Colors.OKGREEN}✓ Logged out successfully{Colors.ENDC}")
    else:
        print(f"{Colors.WARNING}No saved credentials found{Colors.ENDC}")


def load_config() -> Optional[dict[str, str]]:
    """Load configuration from config file"""
    config_file = os.path.expanduser("~/.ticketforge/config.json")
    if os.path.exists(config_file):
        with open(config_file, "r") as f:
            return json.load(f)
    return None


def main() -> None:
    parser = argparse.ArgumentParser(
        description="TicketForge CLI - Manage tickets from the command line",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
EXAMPLES:
  Setup (first time only):
    ticketforge.py setup --base-url https://... --username user1 --password pass

  Test connection:
    ticketforge.py login

  List all tickets:
    ticketforge.py list

  List with pagination:
    ticketforge.py list --limit 10 --skip 5

  Get JSON output:
    ticketforge.py list --format json

NOTES:
  - After setup, credentials are cached in ~/.ticketforge/config.json
  - The TicketForge API version used by this server only supports reading tickets
  - Use the web interface to create, update, or delete tickets
  - Run 'ticketforge.py <command> -h' for command-specific help
        """
    )
    
    parser.add_argument(
        "--base-url",
        help="TicketForge base URL",
    )
    parser.add_argument("--username", help="Username for authentication")
    parser.add_argument("--password", help="Password for authentication")
    
    subparsers = parser.add_subparsers(dest="command", required=True)
    
    # Register command
    register_parser = subparsers.add_parser("register", help="Register a new user account")
    register_parser.add_argument("--username", required=True, help="New username")
    register_parser.add_argument("--password", required=True, help="Password")
    
    # Setup command
    setup_parser = subparsers.add_parser("setup", help="Configure TicketForge connection")
    setup_parser.add_argument("--base-url", required=True, help="TicketForge base URL")
    setup_parser.add_argument("--username", required=True, help="Username")
    setup_parser.add_argument("--password", required=True, help="Password")
    
    # Login command
    subparsers.add_parser("login", help="Test login/connectivity")
    
    # Logout command
    subparsers.add_parser("logout", help="Clear saved credentials")
    
    # List command
    list_parser = subparsers.add_parser("list", help="List your tickets")
    list_parser.add_argument("--limit", type=int, default=None, help="Limit number of tickets")
    list_parser.add_argument("--skip", type=int, default=0, help="Skip first N tickets (pagination)")
    list_parser.add_argument("--format", choices=["table", "json"], default="table", help="Output format")
    
    # Get command
    get_parser = subparsers.add_parser("get", help="Get a specific ticket")
    get_parser.add_argument("ticket_ref", help="Ticket reference (e.g., TF-244)")
    get_parser.add_argument("--format", choices=["text", "json"], default="text", help="Output format")
    
    # Create command
    create_parser = subparsers.add_parser("create", help="Create a new ticket")
    create_parser.add_argument("--title", required=True, help="Ticket title")
    create_parser.add_argument("--description", default="", help="Ticket description")
    create_parser.add_argument("--depends-on", nargs="*", default=[], help="Ticket references this depends on (e.g., TF-244 TF-245)")
    create_parser.add_argument("--custom", nargs="*", default=[], help="Custom fields as key=value (e.g., priority=High status=Open)")
    
    # Update command
    update_parser = subparsers.add_parser("update", help="Update an existing ticket")
    update_parser.add_argument("ticket_ref", help="Ticket reference (e.g., TF-244)")
    update_parser.add_argument("--title", help="New title")
    update_parser.add_argument("--description", help="New description")
    update_parser.add_argument("--stage", help="New stage")
    update_parser.add_argument("--depends-on", nargs="+", help="Ticket references this depends on")
    update_parser.add_argument("--custom", nargs="*", default=[], help="Custom fields as key=value (e.g., priority=Medium)")
    
    # Delete command
    delete_parser = subparsers.add_parser("delete", help="Delete a ticket")
    delete_parser.add_argument("ticket_ref", help="Ticket reference (e.g., TF-244)")
    
    # Custom fields commands
    fields_subparsers = subparsers.add_parser("fields", help="Manage custom fields").add_subparsers(dest="fields_command", required=True)
    
    # List fields command
    fields_subparsers.add_parser("list", help="List all custom field definitions")
    
    # Create field command
    create_field_parser = fields_subparsers.add_parser("create", help="Create a new custom field")
    create_field_parser.add_argument("--name", required=True, help="Field name (e.g., 'priority')")
    create_field_parser.add_argument("--label", required=True, help="Field label for display (e.g., 'Priority')")
    create_field_parser.add_argument("--type", default="text", help="Field type (default: text)")
    
    # Delete field command
    delete_field_parser = fields_subparsers.add_parser("delete", help="Delete a custom field")
    delete_field_parser.add_argument("field_name", help="Field name to delete (e.g., 'priority')")
    
    # Update field command
    update_field_parser = fields_subparsers.add_parser("update", help="Update a custom field")
    update_field_parser.add_argument("field_name", help="Field name to update (e.g., 'priority')")
    update_field_parser.add_argument("--label", help="New label for the field")
    
    args = parser.parse_args()
    
    # Handle setup command
    if args.command == "setup":
        save_config(args.base_url, args.username, args.password)
        return
    
    # Handle register command (doesn't need setup config)
    if args.command == "register":
        try:
            base_url = args.base_url or "https://integrations-assignment-ticketforge.vercel.app"
            result = TicketForgeClient.register_user(
                base_url=base_url,
                username=args.username,
                password=args.password
            )
            user = result.get("user", {})
            print(f"{Colors.OKGREEN}✓ User registered successfully!{Colors.ENDC}")
            print(f"{Colors.OKCYAN}Username: {user.get('username')}{Colors.ENDC}")
            print(f"{Colors.OKCYAN}User ID: {user.get('id')}{Colors.ENDC}")
            print(f"{Colors.OKCYAN}Created: {user.get('created')}{Colors.ENDC}")
            print(f"\n{Colors.WARNING}You can now login with these credentials:{Colors.ENDC}")
            print(f"  python3 ticketforge.py setup --base-url {base_url} --username {args.username} --password {args.password}")
        except TicketForgeError as e:
            print(f"{Colors.FAIL}Error: {e}{Colors.ENDC}", file=sys.stderr)
            sys.exit(1)
        return
    
    if args.command == "logout":
        delete_config()
        return
    
    # Load credentials from arguments or config file
    base_url = args.base_url
    username = args.username
    password = args.password
    
    if not all([base_url, username, password]):
        config = load_config()
        if config:
            base_url = base_url or config.get("base_url")
            username = username or config.get("username")
            password = password or config.get("password")
        else:
            base_url = base_url or "https://integrations-assignment-ticketforge.vercel.app"
            username = username or "user1"
            password = password or "qwe123"
    
    try:
        client = TicketForgeClient(
            base_url=base_url,
            username=username,
            password=password,
        )
        
        if args.command == "login":
            client.login()
            print(f"{Colors.OKGREEN}✓ Connected successfully to TicketForge{Colors.ENDC}")
        
        
        elif args.command == "list":
            data = client.list_tickets(limit=args.limit, skip=args.skip)
            tickets = data.get("workitems", []) if isinstance(data, dict) else data
            
            if not isinstance(tickets, list):
                tickets = [tickets] if tickets else []
            
            if args.format == "json":
                print(json.dumps(data, indent=2))
            else:
                print(f"\n{Colors.HEADER}{Colors.BOLD}Your Tickets:{Colors.ENDC}\n")
                print(format_ticket_table(tickets))
                total = len(tickets)
                has_more = data.get("pagination", {}).get("hasMore", False)
                more_text = " (more available)" if has_more else ""
                print(f"\n{Colors.OKCYAN}Total: {total} ticket(s){more_text}{Colors.ENDC}\n")
        
        elif args.command == "get":
            ticket = client.get_ticket(args.ticket_ref)
            if args.format == "json":
                print(json.dumps(ticket, indent=2))
            else:
                print(f"\n{format_ticket(ticket)}")
        
        elif args.command == "create":
            # Parse custom fields from key=value format
            custom_fields = {}
            for item in args.custom:
                if "=" in item:
                    key, value = item.split("=", 1)
                    custom_fields[key] = value
            
            # Parse depends_on - convert to list if provided, otherwise None
            depends_on = args.depends_on if args.depends_on else None
            
            result = client.create_ticket(
                title=args.title,
                description=args.description,
                custom_fields=custom_fields if custom_fields else None,
                depends_on=depends_on,
            )
            print(f"{Colors.OKGREEN}✓ Ticket created successfully!{Colors.ENDC}")
            print(f"{Colors.OKCYAN}Ticket Ref: {result.get('ref', 'N/A')}{Colors.ENDC}")
            if result.get('customFields'):
                print(f"{Colors.OKCYAN}Custom Fields: {json.dumps(result.get('customFields'))}{Colors.ENDC}")
            if result.get('dependsOn'):
                print(f"{Colors.OKCYAN}Depends On: {', '.join(result.get('dependsOn'))}{Colors.ENDC}")
            print(json.dumps(result, indent=2))
        
        elif args.command == "update":
            # Parse custom fields from key=value format
            custom_fields = {}
            for item in args.custom:
                if "=" in item:
                    key, value = item.split("=", 1)
                    custom_fields[key] = value
            
            result = client.update_ticket(
                ticket_ref=args.ticket_ref,
                title=args.title,
                description=args.description,
                stage=args.stage,
                custom_fields=custom_fields if custom_fields else None,
                depends_on=args.depends_on,
            )
            print(f"{Colors.OKGREEN}✓ Ticket updated successfully!{Colors.ENDC}")
            if result.get('customFields'):
                print(f"{Colors.OKCYAN}Custom Fields: {json.dumps(result.get('customFields'))}{Colors.ENDC}")
            print(json.dumps(result, indent=2))
        
        elif args.command == "delete":
            client.delete_ticket(args.ticket_ref)
            print(f"{Colors.OKGREEN}✓ Ticket deleted successfully!{Colors.ENDC}")
        
        elif args.command == "fields":
            if args.fields_command == "list":
                result = client.list_custom_fields()
                fields = result.get("customFields", [])
                if not fields:
                    print(f"{Colors.OKCYAN}No custom fields defined yet.{Colors.ENDC}")
                else:
                    print(f"{Colors.HEADER}{Colors.BOLD}Custom Fields:{Colors.ENDC}\n")
                    for field in fields:
                        field_id = field.get("id", "")
                        field_name = field.get("name", "")
                        field_label = field.get("label", "")
                        field_type = field.get("type", "")
                        print(f"  {Colors.OKGREEN}{field_name}{Colors.ENDC} ({field_label}) - {field_type}")
                        print(f"    ID: {field_id}")
                    print()
            
            elif args.fields_command == "create":
                result = client.create_custom_field(
                    name=args.name,
                    label=args.label,
                    field_type=args.type
                )
                print(f"{Colors.OKGREEN}✓ Custom field created successfully!{Colors.ENDC}")
                print(f"{Colors.OKCYAN}Field: {result.get('name')}{Colors.ENDC}")
                print(f"{Colors.OKCYAN}Label: {result.get('label')}{Colors.ENDC}")
                print(f"{Colors.OKCYAN}Type: {result.get('type')}{Colors.ENDC}")
                print(f"{Colors.OKCYAN}ID: {result.get('id')}{Colors.ENDC}")
            
            elif args.fields_command == "delete":
                client.delete_custom_field(args.field_name)
                print(f"{Colors.OKGREEN}✓ Custom field deleted successfully!{Colors.ENDC}")
            
            elif args.fields_command == "update":
                if not args.label:
                    raise TicketForgeError("At least one field must be provided (--label)")
                result = client.update_custom_field(
                    field_name=args.field_name,
                    label=args.label
                )
                print(f"{Colors.OKGREEN}✓ Custom field updated successfully!{Colors.ENDC}")
                print(f"{Colors.OKCYAN}Field: {result.get('name')}{Colors.ENDC}")
                print(f"{Colors.OKCYAN}Label: {result.get('label')}{Colors.ENDC}")
                print(f"{Colors.OKCYAN}Type: {result.get('type')}{Colors.ENDC}")
                print(f"{Colors.OKCYAN}ID: {result.get('id')}{Colors.ENDC}")
    
    except TicketForgeError as e:
        print(f"{Colors.FAIL}Error: {e}{Colors.ENDC}", file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt:
        print(f"\n{Colors.WARNING}Interrupted by user{Colors.ENDC}")
        sys.exit(130)


if __name__ == "__main__":
    main()