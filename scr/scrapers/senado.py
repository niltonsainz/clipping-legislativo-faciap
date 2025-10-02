"""
Scraper especializado para Senado Federal - Versão Melhorada com Captura de Datas
"""
import re
from datetime import datetime
from bs4 import BeautifulSoup
from typing import List, Dict, Optional
from .base import BaseScraper

class SenadoScraper(BaseScraper):
    """Scraper para Senado Federal com extração aprimorada de datas"""
    
    def __init__(self):
        super().__init__(
            source_name='senado',
            base_url='https://www12.senado.leg.br',
            news_url='https://www12.senado.leg.br/noticias/ultimas'
        )
    
    def scrape(self, max_pages: int = 3) -> List[Dict]:
        """Coleta notícias do Senado Federal"""
        print(f"🔍 Coletando: {self.source_name}")
        
        all_news = []
        
        for page in range(1, max_pages + 1):
            try:
                if page == 1:
                    url = self.news_url
                else:
                    url = f'{self.news_url}/{page}'
                
                print(f"  📄 Página {page}")
                self._random_delay()
                
                response = self._safe_request(url)
                if not response:
                    continue
                
                soup = BeautifulSoup(response.content, 'html.parser')
                page_news = self._extract_news_from_page(soup)
                
                all_news.extend(page_news)
                print(f"     ✅ {len(page_news)} notícias coletadas")
                
                if len(page_news) == 0 and page > 1:
                    break
                    
            except Exception as e:
                print(f"     ❌ Erro página {page}: {str(e)[:50]}...")
                continue
        
        print(f"  🎯 Total Senado: {len(all_news)} notícias")
        return all_news
    
    def _extract_datetime_from_text(self, text: str) -> Optional[datetime]:
        """
        Extrai data/hora de texto no formato usado pelo Senado
        Formatos suportados: DD/MM/YYYY HHhMM, DD/MM/YYYY HH:MM, DD/MM/YYYY
        """
        if not text:
            return None
            
        # Formato principal: 02/10/2025 15h24
        pattern1 = r'(\d{1,2})/(\d{1,2})/(\d{4})\s+(\d{1,2})h(\d{1,2})'
        match = re.search(pattern1, text)
        if match:
            try:
                day, month, year, hour, minute = match.groups()
                return datetime(int(year), int(month), int(day), int(hour), int(minute))
            except ValueError:
                pass
        
        # Formato alternativo: 02/10/2025 15:24
        pattern2 = r'(\d{1,2})/(\d{1,2})/(\d{4})\s+(\d{1,2}):(\d{1,2})'
        match = re.search(pattern2, text)
        if match:
            try:
                day, month, year, hour, minute = match.groups()
                return datetime(int(year), int(month), int(day), int(hour), int(minute))
            except ValueError:
                pass
        
        # Formato só data: 02/10/2025
        pattern3 = r'(\d{1,2})/(\d{1,2})/(\d{4})'
        match = re.search(pattern3, text)
        if match:
            try:
                day, month, year = match.groups()
                return datetime(int(year), int(month), int(day))
            except ValueError:
                pass
        
        return None
    
    def _find_datetime_in_context(self, element) -> Optional[datetime]:
        """
        Procura data/hora no contexto do elemento (elementos pais, irmãos, etc.)
        """
        # Lista de elementos para verificar
        elements_to_check = []
        
        # 1. Elemento atual
        elements_to_check.append(element)
        
        # 2. Elemento pai direto
        if element.parent:
            elements_to_check.append(element.parent)
        
        # 3. Irmãos anteriores e posteriores
        if element.parent:
            siblings = element.parent.find_all(['div', 'span', 'p', 'time'])
            elements_to_check.extend(siblings)
        
        # 4. Elementos pais até 3 níveis acima
        current = element.parent
        for _ in range(3):
            if current and current.parent:
                current = current.parent
                elements_to_check.append(current)
            else:
                break
        
        # Procura data/hora em todos os elementos
        for elem in elements_to_check:
            if elem:
                text = elem.get_text().strip()
                datetime_found = self._extract_datetime_from_text(text)
                if datetime_found:
                    return datetime_found
        
        return None
    
    def _clean_title(self, title: str) -> str:
        """Remove datas e timestamps do título"""
        if not title:
            return ""
            
        patterns = [
            r'^\d{1,2}/\d{1,2}/\d{4}\s+\d{1,2}h\d{1,2}\s*',
            r'^\d{1,2}/\d{1,2}/\d{4}\s+\d{1,2}:\d{1,2}\s*',
            r'^\d{1,2}/\d{1,2}/\d{4}\s*',
            r'-\s*$',
            r'^\s*[\|•]\s*',
        ]
        
        cleaned_title = title
        for pattern in patterns:
            cleaned_title = re.sub(pattern, '', cleaned_title)
        
        return ' '.join(cleaned_title.strip().split())
    
    def _extract_date_from_url(self, href: str) -> Optional[datetime]:
        """Extrai data da URL como fallback"""
        if not href:
            return None
            
        date_match = re.search(r'/noticias/materias/(\d{4})/(\d{2})/(\d{2})/', href)
        if date_match:
            try:
                year, month, day = date_match.groups()
                return datetime(int(year), int(month), int(day))
            except ValueError:
                pass
        return None
    
    def _extract_news_from_page(self, soup: BeautifulSoup) -> List[Dict]:
        """Extrai notícias de uma página específica com busca aprimorada de datas"""
        news_items = []
        
        # Múltiplos seletores para diferentes estruturas da página
        selectors = [
            'a[href*="/noticias/materias/"]',  # Links diretos para notícias
            '.listagem-noticias a',            # Links em listagem
            '.ultimas-noticias a',             # Links em últimas notícias
            'article a',                       # Links em artigos
            '.conteudo a'                      # Links em conteúdo geral
        ]
        
        found_links = []
        for selector in selectors:
            links = soup.select(selector)
            found_links.extend(links)
        
        # Se não encontrou com seletores específicos, busca geral
        if not found_links:
            found_links = soup.find_all('a', href=True)
        
        print(f"    🔎 Encontrados {len(found_links)} links para análise")
        
        for link in found_links:
            try:
                href = link.get('href', '')
                
                # Filtro para URLs de notícias válidas
                if not ('/noticias/materias/' in href and re.search(r'/202[0-9]/', href)):
                    continue
                
                titulo_raw = link.get_text().strip()
                
                if not titulo_raw or len(titulo_raw) < 15:
                    continue
                
                # Busca data/hora no contexto do elemento
                data_pub = self._find_datetime_in_context(link)
                
                # Se não encontrou, tenta extrair da URL
                if not data_pub:
                    data_pub = self._extract_date_from_url(href)
                
                # Limpa o título
                titulo = self._clean_title(titulo_raw)
                
                if len(titulo) < 15:
                    continue
                
                # Skip títulos irrelevantes
                skip_titles = ['últimas notícias', 'senado notícias', 'veja mais', 'leia mais']
                if any(skip in titulo.lower() for skip in skip_titles):
                    continue
                
                # Monta link completo
                full_link = self.base_url + href if href.startswith('/') else href
                
                # Evita duplicatas
                if any(news['link'] == full_link for news in news_items):
                    continue
                
                # Log de debug
                if data_pub:
                    data_str = data_pub.strftime("%d/%m/%Y %H:%M")
                    print(f"    📅 {data_str} - {titulo[:60]}...")
                else:
                    print(f"    ⚠️  SEM DATA - {titulo[:60]}...")
                
                news_item = {
                    'titulo': titulo,
                    'link': full_link,
                    'resumo': '',
                    'fonte': self.source_name,
                    'data_coleta': datetime.now().isoformat(),
                    'data_publicacao': data_pub.isoformat() if data_pub else None
                }
                
                news_items.append(news_item)
                
                # Limita quantidade por página
                if len(news_items) >= 20:
                    break
                    
            except Exception as e:
                continue
        
        return news_items
