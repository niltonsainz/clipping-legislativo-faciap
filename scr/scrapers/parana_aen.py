"""
Scraper especializado para Agência de Notícias do Paraná (AEN)
Versão 2.0: Extrai data completa da página de detalhe de cada notícia
"""
import re
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
from typing import List, Dict, Optional
from .base import BaseScraper

class ParanaAENScraper(BaseScraper):
    """Scraper para Agência de Notícias do Paraná com extração de data completa"""
    
    def __init__(self):
        super().__init__(
            source_name='parana_aen',
            base_url='https://www.parana.pr.gov.br',
            news_url='https://www.parana.pr.gov.br/aen/noticias'
        )
    
    def scrape(self, max_pages: int = 3) -> List[Dict]:
        """Coleta notícias da Agência de Notícias do Paraná"""
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
                
                # Se não encontrou notícias, para a coleta
                if len(page_news) == 0 and page > 1:
                    break
                    
            except Exception as e:
                print(f"     Erro página {page}: {str(e)[:30]}...")
                continue
        
        print(f"  Total AEN-PR: {len(all_news)} notícias")
        return all_news
    
    def _extract_news_from_page(self, soup: BeautifulSoup) -> List[Dict]:
        """Extrai notícias de uma página específica"""
        news_items = []
        
        # Busca por artigos com classe 'item item-news'
        articles = soup.find_all('article', class_='item-news')
        
        for article in articles:
            try:
                # Extrai o conteúdo da notícia
                content_div = article.find('div', class_='item-news-content')
                if not content_div:
                    continue
                
                # Extrai o link do título
                titulo_link = content_div.find('h3')
                if not titulo_link:
                    continue
                
                link_elem = titulo_link.find('a', href=True)
                if not link_elem:
                    continue
                
                href = link_elem.get('href', '')
                if not href or '/aen/Noticia/' not in href:
                    continue
                
                titulo = ' '.join(link_elem.get_text().strip().split())
                if len(titulo) < 20:
                    continue
                
                # Converte URL relativa para absoluta
                full_link = self.base_url + href if href.startswith('/') else href
                
                # Evita duplicatas
                if any(news['link'] == full_link for news in news_items):
                    continue
                
                # Extrai categoria (h4)
                categoria_elem = content_div.find('h4')
                categoria = categoria_elem.get_text().strip() if categoria_elem else ''
                
                # Extrai resumo (p)
                resumo_elem = content_div.find('p')
                resumo = ''
                if resumo_elem:
                    resumo_link = resumo_elem.find('a')
                    if resumo_link:
                        resumo = ' '.join(resumo_link.get_text().strip().split())
                    else:
                        resumo = ' '.join(resumo_elem.get_text().strip().split())
                
                # Limita o resumo a 500 caracteres
                if len(resumo) > 500:
                    resumo = resumo[:497] + '...'
                
                # **NOVO**: Extrai data completa da página de detalhe
                data_pub = self._extract_date_from_detail_page(full_link)
                
                news_item = {
                    'titulo': titulo,
                    'link': full_link,
                    'resumo': resumo if resumo else categoria,
                    'fonte': self.source_name,
                    'data_coleta': datetime.now().isoformat(),
                    'data_publicacao': data_pub.isoformat() if data_pub else None
                }
                
                news_items.append(news_item)
                
            except Exception as e:
                print(f"     Erro ao processar artigo: {str(e)[:30]}...")
                continue
        
        return news_items
    
    def _extract_date_from_detail_page(self, news_link: str) -> Optional[datetime]:
        """
        Extrai data completa da página de detalhe da notícia.
        Procura por: <span id="story_date">16/03/2026 - 16:30</span>
        """
        try:
            self._random_delay(min_delay=0.5, max_delay=1.5)  # Delay menor entre requisições
            
            response = self._safe_request(news_link)
            if not response:
                return None
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Procura pelo elemento com id="story_date"
            story_date = soup.find('span', id='story_date')
            if story_date:
                date_text = story_date.get_text().strip()
                # Formato esperado: "16/03/2026 - 16:30"
                return self._parse_date_text(date_text)
            
            # Fallback: procura por data em formato DD/MM/YYYY - HH:MM em qualquer lugar
            date_pattern = r'(\d{2})/(\d{2})/(\d{4})\s*-\s*(\d{2}):(\d{2})'
            match = re.search(date_pattern, soup.get_text())
            if match:
                day = int(match.group(1))
                month = int(match.group(2))
                year = int(match.group(3))
                hour = int(match.group(4))
                minute = int(match.group(5))
                return datetime(year, month, day, hour, minute)
            
        except Exception as e:
            print(f"     Erro ao extrair data da página de detalhe: {str(e)[:30]}...")
        
        return None
    
    def _parse_date_text(self, text: str) -> Optional[datetime]:
        """
        Parseia texto de data em português.
        Formatos suportados:
        - "16/03/2026 - 16:30"
        - "16/03/2026"
        - "9 de Março de 2026"
        - "Ontem", "Anteontem", "Hoje"
        """
        try:
            # Padrão: "16/03/2026 - 16:30" ou "16/03/2026"
            pattern_br = r'(\d{2})/(\d{2})/(\d{4})(?:\s*-\s*(\d{2}):(\d{2}))?'
            match = re.search(pattern_br, text)
            if match:
                day = int(match.group(1))
                month = int(match.group(2))
                year = int(match.group(3))
                hour = int(match.group(4)) if match.group(4) else 0
                minute = int(match.group(5)) if match.group(5) else 0
                return datetime(year, month, day, hour, minute)
            
            # Meses em português
            months_pt = {
                'janeiro': 1, 'fevereiro': 2, 'março': 3, 'abril': 4,
                'maio': 5, 'junho': 6, 'julho': 7, 'agosto': 8,
                'setembro': 9, 'outubro': 10, 'novembro': 11, 'dezembro': 12
            }
            
            # Padrão: "9 de Março de 2026"
            pattern_pt = r'(\d{1,2})\s+de\s+(\w+)\s+de\s+(\d{4})'
            match = re.search(pattern_pt, text)
            if match:
                day = int(match.group(1))
                month_name = match.group(2).lower()
                year = int(match.group(3))
                
                if month_name in months_pt:
                    month = months_pt[month_name]
                    return datetime(year, month, day)
            
            # Padrão: "Ontem", "Anteontem", "Hoje"
            text_lower = text.lower()
            if 'ontem' in text_lower:
                return datetime.now() - timedelta(days=1)
            elif 'anteontem' in text_lower:
                return datetime.now() - timedelta(days=2)
            elif 'hoje' in text_lower:
                return datetime.now()
            
        except Exception as e:
            print(f"     Erro ao parsear data: {str(e)[:30]}...")
        
        return None
