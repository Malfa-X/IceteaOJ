import asyncio

import pytest

from app.models import UserCreate, UserRole
from app.users import (
    InvalidCredentialsError,
    UserAlreadyExistsError,
    UserBannedError,
    UserNotFoundError,
    UserRepository,
)


def test_repository_creates_initial_admin():
    async def run_test():
        repository = UserRepository()
        await repository.initialize()

        admin = await repository.authenticate("admin", "admintestpassword")

        assert admin.username == "admin"
        assert admin.role == UserRole.ADMIN
        assert admin.user_id == "1"

    asyncio.run(run_test())


def test_repository_creates_user_without_exposing_password_hash():
    async def run_test():
        repository = UserRepository()
        await repository.initialize()

        user = await repository.create_user(
            UserCreate(username="alice", password="password123")
        )

        assert user.username == "alice"
        assert user.role == UserRole.USER
        assert not hasattr(user, "password_hash")

    asyncio.run(run_test())


def test_repository_rejects_duplicate_username():
    async def run_test():
        repository = UserRepository()
        await repository.initialize()

        await repository.create_user(UserCreate(username="alice", password="password123"))

        with pytest.raises(UserAlreadyExistsError):
            await repository.create_user(
                UserCreate(username="alice", password="password456")
            )

    asyncio.run(run_test())


def test_repository_authenticates_user():
    async def run_test():
        repository = UserRepository()
        await repository.initialize()

        created = await repository.create_user(
            UserCreate(username="alice", password="password123")
        )
        authenticated = await repository.authenticate("alice", "password123")

        assert authenticated.user_id == created.user_id
        assert authenticated.username == "alice"

    asyncio.run(run_test())


def test_repository_rejects_invalid_credentials():
    async def run_test():
        repository = UserRepository()
        await repository.initialize()

        await repository.create_user(UserCreate(username="alice", password="password123"))

        with pytest.raises(InvalidCredentialsError):
            await repository.authenticate("alice", "wrong-password")

        with pytest.raises(InvalidCredentialsError):
            await repository.authenticate("missing", "password123")

    asyncio.run(run_test())


def test_repository_updates_user_role_and_blocks_banned_login():
    async def run_test():
        repository = UserRepository()
        await repository.initialize()

        user = await repository.create_user(
            UserCreate(username="alice", password="password123")
        )

        updated_user = await repository.update_role(user.user_id, UserRole.BANNED)
        assert updated_user.role == UserRole.BANNED

        with pytest.raises(UserBannedError):
            await repository.authenticate("alice", "password123")

    asyncio.run(run_test())


def test_repository_rejects_missing_user():
    async def run_test():
        repository = UserRepository()
        await repository.initialize()

        with pytest.raises(UserNotFoundError):
            await repository.get_user("missing")

        with pytest.raises(UserNotFoundError):
            await repository.update_role("missing", UserRole.ADMIN)

    asyncio.run(run_test())