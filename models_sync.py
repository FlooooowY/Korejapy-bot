from database_sync import get_session, User, Payment, Broadcast
from typing import Optional


class UserModel:
    @staticmethod
    def get_or_create_user(telegram_id: int, username: str = None, 
                          first_name: str = None, last_name: str = None) -> User:
        """Получить или создать пользователя"""
        session = get_session()
        try:
            user = session.query(User).filter_by(telegram_id=telegram_id).first()
            
            if not user:
                user = User(
                    telegram_id=telegram_id,
                    username=username,
                    first_name=first_name,
                    last_name=last_name,
                    role='client'
                )
                session.add(user)
                session.commit()
                session.refresh(user)
            else:
                user.username = username
                user.first_name = first_name
                user.last_name = last_name
                session.commit()
            
            return user
        finally:
            session.close()
    
    @staticmethod
    def get_user(telegram_id: int) -> Optional[User]:
        """Получить пользователя по telegram_id"""
        session = get_session()
        try:
            return session.query(User).filter_by(telegram_id=telegram_id).first()
        finally:
            session.close()
    
    @staticmethod
    def update_role(telegram_id: int, role: str) -> bool:
        """Обновить роль пользователя"""
        session = get_session()
        try:
            user = session.query(User).filter_by(telegram_id=telegram_id).first()
            if user:
                user.role = role
                session.commit()
                return True
            return False
        finally:
            session.close()
    
    @staticmethod
    def add_points(telegram_id: int, points: float) -> bool:
        """Добавить баллы пользователю"""
        session = get_session()
        try:
            user = session.query(User).filter_by(telegram_id=telegram_id).first()
            if user:
                user.loyalty_points += points
                session.commit()
                return True
            return False
        finally:
            session.close()
    
    @staticmethod
    def spend_points(telegram_id: int, points: float) -> bool:
        """Списать баллы у пользователя"""
        session = get_session()
        try:
            user = session.query(User).filter_by(telegram_id=telegram_id).first()
            if user and user.loyalty_points >= points:
                user.loyalty_points -= points
                session.commit()
                return True
            return False
        finally:
            session.close()
    
    @staticmethod
    def get_all_users():
        """Получить всех пользователей"""
        session = get_session()
        try:
            return session.query(User).all()
        finally:
            session.close()


class PaymentModel:
    @staticmethod
    def create_payment(client_id: int, seller_id: int, amount: float,
                      points_earned: float = 0, points_spent: float = 0,
                      qr_code_path: str = None, description: str = None) -> Payment:
        """Создать запись об оплате"""
        session = get_session()
        try:
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
            session.commit()
            session.refresh(payment)
            return payment
        finally:
            session.close()


class BroadcastModel:
    @staticmethod
    def create_broadcast(sender_id: int, message_text: str) -> Broadcast:
        """Создать запись о рассылке"""
        session = get_session()
        try:
            broadcast = Broadcast(
                sender_id=sender_id,
                message_text=message_text
            )
            session.add(broadcast)
            session.commit()
            session.refresh(broadcast)
            return broadcast
        finally:
            session.close()
    
    @staticmethod
    def update_sent_count(broadcast_id: int, count: int):
        """Обновить количество отправленных сообщений"""
        session = get_session()
        try:
            broadcast = session.query(Broadcast).get(broadcast_id)
            if broadcast:
                broadcast.sent_count = count
                session.commit()
        finally:
            session.close()

