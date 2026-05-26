import discord
from discord import app_commands
import json
import os
import asyncio
from pathlib import Path
from typing import Set

# ========== CONFIGURAÇÃO DE ARQUIVOS LOCAIS ==========
CONFIG_FILE = Path("config.json")
AUTHORIZED_FILE = Path("dados/autorizados.txt")
OWNERS_FILE = Path("dados/donos.txt")

# Cria pastas se não existirem
AUTHORIZED_FILE.parent.mkdir(parents=True, exist_ok=True)

def load_token():
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE) as f:
            data = json.load(f)
            return data.get("token")
    return None

def load_owners() -> Set[int]:
    if OWNERS_FILE.exists():
        with open(OWNERS_FILE) as f:
            return {int(line.strip()) for line in f if line.strip()}
    return set()

def load_authorized() -> Set[str]:
    if AUTHORIZED_FILE.exists():
        with open(AUTHORIZED_FILE) as f:
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
    print("Arquivo config.json não encontrado ou token ausente. Execute setup.py.")
    exit(1)

# ========== BOT ==========
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.presences = True
intents.dm_messages = True
intents.guilds = True

bot = discord.Client(intents=intents)
tree = app_commands.CommandTree(bot)

# ========== EVENTOS ==========
@bot.event
async def on_ready():
    await tree.sync()
    print(f"Bot logado como {bot.user}")
    print(f"Donos: {OWNER_IDS}")
    print(f"Autorizados: {len(authorized_users)}")

# ========== COMANDOS DE PERMISSÃO (APENAS DONO) ==========
@tree.command(name="allow_user", description="Autoriza um usuário a usar o bot")
async def allow_user(interaction: discord.Interaction, user: discord.User):
    if interaction.user.id not in OWNER_IDS:
        await interaction.response.send_message("Apenas o dono pode usar este comando.", ephemeral=True)
        return
    authorized_users.add(str(user.id))
    save_authorized(authorized_users)
    await interaction.response.send_message(f"{user.mention} está autorizado.", ephemeral=True)

@tree.command(name="revoke_user", description="Revoga autorização")
async def revoke_user(interaction: discord.Interaction, user: discord.User):
    if interaction.user.id not in OWNER_IDS:
        await interaction.response.send_message("Apenas o dono pode usar este comando.", ephemeral=True)
        return
    if str(user.id) in authorized_users:
        authorized_users.remove(str(user.id))
        save_authorized(authorized_users)
        await interaction.response.send_message(f"{user.mention} não está mais autorizado.", ephemeral=True)
    else:
        await interaction.response.send_message("Usuário não estava na lista.", ephemeral=True)

@tree.command(name="list_allowed", description="Lista usuários autorizados")
async def list_allowed(interaction: discord.Interaction):
    if interaction.user.id not in OWNER_IDS:
        await interaction.response.send_message("Apenas o dono pode usar este comando.", ephemeral=True)
        return
    if not authorized_users:
        await interaction.response.send_message("Nenhum usuário autorizado além dos donos.", ephemeral=True)
        return
    mentions = []
    for uid in authorized_users:
        user = await bot.fetch_user(int(uid))
        mentions.append(f"{user.name} (ID: {uid})")
    await interaction.response.send_message("Autorizados:\n" + "\n".join(mentions), ephemeral=True)

# ========== COMANDO EXEMPLO (PROTEGIDO) ==========
@tree.command(name="ping", description="Testa o bot (apenas autorizados)")
async def ping(interaction: discord.Interaction):
    if not is_authorized(interaction.user.id):
        await interaction.response.send_message("Você não tem permissão.", ephemeral=True)
        return
    await interaction.response.send_message(f"Pong! Latência: {round(bot.latency * 1000)}ms")

# ========== SPAM (exemplo) ==========
@tree.command(name="spam", description="Envia N mensagens para um usuário (autorizado)")
async def spam(interaction: discord.Interaction, user: discord.User, message: str, quantidade: int = 5):
    if not is_authorized(interaction.user.id):
        await interaction.response.send_message("Permissão negada.", ephemeral=True)
        return
    if quantidade < 1:
        await interaction.response.send_message("Quantidade deve ser positiva.", ephemeral=True)
        return
    await interaction.response.send_message(f"Iniciando spam para {user.mention}", ephemeral=True)
    try:
        dm = await user.create_dm()
        for i in range(quantidade):
            await dm.send(f"{message} (msg {i+1}/{quantidade})")
            await asyncio.sleep(0.5)
        await interaction.followup.send(f"Enviado {quantidade} mensagens.", ephemeral=True)
    except Exception as e:
        await interaction.followup.send(f"Erro: {e}", ephemeral=True)

# ========== EXECUÇÃO ==========
if __name__ == "__main__":
    bot.run(TOKEN)
