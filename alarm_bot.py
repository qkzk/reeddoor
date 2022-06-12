"""
title: qdoor alarm telegram bot
author: qkzk
date: 2022/06/11

Telegram bot alerting me of openings and closing of my door.
Recognize a few commands to help me monitoor Qdoor.
"""
import logging
import datetime
import os

from telegram import Update, KeyboardButton, ReplyKeyboardMarkup
from telegram.ext import (
    Application,
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
)
from bot_token import TOKEN, QKZKID


HELP_MESSAGE = """Hello qkzk 🍺! I'm qdoor alarm bot 🍇🐍🚪🚨
Use :
/help: to see this help message,
/status: to display the alarm status,
/alarm [verbose]: to set the alarm. Verbose will spam you,
/stop: to stop the alarm,
/last: to get last line of logfile,
/lines: to show last 10 lines,

I'm running since {}.
"""
LOGFILE_OPENINGS = "/home/pi/reeddoorlog/ouvertures.log"

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)


class DoorStatus:
    """Holds a door status read of opening logfile"""

    def __init__(self, dt: datetime.datetime, level: str, caller: str, msg: str):
        self.datetime = dt
        self.level = level
        self.caller = caller
        self.msg = msg

    @classmethod
    def from_line(cls, line: str):
        """Parse a line of log"""
        dt = datetime.datetime.strptime(line[:19], "%Y-%m-%d %H:%M:%S")
        elems = line.split(" ")
        level = elems[2]
        caller = elems[3].split("(")[0]
        msg = " ".join(elems[4:]).strip()
        return cls(dt, level, caller, msg)

    def __repr__(self):
        return f"{self.datetime}\n      🦕  {self.msg}"


class DoorWatcher:
    """Record the last status of the door, run the alarm"""

    def __init__(self):
        self.started_time = datetime.datetime.now()
        self._last_status = self.__read_last_line()
        self._last_edit = self.__get_modification_time()
        self._verbose = False
        self._running = False

    @staticmethod
    def am_i_sender(update) -> bool:
        """
        True iff I'm the sender of this message.
        Prevents the bot to answer anyone else.
        """
        return update.effective_user.id == QKZKID

    def __arm(self):
        """Set the alarm running flag to True"""
        self._running = True

    def __disarm(self):
        """Set the alarm running flag to False"""
        self._running = False

    @property
    def verbose(self) -> bool:
        return self._verbose

    @verbose.setter
    def verbose(self, verbose: bool):
        self._verbose = verbose

    @property
    def last_edit(self) -> datetime.datetime:
        """Returns the last edition time of the logfile."""
        self.__update_status()
        return datetime.datetime.fromtimestamp(self._last_edit)

    def __read_last_line(self) -> DoorStatus:
        """
        Returns a DoorStatus instance from the last line of the logs.
        """
        with open(LOGFILE_OPENINGS, "r", encoding="utf-8") as f:
            last_line = f.readlines()[-1]
        return DoorStatus.from_line(last_line)

    def _read_last_lines(self) -> str:
        """
        Returns string of DoorStatus instances from the last lines of the logs.
        """
        with open(LOGFILE_OPENINGS, "r", encoding="utf-8") as f:
            last_lines = f.readlines()[-10:]
        return " 🌸 " + "\n🌸 ".join(
            map(lambda l: repr(DoorStatus.from_line(l)), last_lines)
        )

    def __update_status(self) -> bool:
        """Update the status of the watched door. Returns True if it was modified."""
        last_edit = self.__get_modification_time()
        if self._last_edit != last_edit:
            self._last_edit = last_edit
            self._last_status = self.__read_last_line()
            return True
        return False

    @staticmethod
    def __get_modification_time() -> float:
        """Get the last edition of the logfile"""
        last_edit = os.stat(LOGFILE_OPENINGS).st_mtime
        return last_edit

    async def send_alarm(self, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Send the alarm message"""
        job = context.job
        if self.__update_status():
            await context.bot.send_message(
                job.chat_id,
                text=f"Last line: {self._last_status}",
            )
        elif self.verbose:
            await context.bot.send_message(
                job.chat_id,
                text=f"No edition since {self.last_edit}.",
            )

    async def last_lines(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        if self.am_i_sender(update):
            self.__update_status()
            await context.bot.send_message(
                chat_id=update.effective_chat.id, text=self._read_last_lines()
            )

    async def last(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Respond with last known status"""
        if self.am_i_sender(update):
            self.__update_status()
            await context.bot.send_message(
                chat_id=update.effective_chat.id, text="🐤 " + repr(self._last_status)
            )

    async def status(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Respond with the status (running / stopped) of the alarm"""
        if self.am_i_sender(update):
            msg = "running ✅" if self._running else "stopped 🚫"
            await context.bot.send_message(
                chat_id=update.effective_chat.id, text=f"The alarm is {msg}"
            )

    def set_verbose(self, context):
        """Set the verbose flag from given context args"""
        self.verbose = False
        if context.args:
            if context.args[0] in "verboseVERBOSE":
                self.verbose = True

    async def alarm(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Set the alarm, verbose or not"""
        if self.am_i_sender(update):
            chat_id = update.effective_message.chat_id
            self.set_verbose(context)

            due = 1.0
            job_removed = remove_job_if_exists(str(chat_id), context)
            context.job_queue.run_repeating(
                self.send_alarm, due, chat_id=chat_id, name=str(chat_id), data=due
            )

            self.__arm()
            text = "Alarm successfully set!  ✅"
            if job_removed:
                text += " Old one was removed."
            await update.effective_message.reply_text(text)

    async def stop(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Stop the alarm."""
        if self.am_i_sender(update):
            self.__disarm()
            chat_id = update.message.chat_id
            job_removed = remove_job_if_exists(str(chat_id), context)
            text = (
                "Alarm successfully stopped.  🚫"
                if job_removed
                else "Alarm isn't running."
            )
            await update.message.reply_text(text)

    async def help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Display the help message"""
        if self.am_i_sender(update):
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=HELP_MESSAGE.format(self.started_time),
            )


async def send_keyboard(application: Application):
    """Send the first message with the keyboard"""
    reply_markup = ReplyKeyboardMarkup(
        [
            [
                KeyboardButton("/help"),
                KeyboardButton("/status"),
            ],
            [
                KeyboardButton("/alarm"),
                KeyboardButton("/stop"),
            ],
            [
                KeyboardButton("/last"),
                KeyboardButton("/lines"),
            ],
        ]
    )
    await application.bot.sendMessage(
        chat_id=QKZKID,
        text="qdoor 🚪 alarm bot started ! 🚨",
        reply_markup=reply_markup,
    )


def remove_job_if_exists(name: str, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """Remove job with given name. Returns whether job was removed."""
    current_jobs = context.job_queue.get_jobs_by_name(name)
    if not current_jobs:
        return False
    for job in current_jobs:
        job.schedule_removal()
    return True


def main():
    """
    Run the bot.
    Instanciate a DoorWatcher instance.
    Instanciate a bot with custom commands reading the logs.
    Display a keyboard and send me a message.
    Run the polling loop.
    """
    door = DoorWatcher()

    application = ApplicationBuilder().token(TOKEN).build()

    application.add_handler(CommandHandler(["start", "help"], door.help))
    application.add_handler(CommandHandler("alarm", door.alarm))
    application.add_handler(CommandHandler("stop", door.stop))
    application.add_handler(CommandHandler("last", door.last))
    application.add_handler(CommandHandler("status", door.status))
    application.add_handler(CommandHandler("lines", door.last_lines))

    application.post_init = send_keyboard

    application.run_polling()


if __name__ == "__main__":
    main()
