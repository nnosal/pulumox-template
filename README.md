# Pulumox - 📦 Pulumi template for Proxmox - READY2GO 🚀
![GitHub last commit](https://img.shields.io/github/last-commit/nnosal/pulumox-template?style=flat-square)

Un template pré-configurées pour [Pulumi](https://github.com/pulumi/pulumi), permettant une installation en 1-clic de VM Windows, Mac, Linux.

## 🛠️ Utilisation

0. Générer la passphrase pour vos secrets: `export PULUMI_CONFIG_PASSPHRASE_FILE="$( [ -f ~/.pulumox/passphrase.txt ] || (mkdir -p ~/.pulumox && head -c 32 /dev/urandom | base64 > ~/.pulumox/passphrase.txt); echo ~/.pulumox/passphrase.txt )"`. Sinon utiliser `--secret-provider="uri://see-pulumi-doc..."` lors du `pulumi new`.
1. Créer votre projet *(dans le dossier courant)*: `pulumi new https://github.com/nnosal/pulumox-template` et suivre la procédure...
2. *Optionnel: Installer [mise](https://github.com/jdx/mise) et initialiser le projet: `mise trust . && mise install && mise r show`*, voir le fichier `mise.toml`.
3. Puis tester sa stack pulumi avec les classiques: `pulumi preview`.
4. Par défaut `__main__.py` chargera des templates génériques (:todo)
5. Coder/adapter sa propre logique en python ou en yaml (via la classe d'abstraction).

## 📜 License
GPL v3 License
