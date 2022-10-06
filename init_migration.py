from sqlite3 import connect

db = connect("daily.db")


def init_migration():
    cursor = db.cursor()

    # Enable foreign_keys
    cursor.execute("PRAGMA foreign_keys = ON")

    # Create channels table
    cursor.execute(
        """\
create table channels (
    channel_id TEXT PRIMARY KEY NOT NULL,
    team_id TEXT NOT NULL,
    channel_name TEXT NOT NULL,
    cron TEXT
)\
"""
    )

    # Create users table
    cursor.execute(
        """\
create table users (
    user_id TEXT PRIMARY KEY NOT NULL,
    daily_status INTEGER NOT NULL default FALSE,
    q_idx INTEGER,
    main_channel_id TEXT NOT NULL,
    real_name TEXT NOT NULL,
    FOREIGN KEY (main_channel_id) REFERENCES channels (channel_id)
)\
"""
    )

    # Create questions table
    cursor.execute(
        """\
create table questions (
    channel_id TEXT NOT NULL,
    body TEXT NOT NULL,
    FOREIGN KEY (channel_id) REFERENCES channels (channel_id)
)\
"""
    )

    # Create answers table
    cursor.execute(
        """\
create table answers (
    user_id TEXT NOT NULL,
    question_id INT NOT NULL,
    answer TEXT NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users (user_id),
    FOREIGN KEY (question_id) REFERENCES users (ROWID)
)\
"""
    )

    # Create daily table
    cursor.execute(
        """\
create table daily (
    thread_ts text PRIMARY KEY NOT NULL,
    user_id TEXT NOT NULL,
    was_mentioned INTEGER NOT NULL default FALSE,
    FOREIGN KEY (user_id) REFERENCES users (user_id)
)\
"""
    )

    # Commit migration
    db.commit()

    # Close database connection
    cursor.close()


if __name__ == "__main__":
    init_migration()
