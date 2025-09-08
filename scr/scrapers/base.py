"""
Classe base para scrapers com funcionalidades comuns
"""
import requests
import time
import random
import re
from datetime import datetime
from bs4 import BeautifulSoup
from typing import List, Dict, Optional
from ..config import Config

class BaseScraper:
    """Classe base para todos os scrapers"""
    
    def __init__(self, source_name: str, base_url: str, news_url: str):
        self.source_name = source_name
        self.base_url = base_url
        self.news_url = news_url
        self.session = self._create_session()
    
    def _create_session(self) -> requests.Session:
        """Cria sessão HTTP otimizada"""
        session = requests.Session()
        session.headers.update({
            'User-Agent': Config.USER_AGENT,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'pt-BR,pt;q=0.8,en;q=0.6',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive'
        })
        return session
    
    def _safe_request(self, url: str, timeout: Optional[int] = None) -> Optional[requests.Response]:
        """Request com tratamento de erro"""
        try:
            timeout = timeout or Config.REQUEST_TIMEOUT
            response = self.session.get(url, timeout=timeout)
            response.raise_for_status()
            return response
        except Exception as e:
            print(f"Erro request {url[:50]}...: {str(e)[:30]}...")
            return None
    
    def _random_delay(self):
        """Aplica delay aleatório entre requests"""
        delay = random.uniform(Config.MIN_DELAY, Config.MAX_DELAY)
        time.sleep(delay)
    
    def _extract_date_from_text(self, text: str) -> Optional[datetime]:
        """Extrai data do texto em vários formatos"""
        patterns = [
            r'(\d{2}/\d{2}/\d{4})\s+(\d{2}:\d{2})',
            r'(\d{2}/\d{2}/\d{4})\s+(\d{2}h\d{2})',
            r'(\d{2}/\d{2}/\d{4})',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                try:
                    if len(match.groups()) == 2:
                        date_str = f"{match.group(1)} {match.group(2).replace('h', ':')}"
                        return datetime.strptime(date_str, '%d/%m/%Y %H:%M')
                    else:
                        return datetime.strptime(match.group(1), '%d/%m/%Y')
                except:
                    continue
        return None
    
    def scrape(self, max_pages: int = 3) -> List[Dict]:
        """Método abstrato - deve ser implementado pelas classes filhas"""
        raise NotImplementedError("Método scrape deve ser implementado pela classe filha")
    
    def close_session(self):
        """Fecha a sessão HTTP"""
        if self.session:
            self.session.close()