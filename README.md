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

### Démarrage automatique avec systemd

Pour que vos scripts démarrent automatiquement au boot avec une gestion propre des processus et des logs :

#### 1. Créer le script de lancement
```bash
# Créer le script de lancement
sudo nano /usr/local/bin/start-trading-services.sh
```

Copier ce contenu :
```bash
#!/bin/bash

# Nettoyer toute session existante
tmux kill-session -t tradingview 2>/dev/null || true
rm -f /tmp/tmux-*/default

# Créer la session avec le premier script
tmux new-session -d -s tradingview
tmux send-keys -t tradingview "cd /home/bot/TradingView-Email-Monitor" C-m
tmux send-keys -t tradingview "python3 icloud-Webhook.py --mode local" C-m

# Attendre un peu que la première commande démarre
sleep 2

# Créer le second panneau et lancer le second script
tmux split-window -h -t tradingview
tmux send-keys -t tradingview:0.1 "cd /home/bot/cryptoBot-Future-Trend-Channel" C-m
tmux send-keys -t tradingview:0.1 "python3 src/main.py live --local" C-m

# Retourner au premier panneau
tmux select-pane -t tradingview:0.0
```

Rendre le script exécutable :
```bash
sudo chmod +x /usr/local/bin/start-trading-services.sh
```

#### 2. Créer le service systemd
```bash
# Créer le fichier de service
sudo nano /etc/systemd/system/tradingview-monitor.service
```

Copier ce contenu :
```ini
[Unit]
Description=TradingView Email Monitor Service
# Attendre que le réseau ET la synchronisation NTP soient prêts
After=network.target time-sync.target ntp.service
# S'assurer que l'heure est synchronisée avant de démarrer
Requires=time-sync.target
Wants=ntp.service

[Service]
Type=forking
User=bot
Environment="TMUX="
# Vérifier la synchronisation NTP et attendre plus longtemps
ExecStartPre=/bin/bash -c 'until ntpq -p >/dev/null 2>&1; do sleep 2; done; sleep 30'
ExecStart=/usr/local/bin/start-trading-services.sh
ExecStop=/usr/bin/tmux kill-session -t tradingview
Restart=always
RestartSec=30

[Install]
WantedBy=multi-user.target
```

#### 3. Gestion du service
```bash
# Vérifier l'état du service
sudo systemctl status tradingview-monitor

# Voir les logs du service
sudo journalctl -u tradingview-monitor -f

# Arrêter le service
sudo systemctl stop tradingview-monitor

# Redémarrer le service
sudo systemctl restart tradingview-monitor
```

#### 4. Accéder aux scripts en cours d'exécution
```bash
# Se connecter à la session tmux
tmux attach -t tradingview
```

#### 5. Bonnes pratiques
- Vérifiez régulièrement les logs avec `journalctl`
- Configurez la rotation des logs si nécessaire
- Surveillez l'utilisation des ressources
- Testez le redémarrage automatique
- Gardez une sauvegarde de la configuration systemd 
```

## Mécanismes de sécurité

### Limite de signaux quotidiens
Pour protéger contre les bugs potentiels ou les comportements erratiques des indicateurs, le script implémente une limite de signaux quotidiens :
- Maximum de 15 signaux par jour
- Le compteur se réinitialise à minuit (UTC)
- Au démarrage, le script analyse les emails de la journée pour compter les signaux déjà traités
- Si la limite est atteinte, le script :
  1. Exécute le dernier SELL si c'est un signal de vente
  2. Ignore tous les signaux suivants jusqu'à la réinitialisation du compteur
  3. Envoie un email d'alerte à l'utilisateur
  4. Affiche un avertissement dans les logs

L'email d'alerte contient :
- Le nombre de signaux atteint
- Un rappel des points à vérifier
- L'horodatage de l'événement
- Des recommandations pour la suite

Cette sécurité évite les comportements erratiques en cas de dysfonctionnement des indicateurs tout en permettant de clôturer une position si nécessaire.

## Utilisation manuelle

### Arrêt du programme
Pour arrêter proprement la surveillance des emails :
1. Appuyez sur CTRL+C
2. Le programme se déconnectera proprement d'iCloud
3. Un message confirmera l'arrêt du programme 