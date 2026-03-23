import pytest
from moto import mock_aws

from src.services.item_service import ItemConflictError, ItemNotFoundError


@mock_aws
class TestItemService:
    def test_create_item(self, item_service):
        item = item_service.create_item(
            name="Test Item", description="A test item", owner_id="OWNER-001"
        )

        assert item.name == "Test Item"
        assert item.description == "A test item"
        assert item.owner_id == "OWNER-001"
        assert item.item_id is not None

    def test_get_item(self, item_service):
        created = item_service.create_item(
            name="Test Item", description="A test item", owner_id="OWNER-001"
        )
        fetched = item_service.get_item(created.item_id)

        assert fetched.item_id == created.item_id
        assert fetched.name == "Test Item"

    def test_get_item_not_found(self, item_service):
        with pytest.raises(ItemNotFoundError):
            item_service.get_item("nonexistent-id")

    def test_list_items(self, item_service):
        item_service.create_item(name="Item 1", description="", owner_id="OWNER-001")
        item_service.create_item(name="Item 2", description="", owner_id="OWNER-001")
        item_service.create_item(name="Item 3", description="", owner_id="OWNER-002")

        items, next_token = item_service.list_items(owner_id="OWNER-001")

        assert len(items) == 2
        assert all(i.owner_id == "OWNER-001" for i in items)
        assert next_token is None

    def test_list_items_pagination(self, item_service):
        for i in range(3):
            item_service.create_item(name=f"Item {i}", description="", owner_id="OWNER-001")

        items, next_token = item_service.list_items(owner_id="OWNER-001", limit=2)

        assert len(items) == 2
        assert next_token is not None

        items2, next_token2 = item_service.list_items(
            owner_id="OWNER-001", limit=2, next_token=next_token
        )
        assert len(items2) == 1
        assert next_token2 is None

    def test_delete_item(self, item_service):
        created = item_service.create_item(
            name="Test Item", description="", owner_id="OWNER-001"
        )
        item_service.delete_item(created.item_id)

        with pytest.raises(ItemNotFoundError):
            item_service.get_item(created.item_id)

    def test_delete_item_not_found(self, item_service):
        with pytest.raises(ItemNotFoundError):
            item_service.delete_item("nonexistent-id")
