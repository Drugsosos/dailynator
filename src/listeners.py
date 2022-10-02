import logging

from slack_bolt.context.async_context import AsyncAck, AsyncSay, AsyncWebClient

from src.db import redis_instance
from test2 import app


@app.command("/channel_append")
async def channel_append_listener(
        ack: AsyncAck,
        say: AsyncSay,
        body: dict,
        client: AsyncWebClient,
        logger: logging.Logger,
):
    await ack()

    # If where aren't channels or channel is not in the list - add channel to the list
    if (
            not await redis_instance.llen("channels")
            or body["channel_id"].encode() not in await redis_instance.lrange("channels", 0, -1)
    ):
        await redis_instance.rpush("channels", body["channel_id"])

        await client.chat_postEphemeral(
            text="Added channel to daily bot :blush: ",
            channel=body["channel_id"],
            user=body["user_id"],
        )

        # Parse all members except for bots
        members_list = await client.conversations_members(channel=body["channel_id"])
        await redis_instance.rpush(
            "users",
            *[
                member for member in members_list["members"]
                if not (await client.users_info(user=member))["user"]["is_bot"]
            ]
        )

        await client.chat_postEphemeral(
            text="Parsed all users to the daily bot :robot_face: ",
            channel=body["channel_id"],
            user=body["user_id"],
        )
        return
    # Trash talk if bot is already in the channel
    await client.chat_postEphemeral(
        text="I'm already here :japanese_goblin: ",
        channel=body["channel_id"],
        user=body["user_id"],
    )


@app.command("/channel_pop")
async def channel_pop_listener(
        ack: AsyncAck,
        say: AsyncSay,
        body: dict,
        client: AsyncWebClient,
        logger: logging.Logger,
):
    await ack()

    # If the channel is in the list - delete it from the list
    if body["channel_id"].encode() in await redis_instance.lrange("channels", 0, -1):
        await redis_instance.lrem("channels", 0, body["channel_id"])

        await client.chat_postEphemeral(
            text="Deleted channel from daily bot :wave: ",
            channel=body["channel_id"],
            user=body["user_id"],
        )

        # Delete all members except for bots
        members_list = await client.conversations_members(channel=body["channel_id"])
        for member in members_list["members"]:
            if not (await client.users_info(user=member))["user"]["is_bot"]:
                await redis_instance.lrem(
                    "users",
                    0,
                    member,
                )

        await client.chat_postEphemeral(
            text="Deleted all users in the channel from the daily bot :skull_and_crossbones: ",
            channel=body["channel_id"],
            user=body["user_id"],
        )
        return
    # Trash talk if bot is already left
    await client.chat_postEphemeral(
        text="I don't do stuff here already :japanese_goblin: ",
        channel=body["channel_id"],
        user=body["user_id"],
    )


@app.event("member_joined_channel")
async def join_channel_listener(
        ack: AsyncAck,
        say: AsyncSay,
        body: dict,
        client: AsyncWebClient,
        logger: logging.Logger,
):
    if body["event"].get("subtype"):
        return

    await ack()

    await redis_instance.rpush("users", body["event"]["user"])

    # Parse user's real_name and creator_id
    real_name = (
        await client.users_info(
            user=body["event"]["user"])
    )["user"]["real_name"]

    creator_id = (
        await client.conversations_info(
            channel=body["event"]["channel"])
    )["channel"]["creator"]

    # Send a nice notification to the creator
    await client.chat_postEphemeral(
        text=f"User `{real_name}` joined and was added to daily bot :kangaroo: ",
        channel=body["event"]["channel"],
        user=creator_id,
    )


@app.event("member_left_channel")
async def leave_channel_listener(
        ack: AsyncAck,
        say: AsyncSay,
        body: dict,
        client: AsyncWebClient,
        logger: logging.Logger,
):
    if body["event"].get("subtype"):
        return

    await ack()

    await redis_instance.lrem("users", 0, body["event"]["user"])

    # Parse user's real_name and creator_id
    real_name = (
        await client.users_info(
            user=body["event"]["user"])
    )["user"]["real_name"]

    admin_id = (
        await client.conversations_info(
            channel=body["event"]["channel"])
    )["channel"]["creator"]

    # Send a nice notification to the creator
    await client.chat_postEphemeral(
        text=f"User `{real_name}` left and was removed from daily bot :cry: ",
        channel=body["event"]["channel"],
        user=admin_id,
    )


@app.command("/refresh_users")
async def refresh_users_listener(
        ack: AsyncAck,
        say: AsyncSay,
        body: dict,
        client: AsyncWebClient,
        logger: logging.Logger,
):
    await ack()

    # Delete set users
    await redis_instance.delete("users")

    # Parse and refresh all users in the channel
    members_list = await client.conversations_members(channel=body["channel_id"])
    await redis_instance.rpush(
        "users",
        *[
            member for member in members_list["members"]
            if not (await client.users_info(user=member))["user"]["is_bot"]
        ]
    )

    # Notification to the user
    await client.chat_postEphemeral(
        text="User list was updated :robot_face: ",
        channel=body["channel_id"],
        user=body["user_id"],
    )


@app.command("/questions")
async def questions_listener(
        ack: AsyncAck,
        say: AsyncSay,
        body: dict,
        client: AsyncWebClient,
        logger: logging.Logger,
):
    await ack()

    question_list = await redis_instance.lrange("questions", 0, -1)

    if not len(question_list):
        await client.chat_postEphemeral(
            text=f"None is available.\nAdd some with `/question_append How are you doing`",
            channel=body["channel_id"],
            user=body["user_id"],
        )
        return

    question_list_formatted = ""
    for idx, question in enumerate(question_list, start=1):
        question_list_formatted += f"{idx}.  {question.decode('utf-8')}.\n"

    # Send user list to user
    await client.chat_postEphemeral(
        text=f"Questions:\n{question_list_formatted}",
        channel=body["channel_id"],
        user=body["user_id"],
    )


@app.command("/question_append")
async def question_append_listener(
        ack: AsyncAck,
        say: AsyncSay,
        body: dict,
        client: AsyncWebClient,
        logger: logging.Logger,
):
    await ack()

    # If user specified the question add it and notify the user
    if body["text"]:
        await redis_instance.rpush(
            "questions",
            body["text"],
        )

        await client.chat_postEphemeral(
            text="Your question has been added to the daily bot :zap: ",
            channel=body["channel_id"],
            user=body["user_id"],
        )
        return

    # Else send the instructions
    await client.chat_postEphemeral(
        text="Enter the question after the command\nExample: `/question_append How are you doing`",
        channel=body["channel_id"],
        user=body["user_id"],
    )


@app.command("/question_pop")
async def question_pop_listener(
        ack: AsyncAck,
        say: AsyncSay,
        body: dict,
        client: AsyncWebClient,
        logger: logging.Logger,
):
    await ack()

    # If user specified the question add it and notify the user
    if body["text"]:
        try:
            body["text"] = int(body["text"])
        except ValueError:
            await client.chat_postEphemeral(
                text="Enter the index of the question you want to delete\nExample: `/question_pop 1` ",
                channel=body["channel_id"],
                user=body["user_id"],
            )
            return

        question_list = await redis_instance.lrange("questions", 0, -1)
        for idx, question in enumerate(question_list, start=1):
            if idx == int(body["text"]):
                await redis_instance.lrem(
                    "questions",
                    0,
                    question,
                )
                break

        await client.chat_postEphemeral(
            text="Your question has been removed from the daily bot :zap: ",
            channel=body["channel_id"],
            user=body["user_id"],
        )
        return

    # Else send the instructions
    await client.chat_postEphemeral(
        text="Enter the index after the command\nExample: `/question_pop 1`",
        channel=body["channel_id"],
        user=body["user_id"],
    )