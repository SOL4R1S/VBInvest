"""Notification routes — list, mark read, mark all read."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from scripts.routers.deps import auth_db, current_user

router = APIRouter()


@router.get("/api/notifications")
def list_notifications(
    unread: bool = Query(False, alias="unread"),
    limit: int = Query(20, ge=1, le=100),
    user=Depends(current_user),
):
    items = auth_db().list_notifications(user.auth_user_id, unread_only=unread, limit=limit)
    return {"notifications": items}


@router.post("/api/notifications/{notification_id}/read")
def mark_notification_read(notification_id: str, user=Depends(current_user)):
    updated = auth_db().mark_notification_read(user.auth_user_id, notification_id)
    return {"updated": updated}


@router.post("/api/notifications/read-all")
def mark_all_notifications_read(user=Depends(current_user)):
    count = auth_db().mark_all_notifications_read(user.auth_user_id)
    return {"updated_count": count}
