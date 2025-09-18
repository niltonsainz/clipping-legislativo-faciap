"""
Scraper especializado para Agência Gov - Versão Melhorada
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
    
    def _clean_title(self, title: str) -> str:
        """Remove datas e timestamps do título"""
        # Remove padrões de data/hora no início do título
        patterns = [
            r'^\d{2}/\d{2}/\d{4}\s+\d{2}:\d{2}\s+',  # DD/MM/YYYY HH:MM
            r'^\d{2}/\d{2}/\d{4}\s+',                 # DD/MM/YYYY
            r'^\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}\s+',  # YYYY-MM-DD HH:MM:SS
            r'^\d{4}-\d{2}-\d{2}\s+',                 # YYYY-MM-DD
        ]
        
        cleaned_title = title
        for pattern in patterns:
            cleaned_title = re.sub(pattern, '', cleaned_title)
        
        return cleaned_title.strip()
    
    def _extract_date_from_title(self, title: str) -> datetime:
        """Extrai data do início do título se existir"""
        # Procura por data no formato DD/MM/YYYY HH:MM
        date_match = re.match(r'^(\d{2})/(\d{2})/(\d{4})\s+(\d{2}):(\d{2})', title)
        if date_match:
            try:
                day, month, year, hour, minute = date_match.groups()
                return datetime(int(year), int(month), int(day), int(hour), int(minute))
            except ValueError:
                pass
        
        # Procura por data no formato DD/MM/YYYY
        date_match = re.match(r'^(\d{2})/(\d{2})/(\d{4})', title)
        if date_match:
            try:
                day, month, year = date_match.groups()
                return datetime(int(year), int(month), int(day))
            except ValueError:
                pass
        
        return None
    
    def _extract_date_from_url(self, href: str) -> datetime:
        """Extrai data da URL no formato /noticias/YYYYMM/DD/"""
        # Tenta primeiro o formato mais específico
        date_match = re.search(r'/noticias/(\d{4})(\d{2})(\d{2})/', href)
        if date_match:
            try:
                year, month, day = date_match.groups()
                return datetime(int(year), int(month), int(day))
            except ValueError:
                pass
        
        # Formato alternativo /noticias/YYYY/MM/DD/
        date_match = re.search(r'/noticias/(\d{4})/(\d{2})/(\d{2})/', href)
        if date_match:
            try:
                year, month, day = date_match.groups()
                return datetime(int(year), int(month), int(day))
            except ValueError:
                pass
        
        # Formato apenas ano e mês
        date_match = re.search(r'/noticias/(\d{4})(\d{2})/', href)
        if date_match:
            try:
                year, month = date_match.groups()
                return datetime(int(year), int(month), 1)
            except ValueError:
                pass
        
        return None
    
    def _extract_news_from_page(self, soup: BeautifulSoup) -> List[Dict]:
        """Extrai notícias de uma página específica"""
        news_items = []
        
        # Procura por diferentes estruturas de artigos/notícias
        article_selectors = [
            'article',
            '.news-item',
            '.noticia',
            '.post',
            'div[class*="news"]',
            'div[class*="article"]'
        ]
        
        articles = []
        for selector in article_selectors:
            articles.extend(soup.select(selector))
        
        # Se não encontrar artigos estruturados, usa links como fallback
        if not articles:
            links = soup.find_all('a', href=True)
            for link in links:
                href = link.get('href', '')
                
                # Filtro específico para URLs de notícias da Agência Gov
                if '/noticias/20' in href and re.search(r'/noticias/\d{6}/', href):
                    articles.append(link)
        
        for item in articles:
            try:
                # Extrai link
                if item.name == 'a':
                    link_elem = item
                else:
                    link_elem = item.find('a', href=True)
                
                if not link_elem:
                    continue
                
                href = link_elem.get('href', '')
                if not href:
                    continue
                
                # Filtra URLs relevantes
                if not ('/noticias/20' in href and re.search(r'/noticias/\d{6}/', href)):
                    continue
                
                # Extrai título
                titulo_raw = ''
                if item.name == 'a':
                    titulo_raw = item.get_text().strip()
                else:
                    # Procura por título em diferentes elementos
                    title_selectors = ['h1', 'h2', 'h3', '.title', '.headline', 'a']
                    for selector in title_selectors:
                        title_elem = item.find(selector)
                        if title_elem:
                            titulo_raw = title_elem.get_text().strip()
                            break
                
                if not titulo_raw or len(titulo_raw) < 20:
                    continue
                
                # Limpa o título
                titulo = ' '.join(self._clean_title(titulo_raw).split())
                
                # Pula títulos genéricos
                skip_titles = ['notícias gov', 'canal gov', 'rádio gov', 'acessar', 'distribuição', 'conteúdo']
                if any(skip in titulo.lower() for skip in skip_titles):
                    continue
                
                # Monta link completo
                full_link = self.base_url + href if href.startswith('/') else href
                
                # Evita duplicatas
                if any(news['link'] == full_link for news in news_items):
                    continue
                
                # Extrai resumo
                resumo = self._extract_summary(item)
                
                # Extrai data de publicação
                data_pub = self._extract_date_from_title(titulo_raw)
                if not data_pub:
                    data_pub = self._extract_date_from_url(href)
                
                # Procura por data em elementos específicos
                if not data_pub:
                    date_selectors = ['.date', '.published', '.timestamp', 'time']
                    for selector in date_selectors:
                        date_elem = item.find(selector)
                        if date_elem:
                            date_text = date_elem.get_text().strip()
                            data_pub = self._parse_date_text(date_text)
                            if data_pub:
                                break
                
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
                    
            except Exception as e:
                print(f"     Erro ao processar item: {str(e)[:50]}...")
                continue
        
        return news_items
    
    def _extract_summary(self, item) -> str:
        """Extrai resumo da notícia"""
        resumo = ""
        
        # Procura por resumo em diferentes elementos
        summary_selectors = [
            '.summary',
            '.excerpt',
            '.description',
            '.lead',
            'p',
            '.content p'
        ]
        
        for selector in summary_selectors:
            summary_elem = item.find(selector)
            if summary_elem:
                resumo = ' '.join(summary_elem.get_text().strip().split())
                if len(resumo) > 50:  # Só usa se tiver conteúdo significativo
                    break
        
        # Se não encontrou, procura no contexto
        if not resumo and item.parent:
            next_elem = item.parent.find_next('p')
            if next_elem:
                resumo = ' '.join(next_elem.get_text().strip().split())
        
        return resumo[:200] if resumo else ""
    
    def _parse_date_text(self, date_text: str) -> datetime:
        """Tenta fazer parse de texto de data"""
        date_patterns = [
            r'(\d{2})/(\d{2})/(\d{4})\s+(\d{2}):(\d{2})',  # DD/MM/YYYY HH:MM
            r'(\d{2})/(\d{2})/(\d{4})',                     # DD/MM/YYYY
            r'(\d{4})-(\d{2})-(\d{2})\s+(\d{2}):(\d{2}):(\d{2})',  # YYYY-MM-DD HH:MM:SS
            r'(\d{4})-(\d{2})-(\d{2})',                     # YYYY-MM-DD
        ]
        
        for pattern in date_patterns:
            match = re.search(pattern, date_text)
            if match:
                try:
                    groups = match.groups()
                    if len(groups) == 5:  # DD/MM/YYYY HH:MM
                        day, month, year, hour, minute = groups
                        return datetime(int(year), int(month), int(day), int(hour), int(minute))
                    elif len(groups) == 3:  # DD/MM/YYYY ou YYYY-MM-DD
                        if '/' in date_text:  # DD/MM/YYYY
                            day, month, year = groups
                            return datetime(int(year), int(month), int(day))
                        else:  # YYYY-MM-DD
                            year, month, day = groups
                            return datetime(int(year), int(month), int(day))
                    elif len(groups) == 6:  # YYYY-MM-DD HH:MM:SS
                        year, month, day, hour, minute, second = groups
                        return datetime(int(year), int(month), int(day), int(hour), int(minute), int(second))
                except ValueError:
                    continue
        
        return None
