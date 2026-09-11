"""VPS-only integration smoke test. Inserts tagged negative-ID users; cleans up.

Run before accepting traffic. Sequences advance normally and are never reset.
No Telegram API calls, no TRUNCATE/DROP, no edits to existing application rows.
"""
import asyncio
import secrets
import sys
import uuid

from sqlalchemy import delete, event, func, inspect, select, UniqueConstraint
from sqlalchemy.exc import IntegrityError

from app.database import Base, async_session, engine, verify_schema
from app.models import AdminContact, Appeal, Suggestion, User
from app.services.admin_contact_service import create_admin_contact, claim_admin_contact
from app.services.appeal_service import create_appeal, claim_appeal
from app.services.suggestion_service import create_suggestion
from app.services.user_service import save_user, save_user_location, get_user_by_telegram_id


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def inspect_schema(connection):
    inspector = inspect(connection)
    require(set(Base.metadata.tables) <= set(inspector.get_table_names()), "Missing tables")
    for table in Base.metadata.sorted_tables:
        constraints = inspector.get_unique_constraints(table.name)
        for expected in table.constraints:
            if isinstance(expected, UniqueConstraint):
                require(any(c["column_names"] == [col.name for col in expected.columns]
                            for c in constraints), "Missing unique constraint")
        indexes = inspector.get_indexes(table.name)
        for expected in table.indexes:
            require(any(i["name"] == expected.name and i["unique"] == expected.unique
                        and i["column_names"] == [c.name for c in expected.columns] for i in indexes),
                    "Missing or incorrect unique index")
        foreign_keys = inspector.get_foreign_keys(table.name)
        for fk in table.foreign_keys:
            require(any(fk.parent.name in f["constrained_columns"] and
                        f["referred_table"] == fk.column.table.name and
                        fk.column.name in f["referred_columns"] for f in foreign_keys), "Missing FK")
    from alembic.autogenerate import compare_metadata
    from alembic.migration import MigrationContext
    require(not compare_metadata(MigrationContext.configure(connection), Base.metadata), "Schema drift")


async def settled(*operations):
    results = await asyncio.gather(*operations, return_exceptions=True)
    for result in results:
        if isinstance(result, BaseException):
            raise result
    return results


async def validate():
    require(engine.dialect.name == "postgresql", "Validation requires PostgreSQL")
    await verify_schema()
    async with engine.connect() as connection:
        await connection.run_sync(inspect_schema)
        require((await connection.exec_driver_sql("SELECT version_num FROM alembic_version")).scalar_one()
                == "b9a1e47cb84b", "Unexpected baseline revision")
        require((await connection.exec_driver_sql("SHOW timezone")).scalar_one() == "UTC", "Non-UTC session")
    print("PASS: revision b9a1e47cb84b, tables, indexes, unique constraints, foreign keys, schema and UTC")
    await validate_services()


async def validate_services(*, cleanup_tasks=None):
    """Default: always clean up. Preparation can defer cleanup to its stage 7.

    In deferred mode a failed integration stage stops without further database
    operations; the caller must not claim cleanup succeeded.
    """
    tag = "vps-validation-" + uuid.uuid4().hex
    base = -(secrets.randbits(60) + 100)
    ids = [base - i for i in range(4)]
    models = [(Appeal, "appeal_number", "MUR"), (Suggestion, "suggestion_number", "TAK"),
              (AdminContact, "contact_number", "ADM")]
    observed = set()

    def check_placeholder(mapper, connection, target):
        for model, column, _ in models:
            if isinstance(target, model):
                number = getattr(target, column)
                require(number.startswith("TMP-") and len(number) == 20, "Invalid temporary number")
                observed.add(model)

    # Refuse even a highly improbable collision with another validation run.
    async with async_session() as session:
        require(not (await session.execute(select(User.id).where(User.telegram_id.in_(ids)))).all(),
                "Test identity collision; rerun validation")
    for model, _, _ in models:
        event.listen(model, "before_insert", check_placeholder)
    try:
        user = await save_user(ids[0], tag, tag, "+998900000000")
        updated = await save_user(ids[0], tag, "Updated validation", "+998900000001")
        require(updated.id == user.id and updated.phone == "+998900000001", "User update failed")
        await save_user_location(ids[0], "Test region", "Test district")
        await save_user(ids[0], tag, tag, "+998900000002")
        current = await get_user_by_telegram_id(ids[0])
        require((current.region, current.district) == ("Test region", "Test district"), "Location lost")
        await settled(*(save_user(ids[1], tag, tag, "+998900000003") for _ in range(12)))
        await settled(*(save_user_location(ids[1], "R", "D") for _ in range(8)))
        require((await get_user_by_telegram_id(ids[1])).full_name == tag, "Profile lost")
        print("PASS: create/update and concurrent user/profile/location writes")

        async def submit(i):
            return (await create_appeal(ids[0], tag), await create_suggestion(ids[0], tag),
                    await create_admin_contact(ids[2], tag, tag))
        results = await settled(*(submit(i) for i in range(8)))
        require(observed == {Appeal, Suggestion, AdminContact}, "Missing INSERT coverage")
        for index, (model, column, prefix) in enumerate(models):
            rows = [r[index] for r in results]
            require(len({getattr(r, column) for r in rows}) == 8, "Duplicate public number")
            require(all(getattr(r, column) == f"{prefix}-{r.id:06d}" for r in rows), "Wrong public format")
        for claim, row in [(claim_appeal, results[0][0]), (claim_admin_contact, results[0][2])]:
            claims = await settled(claim(row.id, 101), claim(row.id, 102))
            require(sum(won for _, won in claims) == 1, "Claim race")
        async with async_session() as session:
            for telegram_id in ids[:3]:
                require(await session.scalar(select(func.count()).select_from(User).where(User.telegram_id == telegram_id)) == 1,
                        "Duplicate/missing user")
        print("PASS: concurrent submissions, bounded placeholders, public numbers and claims")

        for model, _, _ in models:
            event.remove(model, "before_insert", check_placeholder)

        async def must_reject(row):
            try:
                async with async_session() as session, session.begin():
                    session.add(row)
            except IntegrityError:
                return
            raise RuntimeError("Constraint did not reject invalid record")

        await must_reject(User(telegram_id=ids[0]))
        for index, (model, column, _) in enumerate(models):
            body = "appeal_text" if model is Appeal else "suggestion_text" if model is Suggestion else "message_text"
            await must_reject(model(**{column: getattr(results[0][index], column), "user_id": user.id, body: tag}))
            await must_reject(model(**{column: "FK-" + secrets.token_hex(8), "user_id": -1, body: tag}))
        print("PASS: duplicate identifiers and orphan foreign keys rejected")

        class InjectedFailure(Exception):
            pass

        def fail_final(mapper, connection, target):
            raise InjectedFailure()

        calls = [lambda: create_appeal(ids[0], tag), lambda: create_suggestion(ids[0], tag),
                 lambda: create_admin_contact(ids[3], tag, tag)]
        for (model, _, _), call in zip(models, calls):
            async with async_session() as session:
                before = await session.scalar(select(func.count()).select_from(model))
            event.listen(model, "before_update", fail_final)
            try:
                try:
                    await call()
                except InjectedFailure:
                    pass
                else:
                    raise RuntimeError("Rollback injection did not run")
            finally:
                event.remove(model, "before_update", fail_final)
            async with async_session() as session:
                require(await session.scalar(select(func.count()).select_from(model)) == before, "Insert not rolled back")
        require(await get_user_by_telegram_id(ids[3]) is None, "Minimal contact user not rolled back")
        print("PASS: transaction rollback for all submission services")
    finally:
        for model, _, _ in models:
            if event.contains(model, "before_insert", check_placeholder):
                event.remove(model, "before_insert", check_placeholder)
        async def cleanup():
            async with async_session() as session, session.begin():
                owned = select(User.id).where(User.telegram_id.in_(ids), User.telegram_username == tag)
                for model, _, _ in models:
                    await session.execute(delete(model).where(model.user_id.in_(owned)))
                await session.execute(delete(User).where(User.telegram_id.in_(ids), User.telegram_username == tag))
            async with async_session() as session:
                require(not (await session.execute(select(User.id).where(User.telegram_id.in_(ids), User.telegram_username == tag))).all(),
                        "Cleanup incomplete")
            print("PASS: run-owned test records removed; sequences intentionally not reset")

        if cleanup_tasks is None:
            await cleanup()
        else:
            cleanup_tasks.append(cleanup)



if __name__ == "__main__":
    if sys.argv[1:] != ["--confirm-test-records"]:
        raise SystemExit("Use --confirm-test-records on the VPS before accepting traffic")
    try:
        from app.migrate import migrate
        asyncio.run(migrate())
        async def run():
            try:
                await validate()
            finally:
                await engine.dispose()
        asyncio.run(run())
    except Exception as exc:
        raise SystemExit(f"FAIL: {type(exc).__name__}; validation stopped (connection details omitted)")
