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

# Couleurs pour le terminal
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

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

def count_todays_signals(mail):
    """Compte le nombre de signaux déjà envoyés aujourd'hui"""
    global signal_count
    today = datetime.now(timezone.utc).date()
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
    current_date = datetime.now(timezone.utc).date()
    if current_date != last_signal_date:
        if signal_count > 0:
            print(f"\n[📊] Réinitialisation du compteur de signaux (précédent : {signal_count})")
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
            print(f"\n[⚠️] Limite de {MAX_DAILY_SIGNALS} signaux atteinte mais exécution du SELL final autorisée")
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

Timestamp: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}

Ce message est automatique, merci de ne pas y répondre.
"""
        send_alert_email(subject, message)
        print(f"\n[🛑] Limite de {MAX_DAILY_SIGNALS} signaux atteinte - Signal ignoré jusqu'à demain")
        return False
    return True

def get_current_time():
    return datetime.now().strftime("%H:%M:%S")

def check_email(mail, webhook_url):
    try:
        # Vérifier et réinitialiser le compteur si nécessaire
        reset_signal_counter()
        
        # Surveillance sur la même ligne avec message d'aide
        print("\r[🔍] Surveillance active... (CTRL+C pour arrêter) ", end="", flush=True)
        
        try:
            # Vérifier que la connexion est toujours active
            mail.noop()
        except:
            print(f"\n[🔄] {get_current_time()} La connexion semble inactive, déclenchement d'une reconnexion...")
            raise imaplib.IMAP4.error("Connection check failed")

        status, messages = mail.search(None, 'UNSEEN FROM "noreply@tradingview.com"')

        if status != "OK" or not messages[0]:
            # Ajoute un point pour montrer que le script est actif
            print(".", end="", flush=True)
            return

        # Récupérer tous les IDs d'emails non lus
        email_ids = messages[0].split()
        if len(email_ids) > 1:
            print(f"\n[⚠️] {get_current_time()} Attention: {len(email_ids)} emails non lus détectés")

        # On va d'abord identifier le dernier email avec un signal valide
        last_valid_signal = None
        last_valid_id = None
        
        # Parcourir les emails dans l'ordre inverse (du plus récent au plus ancien)
        for e_id in reversed(email_ids):
            try:
                print(f"\n[📧] {get_current_time()} Analyse de l'email ID : {e_id}")
                
                # Récupération du message
                status, msg_data = mail.fetch(e_id, '(BODY[])')
                
                if not msg_data or not msg_data[0]:
                    print(f"[❌] {get_current_time()} msg_data est vide ou invalide")
                    continue

                # Extraction du contenu brut de l'email
                raw_email = None
                for part in msg_data:
                    if isinstance(part, tuple) and len(part) > 1:
                        raw_email = part[1]
                        break

                if not raw_email or not isinstance(raw_email, bytes):
                    print(f"[❌] {get_current_time()} Format invalide : raw_email est de type {type(raw_email)} (attendu: bytes)")
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
                    print(f"[❌] {get_current_time()} Aucun contenu text/plain trouvé dans l'email")
                    continue

                signal = payload.decode('utf-8').strip()
                
                # Vérification du signal
                if "BUY" in signal:
                    signal = "BUY"
                    last_valid_signal = signal
                    last_valid_id = e_id
                    print(f"[✅] {get_current_time()} Signal BUY valide trouvé dans l'email {e_id}")
                    break  # On a trouvé notre dernier signal valide
                elif "SELL" in signal:
                    signal = "SELL"
                    last_valid_signal = signal
                    last_valid_id = e_id
                    print(f"[✅] {get_current_time()} Signal SELL valide trouvé dans l'email {e_id}")
                    break  # On a trouvé notre dernier signal valide
                else:
                    print(f"[❌] {get_current_time()} Pas de signal valide dans cet email")

            except Exception as e:
                print(f"[❌] {get_current_time()} Erreur lors de l'analyse de l'email {e_id}: {e}")
                continue

        # Marquer tous les autres emails comme lus
        for e_id in email_ids:
            if e_id != last_valid_id:
                try:
                    mail.store(e_id, "+FLAGS", "\\Seen")
                    print(f"[✓] {get_current_time()} Email {e_id} marqué comme lu (ignoré)")
                except Exception as e:
                    print(f"[❌] {get_current_time()} Erreur lors du marquage de l'email {e_id}: {e}")

        # Traiter uniquement le dernier signal valide si on en a trouvé un
        if last_valid_signal and last_valid_id:
            # Vérifier la limite de transactions
            if not check_signal_limit(last_valid_signal):
                # Marquer l'email comme lu même si on ne le traite pas
                try:
                    mail.store(last_valid_id, "+FLAGS", "\\Seen")
                    print(f"[✓] {get_current_time()} Email marqué comme lu (limite de transactions atteinte)")
                except Exception as e:
                    print(f"[❌] {get_current_time()} Erreur lors du marquage de l'email : {e}")
                return

            print(f"\n[🎯] {get_current_time()} Traitement du dernier signal valide : {last_valid_signal} (Email ID: {last_valid_id})")
            payload = {"side": last_valid_signal}
            
            try:
                # Envoi au webhook
                response = requests.post(webhook_url, json=payload, headers=HEADERS)
                if response.status_code == 200:
                    print(f"[🚀] {get_current_time()} Signal envoyé avec succès (code: {response.status_code})")
                    # Marquer comme lu uniquement si l'envoi a réussi
                    mail.store(last_valid_id, "+FLAGS", "\\Seen")
                    print(f"[✓] {get_current_time()} Email du signal traité marqué comme lu")
                    # Incrémenter le compteur de signaux
                    global signal_count
                    signal_count += 1
                    print(f"\n[📊] Signaux traités aujourd'hui : {signal_count}/{MAX_DAILY_SIGNALS}")
                else:
                    print(f"[❌] {get_current_time()} Erreur lors de l'envoi : code {response.status_code}")
                    print(f"[📝] {get_current_time()} Réponse : {response.text}")
            except requests.exceptions.ConnectionError:
                print(f"[❌] {get_current_time()} Impossible de se connecter au serveur webhook : {webhook_url}")
                print(f"[💡] {get_current_time()} Vérifiez que le serveur est bien en ligne et accessible")
            except Exception as e:
                print(f"[❌] {get_current_time()} Erreur lors de l'envoi au webhook : {str(e)}")

    except Exception as e:
        print(f"\n[❌] {get_current_time()} Erreur lors de la vérification des emails : {e}")
        print(f"[📝] {get_current_time()} Détails de l'erreur : {str(e)}")
        raise  # Propager l'erreur pour déclencher une reconnexion

def main():
    # Parse les arguments
    args = parse_arguments()
    webhook_url = get_webhook_url(args.mode)
    print(f"\n[⚙️] {get_current_time()} Mode du serveur webhook : {args.mode} ({webhook_url})")
    print(f"[🛡️] {get_current_time()} Sécurité : Maximum {MAX_DAILY_SIGNALS} signaux par jour")

    reconnect_delay = 10  # Délai initial de reconnexion en secondes
    max_reconnect_delay = 300  # Délai maximum de 5 minutes

    while True:
        mail = None
        try:
            print(f"\n[🔌] {get_current_time()} Connexion à iCloud...")
            mail = imaplib.IMAP4_SSL(IMAP_SERVER)
            mail.login(EMAIL_ACCOUNT, APP_PASSWORD)
            mail.select("inbox")
            
            # Compter les signaux déjà envoyés aujourd'hui
            global signal_count
            signal_count = count_todays_signals(mail)
            print(f"[📊] {get_current_time()} {signal_count} signaux déjà traités aujourd'hui")
            
            print(f"[✅] {get_current_time()} Connecté et prêt à surveiller les emails de TradingView")
            
            # Réinitialiser le délai après une connexion réussie
            reconnect_delay = 10

            while True:
                check_email(mail, webhook_url)
                time.sleep(10)

        except KeyboardInterrupt:
            print("\n[👋] Arrêt du programme...")
            try:
                if mail:
                    mail.close()
                    mail.logout()
                print("[✅] Déconnexion effectuée")
            except:
                pass
            print("[✅] Programme arrêté")
            sys.exit(0)

        except Exception as e:
            print(f"[❌] {get_current_time()} Erreur de connexion : {str(e)}")
            try:
                if mail:
                    mail.logout()
            except:
                pass

            print(f"[🔄] {get_current_time()} Nouvelle tentative dans {reconnect_delay} secondes...")
            time.sleep(reconnect_delay)
            
            # Augmenter le délai de reconnexion de manière exponentielle
            reconnect_delay = min(reconnect_delay * 2, max_reconnect_delay)

if __name__ == "__main__":
    main()
