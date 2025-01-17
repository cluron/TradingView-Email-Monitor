# TradingView Email Monitor

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.6+](https://img.shields.io/badge/python-3.6+-blue.svg)](https://www.python.org/downloads/)
[![Release](https://img.shields.io/github/release/cluron/TradingView-Email-Monitor.svg)](https://github.com/cluron/TradingView-Email-Monitor/releases)
[![Maintenance](https://img.shields.io/badge/Maintained%3F-yes-green.svg)](https://github.com/cluron/TradingView-Email-Monitor/graphs/commit-activity)

Ce script Python surveille les emails de TradingView et transmet les signaux de trading à un serveur webhook.

## 🚀 Fonctionnalités

- Connexion sécurisée à iCloud Mail via IMAP
- Surveillance automatique des emails de TradingView
- Détection des signaux "BUY" et "SELL"
- Transmission des signaux à un serveur webhook (local ou distant)
- Gestion robuste des erreurs et reconnexion automatique
- Interface en ligne de commande colorée

## 📋 Prérequis

- Python 3.6+
- Compte iCloud Mail
- Mot de passe d'application iCloud
- Serveur webhook (local ou distant) pour recevoir les signaux

## ⚙️ Installation

1. Clonez le repository :
```bash
git clone https://github.com/cluron/TradingView-Email-Monitor.git
cd TradingView-Email-Monitor
```

2. Installez les dépendances :
```bash
pip install -r requirements.txt
```

3. Créez votre fichier de configuration :
```bash
cp config.example.py config.py
```

4. Configurez vos identifiants :
   - Ouvrez `config.py` dans votre éditeur
   - Remplacez les valeurs par défaut par vos informations

### Configuration du mot de passe d'application iCloud

1. Connectez-vous sur [appleid.apple.com](https://appleid.apple.com)
2. Allez dans "Sécurité" → "Mots de passe pour applications"
3. Cliquez sur "+" pour générer un nouveau mot de passe
4. Nommez-le (ex: "TradingView Monitor")
5. Copiez le mot de passe généré dans votre `config.py`

## 🎮 Utilisation

Le script peut fonctionner en deux modes :

### Mode Local
```bash
python3 icloud-Webhook.py --mode local
```
Utilise le serveur webhook local (http://127.0.0.1:5001/webhook)

### Mode Public
```bash
python3 icloud-Webhook.py --mode public
```
Utilise le serveur webhook distant (URL NGROK)

## 📝 Format des Signaux

Le script envoie les signaux au format JSON :
```json
{
    "side": "BUY"  // ou "SELL"
}
```

Les requêtes incluent un header d'authentification :
```
X-WEBHOOK-TOKEN: votre_token
```

## 🛑 Arrêt du Programme

Pour arrêter proprement le programme, utilisez `Ctrl+C`. Le script se déconnectera proprement du serveur IMAP.

## 🔒 Sécurité

- Utilisez toujours un mot de passe d'application dédié pour l'accès IMAP
- Protégez votre webhook avec un token d'authentification
- En mode public, assurez-vous que votre endpoint webhook est sécurisé
- Ne partagez jamais votre fichier `config.py`

## 🐛 Dépannage

- Si le serveur n'est pas accessible, vérifiez qu'il est bien en ligne
- En cas d'erreur IMAP, le script tentera de se reconnecter automatiquement
- Les logs détaillés vous aident à diagnostiquer les problèmes

## 📄 Licence

Ce projet est sous licence MIT - voir le fichier [LICENSE](LICENSE) pour plus de détails.

## 🤝 Contribution

Les contributions sont les bienvenues ! N'hésitez pas à :
1. Fork le projet
2. Créer une branche pour votre fonctionnalité
3. Commiter vos changements
4. Pousser vers la branche
5. Ouvrir une Pull Request 

## 🚀 Déploiement

### Exécution en arrière-plan avec tmux

Pour exécuter le script en continu sur un serveur (ex: Raspberry Pi) sans interface graphique, nous recommandons l'utilisation de `tmux`. Cette solution permet de :
- Exécuter le script en arrière-plan
- Visualiser les logs à tout moment
- Se reconnecter à la session même après déconnexion SSH
- Gérer plusieurs scripts dans différentes fenêtres

#### 1. Installation de tmux
```bash
# Sur Debian/Ubuntu/Raspberry Pi OS
sudo apt update && sudo apt install tmux -y
```

#### 2. Démarrage manuel des scripts
```bash
# Créer une nouvelle session tmux
tmux new -s tradingview

# Diviser la fenêtre horizontalement en deux panneaux
tmux split-window -h

# Dans le panneau de gauche (par défaut), lancer le premier script
python3 icloud-Webhook.py --mode local  # ou --mode public selon votre cas

# Passer au panneau de droite
Ctrl + B, puis flèche droite

# Lancer le second script
python3 src/main.py live --local
```

#### 3. Commandes tmux essentielles
- `Ctrl + B, D` : Se détacher de la session (les scripts continuent en arrière-plan)
- `Ctrl + B, flèche` : Naviguer entre les panneaux
- `Ctrl + B, [` : Mode défilement (utilisez les flèches, `q` pour quitter)
- `Ctrl + B, x` : Fermer le panneau courant
- `Ctrl + B, z` : Zoomer/dézoomer sur le panneau courant

#### 4. Gestion des sessions
```bash
# Lister les sessions tmux actives
tmux ls

# Se rattacher à une session existante
tmux attach -t tradingview

# Tuer une session (et les scripts)
tmux kill-session -t tradingview
```

### Démarrage automatique au boot

Pour que vos scripts démarrent automatiquement dans tmux au démarrage du Raspberry Pi :

#### 1. Créer le script de démarrage
```bash
# Créer et éditer le script
nano ~/start_trading.sh
```

Copier ce contenu :
```bash
#!/bin/bash

# Attendre que le système soit complètement démarré
sleep 10

# Vérifier si la session existe déjà
tmux has-session -t tradingview 2>/dev/null

if [ $? != 0 ]; then
    # Créer une nouvelle session
    tmux new-session -d -s tradingview

    # Diviser la fenêtre en deux panneaux
    tmux split-window -h

    # Panneau gauche : icloud-Webhook.py
    tmux select-pane -t 0
    tmux send-keys "cd $(dirname $(readlink -f $0))" C-m
    tmux send-keys "python3 icloud-Webhook.py --mode local" C-m

    # Panneau droit : main.py
    tmux select-pane -t 1
    tmux send-keys "cd $(dirname $(readlink -f $0))" C-m
    tmux send-keys "python3 src/main.py live --local" C-m

    # Revenir au panneau gauche
    tmux select-pane -t 0
fi
```

#### 2. Rendre le script exécutable
```bash
chmod +x ~/start_trading.sh
```

#### 3. Configurer le démarrage automatique
```bash
# Éditer le crontab
crontab -e

# Ajouter cette ligne (adaptez le chemin)
@reboot /home/pi/start_trading.sh
```

#### 4. Test et vérification
```bash
# Tester sans redémarrer
~/start_trading.sh

# Vérifier que les scripts tournent
tmux attach -t tradingview
```

Vous devriez voir deux panneaux côte à côte avec les logs des deux scripts.

#### 5. Démarrage complet
```bash
# Redémarrer pour tester
sudo reboot

# Après redémarrage, se connecter en SSH et vérifier
tmux attach -t tradingview
```

#### 6. Bonnes pratiques
- Vérifiez les logs régulièrement
- Configurez des alertes en cas d'erreur
- Faites des sauvegardes du script de démarrage
- Documentez les modifications apportées
- Testez après chaque mise à jour système 