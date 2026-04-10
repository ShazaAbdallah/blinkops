import unittest
from unittest.mock import Mock, patch, MagicMock
import json
import sys
import io
from ticketforge import (
    TicketForgeClient,
    TicketForgeError,
    format_ticket,
    format_ticket_table,
    save_config,
    load_config,
)
import tempfile
import os


class TestTicketForgeClient(unittest.TestCase):
    """Test suite for TicketForgeClient"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.base_url = "https://test.example.com"
        self.username = "testuser"
        self.password = "testpass"
        self.client = TicketForgeClient(
            base_url=self.base_url,
            username=self.username,
            password=self.password,
        )
    
    def test_client_initialization(self):
        """Test client initializes with correct attributes"""
        self.assertEqual(self.client.base_url, self.base_url)
        self.assertEqual(self.client.username, self.username)
        self.assertEqual(self.client.password, self.password)
        self.assertEqual(self.client.timeout, 15)
    
    def test_base_url_strips_trailing_slash(self):
        """Test that trailing slashes are removed from base_url"""
        client = TicketForgeClient(
            base_url="https://test.example.com/",
            username=self.username,
            password=self.password,
        )
        self.assertEqual(client.base_url, "https://test.example.com")
    
    def test_session_auth_set(self):
        """Test that session authentication is configured"""
        self.assertEqual(self.client.session.auth, (self.username, self.password))
    
    def test_session_headers_set(self):
        """Test that session headers are properly configured"""
        headers = self.client.session.headers
        self.assertEqual(headers.get("User-Agent"), "TicketForge-CLI/1.0")
        self.assertEqual(headers.get("Content-Type"), "application/json")
    
    @patch("ticketforge.requests.Session.request")
    def test_list_tickets_success(self, mock_request):
        """Test successful ticket listing"""
        mock_response = Mock()
        mock_response.json.return_value = {
            "data": [
                {"id": "1", "title": "Test Ticket", "status": "open"}
            ]
        }
        mock_request.return_value = mock_response
        
        result = self.client.list_tickets()
        
        self.assertIn("data", result)
        self.assertEqual(len(result["data"]), 1)
        self.assertEqual(result["data"][0]["title"], "Test Ticket")
    
    @patch("ticketforge.requests.Session.request")
    def test_list_tickets_with_limit(self, mock_request):
        """Test ticket listing with limit parameter"""
        mock_response = Mock()
        mock_response.json.return_value = {"data": []}
        mock_request.return_value = mock_response
        
        self.client.list_tickets(limit=5)
        
        # Verify the request was made with correct parameters
        call_kwargs = mock_request.call_args[1]
        self.assertEqual(call_kwargs["params"]["limit"], 5)
    
    @patch("ticketforge.requests.Session.request")
    def test_list_tickets_with_pagination(self, mock_request):
        """Test ticket listing with skip parameter for pagination"""
        mock_response = Mock()
        mock_response.json.return_value = {"data": []}
        mock_request.return_value = mock_response
        
        self.client.list_tickets(limit=10, skip=20)
        
        call_kwargs = mock_request.call_args[1]
        self.assertEqual(call_kwargs["params"]["limit"], 10)
        self.assertEqual(call_kwargs["params"]["skip"], 20)
    
    @patch("ticketforge.requests.Session.request")
    def test_get_ticket_success(self, mock_request):
        """Test successful ticket retrieval"""
        mock_response = Mock()
        mock_response.json.return_value = {
            "id": "123",
            "title": "Test",
            "status": "open"
        }
        mock_request.return_value = mock_response
        
        result = self.client.get_ticket("123")
        
        self.assertEqual(result["id"], "123")
        self.assertEqual(result["title"], "Test")
    
    @patch("ticketforge.requests.Session.request")
    def test_create_ticket_success(self, mock_request):
        """Test successful ticket creation"""
        mock_response = Mock()
        mock_response.json.return_value = {
            "id": "456",
            "title": "New Ticket",
            "description": "Test description",
            "status": "open"
        }
        mock_request.return_value = mock_response
        
        result = self.client.create_ticket(
            title="New Ticket",
            description="Test description"
        )
        
        self.assertEqual(result["id"], "456")
        self.assertEqual(result["title"], "New Ticket")
        
        # Verify POST request was made with correct payload
        call_args = mock_request.call_args
        self.assertEqual(call_args[0][0], "POST")
        payload = call_args[1]["json"]
        self.assertEqual(payload["title"], "New Ticket")
        self.assertEqual(payload["description"], "Test description")
    
    @patch("ticketforge.requests.Session.request")
    def test_update_ticket_success(self, mock_request):
        """Test successful ticket update"""
        mock_response = Mock()
        mock_response.json.return_value = {
            "id": "123",
            "title": "Updated Title",
            "status": "closed"
        }
        mock_request.return_value = mock_response
        
        result = self.client.update_ticket(
            ticket_id="123",
            title="Updated Title",
            status="closed"
        )
        
        self.assertEqual(result["title"], "Updated Title")
        self.assertEqual(result["status"], "closed")
        
        # Verify PUT request
        call_args = mock_request.call_args
        self.assertEqual(call_args[0][0], "PUT")
    
    @patch("ticketforge.requests.Session.request")
    def test_delete_ticket_success(self, mock_request):
        """Test successful ticket deletion"""
        mock_response = Mock()
        mock_response.json.return_value = {"success": True}
        mock_request.return_value = mock_response
        
        result = self.client.delete_ticket("123")
        
        # Verify DELETE request
        call_args = mock_request.call_args
        self.assertEqual(call_args[0][0], "DELETE")
        self.assertIn("/123", call_args[0][1])
    
    @patch("ticketforge.requests.Session.request")
    def test_request_handles_http_error(self, mock_request):
        """Test that HTTP errors are handled properly"""
        mock_response = Mock()
        mock_response.status_code = 401
        mock_response.text = "Unauthorized"
        mock_request.return_value = mock_response
        mock_request.side_effect = Exception()
        
        # Mock raise_for_status to raise
        mock_response.raise_for_status.side_effect = Exception("401")
        
        with self.assertRaises(TicketForgeError):
            self.client._request("GET", "/test")
    
    @patch("ticketforge.requests.Session.request")
    def test_request_handles_network_error(self, mock_request):
        """Test that network errors are handled"""
        mock_request.side_effect = Exception("Connection timeout")
        
        with self.assertRaises(TicketForgeError):
            self.client._request("GET", "/test")


class TestFormatting(unittest.TestCase):
    """Test suite for output formatting functions"""
    
    def test_format_ticket_basic(self):
        """Test basic ticket formatting"""
        ticket = {
            "id": "123",
            "title": "Test Ticket",
            "status": "open",
            "description": "Test description",
            "createdAt": "2024-04-10T10:00:00Z"
        }
        
        output = format_ticket(ticket)
        
        self.assertIn("123", output)
        self.assertIn("Test Ticket", output)
        self.assertIn("open", output)
        self.assertIn("Test description", output)
    
    def test_format_ticket_missing_fields(self):
        """Test formatting when fields are missing"""
        ticket = {"id": "123", "title": "Test"}
        
        output = format_ticket(ticket)
        
        self.assertIn("123", output)
        self.assertIn("Test", output)
        self.assertIn("N/A", output)
    
    def test_format_ticket_table_single(self):
        """Test table formatting with single ticket"""
        tickets = [{"id": "1", "title": "Test", "status": "open"}]
        
        output = format_ticket_table(tickets)
        
        self.assertIn("1", output)
        self.assertIn("Test", output)
        self.assertIn("open", output)
        self.assertIn("ID", output)
        self.assertIn("Title", output)
        self.assertIn("Status", output)
    
    def test_format_ticket_table_multiple(self):
        """Test table formatting with multiple tickets"""
        tickets = [
            {"id": "1", "title": "First", "status": "open"},
            {"id": "2", "title": "Second", "status": "closed"},
            {"id": "3", "title": "Third", "status": "open"},
        ]
        
        output = format_ticket_table(tickets)
        
        self.assertIn("1", output)
        self.assertIn("2", output)
        self.assertIn("3", output)
        self.assertIn("First", output)
        self.assertIn("Second", output)
        self.assertIn("Third", output)
    
    def test_format_ticket_table_empty(self):
        """Test table formatting with empty list"""
        output = format_ticket_table([])
        
        self.assertIn("No tickets found", output)


class TestConfigPersistence(unittest.TestCase):
    """Test suite for configuration save/load functions"""
    
    def setUp(self):
        """Set up temporary directory for testing"""
        self.temp_dir = tempfile.mkdtemp()
        self.original_home = os.path.expanduser("~")
    
    def tearDown(self):
        """Clean up temporary files"""
        import shutil
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    @patch("builtins.print")
    @patch("os.path.expanduser")
    @patch("os.makedirs")
    def test_save_config(self, mock_makedirs, mock_expanduser, mock_print):
        """Test saving configuration"""
        mock_expanduser.return_value = self.temp_dir
        
        save_config(
            base_url="https://test.com",
            username="testuser",
            password="testpass"
        )
        
        mock_makedirs.assert_called_once()
        mock_print.assert_called_once()


class TestIntegration(unittest.TestCase):
    """Integration tests for common workflows"""
    
    @patch("ticketforge.requests.Session.request")
    def test_login_workflow(self, mock_request):
        """Test complete login workflow"""
        mock_response = Mock()
        mock_response.json.return_value = {"data": []}
        mock_request.return_value = mock_response
        
        client = TicketForgeClient(
            base_url="https://test.com",
            username="user",
            password="pass"
        )
        
        result = client.login()
        
        self.assertIsNotNone(result)
    
    @patch("ticketforge.requests.Session.request")
    def test_create_and_update_workflow(self, mock_request):
        """Test creating and then updating a ticket"""
        # Setup mocks for create and update
        create_response = Mock()
        create_response.json.return_value = {
            "id": "123",
            "title": "Original",
            "status": "open"
        }
        
        update_response = Mock()
        update_response.json.return_value = {
            "id": "123",
            "title": "Updated",
            "status": "closed"
        }
        
        mock_request.side_effect = [create_response, update_response]
        
        client = TicketForgeClient(
            base_url="https://test.com",
            username="user",
            password="pass"
        )
        
        created = client.create_ticket("Original")
        updated = client.update_ticket("123", title="Updated", status="closed")
        
        self.assertEqual(created["id"], "123")
        self.assertEqual(updated["title"], "Updated")
        self.assertEqual(updated["status"], "closed")


class TestEdgeCases(unittest.TestCase):
    """Test edge cases and boundary conditions"""
    
    def test_empty_string_fields(self):
        """Test formatting with empty string fields"""
        ticket = {
            "id": "",
            "title": "",
            "status": "",
            "description": ""
        }
        
        output = format_ticket(ticket)
        self.assertIsInstance(output, str)
    
    def test_very_long_title(self):
        """Test formatting with very long title"""
        long_title = "A" * 500
        ticket = {
            "id": "1",
            "title": long_title,
            "status": "open"
        }
        
        output = format_ticket_table([ticket])
        self.assertIn(long_title[:50], output)  # Should contain at least part of title
    
    def test_special_characters_in_fields(self):
        """Test formatting with special characters"""
        ticket = {
            "id": "123",
            "title": "Bug: 🐛 Unicode test",
            "status": "open",
            "description": "Contains 'quotes' and \"double quotes\""
        }
        
        output = format_ticket(ticket)
        self.assertIsInstance(output, str)


if __name__ == "__main__":
    unittest.main()
