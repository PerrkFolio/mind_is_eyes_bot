import configparser
import logging
import os
from typing import Final

import aiosqlite
from nextcord.ext import commands
import nextcord


from random import randint

import json
import asyncio

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

class Mod(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.logger = logging.getLogger(LOGGER_NAME)

    @commands.command()
    @commands.has_permissions(kick_members=True)
    async def kick(self, ctx, member: nextcord.Member, *, reason="Без причины"):
        await member.kick(reason=reason)
        await ctx.send(f'{member.mention} был кикнут модератором {ctx.author.mention}. Причина: {reason}.')

    @commands.command()
    @commands.has_permissions(ban_members=True)
    async def ban(self, ctx, member: nextcord.Member, *, reason="Без причины"):
        await member.ban(reason=reason)
        await ctx.send(f'{member.mention} был забанен администратором {ctx.author.mention}. Причина: {reason}.')

    @commands.command()
    @commands.has_permissions(manage_messages=True)
    async def clear(self, ctx, amount: int):
        await ctx.channel.purge(limit=amount + 1)

    @commands.command()
    @commands.has_permissions(manage_messages=True)
    # @commands.is_owner()
    async def reload(self, ctx, cog):
        try:
            await self.bot.unload_extension(f"{cog}")
            await self.bot.load_extension(f"{cog}")
            await ctx.send(f"{cog} перезагружен.")
        except Exception as e:
            self.logger.exception(f"{cog} не может быть запущен.")

    @commands.command()
    @commands.has_permissions(manage_messages=True)
    async def quick_rr(self, ctx, emoji, role: nextcord.Role, *, message):

        embed = nextcord.Embed(description=message)
        msg = await ctx.channel.send(embed=embed)
        await msg.add_reaction(emoji)

        async with aiosqlite.connect("databases/bot.db") as db:
            async with db.cursor() as cursor:
                await cursor.execute('INSERT INTO react_message (guild, role_name, role_id, emoji, message_id) VALUES (?, ?, ?, ?, ?)',
                                     (role.guild.id, role.name, role.id, emoji, msg.id))
            await db.commit()

    # @commands.Cog.listener()
    # @clear.error
    # async def clear_error(self, ctx, error):
    #     if isinstance(error, commands.CheckFailure):
    #         await ctx.send(ERROR_CHECKFAILURE)
    #     if isinstance(error, commands.MissingRequiredArgument):
    #         await ctx.send(ERROR_MISSINGREQUIREDARGUMENT)
    #     if isinstance(error, commands.BadArgument):
    #         await ctx.send(ERROR_BADARGUMENT+": количеством сообщений может быть только целое число.")
    #
    # @commands.Cog.listener()
    # @kick.error
    # async def kick_error(self, ctx, error):
    #     if isinstance(error, commands.CheckFailure):
    #         await ctx.send(ERROR_CHECKFAILURE)
    #     if isinstance(error, commands.MissingRequiredArgument):
    #         await ctx.send(ERROR_MISSINGREQUIREDARGUMENT+' (!kick @nick#0000 reason)!')
    #     if isinstance(error, commands.BadArgument):
    #         await ctx.send(ERROR_BADARGUMENT+' (!kick @nick#0000 reason)!')
    #
    # @commands.Cog.listener()
    # @ban.error
    # async def ban_error(self, ctx, error):
    #     if isinstance(error, commands.CheckFailure):
    #         await ctx.send(ERROR_CHECKFAILURE)
    #     if isinstance(error, commands.MissingRequiredArgument):
    #         await ctx.send(ERROR_MISSINGREQUIREDARGUMENT+' (!ban @nick#0000 reason)!')
    #     if isinstance(error, commands.BadArgument):
    #         await ctx.send(ERROR_BADARGUMENT+' (!ban @nick#0000 reason)!')
    #
    #     raise error


def setup(bot):
    bot.add_cog(Mod(bot))
