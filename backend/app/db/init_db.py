from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.user import User, UserRole
from app.core.security import get_password_hash
from app.core.config import settings


async def init_db(db: AsyncSession) -> None:
    result = await db.execute(select(User).where(User.role == UserRole.admin))
    admin = result.scalar_one_or_none()
    if admin:
        return

    admin = User(
        username=settings.FIRST_ADMIN_USERNAME,
        email=settings.FIRST_ADMIN_EMAIL,
        hashed_password=get_password_hash(settings.FIRST_ADMIN_PASSWORD),
        role=UserRole.admin,
        is_active=True,
    )
    db.add(admin)
    await db.commit()
