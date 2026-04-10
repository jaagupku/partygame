from fastapi import APIRouter, Depends, Header, Request
from fastapi.responses import FileResponse

from partygame.schemas import MediaAsset, MediaKind
from partygame.service.media import LocalFilesystemMediaStorage, get_media_storage

router = APIRouter()


@router.post("", response_model=MediaAsset)
async def upload_media(
    request: Request,
    kind: MediaKind,
    filename: str,
    content_type: str | None = Header(default=None, alias="Content-Type"),
    storage: LocalFilesystemMediaStorage = Depends(get_media_storage),
):
    return await storage.save(
        content=await request.body(),
        kind=kind,
        filename=filename,
        content_type=content_type or "",
    )


@router.get("/{asset_id}", response_class=FileResponse)
async def get_media_file(
    asset_id: str,
    storage: LocalFilesystemMediaStorage = Depends(get_media_storage),
):
    asset = await storage.get(asset_id)
    path = await storage.open(asset)
    return FileResponse(
        path,
        media_type=asset.content_type,
        filename=asset.original_filename,
    )


@router.get("/{asset_id}/meta", response_model=MediaAsset)
async def get_media_meta(
    asset_id: str,
    storage: LocalFilesystemMediaStorage = Depends(get_media_storage),
):
    return await storage.get(asset_id)
