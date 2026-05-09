"""
In-memory data store for conversations and messages.

Thread-safe via asyncio.Lock. Easy to swap for SQLite/PostgreSQL later.
"""

from __future__ import annotations

import asyncio
from datetime import datetime
from typing import Dict, List, Optional

from app.schemas.chat import (
    ConversationOut,
    ConversationSummaryOut,
    MessageOut,
    MessageRole,
    AttachmentOut,
    ContractType,
    UserType,
    ReportVerdict,
)


from prisma import Prisma

class PrismaStore:
    """Async Prisma-backed store for conversations."""

    def __init__(self) -> None:
        self.prisma = Prisma()

    async def connect(self):
        await self.prisma.connect()

    async def disconnect(self):
        if self.prisma.is_connected():
            await self.prisma.disconnect()

    async def _ensure_user_exists(self, user_id: str) -> None:
        """Create a lightweight local user record when auth is bypassed in development."""
        existing = await self.prisma.user.find_unique(where={"id": user_id})
        if existing:
            return

        await self.prisma.user.create(
            data={
                "id": user_id,
                "email": f"{user_id}@local.fortress",
            }
        )

    # ── Users ──────────────────────────────────────────

    async def update_user(
        self,
        user_id: str,
        name: Optional[str] = None,
        user_type: Optional[str] = None,
    ) -> bool:
        data = {}
        if name is not None:
            data["name"] = name
        if user_type is not None:
            data["userType"] = user_type
            
        if not data:
            existing = await self.prisma.user.find_unique(where={"id": user_id})
            return existing is not None
            
        updated = await self.prisma.user.update_many(
            where={"id": user_id},
            data=data
        )
        return updated > 0

    # ── Conversations ────────────────────────────────────────

    async def create_conversation(
        self,
        id: str,
        user_id: str,
        title: str = "New Analysis",
        contract_type: Optional[str] = None,
        user_type: Optional[str] = None,
    ) -> ConversationOut:
        await self._ensure_user_exists(user_id)

        conv = await self.prisma.conversation.create(
            data={
                "id": id,
                "title": title,
                "contractType": contract_type,
                "userType": user_type,
                "userId": user_id,
            },
            include={"messages": {"include": {"attachment": True}}}
        )
        return self._to_conversation_out(conv)

    async def get_conversation(self, id: str, user_id: str) -> Optional[ConversationOut]:
        conv = await self.prisma.conversation.find_first(
            where={"id": id, "userId": user_id},
            include={"messages": {"include": {"attachment": True}, "orderBy": {"timestamp": "asc"}}}
        )
        if not conv:
            return None
        return self._to_conversation_out(conv)

    async def list_conversations(self, user_id: str) -> List[ConversationSummaryOut]:
        convs = await self.prisma.conversation.find_many(
            where={"userId": user_id},
            order=[{"isPinned": "desc"}, {"timestamp": "desc"}],
        )
        return [self._to_summary(c) for c in convs]

    async def update_conversation(
        self,
        id: str,
        user_id: str,
        title: Optional[str] = None,
        is_pinned: Optional[bool] = None,
        verdict: Optional[str] = None,
        contract_type: Optional[str] = None,
        user_type: Optional[str] = None,
    ) -> Optional[ConversationOut]:
        data = {}
        if title is not None:
            data["title"] = title
        if is_pinned is not None:
            data["isPinned"] = is_pinned
        if verdict is not None:
            data["verdict"] = verdict
        if contract_type is not None:
            data["contractType"] = contract_type
        if user_type is not None:
            data["userType"] = user_type

        conv = await self.prisma.conversation.update_many(
            where={"id": id, "userId": user_id},
            data=data
        )
        if conv == 0:
            return None
            
        updated_conv = await self.get_conversation(id, user_id)
        return updated_conv

    async def delete_conversation(self, id: str, user_id: str) -> bool:
        deleted = await self.prisma.conversation.delete_many(
            where={"id": id, "userId": user_id}
        )
        return deleted > 0

    # ── Messages ─────────────────────────────────────────────

    async def add_message(
        self,
        conversation_id: str,
        user_id: str,
        message_id: str,
        role: str,
        content: str,
        attachment: Optional[dict] = None,
    ) -> Optional[MessageOut]:
        # Verify conversation belongs to user
        conv = await self.prisma.conversation.find_first(
            where={"id": conversation_id, "userId": user_id}
        )
        if not conv:
            return None

        data = {
            "id": message_id,
            "role": role,
            "content": content,
            "conversation": {"connect": {"id": conversation_id}},
        }
        
        if attachment:
            data["attachment"] = {
                "create": {
                    "id": attachment["id"],
                    "name": attachment["name"],
                    "size": attachment["size"],
                    "type": attachment["type"],
                }
            }

        msg = await self.prisma.message.create(
            data=data,
            include={"attachment": True}
        )

        # Update last_message and timestamp on conversation
        await self.prisma.conversation.update(
            where={"id": conversation_id},
            data={
                "lastMessage": content[:100],
                "timestamp": datetime.utcnow()
            }
        )

        return self._to_message_out(msg)

    async def get_messages(self, conversation_id: str, user_id: str) -> List[MessageOut]:
        conv = await self.get_conversation(conversation_id, user_id)
        if not conv:
            return []
            
        messages = await self.prisma.message.find_many(
            where={"conversationId": conversation_id},
            order={"timestamp": "asc"},
            include={"attachment": True}
        )
        return [self._to_message_out(m) for m in messages]

    # ── Serialization helpers ────────────────────────────────

    def _to_message_out(self, m) -> MessageOut:
        attachment = None
        if getattr(m, "attachment", None):
            attachment = AttachmentOut(
                id=m.attachment.id,
                name=m.attachment.name,
                size=m.attachment.size,
                type=m.attachment.type
            )
        return MessageOut(
            id=m.id,
            role=MessageRole(m.role),
            content=m.content,
            timestamp=m.timestamp,
            attachment=attachment,
        )

    def _to_conversation_out(self, c) -> ConversationOut:
        messages = []
        if getattr(c, "messages", None):
            messages = [self._to_message_out(m) for m in c.messages]
            
        return ConversationOut(
            id=c.id,
            title=c.title,
            last_message=c.lastMessage,
            timestamp=c.timestamp,
            messages=messages,
            contract_type=ContractType(c.contractType) if getattr(c, "contractType", None) else None,
            user_type=UserType(c.userType) if getattr(c, "userType", None) else None,
            verdict=ReportVerdict(c.verdict) if getattr(c, "verdict", None) else None,
            is_pinned=c.isPinned,
        )

    def _to_summary(self, c) -> ConversationSummaryOut:
        return ConversationSummaryOut(
            id=c.id,
            title=c.title,
            last_message=c.lastMessage,
            timestamp=c.timestamp,
            contract_type=ContractType(c.contractType) if getattr(c, "contractType", None) else None,
            user_type=UserType(c.userType) if getattr(c, "userType", None) else None,
            verdict=ReportVerdict(c.verdict) if getattr(c, "verdict", None) else None,
            is_pinned=c.isPinned,
        )


# Global singleton
store = PrismaStore()
