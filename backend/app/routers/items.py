"""
Example CRUD endpoints for items.

Demonstrates basic create, read, update, and delete operations with in-memory storage.
Replace with database integration in production.
"""
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

router = APIRouter()


class Item(BaseModel):
    """Item model with all fields."""
    
    id: int = Field(..., description="Unique item identifier", examples=[1])
    name: str = Field(..., description="Item name", examples=["Premium Widget"])
    description: str | None = Field(
        None,
        description="Optional item description",
        examples=["A high-quality widget for all your needs"],
    )
    price: float = Field(..., description="Item price in USD", examples=[29.99], gt=0)
    is_active: bool = Field(
        default=True,
        description="Whether the item is active/available",
        examples=[True],
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "id": 1,
                    "name": "Premium Widget",
                    "description": "A high-quality widget for all your needs",
                    "price": 29.99,
                    "is_active": True,
                }
            ]
        }
    }


class ItemCreate(BaseModel):
    """Item creation model (no ID required)."""
    
    name: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Item name",
        examples=["Premium Widget"],
    )
    description: str | None = Field(
        None,
        max_length=500,
        description="Optional item description",
        examples=["A high-quality widget for all your needs"],
    )
    price: float = Field(
        ...,
        description="Item price in USD (must be positive)",
        examples=[29.99],
        gt=0,
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "name": "Premium Widget",
                    "description": "A high-quality widget for all your needs",
                    "price": 29.99,
                }
            ]
        }
    }


# In-memory storage for demo purposes
_items_db: dict[int, Item] = {
    1: Item(id=1, name="Widget", description="A useful widget", price=9.99),
    2: Item(id=2, name="Gadget", description="A fancy gadget", price=19.99),
    3: Item(id=3, name="Gizmo", description="An amazing gizmo", price=29.99),
}
_next_id = 4


@router.get(
    "/items",
    response_model=list[Item],
    summary="List All Items",
    description="Retrieve a list of all items",
    response_description="List of items",
    responses={
        200: {
            "description": "List of all items",
            "content": {
                "application/json": {
                    "example": [
                        {
                            "id": 1,
                            "name": "Widget",
                            "description": "A useful widget",
                            "price": 9.99,
                            "is_active": True,
                        },
                        {
                            "id": 2,
                            "name": "Gadget",
                            "description": "A fancy gadget",
                            "price": 19.99,
                            "is_active": True,
                        },
                    ]
                }
            },
        }
    },
)
async def list_items():
    """
    List all items.
    
    Returns all items currently in the system. In a production environment,
    you might want to add pagination, filtering, and sorting capabilities.
    """
    return list(_items_db.values())


@router.get(
    "/items/{item_id}",
    response_model=Item,
    summary="Get Item by ID",
    description="Retrieve a specific item by its ID",
    response_description="Item details",
    responses={
        200: {
            "description": "Item found",
            "content": {
                "application/json": {
                    "example": {
                        "id": 1,
                        "name": "Widget",
                        "description": "A useful widget",
                        "price": 9.99,
                        "is_active": True,
                    }
                }
            },
        },
        404: {"description": "Item not found"},
    },
)
async def get_item(item_id: int = Field(..., description="ID of the item to retrieve", examples=[1])):
    """
    Get a single item by ID.
    
    Returns detailed information about a specific item. Returns 404 if the item
    doesn't exist.
    """
    if item_id not in _items_db:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Item with ID {item_id} not found",
        )
    return _items_db[item_id]


@router.post(
    "/items",
    response_model=Item,
    status_code=status.HTTP_201_CREATED,
    summary="Create New Item",
    description="Create a new item with the provided details",
    response_description="Created item with assigned ID",
    responses={
        201: {
            "description": "Item successfully created",
            "content": {
                "application/json": {
                    "example": {
                        "id": 4,
                        "name": "Premium Widget",
                        "description": "A high-quality widget",
                        "price": 29.99,
                        "is_active": True,
                    }
                }
            },
        },
        400: {"description": "Invalid input data"},
    },
)
async def create_item(item: ItemCreate):
    """
    Create a new item.
    
    Creates a new item with an auto-generated ID. The item is automatically
    set to active status.
    
    **Note:** This uses in-memory storage. In production, persist to a database.
    """
    global _next_id
    new_item = Item(id=_next_id, **item.model_dump())
    _items_db[_next_id] = new_item
    _next_id += 1
    return new_item


@router.put(
    "/items/{item_id}",
    response_model=Item,
    summary="Update Item",
    description="Update an existing item with new details",
    response_description="Updated item",
    responses={
        200: {
            "description": "Item successfully updated",
            "content": {
                "application/json": {
                    "example": {
                        "id": 1,
                        "name": "Updated Widget",
                        "description": "Updated description",
                        "price": 39.99,
                        "is_active": True,
                    }
                }
            },
        },
        404: {"description": "Item not found"},
        400: {"description": "Invalid input data"},
    },
)
async def update_item(
    item_id: int = Field(..., description="ID of the item to update", examples=[1]),
    item: ItemCreate = None,
):
    """
    Update an existing item.
    
    Replaces all fields of the specified item with the new values. Returns 404
    if the item doesn't exist.
    
    **Note:** This is a full replacement (PUT). For partial updates, consider
    implementing a PATCH endpoint.
    """
    if item_id not in _items_db:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Item with ID {item_id} not found",
        )
    updated_item = Item(id=item_id, **item.model_dump())
    _items_db[item_id] = updated_item
    return updated_item


@router.delete(
    "/items/{item_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete Item",
    description="Delete an item by ID",
    responses={
        204: {"description": "Item successfully deleted"},
        404: {"description": "Item not found"},
    },
)
async def delete_item(item_id: int = Field(..., description="ID of the item to delete", examples=[1])):
    """
    Delete an item.
    
    Permanently removes the specified item from the system. Returns 204 on success
    with no response body.
    
    **Warning:** This operation cannot be undone.
    """
    if item_id not in _items_db:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Item with ID {item_id} not found",
        )
    del _items_db[item_id]

