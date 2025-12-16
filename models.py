from database import async_session, User, Payment, Broadcast
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional


class UserModel:
    @staticmethod
    async def get_or_create_user(telegram_id: int, username: str = None, 
                                 first_name: str = None, last_name: str = None) -> User:
        """Получить или создать пользователя"""
        async with async_session() as session:
            result = await session.execute(
                select(User).where(User.telegram_id == telegram_id)
            )
            user = result.scalar_one_or_none()
            
            if not user:
                user = User(
                    telegram_id=telegram_id,
                    username=username,
                    first_name=first_name,
                    last_name=last_name,
                    role='client'
                )
                session.add(user)
                await session.commit()
                await session.refresh(user)
            else:
                # Обновляем информацию о пользователе
                user.username = username
                user.first_name = first_name
                user.last_name = last_name
                await session.commit()
            
            return user
    
    @staticmethod
    async def get_user(telegram_id: int) -> Optional[User]:
        """Получить пользователя по telegram_id"""
        async with async_session() as session:
            result = await session.execute(
                select(User).where(User.telegram_id == telegram_id)
            )
            return result.scalar_one_or_none()
    
    @staticmethod
    async def update_role(telegram_id: int, role: str) -> bool:
        """Обновить роль пользователя"""
        async with async_session() as session:
            await session.execute(
                update(User)
                .where(User.telegram_id == telegram_id)
                .values(role=role)
            )
            await session.commit()
            return True
    
    @staticmethod
    async def add_points(telegram_id: int, points: float) -> bool:
        """Добавить баллы пользователю"""
        async with async_session() as session:
            user = await session.execute(
                select(User).where(User.telegram_id == telegram_id)
            )
            user = user.scalar_one_or_none()
            if user:
                user.loyalty_points += points
                await session.commit()
                return True
            return False
    
    @staticmethod
    async def spend_points(telegram_id: int, points: float) -> bool:
        """Списать баллы у пользователя"""
        async with async_session() as session:
            user = await session.execute(
                select(User).where(User.telegram_id == telegram_id)
            )
            user = user.scalar_one_or_none()
            if user and user.loyalty_points >= points:
                user.loyalty_points -= points
                await session.commit()
                return True
            return False
    
    @staticmethod
    async def get_all_users() -> list[User]:
        """Получить всех пользователей"""
        async with async_session() as session:
            result = await session.execute(select(User))
            return list(result.scalars().all())


class PaymentModel:
    @staticmethod
    async def create_payment(client_id: int, seller_id: int, amount: float,
                            points_earned: float = 0, points_spent: float = 0,
                            qr_code_path: str = None, description: str = None) -> Payment:
        """Создать запись об оплате"""
        async with async_session() as session:
            payment = Payment(
                client_id=client_id,
                seller_id=seller_id,
                amount=amount,
                points_earned=points_earned,
                points_spent=points_spent,
                qr_code_path=qr_code_path,
                description=description
            )
            session.add(payment)
            await session.commit()
            await session.refresh(payment)
            return payment


class BroadcastModel:
    @staticmethod
    async def create_broadcast(sender_id: int, message_text: str) -> Broadcast:
        """Создать запись о рассылке"""
        async with async_session() as session:
            broadcast = Broadcast(
                sender_id=sender_id,
                message_text=message_text
            )
            session.add(broadcast)
            await session.commit()
            await session.refresh(broadcast)
            return broadcast
    
    @staticmethod
    async def update_sent_count(broadcast_id: int, count: int):
        """Обновить количество отправленных сообщений"""
        async with async_session() as session:
            broadcast = await session.get(Broadcast, broadcast_id)
            if broadcast:
                broadcast.sent_count = count
                await session.commit()

