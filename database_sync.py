from sqlalchemy import create_engine, Column, Integer, String, Float, Boolean, DateTime, Text, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import os
from dotenv import load_dotenv

load_dotenv()

Base = declarative_base()


class User(Base):
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True)
    telegram_id = Column(Integer, unique=True, nullable=False)
    username = Column(String(255), nullable=True)
    first_name = Column(String(255), nullable=True)
    last_name = Column(String(255), nullable=True)
    role = Column(String(50), default='client')
    loyalty_points = Column(Float, default=0.0)
    created_at = Column(DateTime, default=datetime.utcnow)
    is_active = Column(Boolean, default=True)


class Payment(Base):
    __tablename__ = 'payments'
    
    id = Column(Integer, primary_key=True)
    client_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    seller_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    amount = Column(Float, nullable=False)
    points_earned = Column(Float, default=0.0)
    points_spent = Column(Float, default=0.0)
    qr_code_path = Column(String(500), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    description = Column(Text, nullable=True)


class Broadcast(Base):
    __tablename__ = 'broadcasts'
    
    id = Column(Integer, primary_key=True)
    sender_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    message_text = Column(Text, nullable=False)
    sent_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)


# Настройка базы данных (синхронная версия)
DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///korejapy_bot.db').replace('sqlite+aiosqlite://', 'sqlite:///')
engine = create_engine(DATABASE_URL, echo=False)
Session = sessionmaker(bind=engine)


def init_db():
    """Инициализация базы данных"""
    Base.metadata.create_all(engine)


def get_session():
    """Получить сессию базы данных"""
    return Session()

