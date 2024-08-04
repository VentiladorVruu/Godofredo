import discord
from discord.ext import commands
import yt_dlp
import asyncio
import re
import requests
from bs4 import BeautifulSoup

intents=discord.Intents.default()
intents.voice_states = True
intents.message_content = True

time_to_get_out = 150
TOKEN = '' # discord bot token

FFMPEG_OPTIONS = {
    'options': '-vn',
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5'
} 

YDL_OPTIONS = {'format' : 'bestaudio', 'noplaylist' : True }

def get_youtube_title(url):
        response = requests.get(url)
        soup = BeautifulSoup(response.content, 'html.parser')
        title = soup.find('title').string.replace(' - YouTube', '')
        return title
class MusicBot(commands.Cog):
    def __init__(self, client): 
        self.client = client
        self.queue = []
        self.timer_task = None
    @commands.command()
    async def play(self, ctx, *, search):
        voice_channel = ctx.author.voice.channel if ctx.author.voice else None
        if not voice_channel:
           return await ctx.send("You're not in a voice channel!")
        if re.match(r'^(?:https?:\/\/)?(?:www\.)?youtube\.com\/watch\?v=[\w-]+', search) or re.match(r'^(?:https?:\/\/)?youtu\.be\/[\w-]+', search):
            print("YOUTUBE LINK DETECTED")
            url = search
            title = get_youtube_title(url)
            print (title)
            print (url)
            if not ctx.voice_client:
                await voice_channel.connect()
            async with ctx.typing():
                with yt_dlp.YoutubeDL(YDL_OPTIONS) as ydl:
                    info = ydl.extract_info(url, download=False)
                    if 'entries' in info:
                        info = info['entries'][0]
                    url = info['url']
                    title = info['title']
                    self.queue.append((url, title))
                    await ctx.send(f'Added to queue: **{title}**')
                    if not ctx.voice_client.is_playing():
                        await self.play_next(ctx)
        else:
            if not ctx.voice_client:
                await voice_channel.connect()
            async with ctx.typing():
                with yt_dlp.YoutubeDL(YDL_OPTIONS) as ydl:
                    info = ydl.extract_info(f"ytsearch:{search}", download=False)
                    if 'entries' in info:
                        info = info['entries'][0] 
                    url = info['url']
                    title = info['title'] 
                    self.queue.append((url, title))
                    await ctx.send(f'Added to queue: **{title}**')  

        if ctx.voice_client.is_playing():
            if self.timer_task:
                self.timer_task.cancel()
        else:
            await self.play_next(ctx) 

    async def play_next(self, ctx): 
        if self.queue:
            url, title = self.queue.pop(0)
            source = await discord.FFmpegOpusAudio.from_probe(url, **FFMPEG_OPTIONS)
            ctx.voice_client.play(source, after=lambda _:self.client.loop.create_task(self.play_next(ctx)))
            await ctx.send(f'Now playing **{title}**')
        elif not ctx.voice_client.is_playing():
            self.timer_task = self.client.loop.create_task(self.timer(ctx))
            await ctx.send("Queue is empty.")
        elif ctx.voice_client.is_playing():
            if self.timer_task:
                self.timer_task.cancel()

    @commands.command()
    async def skip(self, ctx):
        if ctx.voice_client and ctx.voice_client.is_playing():
            ctx.voice_client.stop()
            await ctx.send("Skipped")
    @commands.command()
    async def queue(self, ctx):
        if self.queue:
            queue_list = [f'**{title}**' for _, title in self.queue]
            queue_str = '\n'.join(queue_list)
            await ctx.send(f"Queue:\n{queue_str}")
        else:
            await ctx.send("Queue is empty.")
    @commands.command()
    async def leave(self, ctx):
        if ctx.voice_client:
            await ctx.voice_client.disconnect()
        else:
            await ctx.send("I am not connected to a voice channel") 
    async def timer(self, ctx): 
        await asyncio.sleep(time_to_get_out)
        print ("Timer is up!")
        if not self.client.is_closed():
            if ctx.voice_client:
                await ctx.voice_client.disconnect()
            else:
                await ctx.send("I am not connected to a voice channel")

client = commands.Bot(command_prefix="!", intents=intents)

async def main():
    await client.add_cog(MusicBot(client))
    await client.start(TOKEN)

asyncio.run(main())
