import configparser
import datetime
import json
import logging
import os
import time
from collections import deque
from typing import Final

from aiofiles.os import listdir
from twitchAPI.twitch import Twitch

import aiosqlite
from quart import Quart, render_template, request, redirect, url_for, jsonify, send_file
from quart_discord import DiscordOAuth2Session, requires_authorization, Unauthorized
from nextcord.ext import ipc
import nextcord

THIS_FILE: Final = os.path.basename(__file__)[:-3]
LOG_NAME: Final = "web"
LOG_PATH: Final = "logs/" + LOG_NAME + ".log"
LOG_LEVEL: Final = "debug"
LOGGER_NAME: Final = LOG_NAME + '.' + THIS_FILE

app = Quart(__name__)

app.secret_key = b'subscribe'
os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "true"
ipc_client = ipc.Client(secret_key="test123")

app.config["DISCORD_CLIENT_ID"] = 958028473568464966
app.config["DISCORD_CLIENT_SECRET"] = "B70rVziEBWjD0pAunuSCnwv6cRehSlh-"
app.config["DISCORD_REDIRECT_URI"] = "http://185.20.227.14:5555/callback"
app.config["DISCORD_BOT_TOKEN"] = "OTU4MDI4NDczNTY4NDY0OTY2.GBKjbs.yc-CiCZYh6RdGySPfWBbL9g9KLr5IIEH_nHLO0"
app.config["DISCORD_BOT_OWNER"] = 310873897132228608
# app.config["DISCORD_BOT_OWNER"] = 307913084780019723

app.config['DOMAIN'] = "http://185.20.227.14:5555" #обязательно без / на конце
app.config['UPLOAD_FOLDER'] = 'static/temp'

ALLOWED_EXTENSIONS = {'jpg', 'png'}


discord = DiscordOAuth2Session(app)

@app.route("/login/")
async def login():
    return await discord.create_session()


@app.route("/callback")
async def callback():
    try:
        await discord.callback()
    except:
        return redirect(url_for("login"))
    return redirect(url_for("dashboard"))


@app.route("/dashboard/")
async def dashboard():
    try:
        user = await discord.fetch_user()
        guild_count = await ipc_client.request("get_guild_count")
        guild_ids = await ipc_client.request("get_guild_ids")
        user_guilds = await user.fetch_guilds()
    except:
        return redirect(url_for("login"))

    guilds = []

    for guild in user_guilds:
        if guild.permissions.manage_guild:
            guild_id = int(guild.id)
            guild_data = await ipc_client.request("get_guild", guild_id=guild_id)
            try:
                if guild_data is not None:
                    member_count = guild_data['member_count']
                    if guild.icon_url is None:
                        icon_url = url_for('static', filename='dist/img/bot-600x600.png')
                    else:
                        icon_url = guild.icon_url
                    guilds.append({"id": guild.id, "name": guild.name, "icon_url": icon_url, "member_count": member_count})
                else:
                    guilds.append({"id": guild.id, "name": guild.name, "icon_url": guild.icon_url, "member_count": None})
            except Exception as e:
                logger.exception(f"Не удалось получить сервер пользователя {user.name}.")
                logger.error(e)


    return await render_template("starter.html", user=user, guild_count=guild_count, guilds=guilds, user_id=user.id, owner=app.config["DISCORD_BOT_OWNER"])


@app.route("/dashboard/superadmin")
async def superadmin():
    try:
        user = await discord.fetch_user()
    except:
        return redirect(url_for("login"))

    if user.id != app.config["DISCORD_BOT_OWNER"]:
        return redirect(url_for("dashboard"))

    main_cfg = "bot/configs/main.ini"
    # main_cfg = "C:\\Users\\User\\PycharmProjects\\ds-bot-crm\\bot\\configs\\main.ini"
    config = configparser.ConfigParser()
    config.read(main_cfg, encoding="windows-1251")

    if request.method == 'POST':
        result = await request.form
        config.set("ERROR_MSG", "error_checkfailure", result["error_checkfailure"])
        config.set("ERROR_MSG", "error_commandnotfound", result["error_commandnotfound"])
        config.set("ERROR_MSG", "error_missingrequiredargument", result["error_missingrequiredargument"])
        config.set("ERROR_MSG", "error_badargument", result["error_badargument"])
        config.set("LOGGING", "log_name", result["log_name"])
        config.set("LOGGING", "log_path", result["log_path"])
        config.set("LOGGING", "log_level", result["log_level"])
        config.set("BOT", "bot_prefix", result["bot_prefix"])
        config.set("BOT", "bot_description", result["bot_description"])

        await ipc_client.request("ipc_load_extensions")
        with open(main_cfg, "w") as config_file:
            config.write(config_file)

    error_checkfailure = config.get("ERROR_MSG", "error_checkfailure")
    error_commandnotfound = config.get("ERROR_MSG", "error_commandnotfound")
    error_missingrequiredargument = config.get("ERROR_MSG", "error_missingrequiredargument")
    error_badargument = config.get("ERROR_MSG", "error_badargument")
    log_name = config.get("LOGGING", "log_name")
    log_path = config.get("LOGGING", "log_path")
    log_level = config.get("LOGGING", "log_level")
    bot_prefix = config.get("BOT", "bot_prefix")
    bot_description = config.get("BOT", "bot_description")

    guild_count = await ipc_client.request("get_guild_count")
    user_count = await ipc_client.request("get_all_users")
    async with aiosqlite.connect("bot/databases/twitch_schedule.db") as db:
        async with db.cursor() as cursor:
            await cursor.execute("SELECT COUNT(_id) FROM twitch_accounts")
            streamer_count = await cursor.fetchone()
        await db.commit()

    return await render_template("superadmin.html", user=user, guild_count=guild_count, user_count=user_count,
                                 streamer_count=streamer_count[0], user_id=user.id, error_checkfailure=error_checkfailure,
                                 error_commandnotfound=error_commandnotfound, error_missingrequiredargument=error_missingrequiredargument,
                                 error_badargument=error_badargument, log_name=log_name, log_path=log_path, log_level=log_level,
                                 bot_prefix=bot_prefix, bot_description=bot_description)


@app.route("/cog_action/<string:action>/<string:name>")
async def cog_action(action, name):
    try:
        user = await discord.fetch_user()
    except:
        return redirect(url_for("login"))

    if user.id != app.config["DISCORD_BOT_OWNER"]:
        return redirect(url_for("dashboard"))

    match action:
        case "load":
            response = await ipc_client.request("load_cog", extension=name)
            return redirect(url_for("superadmin"))
        case "unload":
            response = await ipc_client.request("unload_cog", extension=name)
            return redirect(url_for("superadmin"))
        case "reload":
            response = await ipc_client.request("reload_cog", extension=name)
            return redirect(url_for("superadmin"))
        case _:
            return redirect(url_for("superadmin"))

@app.route("/dashboard/<int:guild_id>", methods=["GET", "POST"])
async def dashboard_main(guild_id):
    if not await discord.authorized:
        return redirect(url_for("login"))

    if request.method == 'POST':
        result = await request.form
        if result['action_for'] == 'send_message':
            await ipc_client.request("send_message", channel_id=int(result['quick_channel']), message=result['quick_message'])
        else:
            twitch_account = result['twitch_account'].split("/")
            streamer_login = twitch_account[3]
            streamer_info = twitch.get_users(logins=[streamer_login])
            streamer_id = streamer_info['data'][0]['id']
            noty_channel = result['noty_channel']
            async with aiosqlite.connect("bot/databases/twitch_schedule.db") as db:
                async with db.cursor() as cursor:
                    await cursor.execute('INSERT INTO twitch_accounts (guild, streamer_id, streamer_login, channel_id, notificated) VALUES (?, ?, ?, ?, ?)', (guild_id, streamer_id, streamer_login, noty_channel, "No"))
                await db.commit()

    user = await discord.fetch_user()
    # channels = await ipc_client.request("get_text_channels", guild_id=guild_id)
    data_channels = await ipc_client.request("get_data_text_channels", guild_id=guild_id)
    logger.debug(data_channels)
    try:
        guild = await ipc_client.request("get_guild", guild_id=guild_id)
        if guild == None:
            return redirect("https://discord.com/api/oauth2/authorize?client_id=958028473568464966&permissions=983312100439&scope=bot%20applications.commands")
        guild_name_sql = guild['name']
        guild_name_sql = guild_name_sql.replace(" ", "_")
        guild_name_sql = guild_name_sql.replace("|", "")
        guild_name_sql = guild_name_sql.replace("'", "")
    except:
        return await render_template("500.html", name=user.name, disc=user.discriminator, guild_id=guild_id, user_id=user.id)

    async with aiosqlite.connect("bot/databases/msg_history.db") as db:
        async with db.cursor() as cursor:
            query = f"SELECT COUNT(guild) FROM {guild_name_sql} WHERE guild = {guild_id}"
            await cursor.execute(query)
            count = await cursor.fetchone()
        await db.commit()

    async with aiosqlite.connect("bot/databases/bot.db") as db:
        async with db.cursor() as cursor:
            query = f"SELECT user_id FROM users WHERE guild = {guild_id}"
            await cursor.execute(query)
            users = await cursor.fetchall()
        await db.commit()
    user_list = await ipc_client.request("get_users", users=users)
    user_list_len = len(user_list)
    if user_list_len >= 12:
        short_user_list = user_list[:12]
    else:
        short_user_list = []

    async with aiosqlite.connect("bot/databases/twitch_schedule.db") as db:
        async with db.cursor() as cursor:
            query = f"SELECT COUNT(streamer_id) FROM stream_schedule WHERE guild = {guild_id}"
            await cursor.execute(query)
            count_streams = await cursor.fetchone()
        await db.commit()

    async with aiosqlite.connect("bot/databases/twitch_schedule.db") as db:
        async with db.cursor() as cursor:
            query = f"SELECT streamer_login FROM twitch_accounts WHERE guild = {guild_id}"
            await cursor.execute(query)
            streamers_request = await cursor.fetchall()
        await db.commit()

    streamer_logins = []
    for streamer in streamers_request:
        streamer_logins.append(streamer[0])

    stream_list = []
    for i in range(len(streamer_logins)):
        try:
            streamer = twitch.get_users(logins=streamer_logins[i])
            streamer_id = streamer['data'][0]['id']
            stream_live = twitch.get_streams(user_id=streamer_id)
            if stream_live['data']:
                if stream_live['data'][0]['type'] == 'live':
                    start_datetime = stream_live['data'][0]['started_at']
                    start_datetime = start_datetime.replace("Z", "")
                    start_datetime = start_datetime.split('T')
                    start_date = start_datetime[0].split("-")
                    start_time = start_datetime[1].split(":")
                    delta = datetime.timedelta(hours=3, minutes=0)
                    format_datetime = datetime.datetime(year=int(start_date[0]), month=int(start_date[1]),
                                                        day=int(start_date[2]), hour=int(start_time[0]),
                                                        minute=int(start_time[1]), second=int(start_time[2])) + delta
                    format_datetime = str(format_datetime).split(" ")
                    stream = {"username": streamer_logins[i], "title": stream_live['data'][0]['title'],
                              "start_date": format_datetime[0], "start_time": format_datetime[1], "status": "В ЭФИРЕ"}

                    async with aiosqlite.connect("bot/databases/twitch_schedule.db") as db:
                        async with db.cursor() as cursor:
                            await cursor.execute('INSERT INTO stream_schedule (guild, data_at, streamer_id, streamer, type) VALUES (?, ?, ?, ?, ?)', (guild_id, format_datetime[0], streamer_id, streamer_logins[i], "-"))
                        await db.commit()

            else:
                schedule = twitch.get_channel_stream_schedule(broadcaster_id=streamer_id)
                start_datetime = schedule['data']['segments'][0]['start_time']
                start_datetime = start_datetime.replace("Z", "")
                start_datetime = start_datetime.split('T')
                start_date = start_datetime[0].split("-")
                start_time = start_datetime[1].split(":")
                delta = datetime.timedelta(hours=3, minutes=0)
                format_datetime = datetime.datetime(year=int(start_date[0]), month=int(start_date[1]),
                                                    day=int(start_date[2]), hour=int(start_time[0]),
                                                    minute=int(start_time[1]), second=int(start_time[2])) + delta
                format_datetime = str(format_datetime).split(" ")

                stream = {"username": streamer_logins[i], "title": schedule['data']['segments'][0]['title'],
                          "start_date": format_datetime[0], "start_time": format_datetime[1], "status": "Запланирован"}
        except:
            schedule = None
            stream = {"username": streamer_logins[i], "title": "-",
                      "start_date": "-", "start_time": "-", "status": "Нет данных"}
        stream_list.append(stream)

    return await render_template("main.html", name=user.name, disc=user.discriminator, guild=guild, user_id=user.id, data_channels=data_channels, guild_id=guild_id, message_count=count[0], count_streams=count_streams[0], user_list=user_list, short_user_list=short_user_list, user_list_len=user_list_len, stream_list=stream_list)


@app.route("/")
async def index():
    return await render_template("index.html")


@app.route('/dashboard/static_pages/<string:page>/<int:guild_id>')
async def static_pages(page, guild_id):
    if not await discord.authorized:
        return redirect(url_for("login"))
    user = await discord.fetch_user()
    try:
        match page:
            case "docs":
                return await render_template("docs.html", name=user.name, disc=user.discriminator, guild_id=guild_id)
            case _:
                logger.info(f"Страница /dashboard/static/{page} не найдена.")
                return await render_template("404.html", name=user.name, disc=user.discriminator, guild_id=guild_id)
    except Exception as e:
        logger.warning(f"Не удалось загрузить страницу /dashboard/static/{page} !")
        logger.exception(e)
        return await render_template("500.html", name=user.name, disc=user.discriminator, guild_id=guild_id)


@app.route('/dashboard/configs/<string:page>/<int:guild_id>', methods=["GET", "POST"])
async def configs(page, guild_id):
    if not await discord.authorized:
        return redirect(url_for("login"))
    user = await discord.fetch_user()
    try:
        main_cfg = "bot/configs/main.ini"
        # main_cfg = "C:\\Users\\User\\PycharmProjects\\ds-bot-crm\\bot\\configs\\main.ini"
        config = configparser.ConfigParser()
        config.read(main_cfg, encoding="windows-1251")

        match page:
            # case "autoroles":
            #     autoroles = await ipc_client.request("get_roles", guild_id=guild_id)
            #     if request.method == 'POST':
            #         active_roles = []
            #         result = await request.form
            #         for role in autoroles:
            #             role_id = str(role['role_id'])
            #             try:
            #                 if result[role_id]:
            #                     active_roles.append(role['role_name'])
            #             except:
            #                 continue
            #
            #         async with aiosqlite.connect("bot/databases/bot.db") as db:
            #             async with db.cursor() as cursor:
            #                 await cursor.execute(f'DELETE FROM autoroles WHERE guild = {guild_id}')
            #                 for active_role in active_roles:
            #                     await cursor.execute('INSERT INTO autoroles (guild, autorole) VALUES (?, ?)',
            #                                          (guild_id, active_role))
            #             await db.commit()
            #
            #     async with aiosqlite.connect("bot/databases/bot.db") as db:
            #         async with db.cursor() as cursor:
            #             await cursor.execute(f'SELECT autorole FROM autoroles WHERE guild = {guild_id}')
            #             data = await cursor.fetchall()
            #             if data is None:
            #                 active_roles = []
            #             else:
            #                 active_roles = []
            #                 for active_role in data:
            #                     active_roles.append(active_role[0])
            #         await db.commit()
            #
            #     return await render_template("autoroles.html", name=user.name, disc=user.discriminator, guild_id=guild_id, autoroles=autoroles, active_roles=active_roles, user_id=user.id)
            case "errors":# super admin
                if request.method == 'POST':
                    result = await request.form
                    config.set("ERROR_MSG", "error_checkfailure", result["error_checkfailure"])
                    config.set("ERROR_MSG", "error_commandnotfound", result["error_commandnotfound"])
                    config.set("ERROR_MSG", "error_missingrequiredargument", result["error_missingrequiredargument"])
                    config.set("ERROR_MSG", "error_badargument", result["error_badargument"])
                    with open(main_cfg, "w") as config_file:
                        config.write(config_file)

                    await ipc_client.request("ipc_load_extensions")
                    await ipc_client.request("update_constants")

                error_checkfailure = config.get("ERROR_MSG", "error_checkfailure")
                error_commandnotfound = config.get("ERROR_MSG", "error_commandnotfound")
                error_missingrequiredargument = config.get("ERROR_MSG", "error_missingrequiredargument")
                error_badargument = config.get("ERROR_MSG", "error_badargument")

                return await render_template("errors.html", name=user.name, disc=user.discriminator, error_checkfailure=error_checkfailure,
                                             error_commandnotfound=error_commandnotfound, error_missingrequiredargument=error_missingrequiredargument,
                                             error_badargument=error_badargument, guild_id=guild_id, user_id=user.id)
            case "logs":# super admin
                if request.method == 'POST':
                    print(await request.form)
                    result = await request.form
                    guilds = user.fetch_guilds()

                    config.set("LOGGING", "log_name", result["log_name"])
                    config.set("LOGGING", "log_path", result["log_path"])
                    config.set("LOGGING", "log_level", result["log_level"])
                    with open(main_cfg, "w") as config_file:
                        config.write(config_file)

                    await ipc_client.request("ipc_load_extensions")
                    await ipc_client.request("update_constants")

                log_name = config.get("LOGGING", "log_name")
                log_path = config.get("LOGGING", "log_path")
                log_level = config.get("LOGGING", "log_level")

                return await render_template("logs.html", name=user.name, disc=user.discriminator, log_name=log_name,
                                             log_path=log_path, log_level=log_level, guild_id=guild_id, user_id=user.id)
            case "welcome":
                autoroles = await ipc_client.request("get_roles", guild_id=guild_id)
                if request.method == 'POST':
                    active_roles = []
                    result = await request.form
                    for role in autoroles:
                        role_id = str(role['role_id'])
                        try:
                            if result[role_id]:
                                active_roles.append(role['role_name'])
                        except:
                            continue

                    async with aiosqlite.connect("bot/databases/bot.db") as db:
                        async with db.cursor() as cursor:
                            await cursor.execute(f'DELETE FROM autoroles WHERE guild = {guild_id}')
                            for active_role in active_roles:
                                await cursor.execute('INSERT INTO autoroles (guild, autorole) VALUES (?, ?)',
                                                     (guild_id, active_role))
                        await db.commit()

                    async with aiosqlite.connect("bot/databases/bot.db") as db:
                        async with db.cursor() as cursor:
                            await cursor.execute('INSERT INTO welcome_config (guild, welcome_channel, '
                                                 'welcome_message, welcome_img_text, welcome_img_font, welcome_img_bg) VALUES (?, ?, ?, ?, ?, ?)',
                                                 (guild_id, result['welcome_channel'], result['welcome_message'], result['welcome_img_text'], result['welcome_img_font'], result['welcome_img_bg']))
                        await db.commit()

                    await ipc_client.request("ipc_load_extensions")


                channels = await ipc_client.request("get_text_channels", guild_id=guild_id)

                async with aiosqlite.connect("bot/databases/bot.db") as db:
                    async with db.cursor() as cursor:
                        await cursor.execute('SELECT welcome_channel, welcome_message, welcome_img_text, welcome_img_font, welcome_img_bg FROM welcome_config WHERE guild = ?', (guild_id,))
                        data = await cursor.fetchone()
                        if data is None:
                            data = ['', '', '', '', '']

                        img_fonts = []
                        font_files = await listdir(path="bot/welcome/fonts")
                        for font in font_files:
                            img_fonts.append(font[:-4])

                        welcome_bgs = []
                        bg_files = await listdir(path="bot/welcome/backgrounds")
                        for background in bg_files:
                            welcome_bgs.append(background[:-4])

                    await db.commit()

                async with aiosqlite.connect("bot/databases/bot.db") as db:
                    async with db.cursor() as cursor:
                        await cursor.execute(f'SELECT autorole FROM autoroles WHERE guild = {guild_id}')
                        roles = await cursor.fetchall()
                        if roles is None:
                            active_roles = []
                        else:
                            active_roles = []
                            for active_role in roles:
                                active_roles.append(active_role[0])
                    await db.commit()

                return await render_template("welcome.html", name=user.name, disc=user.discriminator, channels=channels,
                                             message=data[1], img_text=data[2], img_font=data[3],
                                             welcome_bg=data[4], guild_id=guild_id, data=data, img_fonts=img_fonts,
                                             welcome_bgs=welcome_bgs, autoroles=autoroles, active_roles=active_roles, user_id=user.id)
            case _:
                logger.info(f"Страница /dashboard/configs/{page} не найдена.")
                return await render_template("404.html", name=user.name, disc=user.discriminator, guild_id=guild_id, user_id=user.id)
    except Exception as e:
        logger.warning(f"Не удалось загрузить страницу /dashboard/configs/{page} !")
        logger.exception(e)
        return await render_template("500.html", name=user.name, disc=user.discriminator, guild_id=guild_id, user_id=user.id)


@app.route('/dashboard/streams/<int:guild_id>', methods=["GET", "POST"])
async def streams(guild_id):
    if not await discord.authorized:
        return redirect(url_for("login"))
    user = await discord.fetch_user()
    data_channels = await ipc_client.request("get_data_text_channels", guild_id=guild_id)
    noty_roles = await ipc_client.request("get_roles", guild_id=guild_id)
    if request.method == 'POST':
        active_roles = []
        result = await request.form
        twitch_account = result['twitch_account'].split("/")
        streamer_login = twitch_account[3]
        async with aiosqlite.connect("bot/databases/twitch_schedule.db") as db:
            async with db.cursor() as cursor:
                await cursor.execute(
                    f'SELECT streamer_login FROM twitch_accounts WHERE guild = {guild_id}')
                data = await cursor.fetchone()
                if data is not None:
                    streamer_list = []
                    for streamer in data:
                        streamer_list.append(streamer)
                else:
                    streamer_list = None
            await db.commit()
        if streamer_list is None or streamer_login not in streamer_list:
            streamer_info = twitch.get_users(logins=[streamer_login])
            streamer_id = streamer_info['data'][0]['id']
            noty_channel = result['noty_channel']
            async with aiosqlite.connect("bot/databases/twitch_schedule.db") as db:
                async with db.cursor() as cursor:
                    await cursor.execute(
                        'INSERT INTO twitch_accounts (guild, streamer_id, streamer_login, channel_id, notificated) VALUES (?, ?, ?, ?, ?)',
                        (guild_id, streamer_id, streamer_login, noty_channel, "No"))
                await db.commit()
            for role in noty_roles:
                role_id = str(role['role_id'])
                try:
                    if result[role_id]:
                        active_roles.append(role['role_name'])
                except:
                    continue

            async with aiosqlite.connect("bot/databases/twitch_schedule.db") as db:
                async with db.cursor() as cursor:
                    for active_role in active_roles:
                        await cursor.execute('INSERT INTO notification_roles (guild, streamer_login, noty_role) VALUES (?, ?, ?)',
                                             (guild_id, streamer_login, active_role))
                await db.commit()

    async with aiosqlite.connect("bot/databases/twitch_schedule.db") as db:
        async with db.cursor() as cursor:
            await cursor.execute(f'SELECT streamer_login, noty_role FROM notification_roles WHERE guild = {guild_id}')
            data = await cursor.fetchall()
            if data is None:
                active_roles = []
            else:
                active_roles = []
                for active_role in data:
                    active_roles.append({"streamer_login": active_role[0], "noty_role": active_role[1]})
        await db.commit()

    async with aiosqlite.connect("bot/databases/twitch_schedule.db") as db:
        async with db.cursor() as cursor:
            query = f"SELECT streamer_login FROM twitch_accounts WHERE guild = {guild_id}"
            await cursor.execute(query)
            streamers_request = await cursor.fetchall()
        await db.commit()

    streamer_logins = []
    for streamer in streamers_request:
        streamer_logins.append(streamer[0])

    stream_list = []
    for i in range(len(streamer_logins)):
        try:
            streamer = twitch.get_users(logins=streamer_logins[i])
            streamer_id = streamer['data'][0]['id']
            stream_live = twitch.get_streams(user_id=streamer_id)
            if stream_live['data']:
                if stream_live['data'][0]['type'] == 'live':
                    start_datetime = stream_live['data'][0]['started_at']
                    start_datetime = start_datetime.replace("Z", "")
                    start_datetime = start_datetime.split('T')
                    start_date = start_datetime[0].split("-")
                    start_time = start_datetime[1].split(":")
                    delta = datetime.timedelta(hours=3, minutes=0)
                    format_datetime = datetime.datetime(year=int(start_date[0]), month=int(start_date[1]),
                                                        day=int(start_date[2]), hour=int(start_time[0]),
                                                        minute=int(start_time[1]), second=int(start_time[2])) + delta
                    format_datetime = str(format_datetime).split(" ")
                    stream = {"username": streamer_logins[i], "title": stream_live['data'][0]['title'],
                              "start_date": format_datetime[0], "start_time": format_datetime[1], "status": "В ЭФИРЕ"}

                    async with aiosqlite.connect("bot/databases/twitch_schedule.db") as db:
                        async with db.cursor() as cursor:
                            await cursor.execute('INSERT INTO stream_schedule (guild, data_at, streamer_id, streamer, type) VALUES (?, ?, ?, ?, ?)', (guild_id, format_datetime[0], streamer_id, streamer_logins[i], "-"))
                        await db.commit()

            else:
                schedule = twitch.get_channel_stream_schedule(broadcaster_id=streamer_id)
                start_datetime = schedule['data']['segments'][0]['start_time']
                start_datetime = start_datetime.replace("Z", "")
                start_datetime = start_datetime.split('T')
                start_date = start_datetime[0].split("-")
                start_time = start_datetime[1].split(":")
                delta = datetime.timedelta(hours=3, minutes=0)
                format_datetime = datetime.datetime(year=int(start_date[0]), month=int(start_date[1]),
                                                    day=int(start_date[2]), hour=int(start_time[0]),
                                                    minute=int(start_time[1]), second=int(start_time[2])) + delta
                format_datetime = str(format_datetime).split(" ")

                stream = {"id": streamer_id, "username": streamer_logins[i], "title": schedule['data']['segments'][0]['title'],
                          "start_date": format_datetime[0], "start_time": format_datetime[1], "status": "Запланирован"}
        except:
            schedule = None
            stream = {"id": streamer_id, "username": streamer_logins[i], "title": "-",
                      "start_date": "-", "start_time": "-", "status": "Нет данных"}
        stream_list.append(stream)

    return await render_template("streams.html", name=user.name, disc=user.discriminator, guild_id=guild_id, stream_list=stream_list, active_roles=active_roles, noty_roles=noty_roles, data_channels=data_channels, user_id=user.id)


@app.route('/dashboard/<int:guild_id>/streams/del/<int:streamer_id>')
async def streamer_del(guild_id, streamer_id):
    if not await discord.authorized:
        return redirect(url_for("login"))
    user = await discord.fetch_user()

    async with aiosqlite.connect("bot/databases/twitch_schedule.db") as db:
        async with db.cursor() as cursor:
            await cursor.execute(f'DELETE FROM twitch_accounts WHERE guild = {guild_id} AND streamer_id = {streamer_id}')
            await cursor.execute(f'DELETE FROM notification_roles WHERE guild = {guild_id} AND streamer_id = {streamer_id}')
            await cursor.execute(f'DELETE FROM stream_schedule WHERE guild = {guild_id} AND streamer_id = {streamer_id}')
        await db.commit()

    return redirect(url_for("streams", guild_id=guild_id))




@app.route('/dashboard/actions/<string:page>/<int:guild_id>', methods=["GET", "POST"])
async def actions(page, guild_id):
    if not await discord.authorized:
        return redirect(url_for("login"))
    user = await discord.fetch_user()

    match page:
        case "embed":
            data_channels = await ipc_client.request("get_data_text_channels", guild_id=guild_id)
            if request.method == 'POST':
                result = await request.form
                files = await request.files
                field_data = []
                main_img_path = None
                bt_img_path = None
                try:
                    if 'main_img_embed' in files:
                        file = files['main_img_embed']
                        if file and allowed_file(file.filename):
                            file_format = str(file.filename).split(".")
                            file_format = file_format[1]
                            filename = f"main_{guild_id}.{file_format}"
                            await file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                            main_img_path = f"{app.config['DOMAIN']}/static/temp/{filename}"

                    if 'bt_img_embed' in await request.files:
                        file = files['bt_img_embed']
                        if file and allowed_file(file.filename):
                            file_format = str(file.filename).split(".")
                            file_format = file_format[1]
                            filename = f"bt_{guild_id}.{file_format}"
                            await file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                            bt_img_path = f"{app.config['DOMAIN']}/static/temp/{filename}"

                    for i in range(3):
                        field_name = "field_embed_"+str(i+1)
                        field_value = "field_value_embed_"+str(i+1)

                        if result[field_name] and result[field_value]:
                            field_data.append({"field_name": result[field_name], "field_value": result[field_value]})

                    color_embed = result['color_embed'].replace('#', '')
                    color_embed = int(color_embed, 16)

                    await ipc_client.request("send_embed", guild_id=guild_id, channel_embed=int(result['channel_embed']),
                                             color_embed=color_embed, title_embed=result['title_embed'],
                                             text_embed=result['text_embed'], field_data=field_data,
                                             bt_text_embed=result['bt_text_embed'], main_img_path=main_img_path,
                                             bt_img_path=bt_img_path)
                except Exception as e:
                    logger.exception(e)
                    return await render_template("500.html", name=user.name, disc=user.discriminator, guild_id=guild_id, user_id=user.id)
            return await render_template("embed.html", name=user.name, disc=user.discriminator, guild_id=guild_id,
                                         data_channels=data_channels, user_id=user.id)
        case "react_role":
            data_channels = await ipc_client.request("get_data_text_channels", guild_id=guild_id)
            async with aiosqlite.connect("bot/databases/bot.db") as db:
                async with db.cursor() as cursor:
                    await cursor.execute(f"SELECT COUNT(_id) FROM react_roles WHERE guild = {guild_id}")
                    count = await cursor.fetchone()
                    if count is None:
                        count = 0
                await db.commit()
            react_message_info = f"ReactMessage/ID:{count[0]}"
            with open("ds-emojis/emojis.json") as f:
                emojis = json.load(f)

            if request.method == 'POST':
                result = await request.form
                logger.debug(result["emojis[]"])
                files = await request.files
                field_data = []
                main_img_path = None
                bt_img_path = None
                try:
                    if 'main_img_embed' in files:
                        file = files['main_img_embed']
                        if file and allowed_file(file.filename):
                            file_format = str(file.filename).split(".")
                            file_format = file_format[1]
                            filename = f"main_{guild_id}.{file_format}"
                            await file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                            main_img_path = f"{app.config['DOMAIN']}/static/temp/{filename}"

                    if 'bt_img_embed' in await request.files:
                        file = files['bt_img_embed']
                        if file and allowed_file(file.filename):
                            file_format = str(file.filename).split(".")
                            file_format = file_format[1]
                            filename = f"bt_{guild_id}.{file_format}"
                            await file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                            bt_img_path = f"{app.config['DOMAIN']}/static/temp/{filename}"

                    for i in range(3):
                        field_name = "field_embed_" + str(i + 1)
                        field_value = "field_value_embed_" + str(i + 1)

                        if result[field_name] and result[field_value]:
                            field_data.append({"field_name": result[field_name], "field_value": result[field_value]})

                    color_embed = result['color_embed'].replace('#', '')
                    color_embed = int(color_embed, 16)

                    await ipc_client.request("send_embed", guild_id=guild_id,
                                             channel_embed=int(result['channel_embed']),
                                             color_embed=color_embed, title_embed=result['title_embed'],
                                             text_embed=result['text_embed'], field_data=field_data,
                                             bt_text_embed=result['bt_text_embed'], main_img_path=main_img_path,
                                             bt_img_path=bt_img_path)
                except Exception as e:
                    logger.exception(e)
                    return await render_template("500.html", name=user.name, disc=user.discriminator, guild_id=guild_id, user_id=user.id)
            return await render_template("react_role.html", name=user.name, disc=user.discriminator, guild_id=guild_id,
                                         data_channels=data_channels, react_message_info=react_message_info, emojis=emojis, user_id=user.id)
        case _:
            return await render_template("404.html", name=user.name, disc=user.discriminator, guild_id=guild_id, user_id=user.id)


@app.route('/dashboard/bot_settings/<int:guild_id>')
async def bot_settings(guild_id):
    if not await discord.authorized:
        return redirect(url_for("login"))
    user = await discord.fetch_user()
    return await render_template("bot_settings.html", name=user.name, disc=user.discriminator, guild_id=guild_id, user_id=user.id)


@app.route('/get_last_messages/<int:guild_id>', methods=['GET'])
async def get_last_messages(guild_id):
    try:
        guild = await ipc_client.request("get_guild", guild_id=guild_id)
        guild_name_sql = guild['name']
        guild_name_sql = guild_name_sql.replace(" ", "_")
        guild_name_sql = guild_name_sql.replace("|", "")
        guild_name_sql = guild_name_sql.replace("'", "")
        async with aiosqlite.connect("bot/databases/msg_history.db") as db:
            async with db.cursor() as cursor:
                query = f"SELECT author, channel, message FROM {guild_name_sql} WHERE guild = {guild_id}"
                await cursor.execute(query)
                messages = await cursor.fetchall()
            await db.commit()

        result = await ipc_client.request("get_message_info", messages=messages, limit=50)
    except:
        result = [{'author_id': "-", 'message_id': "-", 'author': "Ошибка", 'channel': "-", 'avatar_url': "http://127.0.0.1:5555/static/dist/img/user.png", 'message': "Данные не получены. Обновите страницу."}]

    return jsonify(result=result)


@app.route('/get_logs', methods=['GET'])
async def get_logs():
    result = []

    with open("bot/logs/app.log", encoding="utf-8") as logs:
        last_logs = list(deque(logs, 5))

    for log in last_logs:
        log = log.split("::")
        log_module = log[1].replace("\n", "")
        log_msg = log[3].replace("\n", "")
        date_time = log[0].split(",")
        date_time = date_time[0]
        j_log = {"datetime": date_time, "module": log_module, "msg": log_msg}
        result.append(j_log)

    return jsonify(result=result)


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


def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


if __name__ == "__main__":
    init_logger(LOG_NAME, LOG_PATH, LOG_LEVEL)
    logger = logging.getLogger(LOGGER_NAME)
    twitch = Twitch('jfaqntyx8b8w5y136870ddvjhrkckz', 'wqkgkr4w8h3l8d7cd7xyb24ig8x3h5')
    app.run(host="185.20.227.14", port=5555, debug=True)