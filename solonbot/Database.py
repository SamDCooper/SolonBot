import asyncio
import calendar
import discord
import logging
import os
import solon
import datetime
__all__ = []

log = logging.getLogger(__name__)

log.info(f"Loading {__name__}")

config = solon.get_config(__name__)


async def run_command(cmd):
    proc = await asyncio.create_subprocess_shell(cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
    stdout, stderr = await proc.communicate()
    log.info(f"{cmd!r} finished with exit code {proc.returncode}")
    if stdout:
        log.info(f"{stdout.decode()}")
    if stderr:
        log.error(f"{cmd!r} produred error:\n{stderr.decode()}")


@solon.Cog(default_active=True, guild_local=False, guild_only=False, toggleable=False)
class Database:
    def __init__(self):
        self.timed_save.start(self, solon.save_interval)
        backup_config = config["backup_config"]
        if backup_config:
            self.backup.start(self, solon.timedelta_from_string(backup_config["backup_interval"]))

    @solon.Command(is_owner=True)
    async def save(self, ctx):
        solon.save_all()
        await ctx.send("Saved.")

    @solon.TimedEvent()
    async def timed_save(self):
        log.info("Scheduled timed save.")
        solon.save_all()

    @solon.TimedEvent()
    async def backup(self):
        backup_config = config["backup_config"]
        backup_folder = backup_config["backup_folder"]

        db_config = solon.get_config("solon.database")
        db_folder_name = db_config["folder_name"]

        try:
            os.makedirs(backup_folder)
        except OSError as e:
            if e.errno != os.errno.EEXIST:
                raise

        now = datetime.datetime.utcnow()
        formatted_date = now.strftime("%Y-%m-%d_%H-%M-%S")
        backup_name = f"{backup_folder}/{formatted_date}.tar.gz"
        log.info(f"Creating backup of database folder at {backup_name}")
        await run_command(f"tar cfz {backup_name} {db_folder_name}")

        if solon.Bot.owner_id is not None:
            owner = solon.Bot.get_user(solon.Bot.owner_id)
            if owner is not None:
                with open(backup_name, "rb") as f:
                    log.info(f"Sending file {backup_name} to {owner}.")
                    file = discord.File(fp=f, filename=os.path.basename(f.name))
                    await owner.send(file=file)
            else:
                log.warning("Cannot send backups to owner - owner id is set but I can't find the owner's user!")
        else:
            log.warning("Cannot send backups to owner - not set!")

        # Clean up backups older than X days
        now = datetime.datetime.utcnow()
        max_backup_age = solon.timedelta_from_string(backup_config["keep_backups_for"])
        minimum_created_time = now - max_backup_age

        files = os.listdir(backup_folder)
        for filename in files:
            fpath = os.path.join(backup_folder, filename)
            stat = os.stat(str(fpath))
            time = stat.st_ctime
            if time < calendar.timegm(minimum_created_time.timetuple()):
                log.info(f"Removing {fpath} as it's an older backup.")
                os.remove(fpath)

