from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime
from sqlalchemy.sql import func
from .database import SessionLocal
from .database import Base
import logging


logging.basicConfig(level=logging.INFO)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


class User(Base):
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True)
    username = Column(String, unique=True, nullable=False)
    password = Column(String, nullable=False)


class Law(Base):
    __tablename__ = 'laws'

    id = Column(Integer, primary_key=True)
    chapter_title = Column(String)
    article_title = Column(String)
    paragraph_num = Column(String)
    item_num = Column(Float)
    item_title = Column(String)
    sentense_text = Column(String)
    references = Column(String)
    # このテーブルは元々のQuizテーブルと同じですが、名前がLawsに変わっています。


class Quiz(Base):
    __tablename__ = 'quizzes'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    question_text = Column(String, nullable=False)
    options = Column(String, nullable=False)  # JSON形式で保存する場合
    correct_choice = Column(Integer, nullable=False)
    user_answer = Column(Integer, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
