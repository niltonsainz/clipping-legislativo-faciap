"""
Pipeline principal do sistema de clipping FACIAP
Orquestra: Coleta → Extração → Scoring → Armazenamento
"""
import time
from datetime import datetime
from typing import Dict, List, Optional
import pandas as pd

from .database import DatabaseManager
from .scrapers import get_all_scrapers
from .content_extractor import ContentExtractor
from .scoring import FACIAPScoring, load_dictionary
from .config import Config

class ClippingPipeline:
    """Pipeline principal do sistema de clipping"""
    
    def __init__(self):
        self.db_manager = DatabaseManager()
        self.content_extractor = ContentExtractor()
        self.scoring_system = FACIAPScoring()
        self.stats = {
            'inicio_execucao': None,
            'fim_execucao': None,
            'tempo_total': 0,
            'coleta': {'total_coletadas': 0, 'total_novas': 0},
            'extracao': {'processadas': 0, 'sucessos': 0},
            'scoring': {'processadas': 0, 'com_termos': 0}
        }
    
    def executar_completo(self, 
                         max_pages_por_fonte: int = None,
                         limite_extracao: int = None,
                         limite_scoring: int = None) -> Dict:
        """Executa pipeline completo"""
        
        print("🚀 PIPELINE COMPLETO DO SISTEMA FACIAP")
        print("=" * 60)
        
        self.stats['inicio_execucao'] = datetime.now()
        inicio_total = time.time()
        
        # Usa valores padrão se não especificados
        max_pages_por_fonte = max_pages_por_fonte or Config.MAX_PAGES_PER_SOURCE
        limite_extracao = limite_extracao or Config.MAX_EXTRACTION_PER_RUN
        limite_scoring = limite_scoring or Config.MAX_SCORING_PER_RUN
        
        try:
            # 1. Inicialização
            print("📋 ETAPA 1: INICIALIZAÇÃO")
            stats_iniciais = self.db_manager.get_stats()
            print(f"   Estado inicial: {stats_iniciais['total_noticias']} notícias no banco")
            
            # 2. Coleta de notícias
            print(f"\n📰 ETAPA 2: COLETA DE NOTÍCIAS")
            self._executar_coleta(max_pages_por_fonte)
            
            # 3. Extração de conteúdo
            print(f"\n📄 ETAPA 3: EXTRAÇÃO DE CONTEÚDO")
            self._executar_extracao(limite_extracao)
            
            # 4. Scoring FACIAP
            print(f"\n🎯 ETAPA 4: SCORING FACIAP")
            self._executar_scoring(limite_scoring)
            
            # 5. Resultados finais
            self.stats['fim_execucao'] = datetime.now()
            self.stats['tempo_total'] = time.time() - inicio_total
            
            stats_finais = self.db_manager.get_stats()
            self._exibir_resultados_finais(stats_iniciais, stats_finais)
            
            return {
                'sucesso': True,
                'tempo_execucao': self.stats['tempo_total'],
                'stats_iniciais': stats_iniciais,
                'stats_finais': stats_finais,
                'coleta': self.stats['coleta'],
                'extracao': self.stats['extracao'],
                'scoring': self.stats['scoring']
            }
            
        except Exception as e:
            print(f"❌ Erro no pipeline: {e}")
            return {
                'sucesso': False,
                'erro': str(e),
                'tempo_execucao': time.time() - inicio_total
            }
        
        finally:
            # Cleanup
            self.content_extractor.close_session()
    
    def _executar_coleta(self, max_pages_por_fonte: int):
        """Executa coleta de notícias de todas as fontes"""
        scrapers = get_all_scrapers()
        
        for source_name, scraper in scrapers.items():
            try:
                print(f"  🔍 Fonte: {source_name}")
                inicio_fonte = time.time()
                
                noticias = scraper.scrape(max_pages_por_fonte)
                
                noticias_novas = 0
                for noticia in noticias:
                    noticia_id, is_new = self.db_manager.insert_noticia(noticia)
                    self.stats['coleta']['total_coletadas'] += 1
                    if is_new:
                        noticias_novas += 1
                        self.stats['coleta']['total_novas'] += 1
                
                tempo_fonte = time.time() - inicio_fonte
                
                # Registra coleta no banco
                self.db_manager.registrar_coleta(
                    fonte=source_name,
                    noticias_coletadas=len(noticias),
                    noticias_novas=noticias_novas,
                    tempo_execucao=tempo_fonte,
                    status='success'
                )
                
                print(f"     ✅ {len(noticias)} coletadas, {noticias_novas} novas ({tempo_fonte:.1f}s)")
                
            except Exception as e:
                print(f"     ❌ Erro em {source_name}: {e}")
                # Registra erro no banco
                self.db_manager.registrar_coleta(
                    fonte=source_name,
                    noticias_coletadas=0,
                    noticias_novas=0,
                    tempo_execucao=0,
                    status='error',
                    observacoes=str(e)
                )
            finally:
                scraper.close_session()
        
        print(f"   📊 Total: {self.stats['coleta']['total_novas']} notícias novas coletadas")
    
    def _executar_extracao(self, limite_extracao: int):
        """Executa extração de conteúdo das notícias"""
        # Busca notícias sem conteúdo
        noticias_sem_conteudo = self.db_manager.get_noticias_sem_conteudo(limite_extracao)
        
        if noticias_sem_conteudo.empty:
            print("   ℹ️ Todas as notícias já possuem conteúdo extraído")
            return
        
        print(f"   🔄 Processando {len(noticias_sem_conteudo)} notícias...")
        
        for _, noticia in noticias_sem_conteudo.iterrows():
            try:
                resultado = self.content_extractor.extract_content(noticia['link'])
                self.db_manager.update_noticia_content(noticia['id'], resultado)
                
                self.stats['extracao']['processadas'] += 1
                if resultado['extraction_success']:
                    self.stats['extracao']['sucessos'] += 1
                
                # Log de progresso
                if self.stats['extracao']['processadas'] % 10 == 0:
                    print(f"     ⏳ Processadas: {self.stats['extracao']['processadas']}")
                    
            except Exception as e:
                print(f"     ⚠️ Erro na extração: {e}")
        
        print(f"   📊 Extração: {self.stats['extracao']['sucessos']}/{self.stats['extracao']['processadas']} sucessos")
    
    def _executar_scoring(self, limite_scoring: int):
        """Executa scoring FACIAP das notícias"""
        if not self.scoring_system.dictionary_df is not None:
            print("   ⚠️ Scoring pulado: dicionário FACIAP não encontrado")
            return
        
        # Busca notícias sem scoring
        noticias_sem_scoring = self.db_manager.get_noticias_sem_scoring(limite_scoring)
        
        if noticias_sem_scoring.empty:
            print("   ℹ️ Todas as notícias elegíveis já possuem scoring")
            return
        
        print(f"   🎯 Pontuando {len(noticias_sem_scoring)} notícias...")
        
        for _, noticia in noticias_sem_scoring.iterrows():
            try:
                scoring_resultado = self.scoring_system.score_content(
                    noticia['titulo'], 
                    noticia['content']
                )
                
                self.db_manager.insert_scoring(noticia['id'], scoring_resultado)
                
                self.stats['scoring']['processadas'] += 1
                if scoring_resultado['score_interesse_total'] > 0:
                    self.stats['scoring']['com_termos'] += 1
                
                # Log de progresso
                if self.stats['scoring']['processadas'] % 20 == 0:
                    print(f"     ⏳ Pontuadas: {self.stats['scoring']['processadas']}")
                    
            except Exception as e:
                print(f"     ⚠️ Erro no scoring: {e}")
        
        print(f"   📊 Scoring: {self.stats['scoring']['com_termos']}/{self.stats['scoring']['processadas']} relevantes")
    
    def _exibir_resultados_finais(self, stats_iniciais: Dict, stats_finais: Dict):
        """Exibe relatório final da execução"""
        print(f"\n📊 RESULTADOS FINAIS:")
        print(f"   • Tempo total: {self.stats['tempo_total']:.1f}s")
        print(f"   • Notícias no banco: {stats_iniciais['total_noticias']} → {stats_finais['total_noticias']}")
        print(f"   • Notícias novas: {self.stats['coleta']['total_novas']}")
        print(f"   • Com conteúdo: {stats_finais['com_conteudo']}")
        print(f"   • Distribuição por fonte:")
        
        for fonte, count in stats_finais.get('por_fonte', {}).items():
            fonte_nome = fonte.replace('_', ' ').title()
            print(f"     - {fonte_nome}: {count}")

# Função utilitária para manter compatibilidade
def executar_pipeline_completo(max_pages_por_fonte: int = 5, 
                              limite_extracao: int = 50, 
                              limite_scoring: int = 100) -> Dict:
    """Executa pipeline completo - função compatível com código existente"""
    pipeline = ClippingPipeline()
    return pipeline.executar_completo(max_pages_por_fonte, limite_extracao, limite_scoring)