import asyncio
import discord
from discord import app_commands
from discord.ext import commands
from utils.checks import require_guild, is_admin_or_manage_guild, is_staff_or_mod
from utils.time import utc_now_ts
from utils.views import TicketPanelView, TicketCloseView, TICKET_CREATE_CUSTOM_ID, TICKET_CLOSE_CUSTOM_ID

async def send_ticketlog(bot, guild: discord.Guild, embed: discord.Embed) -> None:
    cfg = bot.config.get_guild_config(guild.id)
    log_channel_id = (cfg.get("tickets", {}) or {}).get("log_channel_id")
    if not log_channel_id:
        return
    ch = guild.get_channel(int(log_channel_id))
    if isinstance(ch, discord.TextChannel):
        try:
            await ch.send(embed=embed)
        except discord.Forbidden:
            bot.log.warning("No permission to send ticket log in guild=%s", guild.id)

class Tickets(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="ticketpanel", description="Sukuria ticket panelę su mygtuku")
    @require_guild()
    @is_admin_or_manage_guild()
    async def ticketpanel(self, interaction: discord.Interaction):
        cfg = self.bot.config.get_guild_config(interaction.guild.id)
        tcfg = cfg.get("tickets", {}) or {}
        if not tcfg.get("enabled", True):
            await interaction.response.send_message("Tickets išjungti config’e.", ephemeral=True)
            return
        e = discord.Embed(title="Tickets", description="Paspausk **Create Ticket** ir atsidarys privatus kanalas su staff.", color=discord.Color.blurple())
        await interaction.response.send_message(embed=e, view=TicketPanelView())

    @commands.Cog.listener("on_interaction")
    async def on_interaction(self, interaction: discord.Interaction):
        if interaction.type != discord.InteractionType.component or not interaction.data:
            return
        cid = interaction.data.get("custom_id")
        if cid == TICKET_CREATE_CUSTOM_ID:
            await self._create_ticket(interaction)
        elif cid == TICKET_CLOSE_CUSTOM_ID:
            await self._close_ticket(interaction)

    async def _create_ticket(self, interaction: discord.Interaction):
        if not interaction.guild or not isinstance(interaction.user, discord.Member):
            await interaction.response.send_message("Ši funkcija veikia tik serveryje.", ephemeral=True)
            return
        cfg = self.bot.config.get_guild_config(interaction.guild.id)
        tcfg = cfg.get("tickets", {}) or {}
        if not tcfg.get("enabled", True):
            await interaction.response.send_message("Tickets išjungti.", ephemeral=True)
            return

        row = await self.bot.db.fetchone("SELECT channel_id FROM tickets WHERE guild_id=? AND user_id=? AND status='open' LIMIT 1", (interaction.guild.id, interaction.user.id))
        if row:
            ch = interaction.guild.get_channel(int(row["channel_id"]))
            if ch:
                await interaction.response.send_message(f"🎫 Tu jau turi atidarytą ticket: {ch.mention}", ephemeral=True)
                return
            await self.bot.db.execute("UPDATE tickets SET status='closed', closed_at=? WHERE guild_id=? AND user_id=? AND status='open'", (utc_now_ts(), interaction.guild.id, interaction.user.id))

        category_id = tcfg.get("category_id")
        staff_role_id = tcfg.get("staff_role_id") or (cfg.get("moderation", {}) or {}).get("staff_role_id")
        if not category_id or not staff_role_id:
            await interaction.response.send_message("⚠️ Ticket sistema nesukonfigūruota. Naudok `/setticketcategory` ir `/setstaffrole`.", ephemeral=True)
            return

        category = interaction.guild.get_channel(int(category_id))
        staff_role = interaction.guild.get_role(int(staff_role_id))
        if not isinstance(category, discord.CategoryChannel) or not staff_role:
            await interaction.response.send_message("⚠️ Neteisingas ticket category arba staff role config’e.", ephemeral=True)
            return

        overwrites = {
            interaction.guild.default_role: discord.PermissionOverwrite(view_channel=False),
            interaction.user: discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True),
            staff_role: discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True),
            interaction.guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True, manage_channels=True, read_message_history=True),  # type: ignore
        }

        name = f"ticket-{interaction.user.name}".lower().replace(" ", "-")[:90]
        ticket_ch = await interaction.guild.create_text_channel(name=name, category=category, overwrites=overwrites, reason="Ticket created")

        await self.bot.db.execute("INSERT INTO tickets (guild_id, user_id, channel_id, status, created_at) VALUES (?, ?, ?, 'open', ?)", (interaction.guild.id, interaction.user.id, ticket_ch.id, utc_now_ts()))

        e = discord.Embed(title="Ticket atidarytas 🎫", description=f"{interaction.user.mention}, aprašyk problemą / klausimą.\nStaff: {staff_role.mention}", color=discord.Color.green())
        await ticket_ch.send(embed=e, view=TicketCloseView())

        await interaction.response.send_message(f"✅ Sukūriau ticket: {ticket_ch.mention}", ephemeral=True)

        log = discord.Embed(title="Ticket Created", color=discord.Color.blurple(), timestamp=discord.utils.utcnow())
        log.add_field(name="User", value=f"{interaction.user} ({interaction.user.id})", inline=False)
        log.add_field(name="Channel", value=ticket_ch.mention, inline=False)
        await send_ticketlog(self.bot, interaction.guild, log)

    async def _close_ticket(self, interaction: discord.Interaction):
        if not interaction.guild or not isinstance(interaction.user, discord.Member):
            await interaction.response.send_message("Ši funkcija veikia tik serveryje.", ephemeral=True)
            return
        if not isinstance(interaction.channel, discord.TextChannel):
            await interaction.response.send_message("Netinkamas kanalas.", ephemeral=True)
            return

        row = await self.bot.db.fetchone("SELECT user_id, status FROM tickets WHERE guild_id=? AND channel_id=? LIMIT 1", (interaction.guild.id, interaction.channel.id))
        if not row:
            await interaction.response.send_message("⚠️ Šis kanalas nėra ticket (DB įrašo nėra).", ephemeral=True)
            return
        if row["status"] != "open":
            await interaction.response.send_message("ℹ️ Ticket jau uždarytas.", ephemeral=True)
            return

        owner_id = int(row["user_id"])
        is_owner = interaction.user.id == owner_id
        is_staff = await is_staff_or_mod(self.bot).predicate(interaction)
        if not (is_owner or is_staff):
            await interaction.response.send_message("⛔ Tik ticket owner arba staff gali uždaryti.", ephemeral=True)
            return

        await self.bot.db.execute("UPDATE tickets SET status='closed', closed_at=? WHERE guild_id=? AND channel_id=? AND status='open'", (utc_now_ts(), interaction.guild.id, interaction.channel.id))
        await interaction.response.send_message("🔒 Ticket uždaromas…", ephemeral=True)

        log = discord.Embed(title="Ticket Closed", color=discord.Color.red(), timestamp=discord.utils.utcnow())
        log.add_field(name="Closed by", value=f"{interaction.user} ({interaction.user.id})", inline=False)
        log.add_field(name="Channel", value=interaction.channel.mention, inline=False)
        await send_ticketlog(self.bot, interaction.guild, log)

        try:
            await interaction.channel.send("🔒 Ticket uždarytas. Kanalas bus ištrintas po 10s.")
        except Exception:
            pass
        await asyncio.sleep(10)
        try:
            await interaction.channel.delete(reason="Ticket closed")
        except discord.Forbidden:
            await send_ticketlog(self.bot, interaction.guild, discord.Embed(title="Ticket Close Failed", description="⛔ Neturiu teisių ištrinti ticket kanalo.", color=discord.Color.red()))

async def setup(bot):
    await bot.add_cog(Tickets(bot))
