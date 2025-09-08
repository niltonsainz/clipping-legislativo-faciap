#!/usr/bin/env python3
"""
Script principal para automação do clipping FACIAP
Executa apenas de segunda a sexta-feira às 12h e 20h
"""
import sys
import os
import argparse
from pathlib import Path
from datetime import datetime
import pytz

# Adiciona o diretório src ao path
sys.path.insert(0, str(Path(__file__).parent / 'scr'))

from pipeline import ClippingPipeline
from config import Config
import logging

def setup_logging():
    """Configura logging para execução standalone"""
    log_dir = Path('logs')
    log_dir.mkdir(exist_ok=True)
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_dir / 'automation.log'),
            logging.StreamHandler()
        ]
    )

def is_business_hours():
    """Verifica se está em horário comercial (seg-sex, 12h ou 20h)"""
    # Timezone do Brasil
    tz_brasil = pytz.timezone('America/Sao_Paulo')
    agora = datetime.now(tz_brasil)
    
    # Verifica se é dia útil (0=Monday, 6=Sunday)
    if agora.weekday() >= 5:  # Sábado ou Domingo
        return False, f"Final de semana ({agora.strftime('%A')})"
    
    hora_atual = agora.hour
    
    # Verifica se está nos horários programados (12h ou 20h ±30min)
    horarios_permitidos = [
        (11, 13),  # 11h às 13h (janela do meio-dia)
        (19, 21)   # 19h às 21h (janela da noite)
    ]
    
    for inicio, fim in horarios_permitidos:
        if inicio <= hora_atual < fim:
            return True, f"Horário comercial ({agora.strftime('%H:%M')})"
    
    return False, f"Fora do horário ({agora.strftime('%H:%M')})"

def main():
    parser = argparse.ArgumentParser(description='Clipping FACIAP Automation')
    parser.add_argument('--max-pages', type=int, default=Config.MAX_PAGES_PER_SOURCE,
                       help='Máximo de páginas por fonte')
    parser.add_argument('--max-extraction', type=int, default=Config.MAX_EXTRACTION_PER_RUN,
                       help='Máximo de extrações por execução')
    parser.add_argument('--max-scoring', type=int, default=Config.MAX_SCORING_PER_RUN,
                       help='Máximo de scoring por execução')
    parser.add_argument('--force', action='store_true',
                       help='Força execução mesmo fora do horário')
    parser.add_argument('--dry-run', action='store_true',
                       help='Execução de teste (não salva no banco)')
    
    args = parser.parse_args()
    
    # Configuração
    setup_logging()
    logger = logging.getLogger(__name__)
    
    # Verifica horário comercial
    if not args.force:
        permitido, motivo = is_business_hours()
        if not permitido:
            logger.info(f"⏭️ Execução pulada: {motivo}")
            return 0
    
    # Cria diretórios necessários
    Path('data').mkdir(exist_ok=True)
    Path('logs').mkdir(exist_ok=True)
    
    try:
        logger.info("🚀 Iniciando automação do clipping FACIAP")
        logger.info(f"📅 {datetime.now().strftime('%A, %d/%m/%Y às %H:%M')}")
        
        if args.dry_run:
            logger.info("🧪 Modo de teste ativado - não salvará no banco")
        
        pipeline = ClippingPipeline()
        resultado = pipeline.executar_completo(
            max_pages_por_fonte=args.max_pages,
            limite_extracao=args.max_extraction,
            limite_scoring=args.max_scoring
        )
        
        if resultado['sucesso']:
            logger.info(f"✅ Pipeline concluído com sucesso em {resultado['tempo_execucao']:.1f}s")
            logger.info(f"📊 Estatísticas:")
            logger.info(f"   📰 Notícias coletadas: {resultado['coleta']['total_coletadas']}")
            logger.info(f"   🆕 Notícias novas: {resultado['coleta']['total_novas']}")
            logger.info(f"   📄 Extrações processadas: {resultado['extracao']['processadas']}")
            logger.info(f"   🎯 Scoring processado: {resultado['scoring']['processadas']}")
            
            return 0
        else:
            logger.error("❌ Pipeline falhou")
            return 1
            
    except Exception as e:
        logger.error(f"💥 Erro durante execução: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return 1

if __name__ == '__main__':
    sys.exit(main())
