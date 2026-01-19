"""
Pydantic schemas for SlabHub API
Provides request/response models for validation and serialization
"""
from datetime import datetime
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field, ConfigDict


# ============================================================================
# Slab Schemas
# ============================================================================

class SlabBase(BaseModel):
    """Base schema for Slab with common fields"""
    name: str = Field(..., min_length=1, max_length=255, description="Slab name or identifier")
    stone_type: Optional[str] = Field(None, max_length=100, description="Type of stone")
    supplier: Optional[str] = Field(None, max_length=200, description="Supplier or vendor name")
    finish: Optional[str] = Field(None, max_length=50, description="Surface finish")
    thickness: Optional[float] = Field(None, ge=0, description="Thickness in inches")
    color: Optional[str] = Field(None, max_length=100, description="Primary color")
    length: Optional[float] = Field(None, ge=0, description="Length in inches")
    width: Optional[float] = Field(None, ge=0, description="Width in inches")
    square_feet: Optional[float] = Field(None, ge=0, description="Total square footage")
    location: Optional[str] = Field(None, max_length=100, description="Physical storage location")
    status: str = Field(default="available", max_length=50, description="Status")
    quantity: int = Field(default=1, ge=0, description="Number of identical slabs")
    tags: Optional[str] = Field(None, description="Comma-separated tags")
    notes: Optional[str] = Field(None, description="Internal notes and comments")
    primary_image: Optional[str] = Field(None, max_length=500, description="Path to primary image")
    additional_images: Optional[Dict[str, Any]] = Field(None, description="Additional image paths")
    extra_json: Optional[Dict[str, Any]] = Field(None, description="Extra fields from imports")
    cost: Optional[float] = Field(None, ge=0, description="Cost price")
    price: Optional[float] = Field(None, ge=0, description="Selling price")


class SlabCreate(SlabBase):
    """Schema for creating a new slab"""
    # All fields inherited from SlabBase
    # public_id will be auto-generated
    pass


class SlabUpdate(BaseModel):
    """Schema for updating an existing slab (all fields optional)"""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    stone_type: Optional[str] = Field(None, max_length=100)
    supplier: Optional[str] = Field(None, max_length=200)
    finish: Optional[str] = Field(None, max_length=50)
    thickness: Optional[float] = Field(None, ge=0)
    color: Optional[str] = Field(None, max_length=100)
    length: Optional[float] = Field(None, ge=0)
    width: Optional[float] = Field(None, ge=0)
    square_feet: Optional[float] = Field(None, ge=0)
    location: Optional[str] = Field(None, max_length=100)
    status: Optional[str] = Field(None, max_length=50)
    quantity: Optional[int] = Field(None, ge=0)
    tags: Optional[str] = None
    notes: Optional[str] = None
    primary_image: Optional[str] = Field(None, max_length=500)
    additional_images: Optional[Dict[str, Any]] = None
    extra_json: Optional[Dict[str, Any]] = None
    cost: Optional[float] = Field(None, ge=0)
    price: Optional[float] = Field(None, ge=0)


class SlabResponse(SlabBase):
    """Schema for slab responses (includes all database fields)"""
    id: int
    public_id: str
    created_at: datetime
    updated_at: datetime
    import_source: Optional[str] = None
    import_batch_id: Optional[str] = None
    perceptual_hash: Optional[str] = None
    qr_code_path: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class SlabListResponse(BaseModel):
    """Schema for paginated slab list responses"""
    total: int
    skip: int
    limit: int
    items: List[SlabResponse]


# ============================================================================
# Inventory Item Schemas
# ============================================================================

class InventoryItemBase(BaseModel):
    """Base schema for InventoryItem with common fields"""
    sku: str = Field(..., min_length=1, max_length=100, description="Stock keeping unit")
    name: str = Field(..., min_length=1, max_length=255, description="Item name")
    description: Optional[str] = Field(None, description="Detailed item description")
    category: Optional[str] = Field(None, max_length=100, description="Item category")
    unit: Optional[str] = Field(None, max_length=50, description="Unit of measure")
    qty_on_hand: int = Field(default=0, ge=0, description="Current quantity in stock")
    qty_reserved: int = Field(default=0, ge=0, description="Quantity reserved for orders")
    reorder_point: Optional[int] = Field(None, ge=0, description="Minimum quantity before reordering")
    location: Optional[str] = Field(None, max_length=100, description="Physical storage location")
    unit_cost: Optional[float] = Field(None, ge=0, description="Cost per unit")
    unit_price: Optional[float] = Field(None, ge=0, description="Selling price per unit")
    tags: Optional[str] = Field(None, description="Comma-separated tags")
    notes: Optional[str] = Field(None, description="Internal notes")
    images: Optional[Dict[str, Any]] = Field(None, description="Array of image paths")


class InventoryItemCreate(InventoryItemBase):
    """Schema for creating a new inventory item"""
    pass


class InventoryItemUpdate(BaseModel):
    """Schema for updating an existing inventory item (all fields optional)"""
    sku: Optional[str] = Field(None, min_length=1, max_length=100)
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    category: Optional[str] = Field(None, max_length=100)
    unit: Optional[str] = Field(None, max_length=50)
    qty_on_hand: Optional[int] = Field(None, ge=0)
    qty_reserved: Optional[int] = Field(None, ge=0)
    reorder_point: Optional[int] = Field(None, ge=0)
    location: Optional[str] = Field(None, max_length=100)
    unit_cost: Optional[float] = Field(None, ge=0)
    unit_price: Optional[float] = Field(None, ge=0)
    tags: Optional[str] = None
    notes: Optional[str] = None
    images: Optional[Dict[str, Any]] = None


class InventoryItemResponse(InventoryItemBase):
    """Schema for inventory item responses (includes all database fields)"""
    id: int
    created_at: datetime
    updated_at: datetime
    qty_available: int = Field(..., description="Computed: qty_on_hand - qty_reserved")

    model_config = ConfigDict(from_attributes=True)

    @property
    def qty_available(self) -> int:
        """Calculate available quantity"""
        return self.qty_on_hand - self.qty_reserved


class InventoryItemListResponse(BaseModel):
    """Schema for paginated inventory item list responses"""
    total: int
    skip: int
    limit: int
    items: List[InventoryItemResponse]


# ============================================================================
# Shipment Schemas
# ============================================================================

class ShipmentBase(BaseModel):
    """Base schema for Shipment with common fields"""
    tracking_number: Optional[str] = Field(None, max_length=100, description="Carrier tracking number")
    supplier: str = Field(..., min_length=1, max_length=200, description="Supplier or vendor name")
    po_number: Optional[str] = Field(None, max_length=100, description="Purchase order number")
    status: str = Field(default="pending", max_length=50, description="Shipment status")
    items: Optional[Dict[str, Any]] = Field(None, description="Array of items in shipment")
    notes: Optional[str] = Field(None, description="Shipment notes and comments")
    ordered_date: Optional[datetime] = Field(None, description="Date order was placed")
    expected_date: Optional[datetime] = Field(None, description="Expected delivery date")
    received_date: Optional[datetime] = Field(None, description="Actual received date")


class ShipmentCreate(ShipmentBase):
    """Schema for creating a new shipment"""
    pass


class ShipmentUpdate(BaseModel):
    """Schema for updating an existing shipment (all fields optional)"""
    tracking_number: Optional[str] = Field(None, max_length=100)
    supplier: Optional[str] = Field(None, min_length=1, max_length=200)
    po_number: Optional[str] = Field(None, max_length=100)
    status: Optional[str] = Field(None, max_length=50)
    items: Optional[Dict[str, Any]] = None
    notes: Optional[str] = None
    ordered_date: Optional[datetime] = None
    expected_date: Optional[datetime] = None
    received_date: Optional[datetime] = None


class ShipmentResponse(ShipmentBase):
    """Schema for shipment responses (includes all database fields)"""
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ShipmentListResponse(BaseModel):
    """Schema for paginated shipment list responses"""
    total: int
    skip: int
    limit: int
    items: List[ShipmentResponse]


# ============================================================================
# QR Code and Label Generation Schemas
# ============================================================================

class QRGenerateRequest(BaseModel):
    """Request schema for QR code generation"""
    regenerate: bool = Field(default=False, description="Force regenerate even if exists")


class QRGenerateResponse(BaseModel):
    """Response schema for QR code generation"""
    slab_id: int
    public_id: str
    qr_code_path: str
    qr_url: str


class LabelGenerateResponse(BaseModel):
    """Response schema for label generation"""
    slab_id: int
    public_id: str
    label_path: str


# ============================================================================
# Bulk Action Schemas
# ============================================================================

class BulkActionRequest(BaseModel):
    """Request schema for bulk actions on multiple slabs"""
    ids: List[int]
    action: str = Field(..., description="Action to perform: delete, update_status, update_location, analyze")
    status: Optional[str] = Field(None, description="New status for update_status action")
    location: Optional[str] = Field(None, description="New location for update_location action")


# ============================================================================
# Health Check Schema
# ============================================================================

class HealthCheckResponse(BaseModel):
    """Response schema for health check endpoint"""
    status: str
    version: str
    database: str
    watch_folder_enabled: bool
    watch_folder_running: bool = False


# ============================================================================
# Metadata Import Schemas (Phase 2)
# ============================================================================

class ImportRowError(BaseModel):
    """Schema for individual row validation errors"""
    row: int = Field(..., description="Row number (1-indexed, header is row 1)")
    column: Optional[str] = Field(None, description="Column name where error occurred")
    message: str = Field(..., description="Error message")


class ImportResult(BaseModel):
    """Response schema for metadata import operations"""
    batch_id: str = Field(..., description="Unique batch identifier for this import")
    status: str = Field(..., description="Import status: completed, partial, failed")
    file_type: str = Field(..., description="File type processed: csv or xlsx")
    rows_processed: int = Field(0, description="Total rows processed (excluding header)")
    rows_imported: int = Field(0, description="New slabs created")
    rows_updated: int = Field(0, description="Existing slabs updated")
    rows_failed: int = Field(0, description="Rows that failed validation")
    rows_skipped: int = Field(0, description="Rows skipped (e.g., duplicates)")
    errors: List[ImportRowError] = Field(default_factory=list, description="List of validation errors")
    warnings: List[ImportRowError] = Field(default_factory=list, description="List of warnings")
    summary: str = Field("", description="Human-readable summary")


class ImportColumnSpec(BaseModel):
    """Schema describing expected columns for import"""
    name: str = Field(..., description="Column name")
    required: bool = Field(False, description="Whether column is required")
    data_type: str = Field("string", description="Expected data type: string, number, integer")
    description: str = Field("", description="Column description")
