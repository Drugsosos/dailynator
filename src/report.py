from typing import Sequence

from slack_sdk.models.attachments import BlockAttachment
from slack_sdk.web.async_client import AsyncWebClient


async def post_report(
        app: AsyncWebClient,
        channel: str,
        attachments: Sequence[BlockAttachment],
        username: str,
        icon_url: str,
) -> None:
    """
    Posts a report to the specified channel

    :param app: Async App instance
    :param channel: Channel id
    :param attachments: Sequence of attachments
    :param username: Custom username
    :param icon_url: Custom icon url
    """

    from os import getenv

    # Collect kwargs from params
    kwargs = dict()
    kwargs["channel"] = channel
    kwargs["attachments"] = attachments
    kwargs["username"] = username
    kwargs["icon_url"] = icon_url
    kwargs["icon_emoji"] = None

    # Parse emoji if USE_AVATARS is set to False
    if getenv("USE_AVATARS").lower() == "false":
        from src.utils import parse_emoji_list
        from random import choice

        # Parse emoji list
        emoji_list = await parse_emoji_list(app=app)
        # Choose random emoji
        kwargs["icon_emoji"] = choice(emoji_list)

    await app.chat_postMessage(**kwargs)


async def start_daily(
        channel_id: str,
) -> None:
    from main import app
    from src.db import Database
    from src.block_kit import start_daily_block

    db = Database()
    await db.connect()

    # Get user_list
    user_list: list[str, str] = await db.get_all_users_by_channel_id(channel_id=channel_id)

    # Get first question
    first_question: str = (await db.get_all_questions())[0]

    for user in user_list:
        # Get users main channel
        user_main_channel = await db.get_user_main_channel(user_id=user)

        # Set user daily status & delete user's old idx
        await db.create_user(
            user_id=user,
            daily_status=True,
            q_idx=1,
            main_channel_id=user_main_channel,
        )

        # Delete old user's answers from Redis
        await db.delete_user_answers(user_id=user)

        # Get channel_id
        user_im_channel = (await app.client.conversations_open(users=user))["channel"]["id"]

        # Get user info
        user_info = (await app.client.users_info(user=user))["user"]

        # Send first question
        await app.client.chat_postMessage(
            channel=user_im_channel,
            blocks=start_daily_block(
                header_text=f"Hey, {user_info['real_name']}! :sun_with_face: ",
                body_text="*Daily time has come* :melting_face: ",
                first_question=first_question
            ),
        )
