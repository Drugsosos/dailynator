from slack_sdk.web.async_slack_response import AsyncSlackResponse
from slack_sdk.web.async_client import AsyncWebClient

from src.db import Database

default_colors = ["#e8aeb7", "#b8e1ff", "#3c7a89", "#f4d06f", "#82aba1"]


async def parse_emoji_list(
        app: AsyncWebClient,
) -> list[str]:
    """
    Returns a list of emoji names

    :param app: App instance
    :return: List of all emoji names
    """

    emoji_r: AsyncSlackResponse = await app.emoji_list()
    return list(emoji_r.data.get("emoji", {':+1:'}).keys())


async def start_cron() -> None:
    """
    Adds cron triggered jobs to default async job store
    """

    from functools import partial
    from apscheduler.triggers.cron import CronTrigger
    from main import scheduler, app
    from src.report import start_daily
    from src.db import Database

    db = Database()

    # Get current cron as str
    cron_list = await db.get_all_cron_with_channels()

    for channel_id, team_id, cron in cron_list:
        # Skip if cron not set
        if not cron:
            from src.block_kit import error_block

            await app.client.chat_postMessage(
                channel=channel_id,
                text=":x: No scheduler was added",
                blocks=error_block(
                    header_text="No scheduler was added",
                    body_text="Can't start daily 'cause no scheduler was added.\n" +
                              "Use this to add schedule `/cron <* * * * *>`",
                ),
            )
            return

        # Get an instance of CronTrigger
        cron_trigger = CronTrigger().from_crontab(cron)

        # Schedule a job
        scheduler.add_job(
            func=partial(start_daily, channel_id=channel_id),  # Supply channel_id to start_daily
            trigger=cron_trigger,
            id=f"{team_id}_{channel_id}",
            replace_existing=True,
        )

    # Start Async scheduler
    if not scheduler.state:
        scheduler.start()


async def skip_cron(
        channel_id: str,
) -> None:
    """
    Skip next daily trigger time for specified channel

    :param channel_id: Slack channel id
    """

    from functools import partial
    from apscheduler.triggers.cron import CronTrigger
    from apscheduler.job import Job
    from main import scheduler, app
    from src.report import start_daily
    from src.db import Database

    db = Database()

    # Get channel cron and team_id
    channel_cron, team_id = await db.get_cron_by_channel_id(
        channel_id=channel_id,
    )

    # Send notification to channel if there is no cron or team id
    if not channel_cron or not team_id:
        from src.block_kit import error_block

        await app.client.chat_postMessage(
            channel=channel_id,
            text=":x: Can't skip scheduled daily",
            blocks=error_block(
                header_text="Can't skip scheduled daily",
                body_text="Schedule wasn't set or channel wasn't parsed properly",
            ),
        )

    from datetime import timedelta

    # Get previous job's trigger
    cron_job: Job = scheduler.get_job(
        job_id=f"{team_id}_{channel_id}",
    )

    cron_trigger: CronTrigger = cron_job.trigger

    # Get previous job's next fire datetime
    cron_trigger_next_fire_time = cron_trigger.get_next_fire_time(
        previous_fire_time=cron_job.next_run_time,  # noqa
        now=cron_job.next_run_time + timedelta(seconds=1),
    )

    # Set new start time
    cron_trigger.start_date = cron_trigger_next_fire_time

    # Update a job w/ trigger w/ new start time
    scheduler.add_job(
        func=partial(start_daily, channel_id=channel_id),  # Supply channel_id to start_daily
        trigger=cron_trigger,
        id=f"{team_id}_{channel_id}",
        replace_existing=True,
    )

    # Start Async scheduler
    if not scheduler.state:
        scheduler.start()


async def is_dm_in_command(
        client: AsyncWebClient,
        channel_id: str,
        channel_name: str,
        user_id: str,
) -> bool:
    """
    Checks if command was used in DM

    :param client: AsyncWebClient instance
    :param channel_id: Slack channel id
    :param channel_name: Slack channel name
    :param user_id: Slack user id
    :return: True if command was used in DM else False
    """

    # Catch if command was used in DM
    if channel_name == "directmessage":  # noqa
        from src.block_kit import error_block

        await client.chat_postEphemeral(
            channel=channel_id,
            text=":x: You can't use command in DMs",
            blocks=error_block(
                header_text="You can't use command in DMs",
                body_text="Open any available channel and send the command there",
            ),
            user=user_id,
        )
        return True
    return False


async def all_non_bot_members(
        client: AsyncWebClient,
        channel_id: str,
) -> list[str]:
    """
    Get all non bot members of the channel

    :param client: AsyncWebClient instance
    :param channel_id: Slack channel id
    :return: List of all non bot members
    """

    from asyncio import gather

    # Parse all members except bots
    raw_member_list = (await client.conversations_members(channel=channel_id))["members"]

    member_list = list()

    async def check_member_is_bot(
            user_id: str,
    ) -> None:
        """
        Wrapper for async check if member is bot and populating member list

        :param user_id: Slack channel id
        """
        if not (await client.users_info(user=user_id))["user"]["is_bot"]:
            member_list.append(user_id)

    async_tasks = list()

    for member in raw_member_list:
        async_tasks.append(
            check_member_is_bot(user_id=member)
        )

    await gather(*async_tasks)

    return member_list


async def create_user_with_real_name(
        client: AsyncWebClient,
        db_connection: Database,
        user_id: str,
        channel_id: str,
) -> None:
    """
    Wrapper for async creating new user in database w/ real_name

    :param client: ASyncWebClient instance
    :param db_connection: Database connection instance
    :param user_id: Slack user id
    :param channel_id: Slack channel id
    """

    real_name = (
            await client.users_info(
                user=user_id,
            )
        )["user"]["real_name"]

    await db_connection.create_user(
        user_id=user_id,
        daily_status=False,
        q_idx=0,
        main_channel_id=channel_id,
        real_name=real_name,
    )


async def create_multiple_user_with_real_name(
        client: AsyncWebClient,
        db_connection: Database,
        channel_id: str,
        member_list: list[str],
) -> None:
    """
    Create lots new users in database w/ real_name

    :param client: AsyncWebClient
    :param db_connection: Database connection instance
    :param channel_id: Slack channel id
    :param member_list: List of users to be created
    """

    from asyncio import gather
    async_tasks = list()

    for user in member_list:
        async_tasks.append(
            create_user_with_real_name(
                client=client,
                db_connection=db_connection,
                user_id=user,
                channel_id=channel_id,
            )
        )

    await gather(*async_tasks)
