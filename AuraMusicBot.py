import discord
import yt_dlp
from discord.ui import View, Button

intents = discord.Intents.default()
intents.message_content = True
bot = discord.Client(intents=intents)

TOKEN = 'Put Bot Token Here' #Token here
ffmpeg_path = "ffmpeg.exe"

import shutil
import sys

def check_ffmpeg_installed():
    if shutil.which("ffmpeg") is None:
        print("\n[ERROR] ffmpeg not found! Install it using one of these commands:")
        print(" - winget install --id Gyan.FFmpeg -e")
        print(" - OR choco install ffmpeg (if using Chocolatey)")
        print(" - OR scoop install ffmpeg (if using Scoop)")
        sys.exit(1)  # Exit program if ffmpeg is missing
    else:
        print("[INFO] ffmpeg is installed and ready.")

# ===== Usage =====
check_ffmpeg_installed()

# yt-dlp config
ytdl_format_options = {
    'format': 'bestaudio',
    'quiet': True,
    'default_search': 'ytsearch',
    'no_warnings': True,
    'noplaylist': True,
    'source_address': '0.0.0.0',
    'cookiefile': 'cookies.txt' #cookies here
}

ffmpeg_options = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
    'options': '-vn'
}

queues = {}   # guild_id: [(stream_url, title, watch_url)]
history = {}  # guild_id: [(stream_url, title, watch_url)]

class MusicControls(View):
    def __init__(self, vc, guild_id):
        super().__init__(timeout=None)
        self.vc = vc
        self.guild_id = guild_id
        self.loop_one = False
        self.loop_all = False
        self.update_styles()

    def update_styles(self):
        for child in self.children:
            if child.label == "🔁 Loop":
                child.style = discord.ButtonStyle.blurple if self.loop_one else discord.ButtonStyle.gray
            elif child.label == "📃 Playlist Loop":
                child.style = discord.ButtonStyle.blurple if self.loop_all else discord.ButtonStyle.gray

    def play_next(self):
        q = queues.get(self.guild_id, [])
        if not q:
            return

        stream_url, title, watch_url = q[0]
        history.setdefault(self.guild_id, []).append((stream_url, title, watch_url))

        def after_playing(error):
            if error:
                print(f"[Playback Error] {error}")

            if self.loop_one:
                self.vc.play(discord.FFmpegPCMAudio(executable=ffmpeg_path, source=stream_url, **ffmpeg_options), after=after_playing)
            elif self.loop_all:
                queues[self.guild_id].append(queues[self.guild_id].pop(0))
                self.play_next()
            else:
                queues[self.guild_id].pop(0)
                if queues[self.guild_id]:
                    self.play_next()

        self.vc.play(discord.FFmpegPCMAudio(executable=ffmpeg_path, source=stream_url, **ffmpeg_options), after=after_playing)

    @discord.ui.button(label="⏮ Prev", style=discord.ButtonStyle.gray, row=0)
    async def prev_button(self, interaction: discord.Interaction, button: Button):
        prev = history.get(self.guild_id, [])
        if prev:
            last = prev.pop()
            queues.setdefault(self.guild_id, []).insert(0, last)
            self.vc.stop()
            await interaction.response.send_message(f"⏮ Playing previous: **{last[1]}**", ephemeral=True)
        else:
            await interaction.response.send_message("❌ No previous track", ephemeral=True)

    @discord.ui.button(label="⏯ Pause", style=discord.ButtonStyle.gray, row=0)
    async def pause_button(self, interaction: discord.Interaction, button: Button):
        if self.vc.is_playing():
            self.vc.pause()
            await interaction.response.send_message("⏸ Paused", ephemeral=True)
        else:
            self.vc.resume()
            await interaction.response.send_message("▶️ Resumed", ephemeral=True)

    @discord.ui.button(label="⏭ Skip", style=discord.ButtonStyle.gray, row=0)
    async def skip_button(self, interaction: discord.Interaction, button: Button):
        if self.vc.is_playing():
            self.vc.stop()
            await interaction.response.send_message("⏭ Skipped", ephemeral=True)
        else:
            await interaction.response.send_message("⚠️ Nothing is playing", ephemeral=True)

    @discord.ui.button(label="🔁 Loop", style=discord.ButtonStyle.gray, row=1)
    async def loop_one_button(self, interaction: discord.Interaction, button: Button):
        self.loop_one = not self.loop_one
        self.update_styles()
        await interaction.response.edit_message(view=self)

    @discord.ui.button(label="📃 Playlist Loop", style=discord.ButtonStyle.gray, row=1)
    async def loop_all_button(self, interaction: discord.Interaction, button: Button):
        self.loop_all = not self.loop_all
        self.update_styles()
        await interaction.response.edit_message(view=self)

    @discord.ui.button(label="📄 Show Queue", style=discord.ButtonStyle.gray, row=1)
    async def show_queue(self, interaction: discord.Interaction, button: Button):
        q = queues.get(self.guild_id, [])
        h = history.get(self.guild_id, [])
        embed = discord.Embed(title="🎶 Playlist", color=discord.Color.purple())

        if self.vc.is_playing() and h:
            embed.add_field(name="▶️ Now Playing", value=h[-1][1], inline=False)

        if q:
            desc = ""
            for i, (_, title, _) in enumerate(q[:10], start=1):
                desc += f"{i}. {title}\n"
            embed.add_field(name="📝 Up Next", value=desc, inline=False)
        else:
            embed.description = "Queue is empty."

        await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")

@bot.event
async def on_message(message):
    if message.author.bot:
        return

    content = message.content.lower()
    guild_id = message.guild.id

    if "aura join" in content:
        if message.author.voice:
            await message.author.voice.channel.connect()
            await message.channel.send("🎧 Joined VC.")
        else:
            await message.channel.send("❌ You're not in a voice channel.")

    elif "aura leave" in content:
        if message.guild.voice_client:
            await message.guild.voice_client.disconnect()
            await message.channel.send("👋 Left VC.")
        else:
            await message.channel.send("❌ Not connected to VC.")

    elif content.startswith("aura play"):
        query = message.content[len("aura play"):].strip()
        if not query:
            await message.channel.send("❓ Provide a YouTube link or search.")
            return

        # ✅ Send "loading" message ASAP for responsiveness
        loading = await message.channel.send("⏳ Loading...")

        vc = message.guild.voice_client
        if not vc:
            if message.author.voice:
                vc = await message.author.voice.channel.connect()
            else:
                await loading.edit(content="❌ You're not in a voice channel.")
                return

        try:
            with yt_dlp.YoutubeDL(ytdl_format_options) as ydl:
                info = ydl.extract_info(query, download=False)
                if "entries" in info:
                    info = info["entries"][0]
                stream_url = info["url"]
                watch_url = info.get("webpage_url", f"https://www.youtube.com/watch?v={info.get('id')}")
                title = info.get("title", "Unknown Title")
        except Exception as e:
            await loading.edit(content=f"❌ Could not play: `{e}`")
            return

        queues.setdefault(guild_id, []).append((stream_url, title, watch_url))

        if not vc.is_playing():
            view = MusicControls(vc, guild_id)
            view.play_next()
            embed = discord.Embed(title="Now Playing 🎶", description=title, color=discord.Color.blurple())
            await loading.edit(content=None, embed=embed, view=view)
        else:
            await loading.edit(content=f"✅ Queued: **{title}**")


bot.run(TOKEN)
