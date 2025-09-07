import csv
import scrapy
import re
from urllib.parse import urlencode
from kbo_project.utils.parsing import clean_num, parse_date

SEARCH_BASE = "https://www.ejustice.just.fgov.be/cgi_t/ts.pl"

class EJusticeSpider(scrapy.Spider):
    name = "ejustice_spider"

    def start_requests(self):
        with open("entreprises.csv", newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                num = clean_num(row.get("EnterpriseNumber", ""))
                
                if not num:
                    continue

                # nettoyage spécifique eJustice
                numero_clean = num.replace(".", "").strip()
                if numero_clean.startswith("0"):
                    numero_clean = numero_clean[1:]

                url = f"https://www.ejustice.just.fgov.be/cgi_tsv/list.pl?btw={numero_clean}"
                self.logger.info(f"Requesting URL: {url}")
                yield scrapy.Request(
                    url, 
                    callback=self.parse_list, 
                    cb_kwargs={"num": num, "numero_clean": numero_clean},
                    dont_filter=True,
                    errback=self.handle_error
                )

    def handle_error(self, failure):
        self.logger.error(f"Request failed: {failure}")
        if hasattr(failure.value, 'response'):
            self.logger.error(f"Response status: {failure.value.response.status}")
        request = failure.request
        if hasattr(request, 'cb_kwargs') and 'num' in request.cb_kwargs:
            num = request.cb_kwargs['num']
            return {
                "EnterpriseNumber": num,
                "source": "ejustice",
                "ejustice_publications": [],
                "error": f"Request failed: {str(failure.value)}"
            }

    def parse_list(self, response, num, numero_clean):
        self.logger.info(f"Parsing list page for {num}, response length: {len(response.text)}")
        
        found_links = False
        
        # Chercher uniquement les liens vers les détails des publications (article.pl seulement)
        all_links = response.css("a")
        for link_elem in all_links:
            href = link_elem.css("::attr(href)").get()
            link_text = link_elem.css("::text").get(default="").strip()
            
            # Ne garder que les liens vers les articles HTML (pas les PDFs)
            if href and href.startswith('article.pl'):
                found_links = True
                
                self.logger.info(f"Found publication link: {href}, title: {link_text}")
                
                yield response.follow(
                    href, 
                    callback=self.parse_detail, 
                    cb_kwargs={
                        "num": num,
                        "title_hint": link_text,
                    },
                    dont_filter=True
                )
            
            # Pour les PDFs, on crée directement un item avec les infos de base
            elif href and href.startswith('/tsv_pdf/'):
                found_links = True
                
                # Extraire la date du nom du fichier PDF
                date_from_path = None
                if '/tsv_pdf/' in href:
                    parts = href.split('/')
                    if len(parts) >= 5:
                        try:
                            year, month, day = parts[2], parts[3], parts[4]
                            date_from_path = f"{day}/{month}/{year}"
                        except:
                            pass
                
                # Récupérer le contexte de la ligne
                parent_text = " ".join(link_elem.xpath("./ancestor::tr//text() | ./ancestor::div//text()").getall()).strip()
                
                pub = {
                    "numero": None,
                    "titre": link_text or "Document PDF",
                    "code": None,
                    "adresse": parent_text if parent_text else None,
                    "type": "PDF",
                    "date": date_from_path,
                    "reference": href.split('/')[-1].replace('.pdf', '') if href else None,
                    "image_url": response.urljoin(href) if href else None,
                    "detail_url": response.urljoin(href) if href else None,
                }
                
                item = {
                    "EnterpriseNumber": num,
                    "source": "ejustice",
                    "ejustice_publications": [pub],
                }
                
                self.logger.info(f"Created PDF item for {num}: {href}")
                yield item
        
        # Vérifier s'il y a une pagination à suivre
        pagination_links = [link for link in response.css("a::attr(href)").getall() 
                          if 'page=' in link and 'btw=' in link and 'language=fr' in link and 'page=0' not in link]
        
        for page_link in pagination_links[:2]:  # Limiter à 2 pages max
            if page_link not in getattr(self, '_visited_pages', set()):
                if not hasattr(self, '_visited_pages'):
                    self._visited_pages = set()
                self._visited_pages.add(page_link)
                
                self.logger.info(f"Following pagination: {page_link}")
                yield response.follow(
                    page_link,
                    callback=self.parse_list,
                    cb_kwargs={"num": num, "numero_clean": numero_clean},
                    dont_filter=True
                )
        
        # Si aucun lien n'est trouvé, créer un item vide
        if not found_links and 'page=' not in response.url:
            self.logger.warning(f"No publications found for {num}")
            
            item = {
                "EnterpriseNumber": num,
                "source": "ejustice",
                "ejustice_publications": [],
            }
            yield item

    def parse_detail(self, response, num, title_hint):
        self.logger.info(f"Parsing detail page for {num}: {response.url}")
        
        # Extraire tout le contenu principal
        main_content = response.css("main.article-text").get()
        if not main_content:
            self.logger.warning(f"No main content found for {num}")
            item = {
                "EnterpriseNumber": num,
                "source": "ejustice",
                "ejustice_publications": [],
            }
            yield item
            return

        # Parser le contenu HTML pour extraire les publications
        publications = self.parse_ejustice_content(main_content, response.url)
        
        if not publications:
            # Si aucune publication n'est trouvée, créer au moins un item avec l'URL
            publications = [{
                "numero": None,
                "titre": title_hint or "Publication eJustice",
                "code": None,
                "adresse": None,
                "type": None,
                "date": None,
                "reference": None,
                "image_url": None,
                "detail_url": response.url,
            }]

        item = {
            "EnterpriseNumber": num,
            "source": "ejustice",
            "ejustice_publications": publications,
        }

        self.logger.info(f"Yielding {len(publications)} publications for {num}")
        yield item

    def parse_ejustice_content(self, html_content, detail_url):
        """Parse le contenu HTML d'eJustice pour extraire les publications individuelles"""
        publications = []
        
        # Diviser le contenu par les séparateurs <hr>
        sections = html_content.split('<hr>')
        
        current_company_name = None
        current_company_type = None
        current_address = None
        
        for section in sections:
            # Garder une version avec HTML pour extraire les noms en bleu
            html_section = section
            
            # Nettoyer la section pour le texte
            clean_section = re.sub(r'<[^>]+>', ' ', section)
            clean_section = re.sub(r'\s+', ' ', clean_section).strip()
            
            if not clean_section or len(clean_section) < 5:
                continue
            
            pub_data = {
                "numero": None,
                "titre": None,
                "code": None,
                "adresse": None,
                "type": None,
                "date": None,
                "reference": None,
                "image_url": None,
                "detail_url": detail_url,
            }
            
            # Détecter le nom de la société (en bleu dans le HTML)
            company_match = re.search(r'<font color="blue">([^<]+)</font>', html_section)
            if company_match:
                current_company_name = company_match.group(1).strip()
                pub_data["titre"] = current_company_name
            
            # Détecter le type de société (après le nom en bleu)
            type_after_name = re.search(r'</font>&nbsp;&nbsp;([A-Z\s]+)', html_section)
            if type_after_name:
                current_company_type = type_after_name.group(1).strip()
            
            # Analyser le texte nettoyé ligne par ligne
            lines = [line.strip() for line in clean_section.split(' ') if line.strip()]
            full_text = clean_section
            
            # Détecter l'adresse (format belge)
            address_patterns = [
                r'([A-Z][A-Z\s\d\.]{5,}\s+\d{4}\s+[A-Z]+)',  # Format: RUE NUMERO CODE_POSTAL VILLE
                r'(STROPKAAI\s*\d+\s*\d{4}\s+GENT)',
                r'(STROPSTRAAT\s*\d+\s*\d{4}\s+GENT)'
            ]
            for pattern in address_patterns:
                addr_match = re.search(pattern, full_text, re.IGNORECASE)
                if addr_match:
                    pub_data["adresse"] = addr_match.group(1).strip()
                    current_address = pub_data["adresse"]
                    break
            
            # Détecter les dates (format YYYY-MM-DD)
            date_match = re.search(r'(\d{4}-\d{2}-\d{2})', full_text)
            if date_match:
                pub_data["date"] = parse_date(date_match.group(1))
            
            # Détecter les références de publication (format: YYYY / numéro)
            ref_patterns = [
                r'(\d{4})\s*/\s*(\d+)',  # 2019 / 0038251
                r'(\d{4}-\d{2}-\d{2})\s*/\s*(\d+)'  # avec date
            ]
            for pattern in ref_patterns:
                ref_match = re.search(pattern, full_text)
                if ref_match:
                    if len(ref_match.groups()) == 2:
                        year_or_date, ref_num = ref_match.groups()
                        # Si c'est juste une année
                        if re.match(r'^\d{4}$', year_or_date):
                            pub_data["reference"] = f"{year_or_date}/{ref_num}"
                        else:
                            # Si c'est une date complète, extraire l'année
                            year = year_or_date.split('-')[0]
                            pub_data["reference"] = f"{year}/{ref_num}"
                    break
            
            # Détecter les codes de publication (format: YYDDD-DDDD-DDD)
            code_patterns = [
                r'(\d{2}\d{3}-\d{4}-\d{3})',  # 84109-0150-024
                r'(\d{5}-\d{4}-\d{3})'        # Variante
            ]
            for pattern in code_patterns:
                code_match = re.search(pattern, full_text)
                if code_match:
                    pub_data["code"] = code_match.group(1)
                    break
            
            # Détecter le type de publication - nettoyer et extraire
            type_keywords = [
                'ONTSLAGEN - BENOEMINGEN',
                'KAPITAAL - AANDELEN',
                'JAARREKENING',
                'COMPTES ANNUELS',
                'STATUTEN',
                'ALGEMENE VERGADERING',
                'RUBRIEK HERSTRUCTURERING',
                'GECONSOLIDEERDE REKENING',
                'COMPTES CONSOLIDES',
                'BENAMING',
                'DOEL'
            ]
            
            # Chercher le type de publication dans le texte
            for keyword in type_keywords:
                if keyword in full_text.upper():
                    # Extraire la partie qui contient le type
                    type_start = full_text.upper().find(keyword)
                    if type_start >= 0:
                        # Prendre du début du mot-clé jusqu'au prochain élément structurel
                        type_end = full_text.find('IMAGE', type_start)
                        if type_end == -1:
                            type_end = len(full_text)
                        
                        potential_type = full_text[type_start:type_end].strip()
                        # Nettoyer les dates et références du type
                        potential_type = re.sub(r'\d{4}-\d{2}-\d{2}', '', potential_type)
                        potential_type = re.sub(r'\d{4}\s*/\s*\d+', '', potential_type)
                        potential_type = re.sub(r'\s+', ' ', potential_type).strip()
                        
                        if potential_type and len(potential_type) > 5:
                            pub_data["type"] = potential_type
                        break
            
            # Utiliser les informations globales si nécessaire
            if not pub_data["titre"] and current_company_name:
                pub_data["titre"] = current_company_name
            
            if not pub_data["adresse"] and current_address:
                pub_data["adresse"] = current_address
            
            # Ajouter la publication si elle contient des informations utiles
            if any([pub_data["titre"], pub_data["type"], pub_data["date"], pub_data["reference"]]):
                publications.append(pub_data)
        
        return publications
