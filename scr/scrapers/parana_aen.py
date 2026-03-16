"""
Scraper especializado para Agência de Notícias do Paraná (AEN)
"""
import re
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
from typing import List, Dict, Optional
from .base import BaseScraper

class ParanaAENScraper(BaseScraper):
    """Scraper para Agência de Notícias do Paraná"""
    
    def __init__(self):
        super().__init__(
            source_name='parana_aen',
            base_url='https://www.parana.pr.gov.br',
            news_url='https://www.parana.pr.gov.br/aen/noticias'
        )
        self.current_date = None  # Rastreia data atual para notícias sem data completa
    
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
                    # Tenta diferentes parâmetros de paginação
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
                
                # Extrai data e hora
                data_pub = self._extract_date_from_article(article)
                
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
    
    def _extract_date_from_article(self, article) -> Optional[datetime]:
        """Extrai data de um artigo da AEN"""
        try:
            # Tenta extrair da tag <time>
            time_elem = article.find('time')
            if time_elem:
                time_text = time_elem.get_text().strip()
                
                # Tenta extrair hora
                hora_match = re.search(r'(\d{2}):(\d{2})', time_text)
                hora = None
                if hora_match:
                    hora = f"{hora_match.group(1)}:{hora_match.group(2)}"
                
                # Tenta extrair data do atributo datetime
                datetime_attr = time_elem.get('datetime')
                if datetime_attr:
                    try:
                        # Formato ISO: YYYY-MM-DDTHH:MM:SS
                        return datetime.fromisoformat(datetime_attr.replace('Z', '+00:00'))
                    except:
                        pass
                
                # Se tem hora mas não tem data, usa data de hoje
                if hora:
                    try:
                        hora_obj = datetime.strptime(hora, '%H:%M')
                        today = datetime.now()
                        return today.replace(hour=hora_obj.hour, minute=hora_obj.minute, second=0, microsecond=0)
                    except:
                        pass
            
            # Alternativa: procura por data formatada próxima ao artigo
            # (pode estar em um elemento anterior com classe 'item-date')
            parent = article.parent
            if parent:
                date_elem = parent.find_previous('article', class_='item-date')
                if date_elem:
                    date_text = date_elem.get_text().strip()
                    return self._parse_date_text(date_text)
            
        except Exception as e:
            print(f"     Erro ao extrair data: {str(e)[:30]}...")
        
        return None
    
    def _parse_date_text(self, text: str) -> Optional[datetime]:
        """Parseia texto de data em português"""
        try:
            # Meses em português
            months_pt = {
                'janeiro': 1, 'fevereiro': 2, 'março': 3, 'abril': 4,
                'maio': 5, 'junho': 6, 'julho': 7, 'agosto': 8,
                'setembro': 9, 'outubro': 10, 'novembro': 11, 'dezembro': 12
            }
            
            # Padrão: "9 de Março de 2026"
            pattern = r'(\d{1,2})\s+de\s+(\w+)\s+de\s+(\d{4})'
            match = re.search(pattern, text)
            if match:
                day = int(match.group(1))
                month_name = match.group(2).lower()
                year = int(match.group(3))
                
                if month_name in months_pt:
                    month = months_pt[month_name]
                    return datetime(year, month, day)
            
            # Padrão: "Ontem", "Anteontem"
            if 'ontem' in text.lower():
                return datetime.now() - timedelta(days=1)
            elif 'anteontem' in text.lower():
                return datetime.now() - timedelta(days=2)
            elif 'hoje' in text.lower():
                return datetime.now()
            
        except Exception as e:
            print(f"     Erro ao parsear data em português: {str(e)[:30]}...")
        
        return None
