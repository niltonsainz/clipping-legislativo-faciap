"""
Sistema de automação e agendamento do pipeline
"""
import os
import sys
import time
import schedule
import threading
import logging
from datetime import datetime
from pathlib import Path
import signal

from ..pipeline import ClippingPipeline
from ..database import DatabaseManager
from ..config import Config

class AutomationScheduler:
    """Agendador automático para execução do pipeline"""
    
    def __init__(self):
        self.setup_logging()
        self.running = False
        self.lock_file = Path(Config.DATABASE_PATH).parent / 'automation.lock'
        self.pipeline = ClippingPipeline()
        
        # Configurar handler para sinais do sistema
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def setup_logging(self):
        """Configura sistema de logging"""
        log_dir = Path('logs')
        log_dir.mkdir(exist_ok=True)
        
        # Configuração do logger
        logging.basicConfig(
            level=getattr(logging, Config.LOG_LEVEL),
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.handlers.RotatingFileHandler(
                    log_dir / 'automation.log',
                    maxBytes=Config.LOG_MAX_SIZE,
                    backupCount=Config.LOG_BACKUP_COUNT
                ),
                logging.StreamHandler(sys.stdout)
            ]
        )
        
        self.logger = logging.getLogger(__name__)
        self.logger.info("🤖 Sistema de automação inicializado")
    
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
    
    def execute_pipeline_job(self):
        """Job para execução do pipeline (usado pelo scheduler)"""
        if self.is_already_running():
            self.logger.warning("⏭️ Pipeline já está em execução. Pulando...")
            return
        
        try:
            self.create_lock()
            self.logger.info("🚀 Iniciando execução automática do pipeline")
            
            # Executa pipeline com configurações padrão
            resultado = self.pipeline.executar_completo(
                max_pages_por_fonte=Config.MAX_PAGES_PER_SOURCE,
                limite_extracao=Config.MAX_EXTRACTION_PER_RUN,
                limite_scoring=Config.MAX_SCORING_PER_RUN
            )
            
            if resultado['sucesso']:
                self.logger.info(f"✅ Pipeline concluído em {resultado['tempo_execucao']:.1f}s")
                self.logger.info(f"   📊 Notícias novas: {resultado['coleta']['total_novas']}")
                self.logger.info(f"   📄 Extrações: {resultado['extracao']['sucessos']}")
                self.logger.info(f"   🎯 Scorings: {resultado['scoring']['com_termos']}")
            else:
                self.logger.error(f"❌ Pipeline falhou: {resultado.get('erro', 'Erro desconhecido')}")
            
        except Exception as e:
            self.logger.error(f"❌ Erro crítico na execução: {e}", exc_info=True)
            
        finally:
            self.remove_lock()
    
    def setup_schedule(self):
        """Configura agendamento baseado na configuração"""
        if not Config.SCHEDULE_ENABLED:
            self.logger.info("📅 Agendamento desabilitado por configuração")
            return
        
        # Limpa agendamentos anteriores
        schedule.clear()
        
        # Agenda execuções para cada horário configurado
        for time_str in Config.SCHEDULE_TIMES:
            try:
                # Agenda para dias úteis
                schedule.every().monday.at(time_str).do(self.execute_pipeline_job)
                schedule.every().tuesday.at(time_str).do(self.execute_pipeline_job)
                schedule.every().wednesday.at(time_str).do(self.execute_pipeline_job)
                schedule.every().thursday.at(time_str).do(self.execute_pipeline_job)
                schedule.every().friday.at(time_str).do(self.execute_pipeline_job)
                
                self.logger.info(f"⏰ Agendado para: {time_str} (seg-sex)")
                
            except Exception as e:
                self.logger.error(f"❌ Erro ao agendar {time_str}: {e}")
        
        self.logger.info(f"📅 Agendamento configurado: {len(Config.SCHEDULE_TIMES)} horários")
    
    def start_scheduler(self):
        """Inicia o loop principal do agendador"""
        self.logger.info("🤖 Iniciando sistema de automação...")
        
        # Configura agendamentos
        self.setup_schedule()
        
        # Execução inicial opcional (descomente se desejar)
        # self.logger.info("🎯 Executando pipeline inicial...")
        # self.execute_pipeline_job()
        
        self.running = True
        self.logger.info("⏰ Aguardando próximas execuções agendadas...")
        
        # Loop principal
        while self.running:
            try:
                schedule.run_pending()
                time.sleep(60)  # Verifica agendamentos a cada minuto
                
            except KeyboardInterrupt:
                self.logger.info("⌨️ Interrupção pelo usuário")
                break
            except Exception as e:
                self.logger.error(f"❌ Erro no loop principal: {e}", exc_info=True)
                time.sleep(60)  # Aguarda antes de tentar novamente
        
        self.stop()
    
    def stop(self):
        """Para o agendador e limpa recursos"""
        self.logger.info("🛑 Parando sistema de automação...")
        self.running = False
        self.remove_lock()
        
        # Cleanup de recursos
        if hasattr(self.pipeline, 'content_extractor'):
            self.pipeline.content_extractor.close_session()
        
        self.logger.info("✅ Sistema de automação parado")
    
    def _signal_handler(self, signum, frame):
        """Handler para sinais do sistema operacional"""
        self.logger.info(f"📡 Sinal recebido: {signum}")
        self.stop()
        sys.exit(0)
    
    def run_once(self):
        """Executa pipeline uma única vez (para testes)"""
        self.logger.info("🎯 Execução única solicitada")
        self.execute_pipeline_job()

def main():
    """Função principal para execução do agendador"""
    scheduler = AutomationScheduler()
    
    # Verifica argumentos de linha de comando
    if len(sys.argv) > 1 and sys.argv[1] == '--once':
        scheduler.run_once()
    else:
        try:
            scheduler.start_scheduler()
        except KeyboardInterrupt:
            scheduler.stop()

if __name__ == "__main__":
    main()