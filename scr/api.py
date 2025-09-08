"""
API REST para o sistema de clipping FACIAP
"""
from flask import Flask, jsonify, request
from flask_cors import CORS
import pandas as pd
import numpy as np
from datetime import datetime
from functools import wraps
import traceback

from scr.database import DatabaseManager
from scr.pipeline import ClippingPipeline
from scr.config import Config

class ClippingAPI:
    """API REST para o sistema de clipping"""
    
    def __init__(self):
        self.app = Flask(__name__)
        CORS(self.app)
        
        # Configurações da aplicação
        self.app.config['JSON_SORT_KEYS'] = False
        self.app.config['JSONIFY_PRETTYPRINT_REGULAR'] = True
        
        # Inicializa componentes
        self.db_manager = DatabaseManager()
        self.pipeline = ClippingPipeline()
        
        # Registra rotas
        self._register_routes()
    
    def _register_routes(self):
        """Registra todas as rotas da API"""
        
        @self.app.route('/health', methods=['GET'])
        @self._handle_errors
        def health_check():
            """Endpoint de health check"""
            stats = self.db_manager.get_stats()
            
            health_data = {
                'status': 'healthy',
                'version': '2.0.0',
                'database': 'connected',
                'total_noticias': stats.get('total_noticias', 0),
                'timestamp': datetime.now().isoformat()
            }
            
            return self._format_response(
                data=health_data, 
                message="API funcionando normalmente"
            )
        
        @self.app.route('/api/stats', methods=['GET'])
        @self._handle_errors
        def get_stats():
            """Retorna estatísticas gerais do sistema"""
            return self._format_response(
                data=self._get_comprehensive_stats(),
                message="Estatísticas obtidas com sucesso"
            )
        
        @self.app.route('/api/noticias', methods=['GET'])
        @self._handle_errors
        def get_noticias():
            """Lista notícias com filtros opcionais"""
            # Parâmetros de consulta
            limite = min(int(request.args.get('limit', 20)), 100)
            page = max(int(request.args.get('page', 1)), 1)
            fonte = request.args.get('fonte')
            relevancia = request.args.get('relevancia')
            data_inicio = request.args.get('data_inicio')
            data_fim = request.args.get('data_fim')
            
            # Busca notícias
            df = self.db_manager.get_noticias(
                limit=limite * page,  # Busca mais para permitir paginação
                fonte=fonte,
                relevancia=relevancia,
                data_inicio=data_inicio,
                data_fim=data_fim
            )
            
            # Aplica paginação
            start_idx = (page - 1) * limite
            end_idx = start_idx + limite
            df_page = df.iloc[start_idx:end_idx]
            
            # Converte para formato da API
            noticias = []
            for _, row in df_page.iterrows():
                noticia = self._format_noticia(row)
                noticias.append(noticia)
            
            # Metadados de paginação
            total = len(df)
            total_pages = (total + limite - 1) // limite
            
            meta = {
                'total': total,
                'page': page,
                'per_page': limite,
                'total_pages': total_pages,
                'has_next': page < total_pages,
                'has_prev': page > 1
            }
            
            return self._format_response(
                data=noticias,
                meta=meta,
                message=f"{len(noticias)} notícias encontradas"
            )
        
        @self.app.route('/api/noticias/<int:noticia_id>', methods=['GET'])
        @self._handle_errors
        def get_noticia_detalhes(noticia_id):
            """Retorna detalhes completos de uma notícia"""
            noticia = self._get_noticia_completa(noticia_id)
            
            if not noticia:
                return self._format_response(
                    success=False,
                    message="Notícia não encontrada",
                    status_code=404
                )
            
            return self._format_response(
                data=noticia,
                message="Detalhes da notícia obtidos com sucesso"
            )
        
        @self.app.route('/api/fontes', methods=['GET'])
        @self._handle_errors
        def get_fontes():
            """Lista fontes disponíveis com estatísticas"""
            fontes = self._get_fontes_stats()
            
            return self._format_response(
                data=fontes,
                message=f"{len(fontes)} fontes encontradas"
            )
        
        @self.app.route('/api/pipeline/executar', methods=['POST'])
        @self._handle_errors
        def executar_pipeline():
            """Executa pipeline completo via API"""
            # Parâmetros opcionais
            data = request.get_json() or {}
            max_pages = data.get('max_pages_por_fonte', Config.MAX_PAGES_PER_SOURCE)
            limite_extracao = data.get('limite_extracao', Config.MAX_EXTRACTION_PER_RUN)
            limite_scoring = data.get('limite_scoring', Config.MAX_SCORING_PER_RUN)
            
            # Executa pipeline
            resultado = self.pipeline.executar_completo(
                max_pages, limite_extracao, limite_scoring
            )
            
            if resultado['sucesso']:
                return self._format_response(
                    data=resultado,
                    message="Pipeline executado com sucesso"
                )
            else:
                return self._format_response(
                    success=False,
                    data=resultado,
                    message="Erro na execução do pipeline",
                    status_code=500
                )
    
    def _handle_errors(self, f):
        """Decorator para tratamento de erros"""
        @wraps(f)
        def decorated_function(*args, **kwargs):
            try:
                return f(*args, **kwargs)
            except Exception as e:
                traceback.print_exc()
                return self._format_response(
                    success=False,
                    message=f"Erro interno: {str(e)}",
                    status_code=500
                )
        return decorated_function
    
    def _format_response(self, data=None, success=True, message=None, 
                        meta=None, status_code=200):
        """Padroniza formato das respostas"""
        response = {
            'success': success,
            'timestamp': datetime.now().isoformat(),
            'message': message
        }
        
        if data is not None:
            response['data'] = data
        
        if meta is not None:
            response['meta'] = meta
        
        return jsonify(response), status_code
    
    def _safe_json_convert(self, value):
        """Converte valores para tipos serializáveis em JSON"""
        if pd.isna(value) or value is None:
            return None
        elif isinstance(value, (np.bool_, bool)):
            return bool(value)
        elif isinstance(value, (np.integer, int)):
            return int(value)
        elif isinstance(value, (np.floating, float)):
            return float(value)
        elif isinstance(value, str):
            return value
        else:
            return str(value)
    
    def _format_noticia(self, row):
        """Formata dados de uma notícia para a API"""
        return {
            'id': self._safe_json_convert(row['id']),
            'titulo': self._safe_json_convert(row['titulo']),
            'link': self._safe_json_convert(row['link']),
            'resumo': self._safe_json_convert(row['resumo']),
            'fonte': self._safe_json_convert(row['fonte']),
            'data_coleta': self._safe_json_convert(row['data_coleta']),
            'data_publicacao': self._safe_json_convert(row['data_publicacao']),
            'word_count': self._safe_json_convert(row['word_count']),
            'extraction_success': self._safe_json_convert(row['extraction_success']),
            'scoring': {
                'score_interesse': self._safe_json_convert(row.get('score_interesse')),
                'score_risco': self._safe_json_convert(row.get('score_risco')),
                'relevancia': self._safe_json_convert(row.get('relevancia')),
                'eixo_principal': self._safe_json_convert(row.get('eixo_principal'))
            }
        }
    
    def _get_comprehensive_stats(self):
        """Retorna estatísticas abrangentes do sistema"""
        import sqlite3
        
        with sqlite3.connect(self.db_manager.db_path) as conn:
            cursor = conn.cursor()
            
            # Estatísticas básicas
            stats_basicas = self.db_manager.get_stats()
            
            # Estatísticas de scoring
            cursor.execute("""
                SELECT 
                    COUNT(CASE WHEN s.relevancia = 'Alta' THEN 1 END) as alta,
                    COUNT(CASE WHEN s.relevancia = 'Média' THEN 1 END) as media,
                    COUNT(CASE WHEN s.relevancia = 'Baixa-Média' THEN 1 END) as baixa_media,
                    COUNT(CASE WHEN s.relevancia = 'Baixa' THEN 1 END) as baixa,
                    AVG(s.score_interesse) as score_medio,
                    MAX(s.score_interesse) as score_maximo
                FROM scoring s
            """)
            scoring_stats = cursor.fetchone()
            
            # Estatísticas de extração
            cursor.execute("""
                SELECT 
                    COUNT(*) as total,
                    COUNT(CASE WHEN extraction_success = 1 THEN 1 END) as com_sucesso,
                    AVG(word_count) as palavras_media,
                    MAX(word_count) as palavras_maximo
                FROM noticias
                WHERE extraction_success IS NOT NULL
            """)
            extracao_stats = cursor.fetchone()
            
            # Ultimas execuções
            cursor.execute("""
                SELECT fonte, data_execucao, status, noticias_novas, tempo_execucao
                FROM coletas 
                ORDER BY data_execucao DESC 
                LIMIT 10
            """)
            ultimas_execucoes = cursor.fetchall()
            
            # Tendências por data (últimos 30 dias)
            cursor.execute("""
                SELECT 
                    DATE(data_coleta) as data,
                    COUNT(*) as total_noticias,
                    COUNT(CASE WHEN s.relevancia IN ('Alta', 'Média') THEN 1 END) as relevantes
                FROM noticias n
                LEFT JOIN scoring s ON n.id = s.noticia_id
                WHERE DATE(data_coleta) >= DATE('now', '-30 days')
                GROUP BY DATE(data_coleta)
                ORDER BY data DESC
            """)
            tendencias = cursor.fetchall()
            
            # Eixos mais frequentes
            cursor.execute("""
                SELECT 
                    eixo_principal,
                    COUNT(*) as quantidade,
                    AVG(score_interesse) as score_medio
                FROM scoring 
                WHERE eixo_principal IS NOT NULL AND eixo_principal != ''
                GROUP BY eixo_principal
                ORDER BY quantidade DESC
                LIMIT 10
            """)
            eixos_stats = cursor.fetchall()
        
        return {
            'resumo_geral': {
                'total_noticias': stats_basicas['total_noticias'],
                'com_conteudo': stats_basicas['com_conteudo'],
                'periodo': stats_basicas['periodo']
            },
            'por_fonte': stats_basicas['por_fonte'],
            'scoring': {
                'alta_relevancia': scoring_stats[0] or 0,
                'media_relevancia': scoring_stats[1] or 0,
                'baixa_media_relevancia': scoring_stats[2] or 0,
                'baixa_relevancia': scoring_stats[3] or 0,
                'score_medio': round(scoring_stats[4], 2) if scoring_stats[4] else 0,
                'score_maximo': round(scoring_stats[5], 2) if scoring_stats[5] else 0
            },
            'extracao': {
                'total_processadas': extracao_stats[0] or 0,
                'sucessos': extracao_stats[1] or 0,
                'taxa_sucesso': round((extracao_stats[1] / extracao_stats[0] * 100), 2) if extracao_stats[0] else 0,
                'palavras_media': round(extracao_stats[2], 0) if extracao_stats[2] else 0,
                'palavras_maximo': extracao_stats[3] or 0
            },
            'ultimas_execucoes': [
                {
                    'fonte': exec[0],
                    'data': exec[1],
                    'status': exec[2],
                    'noticias_novas': exec[3] or 0,
                    'tempo_execucao': round(exec[4], 2) if exec[4] else 0
                }
                for exec in ultimas_execucoes
            ],
            'tendencias_30_dias': [
                {
                    'data': tend[0],
                    'total_noticias': tend[1],
                    'noticias_relevantes': tend[2] or 0,
                    'percentual_relevantes': round((tend[2] / tend[1] * 100), 2) if tend[1] and tend[2] else 0
                }
                for tend in tendencias
            ],
            'eixos_principais': [
                {
                    'eixo': eixo[0],
                    'quantidade': eixo[1],
                    'score_medio': round(eixo[2], 2) if eixo[2] else 0
                }
                for eixo in eixos_stats
            ]
        }
    
    def _get_noticia_completa(self, noticia_id):
        """Retorna detalhes completos de uma notícia específica"""
        import sqlite3
        import json
        
        query = """
            SELECT 
                n.id, n.titulo, n.link, n.resumo, n.fonte, n.content,
                n.data_coleta, n.data_publicacao, n.word_count,
                n.extraction_success, n.title_extracted, n.favorita,
                n.created_at, n.updated_at,
                s.score_interesse, s.score_risco, s.relevancia, 
                s.eixo_principal, s.termos_encontrados, s.termos_detalhes,
                s.scoring_version, s.created_at as scoring_created_at
            FROM noticias n
            LEFT JOIN scoring s ON n.id = s.noticia_id
            WHERE n.id = ?
        """
        
        with sqlite3.connect(self.db_manager.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(query, (noticia_id,))
            row = cursor.fetchone()
            
            if not row:
                return None
            
            # Mapeia resultado
            columns = [desc[0] for desc in cursor.description]
            noticia_data = dict(zip(columns, row))
            
            # Parse de termos_detalhes se existir
            termos_detalhes = []
            if noticia_data['termos_detalhes']:
                try:
                    termos_detalhes = json.loads(noticia_data['termos_detalhes'])
                except:
                    termos_detalhes = []
            
            # Formatar resposta completa
            noticia_completa = {
                'id': self._safe_json_convert(noticia_data['id']),
                'titulo': self._safe_json_convert(noticia_data['titulo']),
                'link': self._safe_json_convert(noticia_data['link']),
                'resumo': self._safe_json_convert(noticia_data['resumo']),
                'fonte': self._safe_json_convert(noticia_data['fonte']),
                'conteudo': self._safe_json_convert(noticia_data['content']),
                'title_extracted': self._safe_json_convert(noticia_data['title_extracted']),
                'datas': {
                    'coleta': self._safe_json_convert(noticia_data['data_coleta']),
                    'publicacao': self._safe_json_convert(noticia_data['data_publicacao']),
                    'criacao': self._safe_json_convert(noticia_data['created_at']),
                    'atualizacao': self._safe_json_convert(noticia_data['updated_at'])
                },
                'extracao': {
                    'sucesso': self._safe_json_convert(noticia_data['extraction_success']),
                    'word_count': self._safe_json_convert(noticia_data['word_count']),
                    'tem_conteudo': bool(noticia_data['content'] and len(str(noticia_data['content'])) > 100)
                },
                'scoring': {
                    'score_interesse': self._safe_json_convert(noticia_data['score_interesse']),
                    'score_risco': self._safe_json_convert(noticia_data['score_risco']),
                    'relevancia': self._safe_json_convert(noticia_data['relevancia']),
                    'eixo_principal': self._safe_json_convert(noticia_data['eixo_principal']),
                    'termos_encontrados': self._safe_json_convert(noticia_data['termos_encontrados']),
                    'termos_detalhes': termos_detalhes,
                    'scoring_version': self._safe_json_convert(noticia_data['scoring_version']),
                    'scoring_data': self._safe_json_convert(noticia_data['scoring_created_at'])
                },
                'metadata': {
                    'favorita': self._safe_json_convert(noticia_data['favorita']),
                    'possui_scoring': bool(noticia_data['score_interesse'] is not None)
                }
            }
            
            return noticia_completa
    
    def _get_fontes_stats(self):
        """Retorna estatísticas detalhadas das fontes"""
        import sqlite3
        from .config import SOURCES_CONFIG
        
        query = """
            SELECT 
                n.fonte,
                COUNT(*) as total_noticias,
                COUNT(CASE WHEN n.extraction_success = 1 THEN 1 END) as com_conteudo,
                COUNT(s.id) as com_scoring,
                AVG(s.score_interesse) as score_medio,
                COUNT(CASE WHEN s.relevancia = 'Alta' THEN 1 END) as alta_relevancia,
                COUNT(CASE WHEN s.relevancia = 'Média' THEN 1 END) as media_relevancia,
                MAX(n.data_coleta) as ultima_coleta,
                AVG(n.word_count) as palavras_media,
                COUNT(CASE WHEN DATE(n.data_coleta) = DATE('now') THEN 1 END) as noticias_hoje
            FROM noticias n
            LEFT JOIN scoring s ON n.id = s.noticia_id
            GROUP BY n.fonte
            ORDER BY total_noticias DESC
        """
        
        with sqlite3.connect(self.db_manager.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(query)
            rows = cursor.fetchall()
            
            # Busca últimas execuções por fonte
            cursor.execute("""
                SELECT fonte, status, data_execucao, noticias_novas, tempo_execucao
                FROM coletas c1
                WHERE data_execucao = (
                    SELECT MAX(data_execucao) 
                    FROM coletas c2 
                    WHERE c2.fonte = c1.fonte
                )
            """)
            ultimas_execucoes = {row[0]: {
                'status': row[1],
                'data': row[2],
                'noticias_novas': row[3] or 0,
                'tempo_execucao': row[4] or 0
            } for row in cursor.fetchall()}
        
        fontes = []
        for row in rows:
            fonte_key = row[0]
            
            # Busca informações de configuração
            fonte_config = SOURCES_CONFIG.get(fonte_key, {})
            nome_display = fonte_config.get('name', fonte_key.replace('_', ' ').title())
            
            # Calcula métricas
            total = row[1] or 0
            com_conteudo = row[2] or 0
            com_scoring = row[3] or 0
            alta_relevancia = row[5] or 0
            
            taxa_extracao = round((com_conteudo / total * 100), 2) if total > 0 else 0
            taxa_scoring = round((com_scoring / total * 100), 2) if total > 0 else 0
            taxa_alta_relevancia = round((alta_relevancia / com_scoring * 100), 2) if com_scoring > 0 else 0
            
            # Informações da última execução
            ultima_exec = ultimas_execucoes.get(fonte_key, {})
            
            fonte_info = {
                'codigo': fonte_key,
                'nome': nome_display,
                'configuracao': {
                    'url_base': fonte_config.get('base_url', ''),
                    'url_noticias': fonte_config.get('news_url', ''),
                    'max_pages': fonte_config.get('max_pages', 0)
                },
                'estatisticas': {
                    'total_noticias': total,
                    'com_conteudo': com_conteudo,
                    'com_scoring': com_scoring,
                    'noticias_hoje': row[9] or 0,
                    'alta_relevancia': alta_relevancia,
                    'media_relevancia': row[6] or 0
                },
                'metricas': {
                    'score_medio': round(row[4], 2) if row[4] else 0,
                    'palavras_media': round(row[8], 0) if row[8] else 0,
                    'taxa_extracao_sucesso': taxa_extracao,
                    'taxa_com_scoring': taxa_scoring,
                    'taxa_alta_relevancia': taxa_alta_relevancia
                },
                'ultima_coleta': {
                    'data': row[7],
                    'status': ultima_exec.get('status', 'desconhecido'),
                    'noticias_novas': ultima_exec.get('noticias_novas', 0),
                    'tempo_execucao': round(ultima_exec.get('tempo_execucao', 0), 2)
                },
                'saude': {
                    'status': 'ativo' if row[9] and row[9] > 0 else 'inativo',
                    'ultima_atividade': row[7],
                    'funcionando': ultima_exec.get('status') == 'success'
                }
            }
            
            fontes.append(fonte_info)
        
        return fontes
    
    def run(self, host=None, port=None, debug=None):
        """Inicia o servidor da API"""
        host = host or Config.API_HOST
        port = port or Config.API_PORT
        debug = debug or Config.API_DEBUG
        
        print(f"🌐 API iniciada em http://{host}:{port}")
        self.app.run(host=host, port=port, debug=debug)

# Função utilitária para criar aplicação Flask
def create_app():
    """Cria e configura aplicação Flask"""
    api = ClippingAPI()
    return api.app

# Função utilitária para iniciar API
def start_api():
    """Inicia a API"""
    api = ClippingAPI()
    api.run()

if __name__ == '__main__':

    start_api()
