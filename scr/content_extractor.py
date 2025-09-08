"""
Módulo para extração de conteúdo das notícias
"""
import requests
import time
import random
import re
from bs4 import BeautifulSoup
from typing import Dict, Optional
from scr.config import Config

class ContentExtractor:
    """Classe para extração de conteúdo de notícias"""
    
    def __init__(self):
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
    
    def extract_content(self, url: str, source: str = 'auto') -> Dict:
        """Extrai conteúdo de uma URL específica"""
        try:
            # Delay aleatório para evitar sobrecarga
            time.sleep(random.uniform(1, 2))
            
            response = self.session.get(url, timeout=Config.REQUEST_TIMEOUT)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Remove elementos que atrapalham
            self._remove_unwanted_elements(soup)
            
            # Extrai título
            title = self._extract_title(soup)
            
            # Extrai conteúdo
            content = self._extract_content_text(soup)
            
            # Limpeza final do texto
            content = self._clean_text(content)
            
            word_count = len(content.split()) if content else 0
            success = bool(content and len(content) > 100 and word_count > 30)
            
            return {
                'content': content,
                'title_extracted': title,
                'word_count': word_count,
                'extraction_success': success
            }
            
        except Exception as e:
            return {
                'content': '',
                'title_extracted': '',
                'word_count': 0,
                'extraction_success': False,
                'error': str(e)
            }
    
    def _remove_unwanted_elements(self, soup: BeautifulSoup):
        """Remove elementos desnecessários"""
        unwanted_selectors = [
            'script', 'style', 'nav', 'footer', 'header', 
            '.menu', '.social', '.comments', '.sidebar',
            '.advertisement', '.ads', '.publicity'
        ]
        
        for selector in unwanted_selectors:
            for elem in soup.select(selector):
                elem.decompose()
    
    def _extract_title(self, soup: BeautifulSoup) -> str:
        """Extrai título da página"""
        title_selectors = [
            'h1', 
            '.titulo', 
            '.entry-title', 
            '.post-title',
            '.noticia-titulo',
            '.news-title',
            'title'
        ]
        
        for selector in title_selectors:
            elem = soup.select_one(selector)
            if elem:
                title = elem.get_text().strip()
                if len(title) > 10:
                    return title
        
        return ""
    
    def _extract_content_text(self, soup: BeautifulSoup) -> str:
        """Extrai texto principal da página"""
        content_selectors = [
            '.conteudo',
            '.entry-content', 
            '.post-content',
            '.noticia-content',
            '.news-content',
            'article .content',
            'main article',
            'article',
            '.texto',
            'main'
        ]
        
        # Tenta seletores específicos primeiro
        for selector in content_selectors:
            elem = soup.select_one(selector)
            if elem:
                content = elem.get_text()
                content = re.sub(r'\s+', ' ', content).strip()
                if len(content) > 150:
                    return content
        
        # Fallback: todos os parágrafos
        paragraphs = []
        for p in soup.find_all('p'):
            text = p.get_text().strip()
            if len(text) > 30 and not self._is_unwanted_text(text):
                paragraphs.append(text)
        
        return '\n\n'.join(paragraphs)
    
    def _is_unwanted_text(self, text: str) -> bool:
        """Verifica se o texto deve ser ignorado"""
        unwanted_phrases = [
            'copyright', 'política', 'cookie', 'termos de uso',
            'todos os direitos', 'developed by', 'powered by'
        ]
        
        text_lower = text.lower()
        return any(phrase in text_lower for phrase in unwanted_phrases)
    
    def _clean_text(self, content: str) -> str:
        """Limpa e normaliza o texto extraído"""
        if not content:
            return ""
        
        # Remove quebras de linha excessivas
        content = re.sub(r'\n\s*\n\s*\n+', '\n\n', content)
        
        # Remove caracteres especiais
        content = content.replace('\xa0', ' ')
        content = content.replace('\u00a0', ' ')
        
        # Normaliza espaços
        content = re.sub(r'\s+', ' ', content)
        
        return content.strip()
    
    def close_session(self):
        """Fecha a sessão HTTP"""
        if self.session:
            self.session.close()

# Função utilitária para manter compatibilidade
def extract_content_simple(url: str, source: str = 'auto') -> Dict:
    """Função utilitária para extração simples de conteúdo"""
    extractor = ContentExtractor()
    try:
        return extractor.extract_content(url, source)
    finally:

        extractor.close_session()
