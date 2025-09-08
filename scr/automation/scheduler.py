"""
Sistema de agendamento para dias úteis (segunda a sexta) 
com horários específicos: 12h e 20h (horário de Brasília)
"""
import os
import sys
import time
import schedule
import threading
import logging
from datetime import datetime
from pathlib import Path
import pytz
import signal

from scr.pipeline import ClippingPipeline
from scr.database import DatabaseManager
from scr.config import Config

class WeekdayScheduler:
    """Agendador para execução em dias úteis apenas"""
    
    def __init__(self):
        self.setup_logging()
        self.running = False
        self.lock_file = Path(Config.DATABASE_PATH).parent / 'automation.lock'
        self.pipeline = ClippingPipeline()
        self.tz_brasil = pytz.timezone('America/Sao_Paulo')
        
        # Configurar handler para sinais do sistema
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def setup_logging(self):
        """Configura sistema de logging"""
        log_dir = Path('logs')
        log_dir.mkdir(exist_ok=True)
        
        logging.basicConfig(
            level=getattr(logging, Config.LOG_LEVEL),
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.handlers.RotatingFileHandler(
                    log_dir / 'weekday_automation.log',
                    maxBytes=Config.LOG_MAX_SIZE,
                    backupCount=Config.LOG_BACKUP_COUNT
                ),
                logging.StreamHandler(sys.stdout)
            ]
        )
        
        self.logger = logging.getLogger(__name__)
        self.logger.info("🗓️ Sistema de automação para dias úteis inicializado")
    
    def _signal_handler(self, signum, frame):
        """Handler para sinais de sistema"""
        self.logger.info(f"🛑 Recebido sinal {signum}, finalizando...")
        self.running = False
        self.remove_lock()
        sys.exit(0)
    
    def is_business_day(self) -> bool:
        """Verifica se hoje é dia útil"""
        agora = datetime.now(self.tz_brasil)
        return agora.weekday() < 5  # 0-4 = Segunda a Sexta
    
    def execute_if_business_day(self):
        """Executa pipeline apenas se for dia útil"""
        if not self.is_business_day():
            agora = datetime.now(self.tz_brasil)
            self.logger.info(f"⏭️ Pulando execução - {agora.strftime('%A')} não é dia útil")
            return
        
        if self.is_already_running():
            self.logger.warning("⏭️ Pipeline já está em execução. Pulando...")
            return
        
        try:
            self.create_lock()
            agora = datetime.now(self.tz_brasil)
            self.logger.info(f"🚀 Iniciando execução automática - {agora.strftime('%A, %d/%m/%Y às %H:%M')}")
            
            # Executa pipeline
            resultado = self.pipeline.executar_completo(
                max_pages_por_fonte=Config.MAX_PAGES_PER_SOURCE,
                limite_extracao=Config.MAX_EXTRACTION_PER_RUN,
                limite_scoring=Config.MAX_SCORING_PER_RUN
            )
            
            if resultado['sucesso']:
                self.logger.info(f"✅ Pipeline concluído em {resultado['tempo_execucao']:.1f}s")
                self.logger.info(f"   📊 Notícias novas: {resultado['coleta']['total_novas']}")
                self.logger.info(f"   📄 Extrações: {resultado['extracao']['processadas']}")
                self.logger.info(f"   🎯 Scoring: {resultado['scoring']['processadas']}")
            else:
                self.logger.error("❌ Pipeline falhou")
                
        except Exception as e:
            self.logger.error(f"💥 Erro durante execução: {e}")
            import traceback
            self.logger.error(traceback.format_exc())
        finally:
            self.remove_lock()
    
    def is_already_running(self) -> bool:
        """Verifica se já existe execução em andamento"""
        if not self.lock_file.exists():
            return False
        
        try:
            with open(self.lock_file, 'r') as f:
                pid = int(f.read().strip())
            
            # Verifica se processo ainda existe
            os.kill(pid, 0)
            return True
            
        except (ProcessLookupError, ValueError, OSError):
            # Processo morreu, remove lock file órfão
            self.lock_file.unlink(missing_ok=True)
            return False
    
    def create_lock(self):
        """Cria arquivo de lock para evitar execuções simultâneas"""
        self.lock_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.lock_file, 'w') as f:
            f.write(str(os.getpid()))
        self.logger.debug(f"Lock criado: {self.lock_file}")
    
    def remove_lock(self):
        """Remove arquivo de lock"""
        if self.lock_file.exists():
            self.lock_file.unlink()
            self.logger.debug("Lock removido")
    
    def start_scheduler(self):
        """Inicia o agendador com horários específicos para dias úteis"""
        self.logger.info("📅 Configurando agendamento para dias úteis")
        self.logger.info("   🕛 Horários: 12:00 e 20:00 (horário de Brasília)")
        self.logger.info("   📆 Dias: Segunda a Sexta-feira")
        
        # Agenda para 12:00 (meio-dia)
        schedule.every().monday.at("12:00").do(self.execute_if_business_day)
        schedule.every().tuesday.at("12:00").do(self.execute_if_business_day)
        schedule.every().wednesday.at("12:00").do(self.execute_if_business_day)
        schedule.every().thursday.at("12:00").do(self.execute_if_business_day)
        schedule.every().friday.at("12:00").do(self.execute_if_business_day)
        
        # Agenda para 20:00 (noite)
        schedule.every().monday.at("20:00").do(self.execute_if_business_day)
        schedule.every().tuesday.at("20:00").do(self.execute_if_business_day)
        schedule.every().wednesday.at("20:00").do(self.execute_if_business_day)
        schedule.every().thursday.at("20:00").do(self.execute_if_business_day)
        schedule.every().friday.at("20:00").do(self.execute_if_business_day)
        
        self.running = True
        self.logger.info("✅ Agendador iniciado com sucesso")
        
        # Loop principal
        while self.running:
            schedule.run_pending()
            time.sleep(60)  # Verifica a cada minuto
    
    def run_now(self):
        """Executa imediatamente (para testes)"""
        self.logger.info("🧪 Execução manual solicitada")
        self.execute_if_business_day()

if __name__ == "__main__":
    scheduler = WeekdayScheduler()
    
    try:
        if len(sys.argv) > 1 and sys.argv[1] == '--run-now':
            scheduler.run_now()
        else:
            scheduler.start_scheduler()
    except KeyboardInterrupt:
        scheduler.logger.info("🛑 Agendador interrompido pelo usuário")
        scheduler.running = False
        scheduler.remove_lock()

