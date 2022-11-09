import json
from pathlib import Path
from models import User, UserMark, Mark, ViewHistory
from postgres_db import VKinderPostgresqlDB
from sqlalchemy.exc import OperationalError, IntegrityError


def main():
    file_path = str(Path(__file__).parents[2]) + '/info_not_for_git/postgresql.json'
    with open(file_path) as f:
        creds = json.load(f)
    try:
        VKinder_DB = VKinderPostgresqlDB('vkinder_db', creds)
        session = VKinder_DB.new_session()
        with session:
            try:
                VKinder_DB.add_row(session=session, model=User, data={'user_id': 123})
                session.commit()
            except IntegrityError:
                session.rollback()
    except OperationalError as err:
        print('Ошибка подключения к БД:', err)


if __name__ == "__main__":
    main()
