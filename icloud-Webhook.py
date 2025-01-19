#!/usr/bin/env python3

"""Fonctionnement
- Se connecte à iCloud Mail via IMAP
- Récupère les nouveaux emails de TradingView (noreply@tradingview.com)
- Lit le corps du mail pour détecter "BUY" ou "SELL"
- Envoie une requête POST avec le bon JSON (BUY ou SELL)

Usage:
    python icloud-Webhook.py --mode [local|public]
    
Options:
    --mode local   Utilise le serveur local (http://127.0.0.1:5001/webhook)
    --mode public  Utilise le serveur public (URL NGROK)
"""

import imaplib
import email
import requests
import time
import argparse
import sys
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from config import *
from datetime import datetime, timezone
from zoneinfo import ZoneInfo  # Ajout de l'import pour les fuseaux horaires
import os
import shutil

# Couleurs pour le terminal
class Colors:
    HEADER = '\033[95m'  # Violet
    BLUE = '\033[94m'    # Bleu
    GREEN = '\033[92m'   # Vert
    YELLOW = '\033[93m'  # Jaune
    RED = '\033[91m'     # Rouge
    ENDC = '\033[0m'     # Reset
    BOLD = '\033[1m'     # Gras
    UNDERLINE = '\033[4m'# Souligné

def parse_arguments():
    # Création d'un formateur personnalisé pour l'aide
    class CustomFormatter(argparse.HelpFormatter):
        def _format_action_invocation(self, action):
            if not action.option_strings:
                return self._metavar_formatter(action, action.dest)(1)[0]
            else:
                parts = []
                if action.nargs == 0:
                    parts.extend(action.option_strings)
                else:
                    default = action.dest.upper()
                    args_string = self._format_args(action, default)
                    for option_string in action.option_strings:
                        parts.append(f"{Colors.GREEN}{option_string}{Colors.ENDC}")
                    parts[-1] += f" {Colors.BLUE}{args_string}{Colors.ENDC}"
                return ', '.join(parts)

    # Création du parser avec une description colorée
    parser = argparse.ArgumentParser(
        description=f'{Colors.HEADER}{Colors.BOLD}TradingView Email Monitor{Colors.ENDC}\n\n'
                   f'{Colors.YELLOW}Ce script surveille les emails de TradingView et transmet les signaux à un serveur webhook.{Colors.ENDC}\n\n'
                   f'{Colors.BOLD}Fonctionnement :{Colors.ENDC}\n'
                   f'  • Connexion à iCloud Mail via IMAP\n'
                   f'  • Surveillance des emails de TradingView\n'
                   f'  • Détection des signaux BUY/SELL\n'
                   f'  • Transmission au serveur webhook\n\n'
                   f'{Colors.BOLD}Exemples :{Colors.ENDC}\n\n'
                   f'  {Colors.GREEN}Mode Local :{Colors.ENDC}\n'
                   f'    python3 icloud-Webhook.py --mode local\n'
                   f'    → Utilise http://127.0.0.1:5001/webhook\n'
                   f'    → Idéal pour les tests ou quand le serveur est sur la même machine\n\n'
                   f'  {Colors.GREEN}Mode Public :{Colors.ENDC}\n'
                   f'    python3 icloud-Webhook.py --mode public\n'
                   f'    → Utilise l\'URL NGROK configurée dans config.py\n'
                   f'    → Pour un serveur distant ou accessible via Internet\n',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        usage=f'{Colors.BOLD}%(prog)s{Colors.ENDC} --mode {Colors.BLUE}[local|public]{Colors.ENDC}'
    )
    
    parser.add_argument('--mode', 
                      type=str,
                      choices=['local', 'public'],
                      required=True,
                      help=f'Mode de fonctionnement :\n\n'
                           f'  {Colors.GREEN}local{Colors.ENDC}  : Utilise le serveur webhook local (127.0.0.1:5001)\n'
                           f'  {Colors.GREEN}public{Colors.ENDC} : Utilise le serveur webhook distant (NGROK)\n')
    
    return parser.parse_args()

def get_webhook_url(mode):
    if mode == 'local':
        return WEBHOOK_URL_LOCAL
    return WEBHOOK_URL_PUBLIC

# Configuration des headers pour le webhook
HEADERS = {
    "Content-Type": "application/json",
    "X-WEBHOOK-TOKEN": WEBHOOK_TOKEN
}

# Sécurité : compteur de signaux
MAX_DAILY_SIGNALS = 15
signal_count = 0
last_signal_date = datetime.now(timezone.utc).date()

# Historique des messages
MAX_MESSAGE_HISTORY = 5  # Nombre de messages à conserver
message_history = []

def add_to_history(message):
    """Ajoute un message à l'historique"""
    global message_history
    message_history.append(message)
    if len(message_history) > MAX_MESSAGE_HISTORY:
        message_history.pop(0)

def count_todays_signals(mail):
    """Compte le nombre de signaux déjà envoyés aujourd'hui"""
    global signal_count
    today = datetime.now(ZoneInfo("Europe/Paris")).date()
    today_str = today.strftime("%d-%b-%Y")  # Format: 24-Mar-2024
    
    # Recherche des emails de TradingView d'aujourd'hui
    status, messages = mail.search(None, f'(FROM "noreply@tradingview.com" SENTON {today_str})')
    if status != "OK" or not messages[0]:
        return 0
        
    count = 0
    for e_id in messages[0].split():
        try:
            status, msg_data = mail.fetch(e_id, '(BODY[])')
            if not msg_data or not msg_data[0]:
                continue

            raw_email = None
            for part in msg_data:
                if isinstance(part, tuple) and len(part) > 1:
                    raw_email = part[1]
                    break

            if not raw_email or not isinstance(raw_email, bytes):
                continue

            email_msg = email.message_from_bytes(raw_email)
            
            payload = None
            if email_msg.is_multipart():
                for part in email_msg.walk():
                    if part.get_content_type() == "text/plain":
                        payload = part.get_payload(decode=True)
                        break
            else:
                payload = email_msg.get_payload(decode=True)

            if not payload:
                continue

            signal = payload.decode('utf-8').strip()
            if "BUY" in signal or "SELL" in signal:
                count += 1
        except:
            continue
            
    return count

def reset_signal_counter():
    global signal_count, last_signal_date
    current_date = datetime.now(ZoneInfo("Europe/Paris")).date()
    if current_date != last_signal_date:
        if signal_count > 0:
            log_success(f"\n[📊] Réinitialisation du compteur de signaux quotidiens")
            log_info(f"    ├── Précédent : {signal_count} signaux")
            log_info(f"    └── Nouveau   : 0 signal")
        signal_count = 0
        last_signal_date = current_date

def send_alert_email(subject, message):
    """Envoie un email d'alerte via iCloud SMTP"""
    try:
        msg = MIMEMultipart()
        msg['From'] = EMAIL_ACCOUNT
        msg['To'] = EMAIL_ACCOUNT
        msg['Subject'] = subject
        
        msg.attach(MIMEText(message, 'plain'))
        
        # Connexion au serveur SMTP d'iCloud
        server = smtplib.SMTP_SSL('smtp.mail.me.com', 587)
        server.login(EMAIL_ACCOUNT, APP_PASSWORD)
        
        # Envoi de l'email
        server.send_message(msg)
        server.quit()
        print(f"[📧] {get_current_time()} Email d'alerte envoyé avec succès")
        return True
    except Exception as e:
        print(f"[❌] {get_current_time()} Erreur lors de l'envoi de l'email d'alerte : {str(e)}")
        return False

def check_signal_limit(signal):
    global signal_count
    if signal_count >= MAX_DAILY_SIGNALS:
        if signal == "SELL":
            log_warning(f"\n[⚠️] Limite de {MAX_DAILY_SIGNALS} signaux atteinte mais exécution du SELL final autorisée")
            return True
            
        # Envoyer un email d'alerte
        subject = "⚠️ Alerte TradingView Monitor - Limite de signaux atteinte"
        message = f"""
Bonjour,

Le moniteur TradingView a atteint sa limite de {MAX_DAILY_SIGNALS} signaux pour aujourd'hui.
Le dernier signal reçu a été ignoré.

Il est recommandé de vérifier :
1. Le bon fonctionnement de vos indicateurs
2. L'historique des signaux de la journée
3. L'état de vos positions actuelles

Timestamp: {datetime.now(ZoneInfo("Europe/Paris")).strftime('%Y-%m-%d %H:%M:%S (Europe/Paris)')}

Ce message est automatique, merci de ne pas y répondre.
"""
        send_alert_email(subject, message)
        log_error(f"\n[🛑] Limite de {MAX_DAILY_SIGNALS} signaux atteinte - Signal ignoré jusqu'à demain")
        return False
    return True

def get_current_time():
    return datetime.now(ZoneInfo("Europe/Paris")).strftime("%H:%M:%S")

def format_email_id(email_id):
    """Formate l'ID de l'email pour un meilleur affichage"""
    return f"#{str(int(email_id))}"

def log_info(message, end="\n"):
    print(f"{Colors.BLUE}{message}{Colors.ENDC}", end=end, flush=True)

def log_success(message, end="\n"):
    print(f"{Colors.GREEN}{message}{Colors.ENDC}", end=end, flush=True)

def log_warning(message, end="\n"):
    print(f"{Colors.YELLOW}{message}{Colors.ENDC}", end=end, flush=True)

def log_error(message, end="\n"):
    print(f"{Colors.RED}{message}{Colors.ENDC}", end=end, flush=True)

def log_header(message, end="\n"):
    print(f"{Colors.HEADER}{message}{Colors.ENDC}", end=end, flush=True)

def clear_screen():
    """Efface l'écran du terminal"""
    os.system('cls' if os.name == 'nt' else 'clear')

def get_terminal_width():
    """Récupère la largeur du terminal"""
    return shutil.get_terminal_size().columns

def display_banner():
    """Affiche le titre et la description du script"""
    version = get_version()
    width = get_terminal_width()
    separator = "═" * width

    clear_screen()
    print(f"\n{separator}")
    print(f"📧 TradingView Email Monitor {version}".center(width))
    print(f"{separator}\n")

    print(f"{Colors.BLUE}Ce script :{Colors.ENDC}")
    print("• Se connecte à iCloud Mail via IMAP")
    print("• Surveille les emails provenant de TradingView, qui applique la stratégie 'Future Trend Channel'")
    print("• Détecte les signaux BUY/SELL dans les messages")
    print("• Transmet les signaux au bot de trading pour qu'il puisse BUY/SELL")
    print(f"• Limite à {Colors.BOLD}{MAX_DAILY_SIGNALS}{Colors.ENDC} signaux BUY/SELL envoyés par jour pour éviter les emballements")
    print("• Envoie une alerte email si la limite est atteinte\n")

def display_status(mode, webhook_url):
    """Affiche l'état du service"""
    print(f"🔵 Mode {mode.upper()} activé (envoi des alertes de trading vers un serveur {mode.lower()})")
    print(f"✅ Connexion IMAP établie et vérifiée\n")

def display_stats(signal_count, last_signal=None):
    """Affiche les statistiques"""
    width = get_terminal_width()
    print("STATISTIQUES JOURNALIÈRES")
    print("═" * 24)
    print(f"Signaux traités    : {signal_count}/{MAX_DAILY_SIGNALS} (prochain reset à minuit)")
    if last_signal:
        print(f"Dernier signal     : {last_signal}\n")
    else:
        print("Dernier signal     : Aucun\n")

def display_last_event(message):
    """Affiche le dernier événement et son historique"""
    width = get_terminal_width()
    print("DERNIERS ÉVÉNEMENTS")
    print("═" * 18)
    
    if message:
        add_to_history(message)
    
    # Afficher l'historique du plus récent au plus ancien
    for msg in reversed(message_history):
        print(msg)
    print()

def display_error_zone(error_message=None):
    """Affiche la zone d'erreurs"""
    width = get_terminal_width()
    print("ERREURS ET ALERTES")
    print("═" * 16)
    if error_message:
        print(f"{Colors.RED}{error_message}{Colors.ENDC}\n")
    else:
        print("Aucune erreur\n")

def update_display(mode, webhook_url, signal_count, last_signal=None, last_event=None, error=None):
    """Met à jour l'affichage complet"""
    display_banner()
    display_status(mode, webhook_url)
    display_stats(signal_count, last_signal)
    if last_event:
        display_last_event(last_event)
    display_error_zone(error)

def get_version():
    """Récupère la version depuis le dernier tag Git"""
    try:
        import subprocess
        result = subprocess.run(['git', 'describe', '--tags', '--abbrev=0'], 
                              capture_output=True, text=True)
        if result.returncode == 0:
            return result.stdout.strip()
        return "version inconnue"
    except Exception:
        return "version inconnue"

def check_email(mail, webhook_url, mode):
    global signal_count
    try:
        # Vérifier et réinitialiser le compteur si nécessaire
        reset_signal_counter()
        
        try:
            mail.noop()
        except:
            update_display(mode, webhook_url, signal_count, error=f"[🔄] {get_current_time()} La connexion semble inactive, déclenchement d'une reconnexion...")
            raise imaplib.IMAP4.error("Connection check failed")

        status, messages = mail.search(None, 'UNSEEN FROM "noreply@tradingview.com"')

        if status != "OK" or not messages[0]:
            update_display(mode, webhook_url, signal_count, last_event=f"[🔍] {get_current_time()} Surveillance active...")
            return

        # Récupérer tous les IDs d'emails non lus
        email_ids = messages[0].split()
        if len(email_ids) > 1:
            update_display(mode, webhook_url, signal_count, 
                         last_event=f"[⚠️] {get_current_time()} Attention: {len(email_ids)} emails non lus détectés")

        # On va d'abord identifier le dernier email avec un signal valide
        last_valid_signal = None
        last_valid_id = None
        
        # Parcourir les emails dans l'ordre inverse
        for e_id in reversed(email_ids):
            try:
                update_display(mode, webhook_url, signal_count, 
                             last_event=f"[📧] {get_current_time()} Analyse de l'email {format_email_id(e_id)}")
                
                status, msg_data = mail.fetch(e_id, '(BODY[])')
                
                if not msg_data or not msg_data[0]:
                    update_display(mode, webhook_url, signal_count, 
                                 error=f"[❌] {get_current_time()} msg_data est vide ou invalide")
                    continue

                # Extraction du contenu brut de l'email
                raw_email = None
                for part in msg_data:
                    if isinstance(part, tuple) and len(part) > 1:
                        raw_email = part[1]
                        break

                if not raw_email or not isinstance(raw_email, bytes):
                    update_display(mode, webhook_url, signal_count, 
                                 error=f"[❌] {get_current_time()} Format invalide : raw_email est de type {type(raw_email)} (attendu: bytes)")
                    continue

                email_msg = email.message_from_bytes(raw_email)
                
                # Extraction du signal (corps du message)
                payload = None
                if email_msg.is_multipart():
                    for part in email_msg.walk():
                        if part.get_content_type() == "text/plain":
                            payload = part.get_payload(decode=True)
                            break
                else:
                    payload = email_msg.get_payload(decode=True)

                if not payload:
                    update_display(mode, webhook_url, signal_count, 
                                 error=f"[❌] {get_current_time()} Aucun contenu text/plain trouvé dans l'email")
                    continue

                signal = payload.decode('utf-8').strip()
                
                # Vérification du signal
                if "BUY" in signal:
                    signal = "BUY"
                    last_valid_signal = signal
                    last_valid_id = e_id
                    update_display(mode, webhook_url, signal_count, 
                                 last_event=f"[✅] {get_current_time()} Signal {Colors.BOLD}BUY{Colors.ENDC} valide trouvé dans l'email {format_email_id(e_id)}")
                    break
                elif "SELL" in signal:
                    signal = "SELL"
                    last_valid_signal = signal
                    last_valid_id = e_id
                    update_display(mode, webhook_url, signal_count, 
                                 last_event=f"[✅] {get_current_time()} Signal {Colors.BOLD}SELL{Colors.ENDC} valide trouvé dans l'email {format_email_id(e_id)}")
                    break
                else:
                    update_display(mode, webhook_url, signal_count, 
                                 error=f"[❌] {get_current_time()} Pas de signal valide dans cet email")

            except Exception as e:
                update_display(mode, webhook_url, signal_count, 
                             error=f"[❌] {get_current_time()} Erreur lors de l'analyse de l'email {format_email_id(e_id)}: {e}")
                continue

        # Marquer les autres emails comme lus
        for e_id in email_ids:
            if e_id != last_valid_id:
                try:
                    mail.store(e_id, "+FLAGS", "\\Seen")
                    update_display(mode, webhook_url, signal_count, 
                                 last_event=f"[✓] {get_current_time()} Email {format_email_id(e_id)} marqué comme lu (ignoré)")
                except Exception as e:
                    update_display(mode, webhook_url, signal_count, 
                                 error=f"[❌] {get_current_time()} Erreur lors du marquage de l'email {format_email_id(e_id)}: {e}")

        # Traiter le dernier signal valide
        if last_valid_signal and last_valid_id:
            if not check_signal_limit(last_valid_signal):
                try:
                    mail.store(last_valid_id, "+FLAGS", "\\Seen")
                    update_display(mode, webhook_url, signal_count, 
                                 last_event=f"[✓] {get_current_time()} Email marqué comme lu (limite de signaux atteinte)")
                except Exception as e:
                    update_display(mode, webhook_url, signal_count, 
                                 error=f"[❌] {get_current_time()} Erreur lors du marquage de l'email : {e}")
                return

            update_display(mode, webhook_url, signal_count, 
                         last_event=f"[🎯] {get_current_time()} Traitement du signal {Colors.BOLD}{last_valid_signal}{Colors.ENDC}")
            payload = {"side": last_valid_signal}
            
            try:
                response = requests.post(webhook_url, json=payload, headers=HEADERS)
                if response.status_code == 200:
                    mail.store(last_valid_id, "+FLAGS", "\\Seen")
                    signal_count += 1
                    update_display(mode, webhook_url, signal_count, 
                                 last_signal=f"{last_valid_signal} à {get_current_time()}",
                                 last_event=f"[🚀] {get_current_time()} Signal {last_valid_signal} envoyé avec succès")
                else:
                    update_display(mode, webhook_url, signal_count, 
                                 error=f"[❌] {get_current_time()} Erreur lors de l'envoi : code {response.status_code}\n[📝] Réponse : {response.text}")
            except requests.exceptions.ConnectionError:
                update_display(mode, webhook_url, signal_count, 
                             error=f"[❌] {get_current_time()} Impossible de se connecter au serveur webhook : {webhook_url}\n[💡] Vérifiez que le serveur est bien en ligne et accessible")
            except Exception as e:
                update_display(mode, webhook_url, signal_count, 
                             error=f"[❌] {get_current_time()} Erreur lors de l'envoi au webhook : {str(e)}")

    except Exception as e:
        update_display(mode, webhook_url, signal_count, 
                      error=f"[❌] {get_current_time()} Erreur lors de la vérification des emails : {e}\n[📝] Détails : {str(e)}")
        raise

def main():
    args = parse_arguments()
    webhook_url = get_webhook_url(args.mode)
    
    reconnect_delay = 10
    max_reconnect_delay = 300

    while True:
        mail = None
        try:
            update_display(args.mode, webhook_url, 0, last_event=f"[🔌] {get_current_time()} Connexion à iCloud...")
            mail = imaplib.IMAP4_SSL(IMAP_SERVER)
            mail.login(EMAIL_ACCOUNT, APP_PASSWORD)
            mail.select("inbox")
            
            global signal_count
            signal_count = count_todays_signals(mail)
            
            update_display(args.mode, webhook_url, signal_count, last_event=f"[✅] {get_current_time()} Connecté et prêt à surveiller les emails de TradingView")
            
            reconnect_delay = 10

            while True:
                check_email(mail, webhook_url, args.mode)
                time.sleep(10)

        except KeyboardInterrupt:
            update_display(args.mode, webhook_url, signal_count, last_event="[👋] Arrêt du programme...")
            try:
                if mail:
                    mail.close()
                    mail.logout()
                update_display(args.mode, webhook_url, signal_count, last_event="[✅] Déconnexion effectuée")
            except:
                pass
            update_display(args.mode, webhook_url, signal_count, last_event="[✅] Programme arrêté")
            sys.exit(0)

        except Exception as e:
            update_display(args.mode, webhook_url, signal_count, error=f"[❌] {get_current_time()} Erreur de connexion : {str(e)}")
            try:
                if mail:
                    mail.logout()
            except:
                pass

            update_display(args.mode, webhook_url, signal_count, last_event=f"[🔄] {get_current_time()} Nouvelle tentative dans {reconnect_delay} secondes...")
            time.sleep(reconnect_delay)
            reconnect_delay = min(reconnect_delay * 2, max_reconnect_delay)

if __name__ == "__main__":
    main()
