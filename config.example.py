# Serveur IMAP iCloud
IMAP_SERVER = "imap.mail.me.com"
EMAIL_ACCOUNT = "votre_email@icloud.com"
APP_PASSWORD = "votre_mot_de_passe_app"  # Généré depuis appleid.apple.com

# URLs des webhooks
WEBHOOK_URL_LOCAL = "http://127.0.0.1:5001/webhook"  # URL locale pour les tests
WEBHOOK_URL_PUBLIC = "https://votre-url-ngrok.ngrok.io/webhook"  # URL publique (ex: NGROK)

# Token d'authentification pour le webhook
WEBHOOK_TOKEN = "votre_token_secret"  # Token pour sécuriser les requêtes 

# Paramètres de l'historique
MAX_SIGNAL_HISTORY = 15    # Nombre de signaux BUY/SELL à conserver
MAX_EVENT_HISTORY = 30     # Nombre d'événements relatifs aux signaux à conserver
MAX_ALERT_HISTORY = 30     # Nombre d'alertes et erreurs à conserver

# Paramètres de sécurité et performance
MAX_DAILY_SIGNALS = 15     # Limite de signaux BUY/SELL par jour
CHECK_INTERVAL = 10        # Délai entre chaque vérification des emails (en secondes)
RECONNECT_DELAY = 10       # Délai initial avant reconnexion en cas d'erreur (en secondes)
MAX_RECONNECT_DELAY = 300  # Délai maximum de reconnexion (en secondes) 