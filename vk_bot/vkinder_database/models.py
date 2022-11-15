"""Модели таблиц базы данных проекта VKinder"""
import sqlalchemy as sa
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


class User(Base):
    __tablename__ = "user"
    user_id = sa.Column(sa.Integer, primary_key=True)

    # user_marks = relationship("UserMark", back_populates="user")
    # view_histories = relationship("ViewHistory", back_populates="user")

    def __str__(self):
        return f"Пользователь бота с VK_ID: {self.user_id}"


class UserMark(Base):
    __tablename__ = "user_mark"
    user_id = sa.Column(sa.Integer, sa.ForeignKey("user.user_id"), nullable=False)
    # marked_user_id = sa.Column(sa.Integer, sa.ForeignKey("user.user_id"), nullable=False)
    marked_user_id = sa.Column(sa.Integer, nullable=False)
    mark_id = sa.Column(sa.Integer, sa.ForeignKey("mark.mark_id"), nullable=False)
    __table_args__ = (sa.PrimaryKeyConstraint("user_id", "marked_user_id"),)

    user = relationship("User", foreign_keys=[user_id])
    # marked_user = relationship("User", foreign_keys=[marked_user_id])
    mark = relationship("Mark", foreign_keys=[mark_id])

    # mark = relationship("Mark", back_populates="user_marks")

    def __str__(self):
        return f"Отметка '{self.mark_id}', поставленная пользователем {self.user_id} пользователю {self.marked_user_id}"


class Mark(Base):
    __tablename__ = "mark"
    mark_id = sa.Column(sa.Integer, primary_key=True)
    name = sa.Column(sa.String(length=50), nullable=False)

    # user_marks = relationship("UserMark", back_populates="mark")

    def __str__(self):
        return f"Отметка '{self.mark_id}' - {self.name}"


class ViewHistory(Base):
    __tablename__ = "view_history"
    view_id = sa.Column(sa.Integer, primary_key=True)
    viewer_id = sa.Column(sa.Integer, sa.ForeignKey("user.user_id"), nullable=False)
    viewed_id = sa.Column(sa.Integer, nullable=False)
    view_date = sa.Column(sa.DateTime, nullable=False)

    viewer = relationship("User", foreign_keys=[viewer_id])
    # viewed = relationship("User", foreign_keys=[viewed_id])

    # user = relationship("User", back_populates="view_histories")

    def __str__(self):
        return f"Просмотр ID {self.viewed_id}: Пользователь {self.viewer_id} посмотрел пользователя {self.viewed_id} " \
               f"{self.view_date}"
