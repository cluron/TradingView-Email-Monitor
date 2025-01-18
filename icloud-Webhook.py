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
from config import *

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

def check_email(mail, webhook_url):
    try:
        # Utilisation de \r pour rester sur la même ligne et effacer le contenu précédent
        print("\r[🔍] Surveillance active... ", end="", flush=True)
        
        try:
            # Vérifier que la connexion est toujours active
            mail.noop()
        except:
            print("\n[🔄] La connexion semble inactive, déclenchement d'une reconnexion...")
            raise imaplib.IMAP4.error("Connection check failed")

        status, messages = mail.search(None, 'UNSEEN FROM "noreply@tradingview.com"')

        if status != "OK" or not messages[0]:
            # Ajoute un point pour montrer que le script est actif
            print(".", end="", flush=True)
            return

        # Récupérer tous les IDs d'emails non lus
        email_ids = messages[0].split()
        if len(email_ids) > 1:
            print(f"\n[⚠️] Attention: {len(email_ids)} emails non lus détectés")

        # On va d'abord identifier le dernier email avec un signal valide
        last_valid_signal = None
        last_valid_id = None
        
        # Parcourir les emails dans l'ordre inverse (du plus récent au plus ancien)
        for e_id in reversed(email_ids):
            try:
                print(f"\n[📧] Analyse de l'email ID : {e_id}")
                
                # Récupération du message
                status, msg_data = mail.fetch(e_id, '(BODY[])')
                
                if not msg_data or not msg_data[0]:
                    print("[❌] msg_data est vide ou invalide")
                    continue

                # Extraction du contenu brut de l'email
                raw_email = None
                for part in msg_data:
                    if isinstance(part, tuple) and len(part) > 1:
                        raw_email = part[1]
                        break

                if not raw_email or not isinstance(raw_email, bytes):
                    print(f"[❌] Format invalide : raw_email est de type {type(raw_email)} (attendu: bytes)")
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
                    print("[❌] Aucun contenu text/plain trouvé dans l'email")
                    continue

                signal = payload.decode('utf-8').strip()
                
                # Vérification du signal
                if "BUY" in signal:
                    signal = "BUY"
                    last_valid_signal = signal
                    last_valid_id = e_id
                    print(f"[✅] Signal BUY valide trouvé dans l'email {e_id}")
                    break  # On a trouvé notre dernier signal valide
                elif "SELL" in signal:
                    signal = "SELL"
                    last_valid_signal = signal
                    last_valid_id = e_id
                    print(f"[✅] Signal SELL valide trouvé dans l'email {e_id}")
                    break  # On a trouvé notre dernier signal valide
                else:
                    print(f"[❌] Pas de signal valide dans cet email")

            except Exception as e:
                print(f"[❌] Erreur lors de l'analyse de l'email {e_id}: {e}")
                continue

        # Marquer tous les autres emails comme lus
        for e_id in email_ids:
            if e_id != last_valid_id:
                try:
                    mail.store(e_id, "+FLAGS", "\\Seen")
                    print(f"[✓] Email {e_id} marqué comme lu (ignoré)")
                except Exception as e:
                    print(f"[❌] Erreur lors du marquage de l'email {e_id}: {e}")

        # Traiter uniquement le dernier signal valide si on en a trouvé un
        if last_valid_signal and last_valid_id:
            print(f"\n[🎯] Traitement du dernier signal valide : {last_valid_signal} (Email ID: {last_valid_id})")
            payload = {"side": last_valid_signal}
            
            try:
                # Envoi au webhook
                response = requests.post(webhook_url, json=payload, headers=HEADERS)
                if response.status_code == 200:
                    print(f"[🚀] Signal envoyé avec succès (code: {response.status_code})")
                    # Marquer comme lu uniquement si l'envoi a réussi
                    mail.store(last_valid_id, "+FLAGS", "\\Seen")
                    print("[✓] Email du signal traité marqué comme lu")
                else:
                    print(f"[❌] Erreur lors de l'envoi : code {response.status_code}")
                    print(f"[📝] Réponse : {response.text}")
            except requests.exceptions.ConnectionError:
                print(f"[❌] Impossible de se connecter au serveur webhook : {webhook_url}")
                print("[💡] Vérifiez que le serveur est bien en ligne et accessible")
            except Exception as e:
                print(f"[❌] Erreur lors de l'envoi au webhook : {str(e)}")

    except Exception as e:
        print(f"\n[❌] Erreur lors de la vérification des emails : {e}")
        print(f"[📝] Détails de l'erreur : {str(e)}")
        raise  # Propager l'erreur pour déclencher une reconnexion

def main():
    # Parse les arguments
    args = parse_arguments()
    webhook_url = get_webhook_url(args.mode)
    print(f"[⚙️] Mode du serveur webhook : {args.mode} ({webhook_url})")

    reconnect_delay = 10  # Délai initial de reconnexion en secondes
    max_reconnect_delay = 300  # Délai maximum de 5 minutes

    while True:
        mail = None
        try:
            print("\n[🔌] Connexion à iCloud...")
            mail = imaplib.IMAP4_SSL(IMAP_SERVER)
            mail.login(EMAIL_ACCOUNT, APP_PASSWORD)
            mail.select("inbox")
            print("[✅] Connecté et prêt à surveiller les emails de TradingView")
            
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
            print(f"[❌] Erreur de connexion : {str(e)}")
            try:
                if mail:
                    mail.logout()
            except:
                pass

            print(f"[🔄] Nouvelle tentative dans {reconnect_delay} secondes...")
            time.sleep(reconnect_delay)
            
            # Augmenter le délai de reconnexion de manière exponentielle
            reconnect_delay = min(reconnect_delay * 2, max_reconnect_delay)

if __name__ == "__main__":
    main()
