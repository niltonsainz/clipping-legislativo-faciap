"""
Configurações centralizadas do sistema FACIAP
"""
import os
from pathlib import Path

class Config:
    # Diretórios base
    BASE_DIR = Path(__file__).parent.parent
    DATA_DIR = BASE_DIR / 'data'
    LOGS_DIR = BASE_DIR / 'logs'
    
    # Database
    DATABASE_PATH = os.getenv('DATABASE_PATH', str(DATA_DIR / 'clipping_faciap.db'))
    
    # Scraping
    MAX_PAGES_PER_SOURCE = int(os.getenv('MAX_PAGES_PER_SOURCE', '5'))
    REQUEST_TIMEOUT = int(os.getenv('REQUEST_TIMEOUT', '10'))
    MIN_DELAY = float(os.getenv('MIN_DELAY', '1.0'))
    MAX_DELAY = float(os.getenv('MAX_DELAY', '3.0'))
    USER_AGENT = os.getenv('USER_AGENT', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
    
    # Content Extraction
    MAX_EXTRACTION_PER_RUN = int(os.getenv('MAX_EXTRACTION_PER_RUN', '50'))
    BATCH_SIZE = int(os.getenv('BATCH_SIZE', '10'))
    
    # Scoring
    DICTIONARY_FILE = os.getenv('DICTIONARY_FILE', str(DATA_DIR / 'dicionario_faciap.csv'))
    MAX_SCORING_PER_RUN = int(os.getenv('MAX_SCORING_PER_RUN', '100'))
    
    # API
    API_HOST = os.getenv('API_HOST', '0.0.0.0')
    API_PORT = int(os.getenv('API_PORT', '5000'))
    API_DEBUG = os.getenv('API_DEBUG', 'False').lower() == 'true'
    
    # Automation
    SCHEDULE_ENABLED = os.getenv('SCHEDULE_ENABLED', 'True').lower() == 'true'
    SCHEDULE_TIMES = os.getenv('SCHEDULE_TIMES', '08:00,14:00,20:00').split(',')
    RETENTION_DAYS = int(os.getenv('RETENTION_DAYS', '60'))
    
    # Monitoring
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    LOG_MAX_SIZE = int(os.getenv('LOG_MAX_SIZE', '10485760'))  # 10MB
    LOG_BACKUP_COUNT = int(os.getenv('LOG_BACKUP_COUNT', '5'))

# Configurações específicas por fonte
SOURCES_CONFIG = {
    'camara': {
        'name': 'Câmara dos Deputados',
        'base_url': 'https://www.camara.leg.br',
        'news_url': 'https://www.camara.leg.br/noticias/ultimas',
        'max_pages': Config.MAX_PAGES_PER_SOURCE
    },
    'senado': {
        'name': 'Senado Federal',
        'base_url': 'https://www12.senado.leg.br',
        'news_url': 'https://www12.senado.leg.br/noticias/ultimas',
        'max_pages': Config.MAX_PAGES_PER_SOURCE
    },
    'agencia_gov': {
        'name': 'Agência Gov',
        'base_url': 'https://agenciagov.ebc.com.br',
        'news_url': 'https://agenciagov.ebc.com.br/noticias',
        'max_pages': Config.MAX_PAGES_PER_SOURCE
    }
}