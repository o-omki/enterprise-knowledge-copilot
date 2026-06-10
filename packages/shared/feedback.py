import logging
from typing import Literal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from packages.shared.orm_models import Feedback, Message

logger = logging.getLogger(__name__)


class FeedbackService:
    """Service for handling user feedback on AI-generated messages.

    Provides standard CRUD operations for the Feedback model.
    """

    def __init__(self, session: AsyncSession):
        self.session = session

    async def add_feedback(
        self,
        session_id: str,
        message_id: str,
        rating: Literal["up", "down"],
        comment: str | None = None,
    ) -> Feedback:
        """Records or updates user feedback for a specific message.

        Validates that the message belongs to the given session before recording.
        """
        # Validate that the message exists and belongs to the session
        stmt = select(Message).where(Message.id == message_id, Message.session_id == session_id)
        result = await self.session.execute(stmt)
        message = result.scalar_one_or_none()

        if not message:
            raise ValueError(f"Message {message_id} not found in session {session_id}")

        # Check if feedback already exists to potentially update it
        stmt_fb = select(Feedback).where(
            Feedback.message_id == message_id, Feedback.session_id == session_id
        )
        fb_result = await self.session.execute(stmt_fb)
        existing_feedback = fb_result.scalar_one_or_none()

        if existing_feedback:
            existing_feedback.rating = rating
            existing_feedback.comment = comment
            feedback_record = existing_feedback
            logger.info(f"Updated feedback for message {message_id}")
        else:
            feedback_record = Feedback(
                session_id=session_id,
                message_id=message_id,
                rating=rating,
                comment=comment,
            )
            self.session.add(feedback_record)
            logger.info(f"Created new feedback for message {message_id}")

        await self.session.commit()
        await self.session.refresh(feedback_record)
        return feedback_record

    async def get_feedback_for_message(self, message_id: str) -> Feedback | None:
        """Retrieves feedback for a specific message."""
        stmt = select(Feedback).where(Feedback.message_id == message_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_feedback_for_session(self, session_id: str) -> list[Feedback]:
        """Retrieves all feedback submitted within a specific session."""
        stmt = (
            select(Feedback).where(Feedback.session_id == session_id).order_by(Feedback.created_at)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
