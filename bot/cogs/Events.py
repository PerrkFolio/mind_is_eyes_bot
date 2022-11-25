import configparser
import time
from datetime import datetime

import aiosqlite
import os
from typing import Final
from nextcord.ext import commands
import nextcord
import logging

# Получаем данные из конфига (папка Configs)
main_cfg = "configs/main.ini"
# main_cfg = "C:\\Users\\User\\PycharmProjects\\ds-bot-crm\\bot\\configs\\main.ini"
config = configparser.ConfigParser()
config.read(main_cfg, encoding="windows-1251")
# config.read(main_cfg)

# Константы
THIS_FILE: Final = os.path.basename(__file__)[:-3]
LOG_NAME: Final = config.get("LOGGING", "log_name")
LOGGER_NAME: Final = LOG_NAME + '.' + THIS_FILE


class Events(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.logger = logging.getLogger(LOGGER_NAME)

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        channel = self.bot.get_channel(payload.channel_id)

        async with aiosqlite.connect("databases/bot.db") as db:
            async with db.cursor() as cursor:
                await cursor.execute('SELECT role_id FROM react_message WHERE guild = ? AND message_id = ? AND emoji = ?',
                                     (payload.guild_id, payload.message_id, payload.emoji.name))
                data = await cursor.fetchone()
                if data is not None:
                    role = nextcord.utils.get(self.bot.get_guild(payload.guild_id).roles, id=data[0])
                    await payload.member.add_roles(role)
            await db.commit()

        # emoji_to_role = {
        #     nextcord.PartialEmoji(name='smile', id=self.bot.get_emoji("smile")): 1026828450452996176,
        #     nextcord.PartialEmoji(name='🟡'): 1026828450452996176
        # }
        #
        # guild = self.bot.get_guild(payload.guild_id)
        # if guild is None:
        #     # Check if we're still in the guild and it's cached.
        #     return
        #
        # try:
        #     role_id = emoji_to_role[payload.emoji]
        # except KeyError:
        #     # logger
        #     return
        #
        # role = guild.get_role(role_id)
        # if role is None:
        #     # logger
        #     return
        #
        # try:
        #     await payload.member.add_roles(role)
        # except nextcord.HTTPException:
        #     # logger
        #     pass

    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload):

        channel = self.bot.get_channel(payload.channel_id)

        async with aiosqlite.connect("databases/bot.db") as db:
            async with db.cursor() as cursor:
                await cursor.execute(
                    'SELECT role_id FROM react_message WHERE guild = ? AND message_id = ? AND emoji = ?',
                    (payload.guild_id, payload.message_id, payload.emoji.name))
                data = await cursor.fetchone()
                if data is not None:
                    role = nextcord.utils.get(self.bot.get_guild(payload.guild_id).roles, id=data[0])
                    await self.bot.get_guild(payload.guild_id).get_member(payload.user_id).remove_roles(role)
            await db.commit()

        # channel = self.bot.get_channel(payload.channel_id)
        # emoji_to_role = {
        #     nextcord.PartialEmoji(name='🟡'): 1026828450452996176
        # }
        #
        # guild = self.bot.get_guild(payload.guild_id)
        # if guild is None:
        #     return
        #
        # try:
        #     role_id = emoji_to_role[payload.emoji]
        # except KeyError:
        #     # logger
        #     return
        #
        # role = guild.get_role(role_id)
        # if role is None:
        #     # logger
        #     return
        #
        # member = guild.get_member(payload.user_id)
        # if member is None:
        #     return
        #
        # try:
        #     await member.remove_roles(role)
        # except nextcord.HTTPException:
        #     pass

    @commands.Cog.listener()
    async def on_message(self, message):
        try:
            embeds = message.embeds
            for embed in embeds:
                footer = embed['footer']['text']
                try:
                    footer_spl = footer.split("/")
                    if footer_spl[0] == "ReactMessage":
                        react_message_id = footer_spl[1].split(":")
                        react_message_id = react_message_id[1]
                        message_id = message.id
                    break
                except:
                    continue
        except:
            pass
        channel = message.channel.id
        author = message.author.name
        author_id = message.author.id
        msg = message.content
        msg_for_sql = f"'{msg}'"
        guild = message.guild.id
        table_name = message.guild.name
        table_name = table_name.replace(" ", "_")
        table_name = table_name.replace("'", "")
        date = str(datetime.now()).split(" ")
        date = f"'{date[0]}'"
        query = f"INSERT INTO {table_name} (date, guild, author, channel, message) VALUES ({date}, {guild}, {author_id}, {channel}, {msg_for_sql})"

        async with aiosqlite.connect("databases/msg_history.db") as db:
            async with db.cursor() as cursor:
                await cursor.execute(query)
            await db.commit()

        self.logger.info(f"{author} отправил сообщение: {msg}")

# @commands.Cog.listener()
# async def on_message_delete(self, message):
# 	if DELETE_NOTIFICATION == "yes":
# 		await message.channel.send(DELETE_MESSAGE)

# @commands.Cog.listener()
# async def on_command_error(self, ctx, error):
# 	if isinstance(error, commands.CheckFailure):
# 		await ctx.send(ERROR_CHECKFAILURE)
# 	if isinstance(error, commands.CommandNotFound):
# 		await ctx.send(ERROR_COMMANDNOTFOUND)
#
# 	raise error


def setup(bot):
    bot.add_cog(Events(bot))
