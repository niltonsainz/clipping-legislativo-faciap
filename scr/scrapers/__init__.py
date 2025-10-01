"""
Módulo de scrapers para coleta de notícias legislativas
"""
from .base import BaseScraper
from .camara import CamaraScraper
from .senado import SenadoScraper
from .agencia_gov import AgenciaGovScraper

__all__ = [
    'BaseScraper',
    'CamaraScraper', 
    'SenadoScraper',
    'AgenciaGovScraper'
]

# Mapeamento de scrapers disponíveis
AVAILABLE_SCRAPERS = {
    'camara': CamaraScraper,
    'senado': SenadoScraper,
    'agencia_gov': AgenciaGovScraper
}

def get_scraper(source_name: str):
    """Retorna instância do scraper para a fonte especificada"""
    if source_name not in AVAILABLE_SCRAPERS:
        raise ValueError(f"Scraper '{source_name}' não disponível. Opções: {list(AVAILABLE_SCRAPERS.keys())}")
    
    return AVAILABLE_SCRAPERS[source_name]()

def get_all_scrapers():
    """Retorna todas as instâncias de scrapers disponíveis"""

    return {name: scraper_class() for name, scraper_class in AVAILABLE_SCRAPERS.items()}
