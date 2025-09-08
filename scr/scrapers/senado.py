"""
Scraper especializado para Senado Federal
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
                # Constrói URL da página
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
                
                # Se não encontrou notícias, para a coleta
                if len(page_news) == 0 and page > 1:
                    break
                    
            except Exception as e:
                print(f"     Erro página {page}: {str(e)[:30]}...")
                continue
        
        print(f"  Total Senado: {len(all_news)} notícias")
        return all_news
    
    def _extract_news_from_page(self, soup: BeautifulSoup) -> List[Dict]:
        """Extrai notícias de uma página específica"""
        news_items = []
        links = soup.find_all('a', href=True)
        
        for link in links:
            href = link.get('href', '')
            
            # Filtro específico para URLs de notícias do Senado
            if '/noticias/materias/' in href and '2025' in href:
                titulo = ' '.join(link.get_text().strip().split())
                
                if len(titulo) < 15:
                    continue
                
                full_link = self.base_url + href if href.startswith('/') else href
                
                # Evita duplicatas
                if any(news['link'] == full_link for news in news_items):
                    continue
                
                # Extrai data de publicação do contexto
                data_pub = None
                parent = link.parent
                if parent:
                    context_text = parent.get_text()
                    data_pub = self._extract_date_from_text(context_text)
                
                news_item = {
                    'titulo': titulo,
                    'link': full_link,
                    'resumo': '',
                    'fonte': self.source_name,
                    'data_coleta': datetime.now().isoformat(),
                    'data_publicacao': data_pub.isoformat() if data_pub else None
                }
                
                news_items.append(news_item)
                
                # Limita notícias por página
                if len(news_items) >= 15:
                    break
        
        return news_items