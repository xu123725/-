from sqlalchemy import Column, Integer, String, DateTime, Text, Boolean
from sqlalchemy.ext.declarative import declarative_base
import datetime

Base = declarative_base()

class Question(Base):
    __tablename__ = 'questions'

    id = Column(Integer, primary_key=True, autoincrement=True)
    stem = Column(Text, nullable=False)
    options_json = Column(Text, nullable=False)
    answer = Column(Text, nullable=False)
    question_type = Column(String(50), nullable=False, default='single')
    category = Column(String(255), nullable=False, index=True)
    tag = Column(String(255), default='', index=True)
    difficulty = Column(Integer, nullable=False, index=True)
    analysis = Column(Text)
    source = Column(String(255), default='', index=True)
    hash_val = Column(String(255), nullable=False, unique=True)
    last_used_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

class UserLog(Base):
    __tablename__ = 'user_logs'

    id = Column(Integer, primary_key=True, autoincrement=True)
    question_id = Column(Integer, nullable=False, index=True)
    is_correct = Column(Integer, nullable=False, index=True)
    ts = Column(DateTime, default=datetime.datetime.utcnow)

class WrongQuestion(Base):
    __tablename__ = 'wrong_questions'

    id = Column(Integer, primary_key=True, autoincrement=True)
    question_id = Column(Integer, nullable=False, unique=True)
    wrong_count = Column(Integer, nullable=False, default=1, index=True)
    last_wrong_at = Column(DateTime, nullable=False, default=datetime.datetime.utcnow, index=True)
    is_archived = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime, nullable=False, default=datetime.datetime.utcnow)

class ImportedFile(Base):
    __tablename__ = 'imported_files'

    id = Column(Integer, primary_key=True, autoincrement=True)
    file_name = Column(String(255), nullable=False, index=True)
    file_signature = Column(String(255), nullable=False)
    question_count = Column(Integer, nullable=False, default=0)
    status = Column(String(50), nullable=False, default='done')
    stage = Column(String(50), nullable=False, default='done')
    error_code = Column(String(255), default='')
    last_error = Column(Text, default='')
    cleanup_done = Column(Integer, nullable=False, default=0)
    imported_at = Column(DateTime, nullable=False, default=datetime.datetime.utcnow)

class KnowledgeBase(Base):
    __tablename__ = 'knowledge_base'

    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(255))
    content = Column(Text, nullable=False)
    category = Column(String(255), default='general')
    source = Column(String(255))
    created_at = Column(DateTime, nullable=False, default=datetime.datetime.utcnow)

class Troubleshooting(Base):
    __tablename__ = 'troubleshooting'

    id = Column(Integer, primary_key=True, autoincrement=True)
    category = Column(String(255), nullable=False)
    title = Column(String(255), nullable=False)
    video_path = Column(String(255))
    doc_path = Column(String(255))
    image_path = Column(String(255))
    description = Column(Text)
    tags = Column(String(255))
    created_at = Column(DateTime, nullable=False, default=datetime.datetime.utcnow)