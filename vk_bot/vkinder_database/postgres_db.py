"""Класс-обертка для базы данных проекта VKinder"""
import sqlalchemy as sa
from sqlalchemy.orm import sessionmaker

from models import Base


class VKinderPostgresqlDB:
    """Wrapper class for VKinder postgres database"""

    def __init__(self, db_name, credentials):
        self.db_name = db_name
        self.db_user = credentials.get('user')
        self.db_pass = credentials.get('pass')
        self._engine = self.create_db_engine()
        self.create_tables()
        self.class_session = sessionmaker(bind=self._engine)

    def create_db_engine(self, host='localhost', port=5432):
        DSN = f'postgresql://{self.db_user}:{self.db_pass}@{host}:{port}/{self.db_name}'
        engine = sa.create_engine(DSN)
        return engine

    def create_tables(self):
        # Base.metadata.drop_all(self._engine)
        Base.metadata.create_all(self._engine)

    def new_session(self):
        session = self.class_session()
        return session

    # @staticmethod
    # def new_row(model, data):
    #     return model(**data)

    @staticmethod
    def add_row(session, model, data):
        row = model(**data)
        session.add(row)
        return session
