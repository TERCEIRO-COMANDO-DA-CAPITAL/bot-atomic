#!/usr/bin/env python3
"""
Atomic Bot V2 - Sistema profissional de spam, DM HTML, servidores em comum, perfil, status.
Todos os comandos utilizam ID numérico. Painel de controle interativo via Select Menu.
"""

import discord
from discord import app_commands
from discord.ui import Select, View
import json
import asyncio
import io
from pathlib import Path
from typing import Set, Optional

# ======================== CONFIGURAÇÃO DE ARQUIVOS LOCAIS ========================
CONFIG_FILE = Path("config.json")
AUTHORIZED_FILE = Path("dados/autorizados.txt")
OWNERS_FILE = Path("dados/donos.txt")

AUTHORIZED_FILE.parent.mkdir(parents=True, exist_ok=True)

def load_token() -> Optional[str]:
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE, "r") as f:
            data = json.load(f)
            return data.get("token")
    return None

def load_owners() -> Set[int]:
    if OWNERS_FILE.exists():
        with open(OWNERS_FILE, "r") as f:
            return {int(line.strip()) for line in f if line.strip()}
    return set()

def load_authorized() -> Set[str]:
    if AUTHORIZED_FILE.exists():
        with open(AUTHORIZED_FILE, "r") as f:
            return {line.strip() for line in f if line.strip()}
    return set()

def save_authorized(auth_set: Set[str]):
    with open(AUTHORIZED_FILE, "w") as f:
        f.write("\n".join(auth_set))

TOKEN = load_token()
OWNER_IDS = load_owners()
authorized_users = load_authorized()

def is_authorized(user_id: int) -> bool:
    return user_id in OWNER_IDS or str(user_id) in authorized_users

if not TOKEN:
    print("Erro: config.json não encontrado. Execute o setup primeiro.")
    exit(1)

# ======================== CLASSE DO PAINEL V2 ========================
class PainelView(View):
    def __init__(self, bot, interaction_user):
        super().__init__(timeout=120)
        self.bot = bot
        self.interaction_user = interaction_user

    @discord.ui.select(
        placeholder="Selecione uma opção do painel",
        options=[
            discord.SelectOption(label="Enviar Spam", description="Envia mensagens em massa para um ID", emoji="📨"),
            discord.SelectOption(label="Exportar DM HTML", description="Gera HTML da conversa com usuário", emoji="📄"),
            discord.SelectOption(label="Servidores em Comum", description="Lista servidores que compartilha com o ID", emoji="🌐"),
            discord.SelectOption(label="Perfil do Usuário", description="Mostra avatar, banner, bio", emoji="👤"),
            discord.SelectOption(label="Status do Usuário", description="Verifica se está online/offline", emoji="🟢"),
            discord.SelectOption(label="Gerenciar Autorizados", description="Adicionar ou remover usuários", emoji="⚙️")
        ]
    )
    async def menu_callback(self, interaction: discord.Interaction, select: Select):
        if interaction.user.id != self.interaction_user.id:
            embed = discord.Embed(title="Acesso Negado", description="Apenas quem abriu o painel pode usar.", color=0xff0000)
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        if select.values[0] == "Enviar Spam":
            await interaction.response.send_modal(SpamModal(self.bot, interaction.user))
        elif select.values[0] == "Exportar DM HTML":
            await interaction.response.send_modal(DMHtmlModal(self.bot, interaction.user))
        elif select.values[0] == "Servidores em Comum":
            await interaction.response.send_modal(ServersModal(self.bot, interaction.user))
        elif select.values[0] == "Perfil do Usuário":
            await interaction.response.send_modal(PerfilModal(self.bot, interaction.user))
        elif select.values[0] == "Status do Usuário":
            await interaction.response.send_modal(StatusModal(self.bot, interaction.user))
        elif select.values[0] == "Gerenciar Autorizados":
            if not is_authorized(interaction.user.id):
                embed = discord.Embed(title="Permissão Negada", description="Apenas donos ou autorizados podem gerenciar.", color=0xff0000)
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return
            await interaction.response.send_modal(AdminModal(self.bot, interaction.user))

# ======================== MODAIS PARA ENTRADA DE ID ========================
class SpamModal(discord.ui.Modal, title="Enviar Spam"):
    user_id = discord.ui.TextInput(label="ID do Usuário", placeholder="Digite o ID numérico", required=True)
    message = discord.ui.TextInput(label="Mensagem", placeholder="Conteúdo da mensagem", style=discord.TextStyle.paragraph, required=True)
    quantity = discord.ui.TextInput(label="Quantidade", placeholder="Número de vezes (padrão 5)", required=False, default="5")

    def __init__(self, bot, author):
        super().__init__()
        self.bot = bot
        self.author = author

    async def on_submit(self, interaction: discord.Interaction):
        if not is_authorized(self.author.id):
            embed = discord.Embed(title="Permissão Negada", color=0xff0000)
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        try:
            user = await self.bot.fetch_user(int(self.user_id.value))
        except:
            embed = discord.Embed(title="Erro", description="ID de usuário inválido.", color=0xff0000)
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        qtd = int(self.quantity.value) if self.quantity.value.isdigit() else 5
        if qtd < 1:
            embed = discord.Embed(title="Erro", description="Quantidade deve ser maior que zero.", color=0xff0000)
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        embed = discord.Embed(title="Spam Iniciado", description=f"Enviando {qtd} mensagens para {user.name} (ID: {user.id})", color=0x3498db)
        await interaction.response.send_message(embed=embed, ephemeral=True)

        try:
            dm = await user.create_dm()
            for i in range(qtd):
                await dm.send(f"{self.message.value} (mensagem {i+1}/{qtd})")
                await asyncio.sleep(0.5)
            embed_success = discord.Embed(title="Spam Concluído", description=f"{qtd} mensagens enviadas para {user.name}.", color=0x00ff00)
        except discord.Forbidden:
            embed_success = discord.Embed(title="Erro", description=f"Não foi possível enviar DM para {user.name}.", color=0xff0000)
        except Exception as e:
            embed_success = discord.Embed(title="Erro", description=str(e), color=0xff0000)

        await interaction.followup.send(embed=embed_success, ephemeral=True)

class DMHtmlModal(discord.ui.Modal, title="Exportar DM HTML"):
    user_id = discord.ui.TextInput(label="ID do Usuário", placeholder="Digite o ID numérico", required=True)

    def __init__(self, bot, author):
        super().__init__()
        self.bot = bot
        self.author = author

    async def on_submit(self, interaction: discord.Interaction):
        if not is_authorized(self.author.id):
            embed = discord.Embed(title="Permissão Negada", color=0xff0000)
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        try:
            user = await self.bot.fetch_user(int(self.user_id.value))
        except:
            embed = discord.Embed(title="Erro", description="ID de usuário inválido.", color=0xff0000)
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True)

        try:
            dm_channel = await user.create_dm()
            messages = []
            async for msg in dm_channel.history(limit=200):
                messages.append(msg)

            if not messages:
                embed = discord.Embed(title="Nenhuma Mensagem", description=f"Não há mensagens com {user.name}.", color=0xffaa00)
                await interaction.followup.send(embed=embed, ephemeral=True)
                return

            html = f"""<!DOCTYPE html>
<html><head><meta charset="UTF-8"><title>Conversa com {user.name}</title>
<style>
body {{ font-family: Arial; background: #36393f; color: #fff; padding: 20px; }}
.msg {{ margin-bottom: 15px; padding: 10px; border-radius: 10px; }}
.bot {{ background: #5865f2; }}
.user {{ background: #40444b; }}
.date {{ font-size: 0.7em; color: #b9bbbe; }}
</style></head>
<body><h2>Conversa com {user.name} (ID: {user.id})</h2>"""
            for msg in reversed(messages):
                role = "bot" if msg.author.bot else "user"
                html += f'<div class="msg {role}"><strong>{msg.author.name}:</strong> {msg.content}<br><span class="date">{msg.created_at.strftime("%d/%m/%Y %H:%M:%S")}</span></div>'
            html += "</body></html>"

            file = discord.File(io.BytesIO(html.encode()), filename=f"dm_{user.name}.html")
            embed_success = discord.Embed(title="Arquivo Gerado", description=f"Conversa com {user.name} exportada.", color=0x00ff00)
            await interaction.followup.send(embed=embed_success, file=file, ephemeral=True)
        except Exception as e:
            await interaction.followup.send(embed=discord.Embed(title="Erro", description=str(e), color=0xff0000), ephemeral=True)

class ServersModal(discord.ui.Modal, title="Servidores em Comum"):
    user_id = discord.ui.TextInput(label="ID do Usuário", placeholder="Digite o ID numérico", required=True)

    def __init__(self, bot, author):
        super().__init__()
        self.bot = bot
        self.author = author

    async def on_submit(self, interaction: discord.Interaction):
        if not is_authorized(self.author.id):
            embed = discord.Embed(title="Permissão Negada", color=0xff0000)
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        try:
            user = await self.bot.fetch_user(int(self.user_id.value))
        except:
            embed = discord.Embed(title="Erro", description="ID inválido.", color=0xff0000)
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        mutual = [g for g in self.bot.guilds if g.get_member(user.id)]
        if not mutual:
            embed = discord.Embed(title="Servidores em Comum", description=f"Nenhum servidor compartilhado com {user.name}.", color=0xffaa00)
        else:
            desc = "\n".join([f"- {g.name} (ID: {g.id})" for g in mutual[:25]])
            embed = discord.Embed(title=f"Servidores com {user.name}", description=desc, color=0x3498db)
            if len(mutual) > 25:
                embed.set_footer(text=f"Exibindo 25 de {len(mutual)}")
        await interaction.response.send_message(embed=embed, ephemeral=True)

class PerfilModal(discord.ui.Modal, title="Perfil do Usuário"):
    user_id = discord.ui.TextInput(label="ID do Usuário", placeholder="Digite o ID numérico", required=True)

    def __init__(self, bot, author):
        super().__init__()
        self.bot = bot
        self.author = author

    async def on_submit(self, interaction: discord.Interaction):
        if not is_authorized(self.author.id):
            embed = discord.Embed(title="Permissão Negada", color=0xff0000)
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        try:
            user = await self.bot.fetch_user(int(self.user_id.value))
        except:
            embed = discord.Embed(title="Erro", description="ID inválido.", color=0xff0000)
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        avatar = user.display_avatar.url
        banner = user.banner.url if user.banner else None
        bio = getattr(user, 'bio', None) or "Não disponível"

        embed = discord.Embed(title=f"Perfil de {user.name}", color=0x9b59b6)
        embed.set_thumbnail(url=avatar)
        if banner:
            embed.set_image(url=banner)
        embed.add_field(name="Nome", value=f"{user.name}#{user.discriminator if user.discriminator != '0' else ''}", inline=True)
        embed.add_field(name="ID", value=str(user.id), inline=True)
        embed.add_field(name="Biografia", value=bio[:500], inline=False)
        embed.set_footer(text=f"Criado em {user.created_at.strftime('%d/%m/%Y')}")
        await interaction.response.send_message(embed=embed, ephemeral=True)

class StatusModal(discord.ui.Modal, title="Status do Usuário"):
    user_id = discord.ui.TextInput(label="ID do Usuário", placeholder="Digite o ID numérico", required=True)

    def __init__(self, bot, author):
        super().__init__()
        self.bot = bot
        self.author = author

    async def on_submit(self, interaction: discord.Interaction):
        if not is_authorized(self.author.id):
            embed = discord.Embed(title="Permissão Negada", color=0xff0000)
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        try:
            user = await self.bot.fetch_user(int(self.user_id.value))
        except:
            embed = discord.Embed(title="Erro", description="ID inválido.", color=0xff0000)
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        member = None
        for g in self.bot.guilds:
            m = g.get_member(user.id)
            if m:
                member = m
                break

        if member:
            status_map = {discord.Status.online: "Online", discord.Status.idle: "Ausente", discord.Status.dnd: "Não Perturbe", discord.Status.offline: "Offline"}
            status = status_map.get(member.status, "Desconhecido")
            color = 0x2ecc71 if member.status == discord.Status.online else 0x95a5a6
            embed = discord.Embed(title=f"Status de {user.name}", description=f"**{status}**", color=color)
            if member.activity:
                embed.add_field(name="Atividade", value=member.activity.name)
        else:
            embed = discord.Embed(title="Status Indisponível", description=f"Sem servidor em comum com {user.name}.", color=0xffaa00)
        await interaction.response.send_message(embed=embed, ephemeral=True)

class AdminModal(discord.ui.Modal, title="Gerenciar Autorizados"):
    acao = discord.ui.TextInput(label="Ação", placeholder="add ou remove", required=True)
    user_id = discord.ui.TextInput(label="ID do Usuário", placeholder="ID numérico", required=True)

    def __init__(self, bot, author):
        super().__init__()
        self.bot = bot
        self.author = author

    async def on_submit(self, interaction: discord.Interaction):
        if not is_authorized(self.author.id):
            embed = discord.Embed(title="Permissão Negada", color=0xff0000)
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        acao = self.acao.value.lower().strip()
        uid = self.user_id.value.strip()

        try:
            user = await self.bot.fetch_user(int(uid))
        except:
            embed = discord.Embed(title="Erro", description="ID inválido.", color=0xff0000)
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        if acao == "add":
            authorized_users.add(str(user.id))
            save_authorized(authorized_users)
            embed = discord.Embed(title="Usuário Autorizado", description=f"{user.name} (ID: {user.id}) pode usar os comandos.", color=0x00ff00)
        elif acao == "remove":
            if str(user.id) in authorized_users:
                authorized_users.remove(str(user.id))
                save_authorized(authorized_users)
                embed = discord.Embed(title="Autorização Revogada", description=f"{user.name} (ID: {user.id}) não tem mais permissão.", color=0xffaa00)
            else:
                embed = discord.Embed(title="Nada a Remover", description=f"{user.name} não estava autorizado.", color=0xffaa00)
        else:
            embed = discord.Embed(title="Erro", description="Ação inválida. Use 'add' ou 'remove'.", color=0xff0000)

        await interaction.response.send_message(embed=embed, ephemeral=True)

# ======================== COMANDOS SLASH ========================
bot = discord.Client(intents=discord.Intents.all())
tree = app_commands.CommandTree(bot)

@bot.event
async def on_ready():
    await tree.sync()
    print(f"Bot logado como {bot.user}")
    print(f"Donos: {OWNER_IDS}")
    print(f"Autorizados: {len(authorized_users)}")

@tree.command(name="painel", description="Abre o painel de controle V2 com todas as opções")
async def painel(interaction: discord.Interaction):
    if not is_authorized(interaction.user.id):
        embed = discord.Embed(title="Permissão Negada", description="Você não está autorizado.", color=0xff0000)
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return

    embed = discord.Embed(
        title="Painel de Controle Atomic V2",
        description="Selecione uma opção no menu abaixo para executar a ação desejada.",
        color=0x2c3e50
    )
    embed.add_field(name="Spam", value="Envia mensagens em massa para um ID", inline=True)
    embed.add_field(name="DM HTML", value="Exporta conversa em arquivo HTML", inline=True)
    embed.add_field(name="Servidores", value="Lista servidores em comum", inline=True)
    embed.add_field(name="Perfil", value="Mostra avatar, banner e bio", inline=True)
    embed.add_field(name="Status", value="Verifica online/offline", inline=True)
    embed.add_field(name="Admin", value="Gerencia usuários autorizados", inline=True)
    embed.set_footer(text="Atomic Bot V2 | Desenvolvido para TCC Host")

    view = PainelView(bot, interaction.user)
    await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

# ======================== COMANDOS DIRETOS (OPCIONAIS) ========================
@tree.command(name="spam", description="Envia mensagens em massa para um ID")
@app_commands.describe(user_id="ID numérico", message="Mensagem", quantity="Quantidade")
async def spam_direct(interaction: discord.Interaction, user_id: str, message: str, quantity: int = 5):
    if not is_authorized(interaction.user.id):
        embed = discord.Embed(title="Permissão Negada", color=0xff0000)
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return

    try:
        user = await bot.fetch_user(int(user_id))
    except:
        embed = discord.Embed(title="Erro", description="ID inválido.", color=0xff0000)
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return

    if quantity < 1:
        embed = discord.Embed(title="Erro", description="Quantidade > 0.", color=0xff0000)
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return

    embed = discord.Embed(title="Spam Iniciado", description=f"Enviando {quantity} mensagens para {user.name}", color=0x3498db)
    await interaction.response.send_message(embed=embed, ephemeral=True)

    try:
        dm = await user.create_dm()
        for i in range(quantity):
            await dm.send(f"{message} ({i+1}/{quantity})")
            await asyncio.sleep(0.5)
        embed_success = discord.Embed(title="Concluído", description=f"{quantity} mensagens enviadas.", color=0x00ff00)
    except Exception as e:
        embed_success = discord.Embed(title="Erro", description=str(e), color=0xff0000)
    await interaction.followup.send(embed=embed_success, ephemeral=True)

# ======================== EXECUÇÃO ========================
if __name__ == "__main__":
    bot.run(TOKEN){ margin-bottom: 15px; padding: 10px; border-radius: 10px; }}
.bot {{ background: #5865f2; }}
.user {{ background: #40444b; }}
.date {{ font-size: 0.7em; color: #b9bbbe; }}
</style>
</head>
<body>
<h2>Conversa entre {interaction.user.name} e {user.name}</h2>
"""
        for msg in reversed(messages):
            role = "bot" if msg.author.bot else "user"
            html_content += f"""
<div class="msg {role}">
    <strong>{msg.author.name}:</strong> {msg.content}<br>
    <span class="date">{msg.created_at.strftime('%d/%m/%Y %H:%M:%S')}</span>
</div>"""
        html_content += "</body></html>"

        file = discord.File(io.BytesIO(html_content.encode()), filename=f"dm_conversa_{user.name}.html")
        embed_success = discord.Embed(title="Arquivo Gerado", description=f"Conversa com {user.mention} exportada com sucesso.", color=0x00ff00)
        await interaction.followup.send(embed=embed_success, file=file, ephemeral=True)

    except Exception as e:
        embed_error = discord.Embed(title="Erro", description=str(e), color=0xff0000)
        await interaction.followup.send(embed=embed_error, ephemeral=True)

@tree.command(name="servers", description="Lista servidores em comum entre o bot e o usuário")
@app_commands.describe(user_id="ID numérico do usuário")
async def servers(interaction: discord.Interaction, user_id: str):
    if not is_authorized(interaction.user.id):
        embed = discord.Embed(title="Permissão Negada", color=0xff0000)
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return

    try:
        user = await bot.fetch_user(int(user_id))
    except:
        embed = discord.Embed(title="Erro", description="ID de usuário inválido.", color=0xff0000)
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return

    mutual = [guild for guild in bot.guilds if guild.get_member(user.id)]
    if not mutual:
        embed = discord.Embed(title="Nenhum Servidor em Comum", description=f"O bot não compartilha nenhum servidor com {user.name}.", color=0xffaa00)
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return

    desc = "\n".join([f"- {guild.name} (ID: {guild.id})" for guild in mutual[:25]])
    embed = discord.Embed(title=f"Servidores Compartilhados com {user.name}", description=desc, color=0x3498db)
    if len(mutual) > 25:
        embed.set_footer(text=f"Exibindo 25 de {len(mutual)} servidores.")
    await interaction.response.send_message(embed=embed, ephemeral=True)

@tree.command(name="perfil", description="Mostra avatar, banner, nick e bio do usuário")
@app_commands.describe(user_id="ID numérico do usuário")
async def perfil(interaction: discord.Interaction, user_id: str):
    if not is_authorized(interaction.user.id):
        embed = discord.Embed(title="Permissão Negada", color=0xff0000)
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return

    try:
        user = await bot.fetch_user(int(user_id))
    except:
        embed = discord.Embed(title="Erro", description="ID de usuário inválido.", color=0xff0000)
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return

    await interaction.response.defer()

    avatar_url = user.display_avatar.url
    banner_url = user.banner.url if user.banner else None
    bio = getattr(user, 'bio', None) or "Não disponível"

    nick = None
    for guild in bot.guilds:
        member = guild.get_member(user.id)
        if member and member.nick:
            nick = member.nick
            break

    embed = discord.Embed(title=f"Perfil de {user.name}", color=0x9b59b6)
    embed.set_thumbnail(url=avatar_url)
    if banner_url:
        embed.set_image(url=banner_url)
    embed.add_field(name="Nome Completo", value=f"{user.name}#{user.discriminator if user.discriminator != '0' else ''}", inline=True)
    embed.add_field(name="Apelido (em servidor)", value=nick or "Nenhum", inline=True)
    embed.add_field(name="Biografia", value=bio[:500] if bio else "Vazio", inline=False)
    embed.add_field(name="ID do Usuário", value=str(user.id), inline=False)
    embed.set_footer(text=f"Conta criada em {user.created_at.strftime('%d/%m/%Y %H:%M')}")
    await interaction.followup.send(embed=embed)

@tree.command(name="user_status", description="Verifica o status atual do usuário (online, offline, dnd, ausente)")
@app_commands.describe(user_id="ID numérico do usuário")
async def user_status(interaction: discord.Interaction, user_id: str):
    if not is_authorized(interaction.user.id):
        embed = discord.Embed(title="Permissão Negada", color=0xff0000)
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return

    try:
        user = await bot.fetch_user(int(user_id))
    except:
        embed = discord.Embed(title="Erro", description="ID de usuário inválido.", color=0xff0000)
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return

    member = None
    for guild in bot.guilds:
        m = guild.get_member(user.id)
        if m:
            member = m
            break

    if member:
        status_dict = {
            discord.Status.online: "Online",
            discord.Status.idle: "Ausente",
            discord.Status.dnd: "Não Perturbe",
            discord.Status.offline: "Offline"
        }
        status_text = status_dict.get(member.status, "Desconhecido")
        color = 0x2ecc71 if member.status == discord.Status.online else 0x95a5a6
        embed = discord.Embed(title=f"Status de {user.name}", description=f"**{status_text}**", color=color)
        if member.activity:
            embed.add_field(name="Atividade", value=member.activity.name, inline=False)
    else:
        embed = discord.Embed(
            title="Status Indisponível",
            description=f"Não foi possível obter o status de {user.name}. O bot não compartilha nenhum servidor com este usuário.",
            color=0xffaa00
        )
    await interaction.response.send_message(embed=embed, ephemeral=True)

# ======================== EXECUÇÃO ========================
if __name__ == "__main__":
    bot.run(TOKEN)
