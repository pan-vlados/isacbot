import logging
from email.message import EmailMessage
from email.utils import formatdate
from pathlib import Path
from ssl import Purpose, create_default_context
from typing import TYPE_CHECKING

import aiofiles
import aiosmtplib
import pandas as pd
from aiosmtplib.smtp import SMTP_TLS_PORT


if TYPE_CHECKING:
    from collections.abc import Iterable
    from ssl import SSLContext

    from aiosmtplib import SMTPResponse
    from pandas import DataFrame


logger = logging.getLogger(__name__)


class SMTPClient:
    account: str
    context: 'SSLContext'
    server: aiosmtplib.SMTP

    def __init__(self, /, *, username: str, password: str, hostname: str) -> None:
        self.account = username
        self.context = create_default_context(
            purpose=Purpose.SERVER_AUTH
        )  # Create a secure SSL context and load system CAs
        self.server = aiosmtplib.SMTP(
            username=username,
            password=password,
            hostname=hostname,
            port=SMTP_TLS_PORT,
            use_tls=True,
            tls_context=self.context,
            timeout=60,  # default is 60
        )

    async def send_message(
        self, /, *, message: 'EmailMessage'
    ) -> tuple[dict[str, 'SMTPResponse'], str]:
        async with self.server as client:
            return await client.send_message(message, timeout=5)

    async def create_message(
        self,
        /,
        *,
        from_: str | None = None,
        to_: str,
        subject_: str,
        content_: str = '',
        attachments_: 'Iterable[DataFrame] | None' = None,
    ) -> EmailMessage | None:
        """Create email message with optional attachments as `Iterable[DataFrame]`.

        If there are attachments, create a corresponding Excel file for each attachment
        and add them to the message.
        Return `EmailMessage` if the message was successfully created, otherwise if any error
        occurs, return `None`.
        """
        message = EmailMessage()
        message['From'] = self.account if from_ is None else from_
        message['To'] = to_
        message['Subject'] = subject_
        message['Date'] = formatdate(localtime=True)
        message.set_content(content_, 'plain')

        if not attachments_:
            return message

        for data in attachments_:
            async with aiofiles.tempfile.NamedTemporaryFile(
                mode='wb', delete=False, suffix='.xlsx'
            ) as tmp_file:
                tmp_file_path = Path(tmp_file.name)  # type: ignore
            try:
                with pd.ExcelWriter(path=tmp_file_path, mode='w') as writer:
                    data.to_excel(excel_writer=writer, index=False)
                async with aiofiles.open(file=tmp_file_path, mode='rb') as file:
                    message.add_attachment(
                        await file.read(),
                        maintype='application',
                        subtype='vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                        filename=tmp_file_path.name,
                    )
            except Exception:
                logger.exception('Error while saving data into xlsx file.')
                return None
            finally:
                tmp_file_path.unlink()
        return message
