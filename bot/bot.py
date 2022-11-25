# -*- coding: utf-8 -*-
import configparser
import aiosqlite
from typing import Final
from nextcord.ext import commands, ipc
import nextcord
from PIL import ImageFont
from nextcord import File
from easy_pil import Editor, load_image_async
import logging
import random
import asyncio
import os

# Получаем данные из конфига (папка Configs)
main_cfg = "configs/main.ini"
# main_cfg = "C:\\Users\\User\\WebstormProjects\\admin-bot.jaristo-cyber-room.ru\\bot\\configs\\main.ini"
config = configparser.ConfigParser()
config.read(main_cfg, encoding="windows-1251")
# config.read(main_cfg)


# Подключаемся к БД



# Заносим данные из конфига в константы
THIS_FILE: Final = os.path.basename(__file__)[:-3]
TOKEN: Final = config.get("SECRET", "token")
BOT_DESCRIPTION: Final = config.get("BOT", "bot_description")
BOT_PREFIX: Final = config.get("BOT", "bot_prefix")
LOG_NAME: Final = config.get("LOGGING", "log_name")
LOG_PATH: Final = config.get("LOGGING", "log_path")
LOG_LEVEL: Final = config.get("LOGGING", "log_level")
LOGGER_NAME: Final = LOG_NAME + '.' + THIS_FILE



class MyBot(commands.Bot):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.ipc = ipc.Server(self, secret_key="test123")

    async def on_ready(self):
        logger.info(f"Бот запущен. Имя бота: {bot.user.name}.")

        bot.load_extensions(
            [
                ".Events",
                ".Help",
                ".Mod",
            ],
            packages=[
                "cogs",
                "cogs",
                "cogs",
            ],
        )

        logger.info("Модули загружены.")

        async with aiosqlite.connect("databases/bot.db") as db:
            async with db.cursor() as cursor:
                await cursor.execute('CREATE TABLE IF NOT EXISTS guilds (_id INTEGER PRIMARY KEY, guild INTEGER, guild_name VARCHAR, guild_premium INTEGER)')
                await cursor.execute('CREATE TABLE IF NOT EXISTS users (_id INTEGER PRIMARY KEY, user_id INTEGER, user_name VARCHAR, guild INTEGER)')
                await cursor.execute('CREATE TABLE IF NOT EXISTS welcome_config (_id INTEGER PRIMARY KEY, guild INTEGER, welcome_channel VARCHAR, welcome_message VARCHAR, welcome_img_text VARCHAR, welcome_img_font VARCHAR, welcome_img_bg VARCHAR)')
                await cursor.execute('CREATE TABLE IF NOT EXISTS autoroles (_id INTEGER PRIMARY KEY, guild INTEGER, autorole VARCHAR)')
                await cursor.execute('CREATE TABLE IF NOT EXISTS react_roles (_id INTEGER PRIMARY KEY, guild INTEGER, role_id INTEGER, react_id INTEGER, message_id INTEGER)')
                await cursor.execute('CREATE TABLE IF NOT EXISTS cogs_config (_id INTEGER PRIMARY KEY, guild INTEGER, del_notys INTEGER, err_notys INTEGER)')
                await cursor.execute('CREATE TABLE IF NOT EXISTS react_message (_id INTEGER PRIMARY KEY, guild INTEGER, role_name VARCHAR, role_id INTEGER, emoji VARCHAR, message_id INTEGER)')
                for bot_guild in bot.guilds:
                    await cursor.execute('SELECT _id FROM guilds WHERE guild = ?', (bot_guild.id,))
                    data = await cursor.fetchone()
                    if not data:
                        await cursor.execute('INSERT INTO guilds (guild, guild_name) VALUES (?, ?)', (bot_guild.id, bot_guild.name))

                for user_guild in bot.get_all_members():
                    for bot_guild in bot.guilds:
                        try:
                            if bot_guild.get_member(user_guild.id):
                                await cursor.execute('SELECT _id FROM users WHERE user_id = ? AND guild = ?', (user_guild.id, bot_guild.id))
                                data = await cursor.fetchone()
                                if not data:
                                    await cursor.execute('INSERT INTO users (user_id, user_name, guild) VALUES (?, ?, ?)', (user_guild.id, user_guild.name, bot_guild.id))
                            else:
                                continue
                        except:
                            continue

            await db.commit()

        async with aiosqlite.connect("databases/msg_history.db") as db:
            async with db.cursor() as cursor:
                query_create = "CREATE TABLE IF NOT EXISTS {table} (_id INTEGER PRIMARY KEY, guild INTEGER, date TIMESTAMP, author INTEGER, channel INTEGER, message VARCHAR)"

                for bot_guild in bot.guilds:
                    name = bot_guild.name
                    name = name.replace(" ", "_")
                    name = name.replace("|", "")
                    table = name.replace("'", "")

                    await cursor.execute(query_create.format(table=table))
            await db.commit()

        async with aiosqlite.connect("databases/twitch_schedule.db") as db:
            async with db.cursor() as cursor:
                await cursor.execute("CREATE TABLE IF NOT EXISTS stream_schedule (_id INTEGER PRIMARY KEY, guild INTEGER, date_at TIMESTAMP, streamer_id INTEGER, streamer VARCHAR, type VARCHAR)")
                await cursor.execute("CREATE TABLE IF NOT EXISTS twitch_accounts (_id INTEGER PRIMARY KEY, guild INTEGER, streamer_id INTEGER, streamer_login VARCHAR, channel_id INTEGER, notificated VARCHAR)")
                await cursor.execute("CREATE TABLE IF NOT EXISTS notification_roles (_id INTEGER PRIMARY KEY, guild INTEGER, streamer_login INTEGER, noty_role VARCHAR)")
            await db.commit()

        logger.info("Соединение с базой данных установлено.")


    async def on_ipc_ready(self):
        logger.info(f"Соединение с дашбордом установлено.")


    async def on_ipc_error(self, endpoint, error):
        logger.error(f"В ходе установки соединения с дашбордом, возникла ошибка! :: {endpoint} :: {error}")


bot = MyBot(intents=nextcord.Intents.all(), command_prefix=BOT_PREFIX, description=BOT_DESCRIPTION)
bot.remove_command('help')


# Автоматическое присвоение роли новому участнику сервера
@bot.event
async def on_member_join(member):
    server = member.guild.name
    user = member.mention
    guild_id = member.guild.id

    async with aiosqlite.connect("databases/bot.db") as db:
        async with db.cursor() as cursor:
            await cursor.execute(f'SELECT welcome_channel, welcome_message, welcome_img_text, welcome_img_font, '
                                 f'welcome_img_bg FROM welcome_config WHERE guild = {guild_id}')
            data = await cursor.fetchone()
            if data is None:
                welcome_config = None
            else:
                WELCOME_CHANNEL = int(data[0])
                WELCOME_MESSAGE = data[1]
                WELCOME_IMG_TEXT = data[2]
                WELCOME_IMG_FONT = data[3]
                WELCOME_IMG_BG = data[4]
        await db.commit()

    try:
        channel = bot.get_channel(WELCOME_CHANNEL)
        font_path = f"welcome/fonts/{WELCOME_IMG_FONT}"
        background = Editor(f"welcome/backgrounds/{WELCOME_IMG_BG}")
        profile_image = await load_image_async(str(member.avatar))
        profile = Editor(profile_image).resize((150, 150)).circle_image()
        font_text = ImageFont.truetype(font_path, 30, encoding="utf-8")
        background.paste(profile, (250, 90))
        background.ellipse((250, 90), 150, 150, outline="red", stroke_width=4)
        background.text((300, 260), WELCOME_IMG_TEXT.format(user_name=member.name, user_dcrm=member.discriminator),
                        color="red", font=font_text, align="center", )
        # background.text((400, 325), f"{member.name}#{member.discriminator}", color="white", font=poppins_small,
        #                 align="center")
        file = File(fp=background.image_bytes, filename=f"welcome/backgrounds/{WELCOME_IMG_BG}")
        await channel.send(WELCOME_MESSAGE.format(user=user, server=server), file=file)

        async with aiosqlite.connect("databases/bot.db") as db:
            async with db.cursor() as cursor:
                await cursor.execute(f'SELECT autorole FROM autoroles WHERE guild = {guild_id}')
                data = await cursor.fetchall()
                if data is None:
                    role_names = None
                else:
                    role_names = []
                    for name in data:
                        role_names.append(name[0])
            await db.commit()

        if role_names is not None:
            for name in role_names:
                role = nextcord.utils.get(member.guild.roles, name=name)
                await member.add_roles(role)

        async with aiosqlite.connect("databases/bot.db") as db:
            async with db.cursor() as cursor:
                if member.guild.get_member(member.id):
                    await cursor.execute('SELECT _id FROM users WHERE user_id = ? AND guild = ?',
                                         (member.id, member.guild.id))
                    data = await cursor.fetchone()
                    if not data:
                        await cursor.execute('INSERT INTO users (user_id, user_name, guild) VALUES (?, ?, ?)',
                                             (member.id, member.name, member.guild.id))
            await db.commit()
        logger.info(f"Новый участник на сервере: {member.mention}!")
    except:
        try:
            await channel.send(WELCOME_MESSAGE.format(user=user, server=server))
            logger.warning("Настройте отправку изображения-приветствия в панеле управления Ботом!")
        except:
            await channel.send(f"Добро пожаловать на сервер, {user}!")
            logger.warning("Настройте параметры приветствия в панеле управления Ботом!")


@bot.event
async def on_guild_join(guild):
    async with aiosqlite.connect("databases/bot.db") as db:
        async with db.cursor() as cursor:
            if guild not in bot.guilds:
                await cursor.execute('SELECT _id FROM guilds WHERE guild = ?', (guild.id,))
                data = await cursor.fetchone()
                if not data:
                    await cursor.execute('INSERT INTO guilds (guild, guild_name) VALUES (?, ?)',
                                         (guild.id, guild.name))

            for user_guild in bot.get_all_members():
                for bot_guild in bot.guilds:
                    try:
                        if bot_guild.get_member(user_guild.id):
                            await cursor.execute('SELECT _id FROM users WHERE user_id = ? AND guild = ?',
                                                 (user_guild.id, bot_guild.id))
                            data = await cursor.fetchone()
                            if not data:
                                await cursor.execute('INSERT INTO users (user_id, user_name, guild) VALUES (?, ?, ?)',
                                                     (user_guild.id, user_guild.name, bot_guild.id))
                        else:
                            continue
                    except:
                        continue

        await db.commit()

    async with aiosqlite.connect("databases/msg_history.db") as db:
        async with db.cursor() as cursor:
            query_create = "CREATE TABLE IF NOT EXISTS {table} (_id INTEGER PRIMARY KEY, guild INTEGER, date TIMESTAMP, author INTEGER, channel INTEGER, message VARCHAR)"
            name = guild.name
            name = name.replace(" ", "_")
            table = name.replace("'", "")
            await cursor.execute(query_create.format(table=table))
        await db.commit()


@bot.ipc.route()
async def get_guild_count(data):
    return len(bot.guilds)  # returns the len of the guilds to the client


@bot.ipc.route()
async def get_guild_ids(data):
    result = []
    for guild in bot.guilds:
        result.append(guild.id)
    return result


@bot.ipc.route()
async def get_guild(data):
    guild = bot.get_guild(data.guild_id)
    if guild is None:
        return None

    guild_data = {"name": guild.name, "id": guild.id, "member_count": guild.member_count}
    return guild_data


@bot.ipc.route()
async def get_all_users(data):
    i = 0
    users = bot.get_all_members()
    for _ in users:
        i += 1
    return i


@bot.ipc.route()
async def get_guild_owner(data):
    guild = bot.get_guild(data.guild_id)
    owner = guild.owner
    return owner.id


@bot.ipc.route()
async def check_guild_admin(data):
    guild = bot.get_guild(data.guild_id)
    member = guild.get_member(data.user_id)
    if member.guild_permissions.add_reactions:
        return True
    else:
        return False


@bot.ipc.route()
async def get_text_channels(data):
    result = []
    try:
        guild = bot.get_guild(data.guild_id)
        for channel in guild.channels:
            if channel.type == nextcord.ChannelType.text:
                result.append(channel.name)
    except Exception as e:
        logger.exception(e)
        logger.error("Не удалось получить список каналов.")
        result = ["Ошибка. Перезагрузите страницу."]

    return result


@bot.ipc.route()
async def get_data_text_channels(data):
    result = []
    try:
        guild = bot.get_guild(data.guild_id)
        for channel in guild.channels:
            if channel.type == nextcord.ChannelType.text:
                result.append({"id": channel.id, "name": channel.name})
    except Exception as e:
        logger.exception(e)
        logger.error("Не удалось получить список каналов.")
        result = [{"id": 0, "name": "Ошибка. Перезагрузите страницу."}]

    return result


@bot.ipc.route()
async def get_users(data):
    result = []
    for user in data.users:
        user_info = bot.get_user(user[0])
        name = user_info.name
        try:
            avatar_url = user_info.avatar.url
        except:
            avatar_url = None
        result.append({'id': user, 'name': name, 'avatar_url': avatar_url})
    result.reverse()
    return result


@bot.ipc.route()
async def get_roles(data):
    result = []
    bot_roles = []
    guild = bot.get_guild(data.guild_id)

    for bot_role in guild.bots:
        bot_roles.append(bot_role.name)

    for role in guild.roles:
        if role.name == '@everyone' or role.name in bot_roles: continue
        result.append({"role_id": role.id, "role_name": role.name, "role_guild": role.guild.id})
    return result


@bot.ipc.route()
async def get_message_info(data):
    result = []
    limit = 0
    for message in data.messages:
        author_info = bot.get_user(message[0])
        channel_info = bot.get_channel(message[1])
        author = author_info.name
        channel = channel_info.name
        try:
            avatar_url = author_info.avatar.url
        except:
            avatar_url = None
        result.append({'author_id': message[0], 'message_id': message[1], 'author': author, 'channel': channel, 'avatar_url': avatar_url, 'message': message[2]})
        limit += 1
        if limit >= data.limit:
            break
    result.reverse()
    return result


@bot.ipc.route()
async def send_message(data):
    channel = bot.get_channel(data.channel_id)
    if data.message != "":
        await channel.send(data.message)
        return True
    else:
        logger.error("Пустое сообщение.")
        return False


@bot.ipc.route()
async def ipc_load_extensions(data):
    for filename in os.listdir("./cogs"):
        if filename.endswith(".py"):
            bot.reload_extension(f"cogs.{filename[:-3]}")


@bot.ipc.route()
async def send_noty_twitch(data):
    try:
        channel = bot.get_channel(data.channel_id)
        guild = bot.get_guild(data.guild_id)
        url = "https://www.twitch.tv/"+data.streamer
        streamer = str(data.streamer).upper()
        roles = guild.roles

        async with aiosqlite.connect("databases/twitch_schedule.db") as db:
            async with db.cursor() as cursor:
                await cursor.execute(
                    f'SELECT streamer_login, noty_role FROM notification_roles WHERE guild = {guild.id}')
                response = await cursor.fetchall()
                if response is None:
                    active_roles = ["@everyone"]
                else:
                    active_roles = []
                    for active_role in response:
                        if active_role[0] == data.streamer:
                            active_roles.append(active_role[1])
            await db.commit()

        message = ""

        for role in roles:
            if role.name in active_roles and role.guild.id == data.guild_id:
                message = message+"<@&"+str(role.id)+">, "

        message += f"приглашаем Вас на стрим к **{streamer}**!\n" \
                   f"{url}"

        embed = nextcord.Embed(title=data.stream_title, color=nextcord.Color.dark_purple(),
                               url=nextcord.embeds.EmptyEmbed)
        embed.add_field(name="Игра", value=data.stream_game, inline=False)
        embed.set_image(url=data.stream_img)

        await channel.send(message, embed=embed)
        return True
    except:
        logger.error("Сообщение о начале стрима не отправлено!")
        return False


@bot.ipc.route()
async def send_embed(data):
    channel = bot.get_channel(data.channel_embed)
    embed = nextcord.Embed(title=data.title_embed, description=data.text_embed, color=data.color_embed, url=nextcord.embeds.EmptyEmbed)

    if data.main_img_path is not None:
        embed.set_thumbnail(url=data.main_img_path)

    try:
        embed.add_field(name=data.field_data[0]['field_name'], value=data.field_data[0]['field_value'], inline=False)
    except:
        pass

    try:
        embed.add_field(name=data.field_data[1]['field_name'], value=data.field_data[1]['field_value'], inline=False)
    except:
        pass

    try:
        embed.add_field(name=data.field_data[2]['field_name'], value=data.field_data[2]['field_value'], inline=False)
    except:
        pass

    try:
        if data.bt_img_path is not None:
            embed.set_footer(text=data.bt_text_embed, icon_url=data.bt_img_path)
        else:
            embed.set_footer(text=data.bt_text_embed)
    except:
        pass

    await channel.send(embed=embed)


@bot.ipc.route()
async def load_cog(data):
    extension = data.extension
    try:
        bot.load_extension(f".{extension}", package="cogs")
        logger.warning(f"Инициирована загрузка модуля {extension}!")
    except:
        logger.error(f"Не удалось загрузить модуль {extension}!")


@bot.ipc.route()
async def unload_cog(data):
    extension = data.extension
    try:
        bot.unload_extension(f".{extension}", package="cogs")
        logger.warning(f"Инициировано отключение модуля {extension}!")
    except:
        logger.error(f"Не удалось отключить модуль {extension}!")


@bot.ipc.route()
async def reload_cog(data):
    extension = data.extension
    try:
        bot.reload_extension(f".{extension}", package="cogs")
        logger.warning(f"Инициирован перезапуск модуля {extension}!")
    except:
        logger.error(f"Не удалось перезапустить модуль {extension}!")

# Статус бота
# async def status():
#     await bot.wait_until_ready()
#     statuses = BOT_STATUSES.split(",")
#
#     while not bot.is_closed():
#         status = random.choice(statuses)
#         await bot.change_presence(activity=nextcord.Game(status))
#         await asyncio.sleep(int(BOT_STATUS_INTERVAL))


# async def main():
    # await create_db_pool()
    # await bot.loop.create_task(status())
    # await load_extensions()
    # bot.ipc.start()
    # await bot.start(TOKEN)


# Логирование
def init_logger(name, path, level):
    logger = logging.getLogger(name)
    FORMAT = "%(asctime)s :: %(name)s:%(lineno)s :: %(levelname)s :: %(message)s"
    sh = logging.StreamHandler()
    sh.setFormatter(logging.Formatter(FORMAT))
    fh = logging.FileHandler(filename=path)
    fh.setFormatter(logging.Formatter(FORMAT))

    match level:
        case "debug":
            logger.setLevel(logging.DEBUG)
            sh.setLevel(logging.DEBUG)
            fh.setLevel(logging.DEBUG)
        case "info":
            logger.setLevel(logging.INFO)
            sh.setLevel(logging.INFO)
            fh.setLevel(logging.INFO)
        case "warning":
            logger.setLevel(logging.WARNING)
            sh.setLevel(logging.WARNING)
            fh.setLevel(logging.WARNING)
        case "error":
            logger.setLevel(logging.ERROR)
            sh.setLevel(logging.ERROR)
            fh.setLevel(logging.ERROR)
        case "critical":
            logger.setLevel(logging.CRITICAL)
            sh.setLevel(logging.CRITICAL)
            fh.setLevel(logging.CRITICAL)
        case _:
            logger.setLevel(logging.INFO)
            sh.setLevel(logging.INFO)
            fh.setLevel(logging.INFO)

    logger.addHandler(sh)
    logger.addHandler(fh)
    logger.debug("Логирование запущено.")


if __name__ == "__main__":
    init_logger(LOG_NAME, LOG_PATH, LOG_LEVEL)
    logger = logging.getLogger(LOGGER_NAME)
    bot.ipc.start()
    bot.run(TOKEN)
