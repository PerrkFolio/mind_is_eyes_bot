import configparser
import logging
import os
from typing import Final
from nextcord.ext import commands
import nextcord



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


class Help(commands.Cog):
	def __init__(self, bot):
		self.bot = bot
		self.logger = logging.getLogger(LOGGER_NAME)

	@commands.command()
	async def help(self, ctx):
		embed = nextcord.Embed(title='Помощь', description='Список команд', colour=nextcord.Color.red())

		embed.set_author(name='Список команд')

		embed.add_field(name='Пользовательские', value='help, userinfo, roleinfo, say')
		embed.add_field(name='Модераторские', value='kick, clear')
		embed.add_field(name='Администраторские', value='ban')

		await ctx.send(embed=embed)

	@commands.command()
	async def roleinfo(self, ctx):
		embed = nextcord.Embed(color=nextcord.Color.red())

		embed.set_author(name='Список ролей')

		embed.add_field(name='Участник', value='Описание роли', inline=False)

		await ctx.send(embed=embed)

	@commands.command()
	async def userinfo(self, ctx, member: nextcord.Member = None):
		member = ctx.author if not member else member
		roles = [role for role in member.roles]

		embed = nextcord.Embed(colour=member.color, timestamp=ctx.message.created_at)

		embed.set_author(name=f'Информация о пользователе - {member}')
		embed.set_thumbnail(url=member.avatar)
		embed.set_footer(text=f'Запросил информацию - {ctx.author}')

		embed.add_field(name='ID:', value=member.id)
		embed.add_field(name='Ник:', value=member.display_name)

		embed.add_field(name='Создал аккаунт:', value=member.created_at.strftime('%d.%m.%Y'))
		embed.add_field(name='Присоединился:', value=member.joined_at.strftime('%d.%m.%Y'))

		embed.add_field(name=f'Роли ({len(roles)})', value=' '.join([role.mention for role in roles]))
		embed.add_field(name='Наилучшая роль:', value=member.top_role.mention)

		embed.add_field(name='Bot?', value=member.bot)

		await ctx.send(embed=embed)


def setup(bot):
	bot.add_cog(Help(bot))
