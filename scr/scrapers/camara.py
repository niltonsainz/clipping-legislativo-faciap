"""
Scraper especializado para Câmara dos Deputados
"""
import re
from datetime import datetime
from bs4 import BeautifulSoup
from typing import List, Dict
from .base import BaseScraper

class CamaraScraper(BaseScraper):
    """Scraper para Câmara dos Deputados"""
    
    def __init__(self):
        super().__init__(
            source_name='camara_dos_deputados',
            base_url='https://www.camara.leg.br',
            news_url='https://www.camara.leg.br/noticias/ultimas'
        )
    
    def scrape(self, max_pages: int = 3) -> List[Dict]:
        """Coleta notícias da Câmara dos Deputados"""
        print(f"Coletando: {self.source_name}")
        
        all_news = []
        
        for page in range(1, max_pages + 1):
            try:
                # Constrói URL da página
                if page == 1:
                    url = self.news_url
                else:
                    url = f'{self.news_url}?pagina={page}'
                
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
        
        print(f"  Total Câmara: {len(all_news)} notícias")
        return all_news
    
    def _extract_news_from_page(self, soup: BeautifulSoup) -> List[Dict]:
        """Extrai notícias de uma página específica"""
        news_items = []
        links = soup.find_all('a', href=True)
        
        for link in links:
            href = link.get('href', '')
            
            # Filtro específico para URLs de notícias da Câmara
            if '/noticias/' in href and re.search(r'/noticias/\d{7}-', href):
                titulo = ' '.join(link.get_text().strip().split())
                
                if len(titulo) < 20:
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
                if len(news_items) >= 20:
                    break
        
        return news_items