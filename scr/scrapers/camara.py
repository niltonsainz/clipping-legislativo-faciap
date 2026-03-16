"""
Scraper especializado para Câmara dos Deputados
VERSÃO CORRIGIDA - Extração melhorada de data
"""
import re
from datetime import datetime
from bs4 import BeautifulSoup
from typing import List, Dict, Optional
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
        """Extrai notícias de uma página específica usando estrutura corrigida"""
        news_items = []
        
        # NOVA ABORDAGEM: Buscar diretamente pelos artigos com classe 'g-chamada'
        articles = soup.find_all('article', class_='g-chamada')
        
        for article in articles:
            try:
                # Extrai o link do título
                titulo_link = article.find('h3', class_='g-chamada__titulo')
                if not titulo_link:
                    continue
                
                link_elem = titulo_link.find('a', href=True)
                if not link_elem:
                    continue
                
                href = link_elem.get('href', '')
                if not href or '/noticias/' not in href:
                    continue
                
                titulo = ' '.join(link_elem.get_text().strip().split())
                if len(titulo) < 20:
                    continue
                
                full_link = self.base_url + href if href.startswith('/') else href
                
                # Evita duplicatas
                if any(news['link'] == full_link for news in news_items):
                    continue
                
                # CORREÇÃO PRINCIPAL: Extrai data do elemento específico 'g-chamada__data'
                data_pub = None
                data_elem = article.find('span', class_='g-chamada__data')
                if data_elem:
                    data_text = data_elem.get_text().strip()
                    data_pub = self._extract_date_from_text(data_text)
                
                # Extrai categoria/retranca
                retranca_elem = article.find('span', class_='g-chamada__retranca')
                retranca = retranca_elem.get_text().strip() if retranca_elem else ''
                
                news_item = {
                    'titulo': titulo,
                    'link': full_link,
                    'resumo': retranca,  # Usa a categoria como resumo
                    'fonte': self.source_name,
                    'data_coleta': datetime.now().isoformat(),
                    'data_publicacao': data_pub.isoformat() if data_pub else None
                }
                
                news_items.append(news_item)
                
            except Exception as e:
                print(f"     Erro ao processar artigo: {str(e)[:30]}...")
                continue
        
        return news_items
    
    def _extract_date_from_text(self, text: str) -> Optional[datetime]:
        """
        Extrai data do texto em vários formatos
        Sobrescreve o método da classe base para melhor tratamento
        """
        if not text:
            return None
        
        # Padrões específicos para Câmara dos Deputados
        patterns = [
            # Formato: DD/MM/YYYY HH:MM (mais comum na Câmara)
            (r'(\d{2})/(\d{2})/(\d{4})\s+(\d{2}):(\d{2})', '%d/%m/%Y %H:%M'),
            # Formato: DD/MM/YYYY HHhMM
            (r'(\d{2})/(\d{2})/(\d{4})\s+(\d{2})h(\d{2})', '%d/%m/%Y %H:%M'),
            # Formato: DD/MM/YYYY
            (r'(\d{2})/(\d{2})/(\d{4})', '%d/%m/%Y'),
        ]
        
        for pattern, date_format in patterns:
            match = re.search(pattern, text)
            if match:
                try:
                    # Extrai a string de data do match
                    if len(match.groups()) >= 4:
                        # Tem hora
                        date_str = f"{match.group(1)}/{match.group(2)}/{match.group(3)} {match.group(4)}:{match.group(5)}"
                        return datetime.strptime(date_str, '%d/%m/%Y %H:%M')
                    else:
                        # Só tem data
                        date_str = f"{match.group(1)}/{match.group(2)}/{match.group(3)}"
                        return datetime.strptime(date_str, '%d/%m/%Y')
                except Exception as e:
                    print(f"     Erro ao parsear data '{text}': {str(e)[:30]}...")
                    continue
        
        return None
