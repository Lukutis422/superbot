import discord
from discord import app_commands
from discord.ext import commands
from utils.checks import require_guild
from utils.time import utc_now_ts

def xp_for_next_level(level: int) -> int:
    return 5 * (level ** 2) + 50 * level + 100

class XP(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener("on_message")
    async def on_message(self, message: discord.Message):
        if message.author.bot or not message.guild or not isinstance(message.author, discord.Member):
            return
        cfg = self.bot.config.get_guild_config(message.guild.id)
        xcfg = cfg.get("xp", {}) or {}
        if not xcfg.get("enabled", True):
            return
        ignored = set(int(x) for x in (xcfg.get("ignored_channel_ids") or []))
        if message.channel.id in ignored:
            return
        cooldown = int(xcfg.get("cooldown_seconds", 45))
        gain = int(xcfg.get("xp_per_message", 15))
        now = utc_now_ts()

        row = await self.bot.db.fetchone("SELECT xp, level, last_award_at FROM xp WHERE guild_id=? AND user_id=?", (message.guild.id, message.author.id))
        if row:
            last = int(row["last_award_at"])
            if now - last < cooldown:
                return
            xp = int(row["xp"]) + gain
            level = int(row["level"])
            leveled_up = False
            while xp >= xp_for_next_level(level):
                xp -= xp_for_next_level(level)
                level += 1
                leveled_up = True
            await self.bot.db.execute("UPDATE xp SET xp=?, level=?, last_award_at=? WHERE guild_id=? AND user_id=?", (xp, level, now, message.guild.id, message.author.id))
            if leveled_up:
                await self._on_level_up(message, level)
        else:
            await self.bot.db.execute("INSERT INTO xp (guild_id, user_id, xp, level, last_award_at) VALUES (?, ?, ?, 0, ?)", (message.guild.id, message.author.id, gain, now))

    async def _on_level_up(self, message: discord.Message, new_level: int):
        cfg = self.bot.config.get_guild_config(message.guild.id)
        rewards = (cfg.get("xp", {}) or {}).get("level_rewards", {}) or {}
        role_id = rewards.get(str(new_level))
        if role_id:
            role = message.guild.get_role(int(role_id))
            if role:
                try:
                    await message.author.add_roles(role, reason=f"Level reward: {new_level}")
                except discord.Forbidden:
                    self.bot.log.warning("Level reward forbidden guild=%s role=%s", message.guild.id, role_id)
        try:
            await message.channel.send(f"⭐ {message.author.mention} pasiekė **Level {new_level}**!")
        except discord.Forbidden:
            pass

    @app_commands.command(name="rank", description="Parodo level + XP progresą")
    @app_commands.describe(user="Vartotojas (optional)")
    @require_guild()
    async def rank(self, interaction: discord.Interaction, user: discord.Member | None = None):
        member = user or interaction.user
        assert interaction.guild is not None
        row = await self.bot.db.fetchone("SELECT xp, level FROM xp WHERE guild_id=? AND user_id=?", (interaction.guild.id, member.id))
        if not row:
            await interaction.response.send_message("ℹ️ Dar nėra XP duomenų šiam vartotojui.", ephemeral=True)
            return
        xp = int(row["xp"]); level = int(row["level"])
        next_needed = xp_for_next_level(level)
        progress = int((xp / next_needed) * 100) if next_needed else 0
        e = discord.Embed(title=f"Rank: {member}", color=discord.Color.blurple())
        e.set_thumbnail(url=member.display_avatar.url)
        e.add_field(name="Level", value=str(level), inline=True)
        e.add_field(name="XP", value=f"{xp} / {next_needed} ({progress}%)", inline=True)
        await interaction.response.send_message(embed=e, ephemeral=True)

    @app_commands.command(name="leaderboard", description="Top level/xp")
    @require_guild()
    async def leaderboard(self, interaction: discord.Interaction):
        assert interaction.guild is not None
        rows = await self.bot.db.fetchall("SELECT user_id, level, xp FROM xp WHERE guild_id=? ORDER BY level DESC, xp DESC LIMIT 10", (interaction.guild.id,))
        if not rows:
            await interaction.response.send_message("ℹ️ Nėra XP duomenų.", ephemeral=True)
            return
        e = discord.Embed(title="Leaderboard", color=discord.Color.gold())
        e.description = "\n".join([f"**#{i}** <@{int(r['user_id'])}> • L{int(r['level'])} • XP {int(r['xp'])}" for i, r in enumerate(rows, 1)])
        await interaction.response.send_message(embed=e, ephemeral=True)

async def setup(bot):
    await bot.add_cog(XP(bot))
