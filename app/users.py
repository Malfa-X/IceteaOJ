import asyncio
from datetime import datetime
from itertools import count

import bcrypt

from app.models import User, UserCreate, UserPublic, UserRole


class UserAlreadyExistsError(Exception):
    pass


class UserNotFoundError(Exception):
    pass


class InvalidCredentialsError(Exception):
    pass


class UserBannedError(Exception):
    pass


class UserRepository:
    def __init__(self):
        self._users: dict[str, User] = {}
        self._username_to_id: dict[str, str] = {}
        self._id_counter = count(1)
        self._lock = asyncio.Lock()

    async def initialize(self) -> None:
        async with self._lock:
            if "admin" not in self._username_to_id:
                admin = self._build_user(
                    user_id=str(next(self._id_counter)),
                    username="admin",
                    password="admintestpassword",
                    role=UserRole.ADMIN,
                )
                self._users[admin.user_id] = admin
                self._username_to_id[admin.username] = admin.user_id

    async def create_user(self, user_create: UserCreate) -> UserPublic:
        async with self._lock:
            if user_create.username in self._username_to_id:
                raise UserAlreadyExistsError(user_create.username)

            user = self._build_user(
                user_id=str(next(self._id_counter)),
                username=user_create.username,
                password=user_create.password,
                role=UserRole.USER,
            )
            self._users[user.user_id] = user
            self._username_to_id[user.username] = user.user_id

            return self.to_public(user)

    async def get_user(self, user_id: str) -> UserPublic:
        async with self._lock:
            if user_id not in self._users:
                raise UserNotFoundError(user_id)

            return self.to_public(self._users[user_id])

    async def get_user_internal(self, user_id: str) -> User:
        async with self._lock:
            if user_id not in self._users:
                raise UserNotFoundError(user_id)

            return self._users[user_id]

    async def authenticate(self, username: str, password: str) -> UserPublic:
        async with self._lock:
            user_id = self._username_to_id.get(username)
            if user_id is None:
                raise InvalidCredentialsError(username)

            user = self._users[user_id]
            if user.role == UserRole.BANNED:
                raise UserBannedError(username)

            if not bcrypt.checkpw(password.encode(), user.password_hash.encode()):
                raise InvalidCredentialsError(username)

            return self.to_public(user)

    async def update_role(self, user_id: str, role: UserRole) -> UserPublic:
        async with self._lock:
            if user_id not in self._users:
                raise UserNotFoundError(user_id)

            user = self._users[user_id].model_copy(update={"role": role})
            self._users[user_id] = user
            return self.to_public(user)

    @staticmethod
    def to_public(user: User) -> UserPublic:
        return UserPublic(
            user_id=user.user_id,
            username=user.username,
            join_time=user.join_time,
            role=user.role,
            submit_count=user.submit_count,
            resolve_count=user.resolve_count,
        )

    @staticmethod
    def _build_user(
        user_id: str,
        username: str,
        password: str,
        role: UserRole,
    ) -> User:
        password_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
        join_time = datetime.now().strftime("%Y-%m-%d")

        return User(
            user_id=user_id,
            username=username,
            password_hash=password_hash,
            join_time=join_time,
            role=role,
        )