# Pulumox - 📦 Pulumi template for Proxmox - ready to go 🚀
![GitHub last commit](https://img.shields.io/github/last-commit/nnosal/pulumox-template?style=flat-square)

Un template pré-configurées pour [Pulumi](https://github.com/pulumi/pulumi), permettant une installation en 1-clic de VM Windows, Mac, Linux.

## 🛠️ Utilisation

1. Créer votre projet: `pulumi new https://github.com/nnosal/pulumox-template`
2. Suivre la procédure...
0. Optionnel: Installer [mise](https://github.com/jdx/mise) et initialiser le projet: `mise trust . && mise install'
3. Puis tester sa stack pulumi avec les classiques: `pulumi preview`.
4. Par défaut __main__.py chargera des templates génériques (:todo)
5. Coder/adapter sa propre logique en python ou en yaml (via la classe d'abstraction).

## 📜 License
GPL v3 License
