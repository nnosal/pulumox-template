# Pulumox - 📦 Pulumi Template + Proxmox - READY2GO 🚀
![GitHub last commit](https://img.shields.io/github/last-commit/nnosal/pulumox-template?style=flat-square)
[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](https://www.gnu.org/licenses/gpl-3.0)
[![ko-fi](https://srv-cdn.himpfen.io/badges/kofi/kofi-square.svg)](https://ko-fi.com/nnosal)
<!--[![Buy Me a Coffee](https://srv-cdn.himpfen.io/badges/buymeacoffee/buymeacoffee-square.svg)](https://www.buymeacoffee.com/nnosal)-->



Une template pré-configurées pour [Pulumi](https://github.com/pulumi/pulumi), permettant une installation en 1-clic de VM Windows, Mac, Linux.

Propulsé avec le provider "[pulumi-proxmoxve](https://github.com/muhlba91/pulumi-proxmoxve)", l'idée est matérialiser ce
 [schéma](https://excalidraw.com/#url=https://raw.githubusercontent.com/nnosal/pulumox-template/main/docs/plan.excalidraw) de VM tout en restant 100% Pythonique pour une portabilité parfaite.

## 🛠️ Utilisation

0. Générer la passphrase pour vos secrets: `export PULUMI_CONFIG_PASSPHRASE_FILE="$( [ -f ~/.pulumox/passphrase.txt ] || (mkdir -p ~/.pulumox && head -c 32 /dev/urandom | base64 > ~/.pulumox/passphrase.txt); echo ~/.pulumox/passphrase.txt )"`. Sinon utiliser `--secret-provider="uri://see-pulumi-doc..."` lors du `pulumi new`.
1. Créer votre projet *(dans le dossier courant)*: `pulumi new https://github.com/nnosal/pulumox-template` et suivre la procédure...
2. *Optionnel: Installer [mise](https://github.com/jdx/mise) et initialiser le projet: `mise trust . && mise install && mise r show`*, voir le fichier `mise.toml`.
3. Puis tester sa stack pulumi avec les classiques: `pulumi preview`.
4. Par défaut `__main__.py` chargera des templates génériques (:todo)
5. Coder/adapter sa propre logique en python ou en yaml (via la classe d'abstraction).

## ⏳ Todo
1. [ ] Ajouter un moteur de template yaml imbriqué afin de pouvoir injecté des variables dynamiques. [➡️ Voir l'étude complète](https://github.com/nnosal/pulumox-template/blob/main/docs/20250814_etude_yaml_templates.ipynb)
2. [ ] Définir la structure optimale pour les méthodes core pour gérer "mac", "windows", linux".

## 📜 License
GPL v3 License
