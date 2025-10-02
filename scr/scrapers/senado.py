"""
Scraper especializado para Senado Federal - Captura correta de datas
"""
import re
from datetime import datetime
from bs4 import BeautifulSoup
from typing import List, Dict, Optional
from .base import BaseScraper

class SenadoScraper(BaseScraper):
    """Scraper para Senado Federal com extração precisa de datas"""
    
    def __init__(self):
        super().__init__(
            source_name='senado',
            base_url='https://www12.senado.leg.br',
            news_url='https://www12.senado.leg.br/noticias/ultimas'
        )
    
    def scrape(self, max_pages: int = 3) -> List[Dict]:
        """Coleta notícias do Senado Federal"""
        print(f"Coletando: {self.source_name}")
        
        all_news = []
        
        for page in range(1, max_pages + 1):
            try:
                if page == 1:
                    url = self.news_url
                else:
                    url = f'{self.news_url}/{page}'
                
                print(f"  Página {page}")
                self._random_delay()
                
                response = self._safe_request(url)
                if not response:
                    continue
                
                soup = BeautifulSoup(response.content, 'html.parser')
                page_news = self._extract_news_from_page(soup)
                
                all_news.extend(page_news)
                print(f"     {len(page_news)} notícias")
                
                if len(page_news) == 0 and page > 1:
                    break
                    
            except Exception as e:
                print(f"     Erro página {page}: {str(e)[:30]}...")
                continue
        
        print(f"  Total Senado: {len(all_news)} notícias")
        return all_news
    
    def _parse_datetime_senado(self, date_str: str) -> Optional[datetime]:
        """
        Converte string de data do Senado para datetime
        Formato: DD/MM/YYYY HHhMM (ex: 02/10/2025 17h07)
        """
        if not date_str:
            return None
        
        # Remove espaços extras
        date_str = date_str.strip()
        
        # Formato principal: DD/MM/YYYY HHhMM
        pattern = r'^(\d{1,2})/(\d{1,2})/(\d{4})\s+(\d{1,2})h(\d{1,2})$'
        match = re.match(pattern, date_str)
        
        if match:
            try:
                day, month, year, hour, minute = match.groups()
                return datetime(
                    int(year), 
                    int(month), 
                    int(day), 
                    int(hour), 
                    int(minute)
                )
            except ValueError as e:
                print(f"     Erro ao converter data '{date_str}': {e}")
                return None
        
        return None
    
    def _find_date_span_near_link(self, link_element) -> Optional[str]:
        """
        Procura pelo span com a data próximo ao link
        O span tem classe 'text-muted' e contém a data no formato DD/MM/YYYY HHhMM
        """
        # Estratégia 1: Procura no elemento pai direto
        parent = link_element.parent
        if parent:
            # Procura spans com classe text-muted no mesmo container
            date_spans = parent.find_all('span', class_=re.compile(r'text-muted'))
            for span in date_spans:
                text = span.get_text().strip()
                # Verifica se tem formato de data
                if re.match(r'\d{2}/\d{2}/\d{4}\s+\d{1,2}h\d{2}', text):
                    return text
        
        # Estratégia 2: Procura nos elementos anteriores (siblings)
        for sibling in link_element.find_previous_siblings():
            if sibling.name == 'span':
                text = sibling.get_text().strip()
                if re.match(r'\d{2}/\d{2}/\d{4}\s+\d{1,2}h\d{2}', text):
                    return text
            # Procura dentro do sibling
            date_spans = sibling.find_all('span', class_=re.compile(r'text-muted'))
            for span in date_spans:
                text = span.get_text().strip()
                if re.match(r'\d{2}/\d{2}/\d{4}\s+\d{1,2}h\d{2}', text):
                    return text
        
        # Estratégia 3: Sobe até o <li> e procura lá
        li_parent = link_element.find_parent('li')
        if li_parent:
            date_spans = li_parent.find_all('span', class_=re.compile(r'text-muted'))
            for span in date_spans:
                text = span.get_text().strip()
                if re.match(r'\d{2}/\d{2}/\d{4}\s+\d{1,2}h\d{2}', text):
                    return text
        
        return None
    
    def _clean_title(self, title: str) -> str:
        """Remove elementos indesejados do título"""
        if not title:
            return ""
        
        # Remove apenas ícones e espaços extras
        patterns = [
            r'^\s*[\|•]\s*',  # Ícones no início
            r'\s+',           # Múltiplos espaços
        ]
        
        cleaned_title = title
        for pattern in patterns:
            if pattern == r'\s+':
                cleaned_title = re.sub(pattern, ' ', cleaned_title)
            else:
                cleaned_title = re.sub(pattern, '', cleaned_title)
        
        return cleaned_title.strip()
    
    def _extract_date_from_url(self, href: str) -> Optional[datetime]:
        """Extrai data da URL como último recurso"""
        if not href:
            return None
            
        date_match = re.search(r'/(\d{4})/(\d{2})/(\d{2})/', href)
        if date_match:
            try:
                year, month, day = date_match.groups()
                return datetime(int(year), int(month), int(day))
            except ValueError:
                pass
        return None
    
    def _extract_news_from_page(self, soup: BeautifulSoup) -> List[Dict]:
        """Extrai notícias de uma página específica"""
        news_items = []
        
        # Encontra todos os links de notícias
        links = soup.find_all('a', href=re.compile(r'/noticias/materias/'))
        
        for link in links:
            try:
                href = link.get('href', '')
                
                # Filtro para URLs válidas
                if not re.search(r'/noticias/materias/\d{4}/\d{2}/\d{2}/', href):
                    continue
                
                # Extrai título
                titulo_raw = link.get_text().strip()
                
                if not titulo_raw or len(titulo_raw) < 15:
                    continue
                
                # Procura a data no span próximo ao link
                date_str = self._find_date_span_near_link(link)
                data_pub = None
                
                if date_str:
                    data_pub = self._parse_datetime_senado(date_str)
                
                # Se não encontrou, tenta extrair da URL
                if not data_pub:
                    data_pub = self._extract_date_from_url(href)
                
                # Limpa o título
                titulo = self._clean_title(titulo_raw)
                
                if len(titulo) < 15:
                    continue
                
                # Pula títulos irrelevantes
                skip_titles = ['últimas notícias', 'veja mais', 'leia mais', 'todas as notícias']
                if any(skip in titulo.lower() for skip in skip_titles):
                    continue
                
                # Monta link completo
                full_link = self.base_url + href if href.startswith('/') else href
                
                # Evita duplicatas
                if any(news['link'] == full_link for news in news_items):
                    continue
                
                news_item = {
                    'titulo': titulo,
                    'link': full_link,
                    'resumo': '',
                    'fonte': self.source_name,
                    'data_coleta': datetime.now().isoformat(),
                    'data_publicacao': data_pub.isoformat() if data_pub else None
                }
                
                news_items.append(news_item)
                
                # Limita por página
                if len(news_items) >= 15:
                    break
                    
            except Exception as e:
                continue
        
        return news_items
