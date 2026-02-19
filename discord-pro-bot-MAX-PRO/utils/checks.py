import discord
from discord import app_commands

def require_guild():
    async def predicate(interaction: discord.Interaction) -> bool:
        return interaction.guild is not None
    return app_commands.check(predicate)

def is_admin_or_manage_guild():
    async def predicate(interaction: discord.Interaction) -> bool:
        if not interaction.guild or not isinstance(interaction.user, discord.Member):
            return False
        perms = interaction.user.guild_permissions
        return perms.administrator or perms.manage_guild
    return app_commands.check(predicate)

def is_staff_or_mod(bot):
    async def predicate(interaction: discord.Interaction) -> bool:
        if not interaction.guild or not isinstance(interaction.user, discord.Member):
            return False
        cfg = bot.config.get_guild_config(interaction.guild.id)
        staff_role_id = (cfg.get("moderation", {}) or {}).get("staff_role_id") or (cfg.get("tickets", {}) or {}).get("staff_role_id")
        if staff_role_id:
            role = interaction.guild.get_role(int(staff_role_id))
            if role and role in interaction.user.roles:
                return True
        perms = interaction.user.guild_permissions
        return perms.manage_messages or perms.kick_members or perms.ban_members or perms.moderate_members or perms.administrator
    return app_commands.check(predicate)

def can_moderate_target(actor: discord.Member, target: discord.Member, bot_member: discord.Member) -> tuple[bool, str]:
    if actor.id == target.id:
        return False, "Negali bausti savęs."
    if target.id == bot_member.id:
        return False, "Negali bausti boto."
    if target.bot:
        return False, "Negali bausti botų."
    if actor.guild.owner_id == target.id:
        return False, "Negali bausti serverio savininko."
    if target.top_role >= actor.top_role and actor.guild.owner_id != actor.id:
        return False, "Negali bausti nario su aukštesne arba lygiaverte role."
    if target.top_role >= bot_member.top_role:
        return False, "Boto rolė per žema (role hierarchy)."
    return True, ""
