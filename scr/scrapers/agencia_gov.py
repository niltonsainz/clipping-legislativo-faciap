"""
Scraper especializado para Agência Gov
"""
import re
from datetime import datetime
from bs4 import BeautifulSoup
from typing import List, Dict
from .base import BaseScraper

class AgenciaGovScraper(BaseScraper):
    """Scraper para Agência Gov"""
    
    def __init__(self):
        super().__init__(
            source_name='agencia_gov',
            base_url='https://agenciagov.ebc.com.br',
            news_url='https://agenciagov.ebc.com.br/noticias'
        )
    
    def scrape(self, max_pages: int = 3) -> List[Dict]:
        """Coleta notícias da Agência Gov"""
        print(f"Coletando: {self.source_name}")
        
        all_news = []
        
        for page in range(1, max_pages + 1):
            try:
                # Constrói URL da página
                if page == 1:
                    url = self.news_url
                else:
                    url = f'{self.news_url}?page={page}'
                
                print(f"  Página {page}")
                self._random_delay()
                
                response = self._safe_request(url)
                if not response:
                    continue
                
                soup = BeautifulSoup(response.content, 'html.parser')
                page_news = self._extract_news_from_page(soup)
                
                all_news.extend(page_news)
                print(f"     {len(page_news)} notícias")
                
                # Se não encontrou notícias ou chegou no limite, para
                if len(page_news) == 0 or page >= 2:
                    break
                    
            except Exception as e:
                print(f"     Erro página {page}: {str(e)[:30]}...")
                continue
        
        print(f"  Total Agência Gov: {len(all_news)} notícias")
        return all_news
    
    def _extract_news_from_page(self, soup: BeautifulSoup) -> List[Dict]:
        """Extrai notícias de uma página específica"""
        news_items = []
        links = soup.find_all('a', href=True)
        
        for link in links:
            href = link.get('href', '')
            titulo = ' '.join(link.get_text().strip().split())
            
            # Filtro específico para URLs de notícias da Agência Gov
            if '/noticias/20' in href and re.search(r'/noticias/\d{6}/', href):
                
                if len(titulo) < 20:
                    continue
                
                # Pula títulos genéricos
                skip_titles = ['notícias gov', 'canal gov', 'rádio gov', 'acessar', 'distribuição', 'conteúdo']
                if any(skip in titulo.lower() for skip in skip_titles):
                    continue
                
                full_link = self.base_url + href if href.startswith('/') else href
                
                # Evita duplicatas
                if any(news['link'] == full_link for news in news_items):
                    continue
                
                # Extrai resumo do contexto
                resumo = ""
                parent = link.parent
                if parent:
                    next_elem = parent.find_next('p')
                    if next_elem:
                        resumo = ' '.join(next_elem.get_text().strip().split())[:200]
                
                # Extrai data da URL
                data_pub = None
                date_match = re.search(r'/noticias/(\d{4})(\d{2})/', href)
                if date_match:
                    try:
                        year, month = date_match.groups()
                        data_pub = datetime(int(year), int(month), 1)
                    except:
                        pass
                
                news_item = {
                    'titulo': titulo,
                    'link': full_link,
                    'resumo': resumo,
                    'fonte': self.source_name,
                    'data_coleta': datetime.now().isoformat(),
                    'data_publicacao': data_pub.isoformat() if data_pub else None
                }
                
                news_items.append(news_item)
                
                # Limita notícias por página
                if len(news_items) >= 15:
                    break
        
        return news_items