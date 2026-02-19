import discord
from discord import app_commands
from discord.ext import commands
from utils.checks import require_guild, is_admin_or_manage_guild
from utils.views import RoleMenuView, ROLEMENU_SELECT_CUSTOM_ID

class Roles(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="rolemenu", description="Sukuria role menu (Select dropdown) iš config")
    @require_guild()
    @is_admin_or_manage_guild()
    async def rolemenu(self, interaction: discord.Interaction):
        cfg = self.bot.config.get_guild_config(interaction.guild.id)
        options = (cfg.get("role_menu", {}) or {}).get("options", []) or []
        if not options:
            await interaction.response.send_message("⚠️ `role_menu.options` tuščias config’e.", ephemeral=True)
            return
        e = discord.Embed(title="Role Menu", description="Pasirink roles iš dropdown. Pasirinkimas yra **toggle**.", color=discord.Color.blurple())
        await interaction.response.send_message(embed=e, view=RoleMenuView(options))

    @commands.Cog.listener("on_interaction")
    async def on_interaction(self, interaction: discord.Interaction):
        if interaction.type != discord.InteractionType.component or not interaction.data:
            return
        if interaction.data.get("custom_id") != ROLEMENU_SELECT_CUSTOM_ID:
            return
        await self._handle_select(interaction)

    async def _handle_select(self, interaction: discord.Interaction):
        if not interaction.guild or not isinstance(interaction.user, discord.Member):
            await interaction.response.send_message("Ši funkcija veikia tik serveryje.", ephemeral=True)
            return
        values = interaction.data.get("values", [])
        selected = set(int(v) for v in values)
        cfg = self.bot.config.get_guild_config(interaction.guild.id)
        options = (cfg.get("role_menu", {}) or {}).get("options", []) or []
        allowed = set(int(o["role_id"]) for o in options if "role_id" in o)
        to_toggle = selected & allowed
        added, removed = [], []
        for rid in to_toggle:
            role = interaction.guild.get_role(rid)
            if not role:
                continue
            (removed if role in interaction.user.roles else added).append(role)
        try:
            if added:
                await interaction.user.add_roles(*added, reason="Role menu selection")
            if removed:
                await interaction.user.remove_roles(*removed, reason="Role menu selection")
        except discord.Forbidden:
            await interaction.response.send_message("⛔ Neturiu teisių pridėti/nuimti rolės (hierarchy).", ephemeral=True)
            return
        msg = "✅ Atnaujinta: "
        if added:
            msg += "pridėta " + ", ".join(r.mention for r in added) + ". "
        if removed:
            msg += "nuimta " + ", ".join(r.mention for r in removed) + ". "
        if not added and not removed:
            msg = "ℹ️ Nieko nepakeičiau."
        await interaction.response.send_message(msg.strip(), ephemeral=True)

async def setup(bot):
    await bot.add_cog(Roles(bot))
