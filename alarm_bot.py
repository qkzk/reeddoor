"""
title: qdoor alarm telegram bot
author: qkzk
date: 2022/06/11

Telegram bot alerting me of openings and closing of my door.
Recognize a few commands to help me monitor Qdoor.
"""
import logging
import datetime
import glob
import os
from functools import wraps
from typing import Callable

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
)
from telegram.ext import (
    Application,
    ApplicationBuilder,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
)
from bot_token import TOKEN, QKZKID, MESKOID


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
VIDEOS_DIR = "/var/lib/motion/*.mkv"

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)


class LogLine:
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


class DoorStatus:
    """
    Holds the status of the door, read from the logfile.
    """

    def __init__(self):
        self._last_edit = self.__get_modification_time(LOGFILE_OPENINGS)
        self._last_line = self.__read_last_line()
        self._last_lines = self.__read_last_lines()

    def __read_last_line(self) -> str:
        """
        Returns a DoorStatus instance from the last line of logs.
        """
        with open(LOGFILE_OPENINGS, "r", encoding="utf-8") as f:
            last_line = f.readlines()[-1]
        return repr(LogLine.from_line(last_line))

    def __read_last_lines(self) -> str:
        """
        Returns a string of DoorStatus instances from the last 10 lines of logs.
        """
        with open(LOGFILE_OPENINGS, "r", encoding="utf-8") as f:
            last_lines = f.readlines()[-10:]
        return " 🌸 " + "\n🌸 ".join(
            map(lambda l: repr(LogLine.from_line(l)), last_lines)
        )

    @staticmethod
    def __get_modification_time(filename: str) -> float:
        """Get the last edition of the file"""
        return os.stat(filename).st_mtime

    def update_status(self) -> bool:
        """Update the status of the watched door. Returns True if it was modified."""
        last_edit = self.__get_modification_time(LOGFILE_OPENINGS)
        if self._last_edit != last_edit:
            self._last_edit = last_edit
            self._last_line = self.__read_last_line()
            self._last_lines = self.__read_last_lines()
            return True
        return False

    def last_video(self) -> str:
        """Returns the last animation from motion folder."""
        return max(glob.glob(VIDEOS_DIR), key=os.path.getmtime)

    def last_videos_recorded(self) -> list:
        """Returns a formated list of last 20 videos from motion folder."""
        return sorted(glob.glob(VIDEOS_DIR), key=os.path.getmtime)[-20:]

    @property
    def last_edit(self) -> datetime.datetime:
        """Returns the last edition time of the logfile."""
        self.update_status()
        return datetime.datetime.fromtimestamp(self._last_edit)

    @property
    def last_line(self) -> str:
        """Returns the last 10 lines of the log file, formatted."""
        self.update_status()
        return self._last_line

    @property
    def last_lines(self) -> str:
        """Returns the last line of the log file, formatted."""
        self.update_status()
        return self._last_lines


class TalkingDoor:
    """Run the alarm and responds to Telegram commands."""

    def __init__(self):
        self.door_status = DoorStatus()
        self._verbose = False
        self._running = False
        self._started_time = datetime.datetime.now()

    def talk_to_me(callback_method: Callable) -> Callable:
        """
        Decorator preventing other Telegram users from talking to the bot.
        Intercept callbacks and prevent them to respond to anyone but me.

        `args` should contain :
        * `self` (DoorWatcher)
        * `update` (telegram._update.update): Updater
        * `context`
        * other arguments may be...

        We only care about `update` since it knows who sent the message.
        If `update.effectif_user.id` isn't mine, returns.
        """

        @wraps(callback_method)
        async def wrapped(*args):
            if len(args) < 1 or args[1].effective_user.id not in (QKZKID, MESKOID):
                return
            return await callback_method(*args)

        return wrapped

    def __arm(self):
        """Set the alarm running flag to True"""
        self._running = True

    def __disarm(self):
        """Set the alarm running flag to False"""
        self._running = False

    @property
    def __verbose(self) -> bool:
        return self._verbose

    @__verbose.setter
    def __verbose(self, verbose: bool):
        self._verbose = verbose

    def __read_verbose_param(self, context):
        """Set the verbose flag from given context args"""
        self.__verbose = False
        if context.args and context.args[0] in "verboseVERBOSE":
            self.__verbose = True

    async def __send_alarm(self, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Send the alarm message"""
        if self.door_status.update_status():
            await context.bot.send_message(
                MESKOID,
                text=f"🐙{self.door_status.last_line}",
            )
            await context.bot.send_message(
                QKZKID,
                text=f"🐙{self.door_status.last_line}",
            )
        elif self.__verbose:
            await context.bot.send_message(
                context.job.chat_id,
                text=f"🚀unedited - {self.door_status.last_edit}.",
            )

    @talk_to_me
    async def last_vid(self, update: Update, _: ContextTypes.DEFAULT_TYPE) -> None:
        video = self.door_status.last_video()
        await update.message.reply_text(
            text=f"🎥 Last video: {self.filename_from_path(video)}"
        )
        with open(video, "rb") as video_stream:
            await update.message.reply_video(video=video_stream)

    @staticmethod
    def filename_from_path(filepath: str) -> str:
        """Extract the filename from a filepath"""
        return filepath.split("/")[-1]

    @talk_to_me
    async def last_vids(self, update: Update, _: ContextTypes.DEFAULT_TYPE) -> None:
        """Sent the last 10 videos as an inline keyboard."""
        keyboard = [
            [
                InlineKeyboardButton(
                    f"🎬 {self.filename_from_path(video_path)}", callback_data=video_path
                )
            ]
            for video_path in self.door_status.last_videos_recorded()
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text("Please choose:", reply_markup=reply_markup)

    @talk_to_me
    async def button(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        Parses the CallbackQuery and updates the message text.
        Send the selected video.
        """
        query = update.callback_query

        # CallbackQueries need to be answered, even if no notification to the user is needed
        # Some clients may have trouble otherwise. See https://core.telegram.org/bots/api#callbackquery
        await query.answer()

        await query.edit_message_text(
            text=f"🎬 Selected video: {self.filename_from_path(query.data)}"
        )
        try:
            with open(query.data, "rb") as video_stream:
                await context.bot.send_video(context._chat_id, video=video_stream)
        except FileNotFoundError:
            await query.edit_message_text(
                text=f"🎬 Selected video {self.filename_from_path(query.data)} not found"
            )

    @talk_to_me
    async def last_lines(self, update: Update, _: ContextTypes.DEFAULT_TYPE) -> None:
        """Repond with the last lines of the log."""
        self.door_status.update_status()
        await update.message.reply_text(text=self.door_status.last_lines)

    @talk_to_me
    async def last(self, update: Update, _: ContextTypes.DEFAULT_TYPE) -> None:
        """Respond with last known status"""
        self.door_status.update_status()
        await update.message.reply_text(text=f"🐤 {self.door_status.last_line}")

    @talk_to_me
    async def status(self, update: Update, _: ContextTypes.DEFAULT_TYPE) -> None:
        """Respond with the status (running / stopped) of the alarm"""
        msg = "running ✅" if self._running else "stopped 🚫"
        await update.message.reply_text(text=f"The alarm is {msg}")

    @talk_to_me
    async def alarm(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        Sets the alarm, verbose or not. Send confirmation.

        Removes all scheduled jobs.
        Set a scheduled job every `due` seconds.

        If "verbose" is present in the command, it will spam the user
        with debugging info every time.
        Else, it will only send messages when the log is changed.

        """
        self.__read_verbose_param(context)
        chat_id = update.effective_message.chat_id
        job_removed = remove_job_if_exists(str(chat_id), context)
        due = 1.0
        context.job_queue.run_repeating(
            self.__send_alarm, due, chat_id=chat_id, name=str(chat_id), data=due
        )

        self.__arm()
        msg = "Alarm set!  ✅"
        if job_removed:
            msg += " Old one was removed."
        await update.message.reply_text(msg)

    @talk_to_me
    async def stop(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Stops the alarm and sends confirmation."""
        self.__disarm()
        chat_id = update.message.chat_id
        job_removed = remove_job_if_exists(str(chat_id), context)
        msg = "Alarm stopped 🚫" if job_removed else "Alarm isn't running 🚫"
        await update.message.reply_text(msg)

    @talk_to_me
    async def help(self, update: Update, _: ContextTypes.DEFAULT_TYPE):
        """Sends the help message"""
        await update.message.reply_text(
            text=HELP_MESSAGE.format(self._started_time),
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
            [
                KeyboardButton("/last_vid"),
                KeyboardButton("/last_vids"),
            ],
        ]
    )
    await application.bot.sendMessage(
        chat_id=QKZKID,
        text="qdoor 🚪 alarm bot started ! 🚨",
        reply_markup=reply_markup,
    )
    await application.bot.sendMessage(
        chat_id=MESKOID,
        text="qdoor 🚪 alarm bot started ! 🚨",
        reply_markup=reply_markup,
    )


def remove_job_if_exists(name: str, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """Removes job with given name. Returns whether job was removed."""
    current_jobs = context.job_queue.get_jobs_by_name(name)
    if not current_jobs:
        return False
    for job in current_jobs:
        job.schedule_removal()
    return True


def main():
    """
    Runs the bot.
    Instanciates a DoorWatcher instance.
    Instanciates a bot with custom commands reading the logs.
    Displays a keyboard and send me a message.
    Run the polling loop.
    """
    door = TalkingDoor()

    application = ApplicationBuilder().token(TOKEN).build()

    application.add_handlers(
        [
            CommandHandler(["start", "help"], door.help),
            CommandHandler("status", door.status),
            CommandHandler("alarm", door.alarm),
            CommandHandler("last_vid", door.last_vid),
            CommandHandler("last_vids", door.last_vids),
            CommandHandler("stop", door.stop),
            CommandHandler("last", door.last),
            CommandHandler("lines", door.last_lines),
        ]
    )
    application.add_handler(CallbackQueryHandler(door.button))

    application.post_init = send_keyboard

    application.run_polling()


if __name__ == "__main__":
    main()
