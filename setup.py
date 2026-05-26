#!/usr/bin/env python3
import json
import os
from pathlib import Path

CONFIG_FILE = Path("config.json")
OWNERS_FILE = Path("dados/donos.txt")

def setup():
    print("=== Configuração do Bot Atomic ===\n")
    token = input("Token do Discord: ").strip()
    if not token:
        print("Token inválido.")
        return
    owner_ids = input("IDs dos donos (separados por vírgula): ").strip()
    owners = [int(x.strip()) for x in owner_ids.split(",") if x.strip().isdigit()]
    if not owners:
        print("Nenhum ID válido.")
        return

    # Salvar token
    CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_FILE, "w") as f:
        json.dump({"token": token}, f, indent=4)
    print(f"Token salvo em {CONFIG_FILE}")

    # Salvar donos
    OWNERS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(OWNERS_FILE, "w") as f:
        f.write("\n".join(str(o) for o in owners))
    print(f"Donos salvos em {OWNERS_FILE}")

    # Criar arquivo de autorizados vazio
    auth_file = Path("dados/autorizados.txt")
    auth_file.touch()
    print("Arquivo de autorizados criado.")

    print("\nConfiguração concluída. Execute 'python bot.py' para iniciar.")

if __name__ == "__main__":
    setup()
