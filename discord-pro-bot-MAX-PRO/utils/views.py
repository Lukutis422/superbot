import discord
from discord import ui
from typing import Any, Dict, List

TICKET_CREATE_CUSTOM_ID = "ticket:create"
TICKET_CLOSE_CUSTOM_ID = "ticket:close"
ROLEMENU_SELECT_CUSTOM_ID = "rolemenu:select"

class TicketPanelView(ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(ui.Button(label="Create Ticket", style=discord.ButtonStyle.primary, custom_id=TICKET_CREATE_CUSTOM_ID, emoji="🎫"))

class TicketCloseView(ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(ui.Button(label="Close Ticket", style=discord.ButtonStyle.danger, custom_id=TICKET_CLOSE_CUSTOM_ID, emoji="🔒"))

class RoleMenuView(ui.View):
    def __init__(self, options: List[Dict[str, Any]]):
        super().__init__(timeout=None)
        select_options: List[discord.SelectOption] = []
        for opt in options[:25]:
            label = str(opt.get("label", "Role"))[:100]
            rid = int(opt["role_id"])
            desc = opt.get("description")
            desc = str(desc)[:100] if desc else None
            select_options.append(discord.SelectOption(label=label, description=desc, value=str(rid)))
        self.add_item(ui.Select(
            placeholder="Pasirink roles (toggle)",
            options=select_options,
            min_values=0,
            max_values=min(len(select_options), 25),
            custom_id=ROLEMENU_SELECT_CUSTOM_ID,
        ))
