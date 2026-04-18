import asyncio

from .database.manager import DBManager


async def seed():
    db_manager = DBManager()
    await db_manager.init_db()

    db = await db_manager.get_db()

    files = []
    files.append((None, "Work", 0, 1, "yandex", "disk:/Work"))
    files.append((None, "Photos", 0, 1, "nextcloud", "nc:/Photos"))

    for i in range(1, 101):
        files.append((1, f"Report_2024_v{i}.pdf", 1024 * i, 0, "yandex", f"disk:/Work/repor"
                                                                         f"t_{i}.pdf"))

    for i in range(1, 101):
        files.append((2, f"Vacation_{i}.jpg", 2048 * i, 0, "nextcloud", f"nc:/Photos/img_{i}.jpg"))

    files.append((1, "Secret_Password.txt", 100, 0, "yandex", "disk:/Work/pass.txt"))
    files.append((1, "Презентация_финал_копия_2.pptx", 500000, 0, "yandex", "disk:/Work/pres.pptx"))

    await db.executemany(
        "INSERT INTO files (parent_id, name, size, is_dir, cloud_type, remote_path) VALUES (?,?,?,?,?,?)",
        files
    )
    await db.commit()
    print(f"База {db_manager.db_path} наполнена!")


if __name__ == "__main__":
    asyncio.run(seed())
