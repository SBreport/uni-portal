"""시술 카탈로그 라우터."""
from typing import Annotated, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from api.deps import require_role
from pydantic import BaseModel

router = APIRouter(prefix="/treatment-catalog", tags=["Treatment Catalog"])
_editor = require_role("editor")


class CatalogCreate(BaseModel):
    item_type: str
    category: str
    item_name: str
    sub_option: Optional[str] = None
    display_name: str
    device_id: Optional[int] = None
    description: str = ""
    sort_order: int = 0


class CatalogUpdate(BaseModel):
    item_type: Optional[str] = None
    category: Optional[str] = None
    item_name: Optional[str] = None
    sub_option: Optional[str] = None
    display_name: Optional[str] = None
    device_id: Optional[int] = None
    description: Optional[str] = None
    sort_order: Optional[int] = None
    is_active: Optional[int] = None


@router.get("")
async def list_catalog(
    item_type: Optional[str] = None,
    category: Optional[str] = None,
    search: Optional[str] = None,
):
    from treatment.db import list_catalog
    return list_catalog(item_type, category, search)


@router.get("/categories")
async def get_categories():
    from treatment.db import get_categories
    return get_categories()


@router.get("/search")
async def search_crossref(q: str = ""):
    from treatment.crossref import search_cross_reference
    if not q:
        return []
    return search_cross_reference(q)


@router.get("/validation-report")
async def validation_report(user: Annotated[dict, Depends(_editor)]):
    from treatment.validation import get_validation_report
    return get_validation_report()


@router.get("/{item_id}")
async def get_item(item_id: int):
    from treatment.db import get_catalog_item
    item = get_catalog_item(item_id)
    if not item:
        raise HTTPException(404, "not found")
    return item


@router.get("/{item_id}/crossref")
async def get_crossref(item_id: int):
    from treatment.crossref import get_cross_reference
    result = get_cross_reference(item_id)
    if not result:
        raise HTTPException(404, "not found")
    return result


@router.post("")
async def create_item(req: CatalogCreate, user: Annotated[dict, Depends(_editor)]):
    from treatment.db import create_catalog_item
    item_id = create_catalog_item(req.model_dump())
    return {"ok": True, "id": item_id}


@router.patch("/{item_id}")
async def update_item(item_id: int, req: CatalogUpdate, user: Annotated[dict, Depends(_editor)]):
    from treatment.db import update_catalog_item
    update_catalog_item(item_id, req.model_dump(exclude_none=True))
    return {"ok": True}


@router.delete("/{item_id}")
async def delete_item(item_id: int, user: Annotated[dict, Depends(_editor)]):
    from treatment.db import delete_catalog_item
    delete_catalog_item(item_id)
    return {"ok": True}


@router.post("/auto-match")
async def auto_match(user: Annotated[dict, Depends(_editor)]):
    from treatment.db import batch_auto_match
    result = batch_auto_match()
    return result
