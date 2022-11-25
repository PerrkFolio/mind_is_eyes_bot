import asyncio
import datetime
import time

import aiosqlite
from twitchAPI.twitch import Twitch
from nextcord.ext import ipc


twitch = Twitch('jfaqntyx8b8w5y136870ddvjhrkckz', 'wqkgkr4w8h3l8d7cd7xyb24ig8x3h5')
ipc_client = ipc.Client(secret_key="test123")


async def twitch_notifications():
    async with aiosqlite.connect("../bot/databases/twitch_schedule.db") as db:
        async with db.cursor() as cursor:
            await cursor.execute("SELECT streamer_login, channel_id, notificated, guild FROM twitch_accounts")
            streamers_request = await cursor.fetchall()
        await db.commit()

    streamers_data = []
    for streamer in streamers_request:
        streamers_data.append({"login": streamer[0], "channel": streamer[1], "notificated": streamer[2], "guild_id": streamer[3]})

    for i in range(len(streamers_data)):
        stream_data = twitch.get_streams(user_login=streamers_data[i]["login"])
        streamer_info = twitch.get_users(logins=[streamers_data[i]["login"]])
        streamer_id = streamer_info['data'][0]['id']
        try:
            if stream_data["data"][0]["type"] == "live" and streamers_data[i]["notificated"] == "No":
                channel_id = streamers_data[i]["channel"]
                guild_id = streamers_data[i]["guild_id"]
                streamer = streamers_data[i]["login"]
                stream_title = stream_data["data"][0]["title"]
                stream_game = stream_data["data"][0]["game_name"]
                stream_img = stream_data["data"][0]["thumbnail_url"]
                stream_img = stream_img.replace("{width}", "1920")
                stream_img = stream_img.replace("{height}", "1080")
                result = await ipc_client.request("send_noty_twitch", stream_title=stream_title, stream_game=stream_game,
                                                  stream_img=stream_img, channel_id=channel_id, guild_id=guild_id,
                                                  streamer=streamer)
                if result:
                    async with aiosqlite.connect("../bot/databases/twitch_schedule.db") as db:
                        async with db.cursor() as cursor:
                            await cursor.execute(f"UPDATE twitch_accounts SET notificated = 'Yes' WHERE streamer_id = {streamer_id}")
                        await db.commit()

        except:
            async with aiosqlite.connect("../bot/databases/twitch_schedule.db") as db:
                async with db.cursor() as cursor:
                    await cursor.execute(
                        f"UPDATE twitch_accounts SET notificated = 'No' WHERE streamer_id = {streamer_id}")
                await db.commit()

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    while True:
        time.sleep(10)
        loop.run_until_complete(twitch_notifications())