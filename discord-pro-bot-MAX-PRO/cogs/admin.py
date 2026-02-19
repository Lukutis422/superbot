import discord
from discord import app_commands
from discord.ext import commands
from utils.checks import require_guild, is_admin_or_manage_guild

class Admin(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="setlogchannel", description="Nustato moderation log kanalą")
    @require_guild()
    @is_admin_or_manage_guild()
    async def setlogchannel(self, interaction: discord.Interaction, channel: discord.TextChannel):
        self.bot.config.set_key(interaction.guild.id, "moderation.log_channel_id", str(channel.id))
        await interaction.response.send_message(f"✅ Moderation log kanalas: {channel.mention}", ephemeral=True)

    @app_commands.command(name="setstaffrole", description="Nustato staff/mod rolę")
    @require_guild()
    @is_admin_or_manage_guild()
    async def setstaffrole(self, interaction: discord.Interaction, role: discord.Role):
        self.bot.config.set_key(interaction.guild.id, "moderation.staff_role_id", str(role.id))
        self.bot.config.set_key(interaction.guild.id, "tickets.staff_role_id", str(role.id))
        await interaction.response.send_message(f"✅ Staff rolė: {role.mention}", ephemeral=True)

    @app_commands.command(name="setticketcategory", description="Nustato ticket kategoriją")
    @require_guild()
    @is_admin_or_manage_guild()
    async def setticketcategory(self, interaction: discord.Interaction, category: discord.CategoryChannel):
        self.bot.config.set_key(interaction.guild.id, "tickets.category_id", str(category.id))
        await interaction.response.send_message(f"✅ Ticket category: **{category.name}**", ephemeral=True)

    config = app_commands.Group(name="config", description="Config peržiūra/keitimas")

    @config.command(name="show", description="Parodo guild config (merged)")
    @require_guild()
    @is_admin_or_manage_guild()
    async def config_show(self, interaction: discord.Interaction):
        dumped = self.bot.config.dump_guild_yaml(interaction.guild.id)
        if len(dumped) > 1800:
            dumped = dumped[:1800] + "\n... (truncated)"
        await interaction.response.send_message(f"```yaml\n{dumped}\n```", ephemeral=True)

    @config.command(name="set", description="Nustato config reikšmę (key/value)")
    @app_commands.describe(key="pvz: moderation.log_channel_id", value="pvz: 123456... arba null")
    @require_guild()
    @is_admin_or_manage_guild()
    async def config_set(self, interaction: discord.Interaction, key: str, value: str):
        try:
            self.bot.config.set_key(interaction.guild.id, key, value)
        except ValueError as e:
            await interaction.response.send_message(f"⚠️ {e}", ephemeral=True)
            return
        await interaction.response.send_message(f"✅ Atnaujinta: `{key}` = `{value}`", ephemeral=True)

async def setup(bot):
    await bot.add_cog(Admin(bot))
