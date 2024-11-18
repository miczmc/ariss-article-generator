#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
ARISS Article Generator for WordPress

Description:
    Ce script génère des articles WordPress pour les contacts ARISS à partir
    du fichier arissnews.txt. Il extrait les informations pertinentes et
    formate un article prêt à être publié sur le site ARISS.

Source du fichier arissnews.txt:
    Le fichier arissnews.txt est disponible via :
    1. Abonnement à la newsletter ARISS-I sur http://ariss-i.org/mailman/listinfo/ariss-i_ariss-i.org
    2. Consultation directe sur https://www.amsat.org/amsat/ariss/news/arissnews.txt
    
    Le fichier est régulièrement mis à jour avec les nouveaux contacts prévus.
    Il est recommandé de toujours utiliser la version la plus récente.

Dépendances requises:
    - Python 3.9+
    - python-dateutil : pour le parsing des dates
    - tzdata : pour la gestion des fuseaux horaires
    - requests : pour le téléchargement de la newsletter

Installation des dépendances:
    pip install python-dateutil tzdata requests

Usage:
    python ariss_article_generator.py [-f FICHIER] [-u URL] [-d DATE]
    
Arguments:
    -f, --ariss-file : Chemin vers le fichier arissnews.txt
                       (par défaut: arissnews.txt dans le répertoire courant)
    -u, --url-newsletter : URL de la newsletter ARISS
                          (par défaut: https://www.amsat.org/amsat/ariss/news/arissnews.txt)
                          Si spécifié, télécharge la dernière version avant traitement
    -d, --date : Date des contacts à traiter (format: JJ/MM/AAAA)
                 Si non spécifié, traite tous les contacts

Exemple:
    python ariss_article_generator.py -f /chemin/vers/arissnews.txt
    python ariss_article_generator.py -u https://www.amsat.org/amsat/ariss/news/arissnews.txt
    python ariss_article_generator.py -d 25/03/2024

Note:
    Le script nécessite que le fichier arissnews.txt soit formaté selon
    le format standard ARISS. Le fichier doit être encodé en UTF-8.

Author: Michel Nawrocki F1AFW, ARISS
Version: 1.0.0
Date: 2024-03-21
"""

import re
import os
import sys
import argparse
import requests
from datetime import datetime
from dateutil import parser
import locale
from zoneinfo import ZoneInfo

class ArissContact:
    def __init__(self):
        self.school = ""
        self.location = ""
        self.callsign = ""
        self.frequency = ""
        self.astronaut = ""
        self.astronaut_callsign = ""
        self.date_time = None
        self.questions = []
        self.livestream = ""
        self.elevation = ""
        self.contact_type = ""
        self.mentor = ""

class ArissArticleGenerator:
    def __init__(self, text):
        self.raw_text = text
        self.contacts = []
        # Set locale for French date formatting
        try:
            locale.setlocale(locale.LC_TIME, 'fr_FR.UTF-8')
        except locale.Error:
            try:
                locale.setlocale(locale.LC_TIME, 'fr_FR')
            except locale.Error:
                print("Warning: French locale not available. Dates will be in English.")
        self.parse_contacts()

    def parse_contacts(self):
        contact_sections = re.split(r'======================================================================', self.raw_text)
        
        for section in contact_sections:
            if not section.strip():
                continue
                
            contact = ArissContact()
            lines = section.strip().split('\n')
            
            for line in lines:
                if 'direct via' in line.lower() or 'telebridge via' in line.lower():
                    school_info = line.split(',')
                    contact.school = school_info[0].strip()
                    if len(school_info) > 1:
                        contact.location = school_info[1].strip()
                        contact_type_info = school_info[2].strip().split(' via ')
                        contact.contact_type = contact_type_info[0].strip()
                        if len(contact_type_info) > 1:
                            contact.callsign = contact_type_info[1].strip()
                
                elif 'frequency' in line.lower():
                    contact.frequency = line.split('be')[1].strip()
                
                elif 'scheduled crewmember is' in line.lower():
                    crew_info = line.split('is')[1].strip()
                    if ' ' in crew_info:
                        name_parts = crew_info.split(' ')
                        contact.astronaut = ' '.join(name_parts[:-1]) if len(name_parts) > 1 else crew_info
                        contact.astronaut_callsign = name_parts[-1] if len(name_parts) > 1 else ""
                    else:
                        contact.astronaut = crew_info
                
                elif 'Contact is go for:' in line:
                    try:
                        date_time_str = line.split('Contact is go for:')[1].split('UTC')[0].strip()
                        # Parser la date en UTC
                        parsed_dt = parser.parse(date_time_str)
                        # Créer un datetime avec le fuseau horaire UTC
                        contact.date_time = datetime(
                            parsed_dt.year, 
                            parsed_dt.month, 
                            parsed_dt.day,
                            parsed_dt.hour,
                            parsed_dt.minute,
                            parsed_dt.second,
                            tzinfo=ZoneInfo('UTC')
                        )
                        elevation_str = line.split('UTC')[1].strip()
                        if elevation_str:
                            contact.elevation = elevation_str
                    except ValueError as e:
                        print(f"Error parsing date: {e}")
                
                elif 'Watch for the Livestream at' in line:
                    contact.livestream = line.split('at')[1].strip()
                
                elif 'The ARISS mentor is' in line:
                    contact.mentor = line.split('is')[1].strip()
            
            # Extract questions
            questions_started = False
            for line in lines:
                if 'Proposed questions' in line:
                    questions_started = True
                    continue
                if questions_started and line.strip() and not line.startswith('==='):
                    if re.match(r'^\d+\.', line.strip()):
                        contact.questions.append(line.strip())
            
            if contact.school:
                self.contacts.append(contact)

    def generate_wordpress_article(self, contact):
        # Conversion en heure de Paris avec gestion automatique de l'heure d'été/hiver
        paris_time = contact.date_time.astimezone(ZoneInfo('Europe/Paris'))
        
        # Format dates
        date_fr = paris_time.strftime("%d/%m/%Y")
        time_utc = contact.date_time.strftime("%H:%M")
        time_paris = paris_time.strftime("%H:%M")
        
        # Generate article title
        title = f"Contact radioamateur du {date_fr} – {contact.callsign}"
        
        # Generate article content
        content = f"""Un contact radioamateur est prévu le {paris_time.strftime('%A %d %B %Y').lower()} vers {time_utc} UTC ({time_paris} heure de Paris).

Il aura lieu entre l'astronaute {contact.astronaut} ({contact.astronaut_callsign}) et {contact.school} en {contact.location}.

Le contact sera sur {contact.frequency} (+/-3 KHz de doppler) en FM étroite. Il sera {contact.contact_type} par la station {contact.callsign} et donc audible depuis la France.
"""

        if contact.livestream:
            content += f"\nUn livestream sera disponible sur : {contact.livestream}\n"

        content += "\n<!-- more -->\n\nQuestions prévues :\n\n"
        
        for question in contact.questions:
            content += f"{question}\n"
            
        content += "\nL'équipe ARISS se tient à votre disposition pour tout support relatif à l'écoute de ce contact.\n\n73 et bonne écoute"
        
        return {
            'title': title,
            'content': content,
            'category': 'Contact ARISS',
            'status': 'draft'
        }

def download_newsletter(url):
    """
    Télécharge la newsletter depuis l'URL spécifiée.
    
    Args:
        url (str): URL de la newsletter
    
    Returns:
        str: Contenu de la newsletter
        
    Raises:
        Exception: Si le téléchargement échoue
    """
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()  # Lève une exception si le statut n'est pas 200
        return response.text
    except requests.exceptions.RequestException as e:
        raise Exception(f"Erreur lors du téléchargement de la newsletter: {str(e)}")

def parse_date(date_str):
    """
    Convertit une date au format JJ/MM/AAAA en objet datetime.
    
    Args:
        date_str (str): Date au format JJ/MM/AAAA
    
    Returns:
        datetime: Objet datetime correspondant à la date
        
    Raises:
        ValueError: Si le format de la date est incorrect
    """
    try:
        return datetime.strptime(date_str, "%d/%m/%Y")
    except ValueError:
        raise ValueError("Le format de date doit être JJ/MM/AAAA (exemple: 25/03/2024)")

def parse_arguments():
    parser = argparse.ArgumentParser(description='Génère des articles WordPress pour les contacts ARISS')
    parser.add_argument('-f', '--ariss-file', 
                      help='Chemin vers le fichier arissnews.txt (par défaut: arissnews.txt dans le répertoire courant)',
                      default='arissnews.txt')
    parser.add_argument('-u', '--url-newsletter',
                      help='URL de la newsletter ARISS (par défaut: https://www.amsat.org/amsat/ariss/news/arissnews.txt)',
                      nargs='?',  # Rend l'argument optionnel
                      const='https://www.amsat.org/amsat/ariss/news/arissnews.txt',  # Valeur si -u présent sans argument
                      default=None)  # Valeur si -u non présent
    parser.add_argument('-d', '--date',
                      help='Date du contact à traiter (format: JJ/MM/AAAA). Si non spécifié, traite tous les contacts',
                      default=None)
    return parser.parse_args()
    
    parser = argparse.ArgumentParser(description='Génère des articles WordPress pour les contacts ARISS')
    parser.add_argument('-f', '--ariss-file', 
                      help='Chemin vers le fichier arissnews.txt (par défaut: arissnews.txt dans le répertoire courant)',
                      default='arissnews.txt')
    parser.add_argument('-u', '--url-newsletter',
                      help='URL de la newsletter ARISS (si spécifié, télécharge la dernière version)',
                      default=None)
    parser.add_argument('-d', '--date',
                      help='Date du contact à traiter (format: JJ/MM/AAAA). Si non spécifié, traite tous les contacts',
                      default=None)
    return parser.parse_args()

def main():
    # Parse command line arguments
    args = parse_arguments()
    
    # Si une date est spécifiée, la valider
    target_date = None
    if args.date:
        try:
            target_date = parse_date(args.date)
            print(f"Recherche des contacts pour la date du {args.date}")
        except ValueError as e:
            print(f"Erreur: {str(e)}")
            sys.exit(1)
    
    try:
        # Si une URL est spécifiée, télécharger la newsletter
        if args.url_newsletter:
            try:
                print(f"Téléchargement de la newsletter depuis {args.url_newsletter}...")
                text = download_newsletter(args.url_newsletter)
                # Sauvegarder la newsletter téléchargée
                with open(args.ariss_file, 'w', encoding='utf-8') as f:
                    f.write(text)
                print(f"Newsletter sauvegardée dans {args.ariss_file}")
            except Exception as e:
                print(f"Erreur: {str(e)}")
                sys.exit(1)
        # Sinon, vérifier si le fichier existe
        elif not os.path.exists(args.ariss_file):
            print(f"Erreur: Le fichier {args.ariss_file} n'existe pas.")
            sys.exit(1)
        
        # Lire le fichier
        try:
            with open(args.ariss_file, 'r', encoding='utf-8') as file:
                text = file.read()
        except Exception as e:
            print(f"Erreur lors de la lecture du fichier {args.ariss_file}: {str(e)}")
            sys.exit(1)
        
        # Générer les articles
        generator = ArissArticleGenerator(text)
        
        contact_count = 0
        for contact in generator.contacts:
            if contact.date_time:  # Only process contacts with valid dates
                # Si une date cible est spécifiée, vérifier si le contact est à cette date
                if target_date:
                    contact_date = datetime(
                        contact.date_time.year,
                        contact.date_time.month,
                        contact.date_time.day
                    )
                    if contact_date.date() != target_date.date():
                        continue
                
                contact_count += 1
                article = generator.generate_wordpress_article(contact)
                print(f"\n{'=' * 80}\n")
                print(f"Title: {article['title']}")
                print(f"Category: {article['category']}")
                print(f"Status: {article['status']}\n")
                print("Content:")
                print(article['content'])
        
        print(f"\n{'=' * 80}\n")
        if target_date:
            print(f"Nombre de contacts traités pour le {args.date} : {contact_count}")
        else:
            print(f"Nombre total de contacts traités : {contact_count}")
        
        if contact_count == 0:
            if target_date:
                print(f"Aucun contact trouvé pour la date du {args.date}")
            else:
                print("Aucun contact trouvé dans le fichier")
        
    except Exception as e:
        print(f"Erreur lors de la génération des articles: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()
