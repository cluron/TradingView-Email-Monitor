# TradingView Email Monitor

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.6+](https://img.shields.io/badge/python-3.6+-blue.svg)](https://www.python.org/downloads/)
[![Release](https://img.shields.io/badge/release-v1.0.0-blue.svg)](https://github.com/cluron/TradingView-Email-Monitor/releases)
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