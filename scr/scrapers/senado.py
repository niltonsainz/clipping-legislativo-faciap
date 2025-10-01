"""
Scraper especializado para Senado Federal - Versão Melhorada
"""
import re
from datetime import datetime
from bs4 import BeautifulSoup
from typing import List, Dict
from .base import BaseScraper

class SenadoScraper(BaseScraper):
    """Scraper para Senado Federal"""
    
    def __init__(self):
        super().__init__(
            source_name='senado_federal',
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
    
    def _clean_title(self, title: str) -> str:
        """Remove datas e timestamps do título"""
        patterns = [
            r'^\d{2}/\d{2}/\d{4}\s+\d{2}h\d{2}\s+',
            r'^\d{2}/\d{2}/\d{4}\s+\d{2}:\d{2}\s+',
            r'^\d{2}/\d{2}/\d{4}\s+',
            r'-\s*$',
        ]
        
        cleaned_title = title
        for pattern in patterns:
            cleaned_title = re.sub(pattern, '', cleaned_title)
        
        return cleaned_title.strip()
    
    def _extract_date_from_title(self, title: str) -> datetime:
        """Extrai data do início do título se existir"""
        date_match = re.match(r'^(\d{2})/(\d{2})/(\d{4})\s+(\d{2})h(\d{2})', title)
        if date_match:
            try:
                day, month, year, hour, minute = date_match.groups()
                return datetime(int(year), int(month), int(day), int(hour), int(minute))
            except ValueError:
                pass
        
        date_match = re.match(r'^(\d{2})/(\d{2})/(\d{4})', title)
        if date_match:
            try:
                day, month, year = date_match.groups()
                return datetime(int(year), int(month), int(day))
            except ValueError:
                pass
        
        return None
    
    def _extract_date_from_url(self, href: str) -> datetime:
        """Extrai data da URL"""
        date_match = re.search(r'/noticias/materias/(\d{4})/(\d{2})/(\d{2})/', href)
        if date_match:
            try:
                year, month, day = date_match.groups()
                return datetime(int(year), int(month), int(day))
            except ValueError:
                pass
        return None
    
    def _extract_date_from_text(self, text: str) -> datetime:
        """Extrai data de um texto"""
        date_match = re.search(r'(\d{2})/(\d{2})/(\d{4})\s+(\d{2})h(\d{2})', text)
        if date_match:
            try:
                day, month, year, hour, minute = date_match.groups()
                return datetime(int(year), int(month), int(day), int(hour), int(minute))
            except ValueError:
                pass
        return None
    
    def _extract_news_from_page(self, soup: BeautifulSoup) -> List[Dict]:
        """Extrai notícias de uma página específica"""
        news_items = []
        links = soup.find_all('a', href=True)
        
        for link in links:
            try:
                href = link.get('href', '')
                
                if not ('/noticias/materias/' in href and re.search(r'/202[0-9]/', href)):
                    continue
                
                titulo_raw = link.get_text().strip()
                
                if not titulo_raw or len(titulo_raw) < 15:
                    continue
                
                context_text = link.parent.get_text() if link.parent else ''
                
                data_pub = self._extract_date_from_title(titulo_raw)
                if not data_pub and context_text:
                    data_pub = self._extract_date_from_text(context_text)
                if not data_pub:
                    data_pub = self._extract_date_from_url(href)
                
                titulo = ' '.join(self._clean_title(titulo_raw).split())
                
                if len(titulo) < 15:
                    continue
                
                skip_titles = ['últimas notícias', 'senado notícias', 'veja mais']
                if any(skip in titulo.lower() for skip in skip_titles):
                    continue
                
                full_link = self.base_url + href if href.startswith('/') else href
                
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
                
                if len(news_items) >= 15:
                    break
                    
            except Exception as e:
                continue
        
        return news_items
