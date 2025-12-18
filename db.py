import asyncpg
from config import DB_HOST, DB_NAME, DB_PASSWORD, DB_PORT, DB_USER

_pool = None


async def init_pool():
    global _pool
    if _pool is None:
        _pool = await init_db_pool()
    return _pool


async def close_pool():
    global _pool
    if _pool is not None:
        await _pool.close()
        _pool = None


async def init_db_pool():
    pool = await asyncpg.create_pool(
        host=DB_HOST,
        port=int(DB_PORT),
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME,
    )
    return pool


async def create_ticket(data: dict):
    async with _pool.acquire() as coon:
        async with coon.transaction():

            colums = [
                "user_id",
                "username",
                "name",
                "org",
                "city",
                "direction",
                "description",
                "phone",
                "manager_id",
            ]

            sql_insert = f"""
                INSERT INTO tickets ({','.join(colums)})
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                RETURNING id

            """

            values = [data[col] for col in colums]

            ticked_id = await coon.fetchval(sql_insert, *values)
            return ticked_id


async def get_ticket_status(id):
    async with _pool.acquire() as conn:
        s = await conn.fetchval("SELECT status FROM tickets WHERE id = $1", id)
        return s


async def set_ticket_status(id: int, status: str):
    async with _pool.acquire() as conn:
        close_at = await conn.fetchval(
            """
            UPDATE tickets 
            SET status = $1::varchar(20),
                close_at = CASE WHEN $1::varchar(20) = 'closed' THEN NOW() ELSE NULL END 
            WHERE id = $2
            RETURNING close_at;
            """,
            status,
            id,
        )
        return close_at


async def get_ticket(ticket_id):
    async with _pool.acquire() as conn:

        columns = [
            "id",
            "name",
            "username",
            "org",
            "city",
            "direction",
            "description",
            "phone",
            "status",
        ]

        sql_select = f"""
            SELECT {','.join(columns)} FROM tickets
            WHERE id = $1
        """
        ticket = await conn.fetchrow(sql_select, ticket_id)
        return dict(ticket) if ticket else None
