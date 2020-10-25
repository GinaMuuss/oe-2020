import enum
from sqlalchemy import Table, Column, Integer, ForeignKey, String, Boolean, Enum, Float
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.ext.automap import automap_base
from sqlalchemy.orm import Session
from sqlalchemy import create_engine
from sqlalchemy_utils import create_database, database_exists


Base = declarative_base()


association_table = Table(
    "actual_answers",
    Base.metadata,
    Column("answer_option", String(100), ForeignKey("answer_options.access_hash", ondelete='CASCADE')),
    Column("group", String(100), ForeignKey("groups.access_hash", ondelete='CASCADE')),
)


class User(Base):
    __tablename__ = "users"
    access_hash = Column(String(100), primary_key=True)
    group_id = Column(String(100), ForeignKey("groups.access_hash", ondelete='SET NULL'))
    group = relationship("Group", back_populates="users")


class Group(Base):
    __tablename__ = "groups"
    access_hash = Column(String(100), primary_key=True)
    name = Column(String(100))
    com_link = Column(String(200), unique=True)
    points = Column(Float, default=0)

    users = relationship("User")
    answers = relationship("AnswerOptions", secondary=association_table, back_populates="groups")


class QuestionState(enum.Enum):
    NEW = 1
    ACTIVE = 2
    FINISHED = 3


class Question(Base):
    __tablename__ = "questions"
    access_hash = Column(String(100), primary_key=True)
    status = Column(Enum(QuestionState))
    text = Column(String(2000))
    answers = relationship("AnswerOptions")

    def get_amount_answers(self):
        return sum([len(x.groups) for x in self.answers])


class AnswerOptions(Base):
    __tablename__ = "answer_options"
    access_hash = Column(String(100), primary_key=True)
    text = Column(String(2000))
    correct = Column(Boolean)
    points = Column(Float)
    question_id = Column(String(100), ForeignKey("questions.access_hash", ondelete='SET NULL'))
    question = relationship("Question", back_populates="answers")
    groups = relationship("Group", secondary=association_table, back_populates="answers")


class GameState(enum.Enum):
    NEW = 0
    GROUPS_HAVE_BEEN_ASSIGNED = 1


class Quiz(Base):
    __tablename__ = "quiz_meta"
    access_hash = Column(Integer, primary_key=True)
    last_finished_question_id = Column(String(100), ForeignKey("questions.access_hash", ondelete='SET NULL'))
    last_finished_question = relationship("Question")
    game_state = Column(Enum(GameState))


class DBHelper:
    def __init__(self, connection_str):
        self.connection_str = connection_str
        self._session = None

    def __enter__(self):
        if self._session:
            return self._session
        if not database_exists(self.connection_str):
            create_database(self.connection_str)
        engine = create_engine(self.connection_str)

        Base.metadata.create_all(engine)

        self._session = Session(engine)

        if not self._session.query(Quiz).first():
            quiz = Quiz(game_state=GameState.NEW)
            self._session.add(quiz)

        return self._session

    def __exit__(self, type, value, traceback):
        self._session.close()
        self._session = None