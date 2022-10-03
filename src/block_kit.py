from typing import Sequence

from slack_sdk.models.attachments import BlockAttachment
from slack_sdk.models.blocks import MarkdownTextObject, DividerBlock, ContextBlock, Block


def report_attachment_block(
        header_text: str,
        body_text: str,
        color: str,
) -> BlockAttachment:
    from slack_sdk.models.blocks import HeaderBlock, SectionBlock

    return BlockAttachment(
        blocks=[
            HeaderBlock(text=header_text),
            SectionBlock(text=MarkdownTextObject(text=body_text))
        ],
        color=color
    )


def start_daily_block(
        header_text: str,
        body_text: str,
        first_question: str,
) -> Sequence[Block, Block]:
    return [
            ContextBlock(
                elements=[
                    MarkdownTextObject(
                        text=header_text,
                    ),
                ]
            ),
            DividerBlock(),
            MarkdownTextObject(
                text=body_text,
            ),
            MarkdownTextObject(
                text=first_question,
            ),
        ]


def end_daily_block(
        start_body_text: str,
        end_body_text: str,
) -> Sequence[Block, Block]:

    # TODO add link to the channel here
    return [
            MarkdownTextObject(
                text=start_body_text,
            ),
            MarkdownTextObject(
                text=end_body_text,
            ),
            DividerBlock()
        ]
