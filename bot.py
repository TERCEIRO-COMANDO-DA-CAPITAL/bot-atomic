#!/usr/bin/env python3
"""
Atomic Bot – Sistema profissional de spam, DM HTML, servidores em comum, perfil e status.
Uso exclusivo via slash commands. Permissões controladas por dono e usuários autorizados.
"""

import discord
from discord import app_commands
from discord.ext import commands
import json
import asyncio
import io
import os
from pathlib import Path
from typing import Set, Optional

# ======================== CONFIGURAÇÃO DE ARQUIVOS LOCAIS ========================
CONFIG_FILE = Path("config.json")
AUTHORIZED_FILE = Path("dados/autorizados.txt")
OWNERS_FILE = Path("dados/donos.txt")

# Criar pastas se não existirem
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
    print("Erro: config.json não encontrado ou token ausente. Execute setup.py primeiro.")
    exit(1)

if not OWNER_IDS:
    print("Aviso: Nenhum dono configurado. Use setup.py para definir os IDs dos donos.")

# ======================== BOT ========================
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.presences = True
intents.dm_messages = True
intents.guilds = True

bot = discord.Client(intents=intents)
tree = app_commands.CommandTree(bot)

# ======================== EVENTOS ========================
@bot.event
async def on_ready():
    await tree.sync()
    print(f"Bot logado como {bot.user}")
    print(f"Donos: {OWNER_IDS}")
    print(f"Usuários autorizados: {len(authorized_users)}")
    print("Slash commands sincronizados globalmente.")

# ======================== COMANDOS DE PERMISSÃO (APENAS DONO) ========================
@tree.command(name="allow_user", description="Autoriza um usuário a usar os comandos do bot")
@app_commands.describe(user_id="ID numérico do usuário a ser autorizado")
async def allow_user(interaction: discord.Interaction, user_id: str):
    if interaction.user.id not in OWNER_IDS:
        embed = discord.Embed(title="Permissão Negada", description="Apenas o dono pode executar este comando.", color=0xff0000)
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return

    try:
        user = await bot.fetch_user(int(user_id))
    except:
        embed = discord.Embed(title="Erro", description="ID de usuário inválido.", color=0xff0000)
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return

    authorized_users.add(str(user.id))
    save_authorized(authorized_users)
    embed = discord.Embed(title="Autorização Concedida", description=f"{user.mention} agora pode usar todos os comandos do bot.", color=0x00ff00)
    await interaction.response.send_message(embed=embed, ephemeral=True)

@tree.command(name="revoke_user", description="Revoga a autorização de um usuário")
@app_commands.describe(user_id="ID numérico do usuário a ser removido")
async def revoke_user(interaction: discord.Interaction, user_id: str):
    if interaction.user.id not in OWNER_IDS:
        embed = discord.Embed(title="Permissão Negada", description="Apenas o dono pode executar este comando.", color=0xff0000)
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return

    try:
        user = await bot.fetch_user(int(user_id))
    except:
        embed = discord.Embed(title="Erro", description="ID de usuário inválido.", color=0xff0000)
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return

    if str(user.id) in authorized_users:
        authorized_users.remove(str(user.id))
        save_authorized(authorized_users)
        embed = discord.Embed(title="Autorização Revogada", description=f"{user.mention} não tem mais permissão para usar os comandos.", color=0xffaa00)
    else:
        embed = discord.Embed(title="Nada a Revogar", description=f"{user.mention} não estava na lista de autorizados.", color=0xffaa00)
    await interaction.response.send_message(embed=embed, ephemeral=True)

@tree.command(name="list_allowed", description="Lista todos os usuários autorizados")
async def list_allowed(interaction: discord.Interaction):
    if interaction.user.id not in OWNER_IDS:
        embed = discord.Embed(title="Permissão Negada", description="Apenas o dono pode executar este comando.", color=0xff0000)
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return

    if not authorized_users:
        embed = discord.Embed(title="Usuários Autorizados", description="Nenhum usuário adicional autorizado.", color=0x3498db)
    else:
        mentions = []
        for uid in authorized_users:
            try:
                user = await bot.fetch_user(int(uid))
                mentions.append(f"{user.name} (ID: {uid})")
            except:
                mentions.append(f"ID desconhecido: {uid}")
        embed = discord.Embed(title="Usuários Autorizados", description="\n".join(mentions), color=0x3498db)
    await interaction.response.send_message(embed=embed, ephemeral=True)

# ======================== COMANDOS PRINCIPAIS (PROTEGIDOS) ========================
@tree.command(name="spam", description="Envia N mensagens para um usuário via DM (precisa de servidor em comum)")
@app_commands.describe(
    user_id="ID numérico do usuário alvo",
    message="Conteúdo da mensagem",
    quantity="Número de vezes a enviar (padrão 5)"
)
async def spam(interaction: discord.Interaction, user_id: str, message: str, quantity: int = 5):
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

    # Verifica se o bot e o usuário compartilham algum servidor
    mutual_guild = None
    for guild in bot.guilds:
        if guild.get_member(user.id):
            mutual_guild = guild
            break

    if not mutual_guild:
        embed = discord.Embed(
            title="Não é possível enviar DM",
            description=f"Não há servidores em comum com {user.name}.\nO bot só pode iniciar conversa com usuários que estejam em pelo menos um servidor que o bot também participa.",
            color=0xffaa00
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return

    if quantity < 1:
        embed = discord.Embed(title="Erro", description="A quantidade deve ser maior que zero.", color=0xff0000)
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return

    embed_start = discord.Embed(title="Spam Iniciado", description=f"Enviando {quantity} mensagens para {user.mention}.", color=0x3498db)
    await interaction.response.send_message(embed=embed_start, ephemeral=True)

    try:
        dm = await user.create_dm()
        for i in range(quantity):
            await dm.send(f"{message} (mensagem {i+1}/{quantity})")
            await asyncio.sleep(0.5)
        embed_success = discord.Embed(title="Spam Concluído", description=f"{quantity} mensagens enviadas para {user.name}.", color=0x00ff00)
    except discord.Forbidden:
        embed_success = discord.Embed(title="Erro", description=f"Não foi possível enviar DM para {user.name}. Usuário bloqueou o bot ou desativou DMs.", color=0xff0000)
    except Exception as e:
        embed_success = discord.Embed(title="Erro", description=str(e), color=0xff0000)

    await interaction.followup.send(embed=embed_success, ephemeral=True)

@tree.command(name="dm_html", description="Gera um arquivo HTML da conversa em DM com o usuário (últimas 200 mensagens)")
@app_commands.describe(user_id="ID numérico do usuário")
async def dm_html(interaction: discord.Interaction, user_id: str):
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

    await interaction.response.defer(ephemeral=True)

    try:
        dm_channel = await user.create_dm()
        messages = []
        async for msg in dm_channel.history(limit=200):
            messages.append(msg)

        if not messages:
            embed = discord.Embed(title="Nenhuma Mensagem", description=f"Não há mensagens na conversa com {user.name}.", color=0xffaa00)
            await interaction.followup.send(embed=embed, ephemeral=True)
            return

        html_content = f"""<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"><title>Conversa com {user.name}</title>
<style>
body {{ font-family: Arial, Helvetica, sans-serif; background: #36393f; color: #fff; padding: 20px; }}
.msg {{ margin-bottom: 15px; padding: 10px; border-radius: 10px; }}
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
