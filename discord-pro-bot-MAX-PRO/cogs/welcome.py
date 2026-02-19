import discord
from discord import app_commands
from discord.ext import commands
from utils.checks import require_guild, is_admin_or_manage_guild

class Welcome(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="setwelcome", description="Nustato welcome kanalą")
    @app_commands.describe(channel="Kanalas")
    @require_guild()
    @is_admin_or_manage_guild()
    async def setwelcome(self, interaction: discord.Interaction, channel: discord.TextChannel):
        self.bot.config.set_key(interaction.guild.id, "welcome.welcome_channel_id", str(channel.id))
        await interaction.response.send_message(f"✅ Welcome kanalas: {channel.mention}", ephemeral=True)

    @app_commands.command(name="setautorole", description="Nustato autorole naujiems nariams")
    @app_commands.describe(role="Rolė")
    @require_guild()
    @is_admin_or_manage_guild()
    async def setautorole(self, interaction: discord.Interaction, role: discord.Role):
        self.bot.config.set_key(interaction.guild.id, "welcome.autorole_id", str(role.id))
        await interaction.response.send_message(f"✅ AutoRole: {role.mention}", ephemeral=True)

    @commands.Cog.listener("on_member_join")
    async def on_member_join(self, member: discord.Member):
        cfg = self.bot.config.get_guild_config(member.guild.id)
        wcfg = cfg.get("welcome", {}) or {}
        autorole_id = wcfg.get("autorole_id")
        if autorole_id:
            role = member.guild.get_role(int(autorole_id))
            if role:
                try:
                    await member.add_roles(role, reason="AutoRole on join")
                except discord.Forbidden:
                    self.bot.log.warning("AutoRole forbidden guild=%s role=%s", member.guild.id, autorole_id)
        welcome_channel_id = wcfg.get("welcome_channel_id")
        if welcome_channel_id:
            ch = member.guild.get_channel(int(welcome_channel_id))
            if isinstance(ch, discord.TextChannel):
                e = discord.Embed(title="Sveikas atvykęs! 👋", description=f"{member.mention} prisijungė prie **{member.guild.name}**.", color=discord.Color.green())
                e.set_thumbnail(url=member.display_avatar.url)
                try:
                    await ch.send(embed=e)
                except discord.Forbidden:
                    self.bot.log.warning("Welcome send forbidden guild=%s", member.guild.id)

    @commands.Cog.listener("on_member_remove")
    async def on_member_remove(self, member: discord.Member):
        cfg = self.bot.config.get_guild_config(member.guild.id)
        goodbye_channel_id = (cfg.get("welcome", {}) or {}).get("goodbye_channel_id")
        if not goodbye_channel_id:
            return
        ch = member.guild.get_channel(int(goodbye_channel_id))
        if isinstance(ch, discord.TextChannel):
            e = discord.Embed(title="Iki! 👋", description=f"**{member}** paliko serverį.", color=discord.Color.orange())
            try:
                await ch.send(embed=e)
            except discord.Forbidden:
                self.bot.log.warning("Goodbye send forbidden guild=%s", member.guild.id)

async def setup(bot):
    await bot.add_cog(Welcome(bot))
