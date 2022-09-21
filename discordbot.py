import asyncio
from datetime import datetime

import discord
from discord.ext import commands
import os
import traceback
import re
# import emoji
import json
import psycopg2
import roma2kana

prefix = os.getenv('DISCORD_BOT_PREFIX', default='🦑')
token = os.environ['DISCORD_BOT_TOKEN']
voicevox_key = os.environ['VOICEVOX_KEY']
client = commands.Bot(command_prefix=prefix)
with open('emoji_ja.json', encoding='utf-8') as file:
    emoji_dataset = json.load(file)
database_url = os.environ.get('DATABASE_URL')

SQLpath = os.environ["DATABASE_URL"]
db = psycopg2.connect(SQLpath)  # sqlに接続
cur = db.cursor()  # なんか操作する時に使うやつ

romaji2katakana, romaji2hiragana, kana2romaji = roma2kana.make_romaji_convertor()


@client.event
async def on_ready():
    presence = f'{prefix}hでヘルプを参照'
    await client.change_presence(activity=discord.Game(name=presence))
    print("Ready")


@client.event
async def on_guild_join(guild):
    presence = f'{prefix}hでヘルプを参照'
    await client.change_presence(activity=discord.Game(name=presence))


@client.event
async def on_guild_remove(guild):
    presence = f'{prefix}hでヘルプを参照'
    await client.change_presence(activity=discord.Game(name=presence))


@client.command()
async def join(ctx):
    if ctx.message.guild:
        if ctx.author.voice is None:
            await ctx.send('ボイスチャンネルに接続してから呼び出してください。')
        else:
            if ctx.guild.voice_client:
                if ctx.author.voice.channel == ctx.guild.voice_client.channel:
                    await ctx.send('接続済みです。')
                else:
                    await ctx.voice_client.disconnect()
                    await asyncio.sleep(0.5)
                    await ctx.author.voice.channel.connect()
            else:
                await ctx.author.voice.channel.connect()


@client.command()
async def leave(ctx):
    if ctx.message.guild:
        if ctx.voice_client is None:
            await ctx.send('ボイスチャンネルに接続していません。')
        else:
            await ctx.voice_client.disconnect()


@client.command(aliases=["da"])
async def dict_add(ctx, *args):
    if len(args) < 2:
        await ctx.send(f'「{prefix}dict_add(da) 単語 よみがな」で入力してください。')
    else:
        with psycopg2.connect(database_url) as conn:
            with conn.cursor() as cur:
                guild_id = ctx.guild.id
                word = args[0]
                kana = args[1]
                sql = 'INSERT INTO dictionary (guildId, word, kana) VALUES (%s,%s,%s) ON CONFLICT (guildId, word) DO UPDATE SET kana = EXCLUDED.kana'
                value = (guild_id, word, kana)
                cur.execute(sql, value)
                await ctx.send(f'辞書登録しました：{word}→{kana}\n')


@client.command(aliases=["dr"])
async def dict_remove(ctx, arg):
    with psycopg2.connect(database_url) as conn:
        with conn.cursor() as cur:
            guild_id = ctx.guild.id
            word = arg

            sql = 'SELECT * FROM dictionary WHERE guildId = %s and word = %s'
            value = (guild_id, word)
            cur.execute(sql, value)
            rows = cur.fetchall()

            if len(rows) == 0:
                await ctx.send(f'辞書登録されていません：{word}')
            else:
                sql = 'DELETE FROM dictionary WHERE guildId = %s and word = %s'
                cur.execute(sql, value)
                await ctx.send(f'辞書削除しました：{word}')


@client.command(aliases=["dc"])
async def dict_check(ctx):
    with psycopg2.connect(database_url) as conn:
        with conn.cursor() as cur:
            sql = 'SELECT * FROM dictionary WHERE guildId = %s'
            value = (ctx.guild.id,)
            cur.execute(sql, value)
            rows = cur.fetchall()
            text = '辞書一覧\n'
            if len(rows) == 0:
                text += 'なし'
            else:
                for row in rows:
                    text += f'{row[1]}→{row[2]}\n'
            await ctx.send(text)


@client.event
async def on_message(message):
    try:
        if message.guild.voice_client:
            if not message.author.bot and message.channel.id == 772438848444694529:
                if not message.content.startswith(prefix) and not message.content.startswith("!") and not message.content.startswith("https://gyazo.com/"):
                    text = message.content

                    # Replace dictionary
                    with psycopg2.connect(database_url) as conn:
                        with conn.cursor() as cur:
                            sql = 'SELECT * FROM dictionary WHERE guildId = %s'
                            value = (message.guild.id,)
                            cur.execute(sql, value)
                            rows = cur.fetchall()
                            for row in rows:
                                word = row[1]
                                kana = row[2]
                                text = text.replace(word, kana)

                    # Replace new line
                    text = text.replace('\n', '、')

                    # Replace mention to user
                    pattern = r'<@!?(\d+)>'
                    match = re.findall(pattern, text)
                    for user_id in match:
                        user = await client.fetch_user(user_id)
                        user_name = f'、{user.name}、'
                        text = re.sub(rf'<@!?{user_id}>', user_name, text)

                    # Replace mention to role
                    pattern = r'<@&(\d+)>'
                    match = re.findall(pattern, text)
                    for role_id in match:
                        role = message.guild.get_role(int(role_id))
                        role_name = f'、{role.name}、'
                        text = re.sub(f'<@&{role_id}>', role_name, text)

                    # Replace Unicode emoji
                    text = re.sub(r'[\U0000FE00-\U0000FE0F]', '', text)
                    text = re.sub(r'[\U0001F3FB-\U0001F3FF]', '', text)
                    # for char in text:
                    #     if char in emoji.UNICODE_EMOJI['en'] and char in emoji_dataset:
                    #         text = text.replace(char, emoji_dataset[char]['short_name'])

                    # Replace Discord emoji
                    pattern = r'<:([a-zA-Z0-9_]+):\d+>'
                    match = re.findall(pattern, text)
                    for emoji_name in match:
                        emoji_read_name = emoji_name.replace('_', ' ')
                        text = re.sub(rf'<:{emoji_name}:\d+>', f'、{emoji_read_name}、', text)

                    # Replace URL
                    pattern = r'https://tenor.com/view/[\w/:%#\$&\?\(\)~\.=\+\-]+'
                    text = re.sub(pattern, '画像', text)
                    pattern = r'https?://[\w/:%#\$&\?\(\)~\.=\+\-]+(\.jpg|\.jpeg|\.gif|\.png|\.bmp)'
                    text = re.sub(pattern, '、画像', text)
                    pattern = r'https?://[\w/:%#\$&\?\(\)~\.=\+\-]+'
                    text = re.sub(pattern, '、ユーアールエル省略', text)

                    # Replace spoiler
                    pattern = r'\|{2}.+?\|{2}'
                    text = re.sub(pattern, '伏せ字', text)

                    # Replace laughing expression
                    if text[-1:] == 'w' or text[-1:] == 'W' or text[-1:] == 'ｗ' or text[-1:] == 'W':
                        while text[-2:-1] == 'w' or text[-2:-1] == 'W' or text[-2:-1] == 'ｗ' or text[-2:-1] == 'W':
                            text = text[:-1]
                        text = text[:-1] + '、ワラ'

                    # Add attachment presence
                    for attachment in message.attachments:
                        if attachment.filename.endswith((".jpg", ".jpeg", ".gif", ".png", ".bmp")):
                            text += '、画像'
                        else:
                            text += '、添付ファイル'

                    # Replace roma 2 kana when start string is "!"
                    text = romaji2hiragana(text)

                    with psycopg2.connect(database_url) as conn:
                        with conn.cursor() as cur:
                            sql = f'SELECT * FROM voice_setting WHERE discord_id = {message.author.id}'
                            cur.execute(sql)
                            result = cur.fetchone()
                            voicevox_speaker = result[1]

                    print(text)

                    mp3url = f'https://api.su-shiki.com/v2/voicevox/audio/?text={text}&key={voicevox_key}&speaker={voicevox_speaker}&intonationScale=1'
                    while message.guild.voice_client.is_playing():
                        await asyncio.sleep(0.5)
                    source = await discord.FFmpegOpusAudio.from_probe(mp3url)
                    message.guild.voice_client.play(source)
        await client.process_commands(message)
    except Exception as e:
        orig_error = getattr(e, "original", e)
        error_msg = ''.join(traceback.TracebackException.from_exception(orig_error).format())
        error_message = f'```{error_msg}```'
        ch = client.get_channel(628807266753183754)
        d = datetime.now()  # 現在時刻の取得
        time = d.strftime("%Y/%m/%d %H:%M:%S")
        embed = discord.Embed(title='Error_log', description=error_message, color=0xf04747)
        embed.set_footer(text=f'channel:on_check_time_loop\ntime:{time}\nuser:None')
        await ch.send(embed=embed)


@client.event
async def on_voice_state_update(member, before, after):
    try:
        with psycopg2.connect(database_url) as conn:
            with conn.cursor() as cur:
                sql = f'SELECT * FROM voice_setting WHERE discord_id = {member.id}'
                cur.execute(sql)
                result = cur.fetchone()
                try:
                    voicevox_speaker = result[1]
                except TypeError:
                    pass
        if before.channel is None:
            if member.id == client.user.id:
                presence = f'{prefix}ヘルプ | {len(client.voice_clients)}/{len(client.guilds)}サーバー'
                await client.change_presence(activity=discord.Game(name=presence))
            else:
                if member.guild.voice_client is None:
                    await asyncio.sleep(0.5)
                    await after.channel.connect()
                else:
                    if member.guild.voice_client.channel is after.channel:
                        text = member.name + 'さんが入室しました'
                        # Replace dictionary
                        with psycopg2.connect(database_url) as conn:
                            with conn.cursor() as cur:
                                sql = 'SELECT * FROM dictionary WHERE guildId = %s'
                                value = (member.guild.id,)
                                cur.execute(sql, value)
                                rows = cur.fetchall()
                                for row in rows:
                                    word = row[1]
                                    kana = row[2]
                                    text = text.replace(word, kana)
                        mp3url = f'https://api.su-shiki.com/v2/voicevox/audio/?text={text}&key={voicevox_key}&speaker={voicevox_speaker}&intonationScale=1'
                        while member.guild.voice_client.is_playing():
                            await asyncio.sleep(0.5)
                        source = await discord.FFmpegOpusAudio.from_probe(mp3url)
                        member.guild.voice_client.play(source)
        elif after.channel is None:
            if member.id == client.user.id:
                presence = f'{prefix}ヘルプ | {len(client.voice_clients)}/{len(client.guilds)}サーバー'
                await client.change_presence(activity=discord.Game(name=presence))
            else:
                if member.guild.voice_client:
                    if member.guild.voice_client.channel is before.channel:
                        mem_check = member.guild.voice_client.channel.members
                        for i in mem_check:
                            if i.bot:
                                mem_check.pop(i)
                        if len(mem_check) <= 1:
                            await asyncio.sleep(0.5)
                            await member.guild.voice_client.disconnect()
                        else:
                            text = member.name + 'さんが退室しました'
                            # Replace dictionary
                            with psycopg2.connect(database_url) as conn:
                                with conn.cursor() as cur:
                                    sql = 'SELECT * FROM dictionary WHERE guildId = %s'
                                    value = (member.guild.id,)
                                    cur.execute(sql, value)
                                    rows = cur.fetchall()
                                    for row in rows:
                                        word = row[1]
                                        kana = row[2]
                                        text = text.replace(word, kana)
                            mp3url = f'https://api.su-shiki.com/v2/voicevox/audio/?text={text}&key={voicevox_key}&speaker={voicevox_speaker}&intonationScale=1'
                            while member.guild.voice_client.is_playing():
                                await asyncio.sleep(0.5)
                            source = await discord.FFmpegOpusAudio.from_probe(mp3url)
                            member.guild.voice_client.play(source)
        elif before.channel != after.channel:
            if member.guild.voice_client:
                if member.guild.voice_client.channel is before.channel:
                    if len(member.guild.voice_client.channel.members) == 1 or member.voice.self_mute:
                        await asyncio.sleep(0.5)
                        await member.guild.voice_client.disconnect()
                        await asyncio.sleep(0.5)
                        await after.channel.connect()
    except Exception as e:
        orig_error = getattr(e, "original", e)
        error_msg = ''.join(traceback.TracebackException.from_exception(orig_error).format())
        error_message = f'```{error_msg}```'
        ch = client.get_channel(628807266753183754)
        d = datetime.now()  # 現在時刻の取得
        time = d.strftime("%Y/%m/%d %H:%M:%S")
        embed = discord.Embed(title='Error_log', description=error_message, color=0xf04747)
        embed.set_footer(text=f'channel:on_check_time_loop\ntime:{time}\nuser:None')
        await ch.send(embed=embed)


@client.event
async def on_command_error(ctx, error):
    orig_error = getattr(error, 'original', error)
    error_msg = ''.join(traceback.TracebackException.from_exception(orig_error).format())
    if "CommandNotFound" in error_msg:
        pass
    else:
        await ctx.send(error_msg)


@client.command(aliases=["s"])
async def settings(ctx):
    try:
        def check(m):
            if m.author.bot:
                return
            return m.channel == ctx.channel and m.author == ctx.author

        def edit_embed(target_embed, title, description):
            embed = target_embed.embeds[0]
            embed.description = description
            embed.title = title
            return embed

        with psycopg2.connect(database_url) as conn:
            with conn.cursor() as cur:
                sql = f'SELECT * FROM voice_setting WHERE discord_id = {ctx.author.id}'
                cur.execute(sql)
                result = cur.fetchone()
                voicevox_speaker = result[1]
        show_embed_description = f"あなたの現在の設定は、声番号{voicevox_speaker}です。\n\n以下から声を番号で指定してください。\n\n" \
                                 f"0: 四国めたん あまあま\n\
                                    1: ずんだもん あまあま\n\
                                    2: 四国めたん ノーマル\n\
                                    3: ずんだもん ノーマル\n\
                                    4: 四国めたん セクシー\n\
                                    5: ずんだもん セクシー\n\
                                    6: 四国めたん ツンツン\n\
                                    7: ずんだもん ツンツン\n\
                                    8: 春日部つむぎ ノーマル\n\
                                    9: 波音リツ ノーマル\n\
                                    10: 雨晴はう ノーマル\n\
                                    11: 玄野武宏 ノーマル\n\
                                    12: 白上虎太郎 ノーマル\n\
                                    13: 青山龍星 ノーマル\n\
                                    14: 冥鳴ひまり ノーマル"
        embed = discord.Embed(
            description=show_embed_description,
            color=0x61c1a9)
        show_embed = await ctx.send(embed=embed)
        user_select_input = await client.wait_for("message", check=check)
        user_select_input = str(user_select_input.content).lower()
        try:
            if 0 <= int(user_select_input) <= 14:
                pass
            else:
                await show_embed.edit(embed=edit_embed(show_embed, "Error", "0～14の整数値で入力して下さい。"))
                return
        except:
            await show_embed.edit(embed=edit_embed(show_embed, "Error", "0～14の整数値で入力して下さい。"))
            return
        with psycopg2.connect(database_url) as conn:
            with conn.cursor() as cur:
                sql = f'UPDATE voice_setting SET voice_setting = {int(user_select_input)} WHERE discord_id = {ctx.author.id}'
                cur.execute(sql)
        await show_embed.edit(embed=edit_embed(show_embed, "Success", f"更新完了。\n現在の声設定: {user_select_input}\n\n\
                                                                        0: 四国めたん あまあま\n\
                                                                        1: ずんだもん あまあま\n\
                                                                        2: 四国めたん ノーマル\n\
                                                                        3: ずんだもん ノーマル\n\
                                                                        4: 四国めたん セクシー\n\
                                                                        5: ずんだもん セクシー\n\
                                                                        6: 四国めたん ツンツン\n\
                                                                        7: ずんだもん ツンツン\n\
                                                                        8: 春日部つむぎ ノーマル\n\
                                                                        9: 波音リツ ノーマル\n\
                                                                        10: 雨晴はう ノーマル\n\
                                                                        11: 玄野武宏 ノーマル\n\
                                                                        12: 白上虎太郎 ノーマル\n\
                                                                        13: 青山龍星 ノーマル\n\
                                                                        14: 冥鳴ひまり ノーマル"))
    except Exception as e:
        orig_error = getattr(e, "original", e)
        error_msg = ''.join(traceback.TracebackException.from_exception(orig_error).format())
        error_message = f'```{error_msg}```'
        ch = client.get_channel(628807266753183754)
        d = datetime.now()  # 現在時刻の取得
        time = d.strftime("%Y/%m/%d %H:%M:%S")
        embed = discord.Embed(title='Error_log', description=error_message, color=0xf04747)
        embed.set_footer(text=f'channel:on_check_time_loop\ntime:{time}\nuser:None')
        await ch.send(embed=embed)


@client.command()
async def h(ctx):
    message = f'''◆◇◆{client.user.name}の使い方◆◇◆
    {prefix}join：ボイスチャンネルに接続します。
    {prefix}leave：ボイスチャンネルから切断します。
    {prefix}dict_check(dc)：辞書に登録されている単語を確認します。
    {prefix}dict_add(da) 単語 よみがな：辞書に[単語]を[よみがな]として追加します。
    {prefix}dict_remove(dr) 単語：辞書から[単語]のよみがなを削除します。
    {prefix}settings(s) 声の種類を登録できます。'''
    await ctx.send(message)


client.run(token)
