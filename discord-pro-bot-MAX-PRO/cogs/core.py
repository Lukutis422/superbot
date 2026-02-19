import discord
from discord import app_commands
from discord.ext import commands
from utils.checks import require_guild
from utils.time import human_timedelta

class Core(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="ping", description="Parodo boto latency")
    async def ping(self, interaction: discord.Interaction):
        await interaction.response.send_message(f"🏓 Pong! **{int(self.bot.latency * 1000)}ms**", ephemeral=True)

    @app_commands.command(name="help", description="Pagalba (kategorijos)")
    async def help_cmd(self, interaction: discord.Interaction):
        e = discord.Embed(title="Pagalba", color=discord.Color.blurple())
        e.description = "Slash komandos (/) – kategorijos:"
        e.add_field(name="🧩 Core", value="`/ping` `/help` `/say` `/avatar` `/userinfo` `/serverinfo` `/uptime`", inline=False)
        e.add_field(name="🛡️ Moderacija", value="`/clear` `/kick` `/ban` `/unban` `/timeout` `/warn` `/warnings` `/unwarn`", inline=False)
        e.add_field(name="👋 Welcome", value="`/setwelcome` `/setautorole`", inline=False)
        e.add_field(name="🎫 Tickets", value="`/ticketpanel`", inline=False)
        e.add_field(name="⭐ XP", value="`/rank` `/leaderboard`", inline=False)
        e.add_field(name="🎭 Role Menu", value="`/rolemenu`", inline=False)
        e.add_field(name="⚙️ Setup/Admin", value="`/setlogchannel` `/setstaffrole` `/setticketcategory` `/config show` `/config set`", inline=False)
        await interaction.response.send_message(embed=e, ephemeral=True)

    @app_commands.command(name="say", description="Botas pakartoja tekstą (apsauga nuo @everyone/@here)")
    @app_commands.describe(text="Tekstas")
    async def say(self, interaction: discord.Interaction, text: str):
        safe = text.replace("@everyone", "@\u200beveryone").replace("@here", "@\u200bhere")
        await interaction.response.send_message("✅ Išsiųsta.", ephemeral=True)
        if interaction.channel:
            await interaction.channel.send(safe)

    @app_commands.command(name="avatar", description="Parodo vartotojo avatarą")
    @app_commands.describe(user="Vartotojas (optional)")
    async def avatar(self, interaction: discord.Interaction, user: discord.User | None = None):
        u = user or interaction.user
        e = discord.Embed(title=f"{u} avatar", color=discord.Color.blurple())
        e.set_image(url=u.display_avatar.url)
        await interaction.response.send_message(embed=e, ephemeral=True)

    @app_commands.command(name="userinfo", description="Info apie vartotoją")
    @app_commands.describe(user="Vartotojas (optional)")
    @require_guild()
    async def userinfo(self, interaction: discord.Interaction, user: discord.Member | None = None):
        m = user or interaction.user
        assert isinstance(m, discord.Member)
        roles = [r.mention for r in m.roles if r.name != "@everyone"]
        e = discord.Embed(title=f"User info: {m}", color=discord.Color.blurple())
        e.set_thumbnail(url=m.display_avatar.url)
        e.add_field(name="ID", value=str(m.id), inline=True)
        e.add_field(name="Bot?", value=str(m.bot), inline=True)
        e.add_field(name="Created", value=discord.utils.format_dt(m.created_at, style="F"), inline=False)
        if m.joined_at:
            e.add_field(name="Joined", value=discord.utils.format_dt(m.joined_at, style="F"), inline=False)
        e.add_field(name=f"Roles ({len(roles)})", value=" ".join(roles) if roles else "—", inline=False)
        await interaction.response.send_message(embed=e, ephemeral=True)

    @app_commands.command(name="serverinfo", description="Info apie serverį")
    @require_guild()
    async def serverinfo(self, interaction: discord.Interaction):
        g = interaction.guild
        assert g is not None
        e = discord.Embed(title=f"Server info: {g.name}", color=discord.Color.blurple())
        if g.icon:
            e.set_thumbnail(url=g.icon.url)
        e.add_field(name="ID", value=str(g.id), inline=True)
        e.add_field(name="Owner", value=f"<@{g.owner_id}>", inline=True)
        e.add_field(name="Members", value=str(g.member_count or "—"), inline=True)
        e.add_field(name="Created", value=discord.utils.format_dt(g.created_at, style="F"), inline=False)
        e.add_field(name="Channels", value=str(len(g.channels)), inline=True)
        e.add_field(name="Roles", value=str(len(g.roles)), inline=True)
        await interaction.response.send_message(embed=e, ephemeral=True)

    @app_commands.command(name="uptime", description="Parodo kiek laiko botas veikia")
    async def uptime(self, interaction: discord.Interaction):
        delta = int((discord.utils.utcnow() - self.bot.started_at).total_seconds())
        await interaction.response.send_message(f"⏱️ Uptime: **{human_timedelta(delta)}**", ephemeral=True)

async def setup(bot):
    await bot.add_cog(Core(bot))
