import discord
from discord import app_commands
from discord.ext import commands
from datetime import timedelta
from utils.checks import require_guild, is_staff_or_mod, can_moderate_target
from utils.time import utc_now_ts

async def send_modlog(bot, guild: discord.Guild, embed: discord.Embed) -> None:
    cfg = bot.config.get_guild_config(guild.id)
    log_channel_id = (cfg.get("moderation", {}) or {}).get("log_channel_id")
    if not log_channel_id:
        return
    ch = guild.get_channel(int(log_channel_id))
    if isinstance(ch, discord.TextChannel):
        try:
            await ch.send(embed=embed)
        except discord.Forbidden:
            bot.log.warning("No permission to send modlog in guild=%s", guild.id)

class Moderation(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="clear", description="Ištrina žinutes")
    @app_commands.describe(amount="Kiek žinučių trinti (1-100)")
    @require_guild()
    async def clear(self, interaction: discord.Interaction, amount: app_commands.Range[int, 1, 100]):
        if not await is_staff_or_mod(self.bot).predicate(interaction):
            raise app_commands.CheckFailure()
        if not isinstance(interaction.user, discord.Member) or not interaction.user.guild_permissions.manage_messages:
            raise app_commands.CheckFailure()

        channel = interaction.channel
        if not isinstance(channel, discord.TextChannel):
            await interaction.response.send_message("Ši komanda veikia tik teksto kanale.", ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True)
        deleted = await channel.purge(limit=amount)
        await interaction.followup.send(f"🧹 Ištrinta: **{len(deleted)}**", ephemeral=True)

        e = discord.Embed(title="Clear", color=discord.Color.orange(), timestamp=discord.utils.utcnow())
        e.add_field(name="Moderator", value=interaction.user.mention, inline=True)
        e.add_field(name="Channel", value=channel.mention, inline=True)
        e.add_field(name="Amount", value=str(len(deleted)), inline=True)
        await send_modlog(self.bot, interaction.guild, e)

    @app_commands.command(name="kick", description="Išmeta narį")
    @app_commands.describe(user="Vartotojas", reason="Priežastis (optional)")
    @require_guild()
    async def kick(self, interaction: discord.Interaction, user: discord.Member, reason: str | None = None):
        if not await is_staff_or_mod(self.bot).predicate(interaction):
            raise app_commands.CheckFailure()
        if not isinstance(interaction.user, discord.Member) or not interaction.user.guild_permissions.kick_members:
            raise app_commands.CheckFailure()
        bot_member = interaction.guild.me  # type: ignore
        ok, msg = can_moderate_target(interaction.user, user, bot_member)
        if not ok:
            await interaction.response.send_message(f"⛔ {msg}", ephemeral=True)
            return
        await user.kick(reason=reason or "No reason provided")
        await interaction.response.send_message(f"✅ {user} išmestas.", ephemeral=True)
        e = discord.Embed(title="Kick", color=discord.Color.orange(), timestamp=discord.utils.utcnow())
        e.add_field(name="User", value=f"{user} ({user.id})", inline=False)
        e.add_field(name="Moderator", value=interaction.user.mention, inline=True)
        e.add_field(name="Reason", value=reason or "—", inline=False)
        await send_modlog(self.bot, interaction.guild, e)

    @app_commands.command(name="ban", description="Užbanina narį")
    @app_commands.describe(user="Vartotojas", reason="Priežastis (optional)")
    @require_guild()
    async def ban(self, interaction: discord.Interaction, user: discord.Member, reason: str | None = None):
        if not await is_staff_or_mod(self.bot).predicate(interaction):
            raise app_commands.CheckFailure()
        if not isinstance(interaction.user, discord.Member) or not interaction.user.guild_permissions.ban_members:
            raise app_commands.CheckFailure()
        bot_member = interaction.guild.me  # type: ignore
        ok, msg = can_moderate_target(interaction.user, user, bot_member)
        if not ok:
            await interaction.response.send_message(f"⛔ {msg}", ephemeral=True)
            return
        await user.ban(reason=reason or "No reason provided", delete_message_days=0)
        await interaction.response.send_message(f"✅ {user} užbanintas.", ephemeral=True)
        e = discord.Embed(title="Ban", color=discord.Color.red(), timestamp=discord.utils.utcnow())
        e.add_field(name="User", value=f"{user} ({user.id})", inline=False)
        e.add_field(name="Moderator", value=interaction.user.mention, inline=True)
        e.add_field(name="Reason", value=reason or "—", inline=False)
        await send_modlog(self.bot, interaction.guild, e)

    @app_commands.command(name="unban", description="Atbanina vartotoją pagal tagą arba ID")
    @app_commands.describe(user="pvz: Name#1234 arba vartotojo ID")
    @require_guild()
    async def unban(self, interaction: discord.Interaction, user: str):
        if not await is_staff_or_mod(self.bot).predicate(interaction):
            raise app_commands.CheckFailure()
        if not isinstance(interaction.user, discord.Member) or not interaction.user.guild_permissions.ban_members:
            raise app_commands.CheckFailure()
        guild = interaction.guild
        assert guild is not None
        target = None
        async for entry in guild.bans(limit=2000):
            u = entry.user
            if str(u.id) == user or str(u) == user or f"{u.name}#{u.discriminator}" == user:
                target = u
                break
        if not target:
            await interaction.response.send_message("⚠️ Neradau užbaninto vartotojo su tuo ID/tagu.", ephemeral=True)
            return
        await guild.unban(target, reason=f"Unbanned by {interaction.user}")
        await interaction.response.send_message(f"✅ Atbanintas: **{target}**", ephemeral=True)
        e = discord.Embed(title="Unban", color=discord.Color.green(), timestamp=discord.utils.utcnow())
        e.add_field(name="User", value=f"{target} ({target.id})", inline=False)
        e.add_field(name="Moderator", value=interaction.user.mention, inline=True)
        await send_modlog(self.bot, guild, e)

    @app_commands.command(name="timeout", description="Timeout (mute) nariui minutėmis")
    @app_commands.describe(user="Vartotojas", minutes="Minutės (1-10080)", reason="Priežastis (optional)")
    @require_guild()
    async def timeout(self, interaction: discord.Interaction, user: discord.Member, minutes: app_commands.Range[int, 1, 10080], reason: str | None = None):
        if not await is_staff_or_mod(self.bot).predicate(interaction):
            raise app_commands.CheckFailure()
        if not isinstance(interaction.user, discord.Member) or not interaction.user.guild_permissions.moderate_members:
            raise app_commands.CheckFailure()
        bot_member = interaction.guild.me  # type: ignore
        ok, msg = can_moderate_target(interaction.user, user, bot_member)
        if not ok:
            await interaction.response.send_message(f"⛔ {msg}", ephemeral=True)
            return
        until = discord.utils.utcnow() + timedelta(minutes=int(minutes))
        await user.timeout(until, reason=reason or "No reason provided")
        await interaction.response.send_message(f"✅ {user.mention} timeout **{minutes} min**.", ephemeral=True)
        e = discord.Embed(title="Timeout", color=discord.Color.orange(), timestamp=discord.utils.utcnow())
        e.add_field(name="User", value=f"{user} ({user.id})", inline=False)
        e.add_field(name="Moderator", value=interaction.user.mention, inline=True)
        e.add_field(name="Minutes", value=str(minutes), inline=True)
        e.add_field(name="Reason", value=reason or "—", inline=False)
        await send_modlog(self.bot, interaction.guild, e)

    @app_commands.command(name="warn", description="Įspėja narį (DB)")
    @app_commands.describe(user="Vartotojas", reason="Priežastis")
    @require_guild()
    async def warn(self, interaction: discord.Interaction, user: discord.Member, reason: str):
        if not await is_staff_or_mod(self.bot).predicate(interaction):
            raise app_commands.CheckFailure()
        if not isinstance(interaction.user, discord.Member) or not interaction.user.guild_permissions.manage_messages:
            raise app_commands.CheckFailure()
        bot_member = interaction.guild.me  # type: ignore
        ok, msg = can_moderate_target(interaction.user, user, bot_member)
        if not ok:
            await interaction.response.send_message(f"⛔ {msg}", ephemeral=True)
            return
        await self.bot.db.execute(
            "INSERT INTO warnings (guild_id, user_id, moderator_id, reason, created_at) VALUES (?, ?, ?, ?, ?)",
            (interaction.guild.id, user.id, interaction.user.id, reason, utc_now_ts()),
        )
        await interaction.response.send_message(f"✅ Warn pridėtas: {user.mention}", ephemeral=True)
        e = discord.Embed(title="Warn", color=discord.Color.orange(), timestamp=discord.utils.utcnow())
        e.add_field(name="User", value=f"{user} ({user.id})", inline=False)
        e.add_field(name="Moderator", value=interaction.user.mention, inline=True)
        e.add_field(name="Reason", value=reason, inline=False)
        await send_modlog(self.bot, interaction.guild, e)

    @app_commands.command(name="warnings", description="Parodo warnings")
    @app_commands.describe(user="Vartotojas (optional)")
    @require_guild()
    async def warnings(self, interaction: discord.Interaction, user: discord.Member | None = None):
        if not await is_staff_or_mod(self.bot).predicate(interaction):
            raise app_commands.CheckFailure()
        target = user or interaction.user
        assert interaction.guild is not None
        rows = await self.bot.db.fetchall(
            "SELECT id, moderator_id, reason FROM warnings WHERE guild_id=? AND user_id=? ORDER BY id DESC LIMIT 20",
            (interaction.guild.id, target.id),
        )
        e = discord.Embed(title=f"Warnings: {target}", color=discord.Color.blurple())
        e.description = "— Nėra warnings." if not rows else "\n".join([f"**#{r['id']}** • mod: <@{r['moderator_id']}> • {r['reason']}" for r in rows])
        await interaction.response.send_message(embed=e, ephemeral=True)

    @app_commands.command(name="unwarn", description="Pašalina warn pagal ID")
    @app_commands.describe(warn_id="Warn ID")
    @require_guild()
    async def unwarn(self, interaction: discord.Interaction, warn_id: int):
        if not await is_staff_or_mod(self.bot).predicate(interaction):
            raise app_commands.CheckFailure()
        if not isinstance(interaction.user, discord.Member) or not interaction.user.guild_permissions.manage_messages:
            raise app_commands.CheckFailure()
        assert interaction.guild is not None
        row = await self.bot.db.fetchone("SELECT id, user_id FROM warnings WHERE guild_id=? AND id=?", (interaction.guild.id, int(warn_id)))
        if not row:
            await interaction.response.send_message("⚠️ Neradau tokio warn_id šiame serveryje.", ephemeral=True)
            return
        await self.bot.db.execute("DELETE FROM warnings WHERE guild_id=? AND id=?", (interaction.guild.id, int(warn_id)))
        await interaction.response.send_message(f"✅ Pašalintas warn **#{warn_id}**.", ephemeral=True)
        e = discord.Embed(title="Unwarn", color=discord.Color.green(), timestamp=discord.utils.utcnow())
        e.add_field(name="Warn ID", value=str(warn_id), inline=True)
        e.add_field(name="Moderator", value=interaction.user.mention, inline=True)
        e.add_field(name="User ID", value=str(row["user_id"]), inline=True)
        await send_modlog(self.bot, interaction.guild, e)

async def setup(bot):
    await bot.add_cog(Moderation(bot))
