import pytest
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime, timedelta
from app.order_service import OrderService, order_service

class TestOrderService:
    @pytest.fixture
    def service(self):
        return OrderService()
    
    @pytest.mark.asyncio
    async def test_create_order_from_voice_success(self, service):
        # Mock the internal methods
        with patch.object(service, '_get_or_create_guest', new_callable=AsyncMock) as mock_guest:
            with patch.object(service, '_find_menu_item_id', new_callable=AsyncMock) as mock_find_item:
                with patch('aiohttp.ClientSession') as mock_session:
                    # Setup mocks
                    mock_guest.return_value = "guest123"
                    mock_find_item.side_effect = ["item123", "item456"]
                    
                    # Mock the POST request
                    mock_response = AsyncMock()
                    mock_response.status = 201
                    mock_response.json = AsyncMock(return_value={
                        "id": "order123",
                        "total_amount": 25.50,
                        "status": "PENDING"
                    })
                    
                    mock_session.return_value.__aenter__.return_value.post.return_value.__aenter__.return_value = mock_response
                    
                    # Test the method
                    result = await service.create_order_from_voice(
                        room_number="101",
                        guest_name="John Doe",
                        items=[
                            {"name": "Coffee", "quantity": 2, "special_notes": "Extra hot"},
                            {"name": "Sandwich", "quantity": 1}
                        ],
                        special_requests="No onions"
                    )
                    
                    assert result["id"] == "order123"
                    assert result["total_amount"] == 25.50
                    mock_guest.assert_called_once_with("101", "John Doe")
                    assert mock_find_item.call_count == 2
    
    @pytest.mark.asyncio
    async def test_create_order_from_voice_no_valid_items(self, service):
        with patch.object(service, '_get_or_create_guest', new_callable=AsyncMock) as mock_guest:
            with patch.object(service, '_find_menu_item_id', new_callable=AsyncMock) as mock_find_item:
                mock_guest.return_value = "guest123"
                mock_find_item.return_value = None  # No items found
                
                with pytest.raises(ValueError, match="No valid menu items found"):
                    await service.create_order_from_voice(
                        room_number="101",
                        guest_name="John Doe",
                        items=[{"name": "NonExistentItem", "quantity": 1}]
                    )
    
    @pytest.mark.asyncio
    async def test_create_order_from_voice_api_error(self, service):
        with patch.object(service, '_get_or_create_guest', new_callable=AsyncMock) as mock_guest:
            with patch.object(service, '_find_menu_item_id', new_callable=AsyncMock) as mock_find_item:
                with patch('aiohttp.ClientSession') as mock_session:
                    mock_guest.return_value = "guest123"
                    mock_find_item.return_value = "item123"
                    
                    # Mock failed response
                    mock_response = AsyncMock()
                    mock_response.status = 400
                    mock_response.text = AsyncMock(return_value="Bad request")
                    
                    mock_session.return_value.__aenter__.return_value.post.return_value.__aenter__.return_value = mock_response
                    
                    with pytest.raises(Exception, match="Order creation failed"):
                        await service.create_order_from_voice(
                            room_number="101",
                            guest_name="John Doe",
                            items=[{"name": "Coffee", "quantity": 1}]
                        )
    
    @pytest.mark.asyncio
    async def test_get_or_create_guest_existing(self, service):
        with patch('aiohttp.ClientSession') as mock_session:
            # Mock finding existing guest
            mock_get_response = AsyncMock()
            mock_get_response.status = 200
            mock_get_response.json = AsyncMock(return_value={"id": "guest123", "name": "John Doe"})
            
            mock_session.return_value.__aenter__.return_value.get.return_value.__aenter__.return_value = mock_get_response
            
            result = await service._get_or_create_guest("101", "John Doe")
            assert result == "guest123"
    
    @pytest.mark.asyncio
    async def test_get_or_create_guest_new(self, service):
        with patch('aiohttp.ClientSession') as mock_session:
            # Mock not finding guest (404)
            mock_get_response = AsyncMock()
            mock_get_response.status = 404
            
            # Mock creating new guest
            mock_post_response = AsyncMock()
            mock_post_response.status = 201
            mock_post_response.json = AsyncMock(return_value={"id": "newguest123"})
            
            mock_session_instance = mock_session.return_value.__aenter__.return_value
            mock_session_instance.get.return_value.__aenter__.return_value = mock_get_response
            mock_session_instance.post.return_value.__aenter__.return_value = mock_post_response
            
            result = await service._get_or_create_guest("101", "John Doe")
            assert result == "newguest123"
    
    @pytest.mark.asyncio
    async def test_get_or_create_guest_fallback_email(self, service):
        with patch('aiohttp.ClientSession') as mock_session:
            # Mock not finding guest by room
            mock_get_room_response = AsyncMock()
            mock_get_room_response.status = 404
            
            # Mock failed creation
            mock_post_response = AsyncMock()
            mock_post_response.status = 400
            mock_post_response.text = AsyncMock(return_value="Guest exists")
            
            # Mock finding by email
            mock_get_email_response = AsyncMock()
            mock_get_email_response.status = 200
            mock_get_email_response.json = AsyncMock(return_value=[{"id": "existingguest123"}])
            
            mock_session_instance = mock_session.return_value.__aenter__.return_value
            
            # Setup the mock to return different responses for different calls
            get_responses = [mock_get_room_response, mock_get_email_response]
            mock_session_instance.get.return_value.__aenter__.side_effect = get_responses
            mock_session_instance.post.return_value.__aenter__.return_value = mock_post_response
            
            result = await service._get_or_create_guest("101", "John Doe")
            assert result == "existingguest123"
    
    @pytest.mark.asyncio
    async def test_find_menu_item_id_exact_match(self, service):
        with patch('aiohttp.ClientSession') as mock_session:
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.json = AsyncMock(return_value=[
                {"id": "item1", "name": "Coffee"},
                {"id": "item2", "name": "Tea"},
                {"id": "item3", "name": "Sandwich"}
            ])
            
            mock_session.return_value.__aenter__.return_value.get.return_value.__aenter__.return_value = mock_response
            
            result = await service._find_menu_item_id("Coffee")
            assert result == "item1"
    
    @pytest.mark.asyncio
    async def test_find_menu_item_id_partial_match(self, service):
        with patch('aiohttp.ClientSession') as mock_session:
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.json = AsyncMock(return_value=[
                {"id": "item1", "name": "Espresso Coffee"},
                {"id": "item2", "name": "Green Tea"},
                {"id": "item3", "name": "Club Sandwich"}
            ])
            
            mock_session.return_value.__aenter__.return_value.get.return_value.__aenter__.return_value = mock_response
            
            result = await service._find_menu_item_id("sandwich")
            assert result == "item3"
    
    @pytest.mark.asyncio
    async def test_find_menu_item_id_not_found(self, service):
        with patch('aiohttp.ClientSession') as mock_session:
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.json = AsyncMock(return_value=[
                {"id": "item1", "name": "Coffee"},
                {"id": "item2", "name": "Tea"}
            ])
            
            mock_session.return_value.__aenter__.return_value.get.return_value.__aenter__.return_value = mock_response
            
            result = await service._find_menu_item_id("Pizza")
            assert result is None
    
    @pytest.mark.asyncio
    async def test_find_menu_item_id_api_error(self, service):
        with patch('aiohttp.ClientSession') as mock_session:
            mock_response = AsyncMock()
            mock_response.status = 500
            
            mock_session.return_value.__aenter__.return_value.get.return_value.__aenter__.return_value = mock_response
            
            result = await service._find_menu_item_id("Coffee")
            assert result is None
    
    def test_format_order_confirmation(self, service):
        order = {
            "id": "abc123def456",
            "total_amount": 25.50,
            "status": "CONFIRMED"
        }
        
        confirmation = service.format_order_confirmation(order)
        
        assert "ABC123DE" in confirmation  # First 8 chars uppercase
        assert "$25.50" in confirmation
        assert "20-30 minutes" in confirmation
        assert "successfully" in confirmation
    
    def test_format_order_confirmation_missing_data(self, service):
        order = {}
        
        confirmation = service.format_order_confirmation(order)
        
        assert "UNKNOWN" in confirmation.upper()
        assert "$0.00" in confirmation
    
    def test_singleton_instance(self):
        assert order_service is not None
        assert isinstance(order_service, OrderService)
        assert order_service.api_base_url == "http://localhost:8000"
    
    def test_custom_api_base_url(self):
        with patch.dict('os.environ', {'API_BASE_URL': 'http://api.example.com'}):
            service = OrderService()
            assert service.api_base_url == "http://api.example.com"
            assert service.api_endpoint == "http://api.example.com/api/v1/orders"