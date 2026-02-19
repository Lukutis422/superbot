import discord
from discord import app_commands

async def safe_respond(interaction: discord.Interaction, *, content: str, ephemeral: bool = True) -> None:
    try:
        if interaction.response.is_done():
            await interaction.followup.send(content, ephemeral=ephemeral)
        else:
            await interaction.response.send_message(content, ephemeral=ephemeral)
    except Exception:
        pass

async def friendly_app_command_error(bot, interaction: discord.Interaction, error: app_commands.AppCommandError) -> None:
    original = getattr(error, "original", error)

    if isinstance(error, app_commands.CheckFailure):
        await safe_respond(interaction, content="⛔ Neturi teisių naudoti šią komandą.")
        return

    if isinstance(original, app_commands.CommandOnCooldown):
        await safe_respond(interaction, content=f"⏳ Cooldown. Bandyk po **{original.retry_after:.1f}s**.")
        return

    if isinstance(original, discord.Forbidden):
        bot.log.warning("Forbidden action in guild=%s", getattr(interaction.guild, "id", None))
        await safe_respond(interaction, content="⛔ Neturiu pakankamai teisių atlikti šį veiksmą. Patikrink bot permissions/role hierarchy.")
        return

    if isinstance(original, (app_commands.TransformerError, ValueError)):
        await safe_respond(interaction, content="⚠️ Neteisingi parametrai. Patikrink įvestį.")
        return

    bot.log.exception("Unhandled app command error: %s", original)
    await safe_respond(interaction, content="⚠️ Įvyko klaida. Developer’is turi logus.")
