"""
Gerenciador de banco de dados SQLite para o sistema de clipping
"""
import sqlite3
import pandas as pd
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from scr.config import Config

class DatabaseManager:
    """Gerenciador de banco de dados SQLite para o sistema de clipping"""
    
    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or Config.DATABASE_PATH
        self.ensure_data_dir()
        self.init_database()
        print(f"✅ Banco de dados inicializado: {self.db_path}")
    
    def ensure_data_dir(self):
        """Garante que o diretório data/ existe"""
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
    
    def init_database(self):
        """Cria as tabelas do banco se não existirem"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Tabela principal de notícias
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS noticias (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    titulo TEXT NOT NULL,
                    link TEXT UNIQUE NOT NULL,
                    resumo TEXT,
                    fonte TEXT NOT NULL,
                    data_coleta DATETIME NOT NULL,
                    data_publicacao DATETIME,
                    content TEXT,
                    title_extracted TEXT,
                    word_count INTEGER DEFAULT 0,
                    extraction_success BOOLEAN DEFAULT FALSE,
                    favorita BOOLEAN DEFAULT FALSE,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Tabela de scoring FACIAP
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS scoring (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    noticia_id INTEGER NOT NULL,
                    score_interesse REAL DEFAULT 0,
                    score_risco REAL DEFAULT 0,
                    relevancia TEXT DEFAULT 'Baixa',
                    eixo_principal TEXT,
                    termos_encontrados INTEGER DEFAULT 0,
                    termos_detalhes TEXT,
                    scoring_version TEXT DEFAULT 'v1',
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (noticia_id) REFERENCES noticias (id) ON DELETE CASCADE
                )
            """)
            
            # Tabela de metadata das coletas
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS coletas (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    data_execucao DATETIME NOT NULL,
                    fonte TEXT NOT NULL,
                    noticias_coletadas INTEGER DEFAULT 0,
                    noticias_novas INTEGER DEFAULT 0,
                    noticias_duplicadas INTEGER DEFAULT 0,
                    tempo_execucao REAL,
                    status TEXT DEFAULT 'success',
                    observacoes TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Índices para performance
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_noticias_fonte ON noticias(fonte)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_noticias_data_coleta ON noticias(data_coleta)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_scoring_relevancia ON scoring(relevancia)")
            
            conn.commit()
    
    def insert_noticia(self, noticia_data: Dict) -> Tuple[int, bool]:
        """Insere uma notícia no banco com deduplicação automática"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            try:
                # Converte datetime para string se necessário
                if isinstance(noticia_data.get('data_coleta'), datetime):
                    noticia_data['data_coleta'] = noticia_data['data_coleta'].isoformat()
                if isinstance(noticia_data.get('data_publicacao'), datetime):
                    noticia_data['data_publicacao'] = noticia_data['data_publicacao'].isoformat()
                
                cursor.execute("""
                    INSERT INTO noticias (
                        titulo, link, resumo, fonte, data_coleta, data_publicacao,
                        content, title_extracted, word_count, extraction_success
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    noticia_data.get('titulo', ''),
                    noticia_data.get('link', ''),
                    noticia_data.get('resumo', ''),
                    noticia_data.get('fonte', ''),
                    noticia_data.get('data_coleta'),
                    noticia_data.get('data_publicacao'),
                    noticia_data.get('content', ''),
                    noticia_data.get('title_extracted', ''),
                    noticia_data.get('word_count', 0),
                    noticia_data.get('extraction_success', False)
                ))
                
                noticia_id = cursor.lastrowid
                conn.commit()
                return noticia_id, True
                
            except sqlite3.IntegrityError:
                cursor.execute("SELECT id FROM noticias WHERE link = ?", (noticia_data.get('link'),))
                result = cursor.fetchone()
                if result:
                    return result[0], False
                else:
                    raise
    
    def get_stats(self) -> Dict:
        """Retorna estatísticas gerais do banco"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            stats = {}
            
            cursor.execute("SELECT COUNT(*) FROM noticias")
            stats['total_noticias'] = cursor.fetchone()[0]
            
            cursor.execute("SELECT fonte, COUNT(*) FROM noticias GROUP BY fonte")
            stats['por_fonte'] = dict(cursor.fetchall())
            
            cursor.execute("""
                SELECT s.relevancia, COUNT(*) 
                FROM noticias n 
                LEFT JOIN scoring s ON n.id = s.noticia_id 
                GROUP BY s.relevancia
            """)
            stats['por_relevancia'] = dict(cursor.fetchall())
            
            cursor.execute("SELECT COUNT(*) FROM noticias WHERE extraction_success = 1")
            stats['com_conteudo'] = cursor.fetchone()[0]
            
            cursor.execute("SELECT MIN(data_coleta), MAX(data_coleta) FROM noticias")
            resultado = cursor.fetchone()
            stats['periodo'] = {
                'inicio': resultado[0],
                'fim': resultado[1]
            }
            
            return stats

    def get_noticias_sem_conteudo(self, limite: int = 50):
        """Busca notícias que precisam de extração de conteúdo"""
        query = """
            SELECT id, link, fonte FROM noticias 
            WHERE (extraction_success = 0 OR extraction_success IS NULL)
            AND (content IS NULL OR content = '' OR LENGTH(content) < 100)
            ORDER BY data_coleta DESC
            LIMIT ?
        """
        with sqlite3.connect(self.db_path) as conn:
            return pd.read_sql_query(query, conn, params=[limite])

    def get_noticias_sem_scoring(self, limite: int = 100):
        """Busca notícias que precisam de scoring"""
        query = """
            SELECT n.id, n.titulo, n.content FROM noticias n
            LEFT JOIN scoring s ON n.id = s.noticia_id
            WHERE n.extraction_success = 1 
            AND n.word_count > 50 
            AND s.id IS NULL
            ORDER BY n.data_coleta DESC
            LIMIT ?
        """
        with sqlite3.connect(self.db_path) as conn:
            return pd.read_sql_query(query, conn, params=[limite])

    def update_noticia_content(self, noticia_id, content_data):
        """Atualiza o conteúdo extraído de uma notícia"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE noticias 
                SET content = ?, title_extracted = ?, word_count = ?, 
                    extraction_success = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (
                content_data.get('content', ''),
                content_data.get('title_extracted', ''),
                content_data.get('word_count', 0),
                content_data.get('extraction_success', False),
                noticia_id
            ))
            conn.commit()

    def insert_scoring(self, noticia_id, scoring_data):
        """Insere ou atualiza o scoring FACIAP de uma notícia"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            termos_json = None
            if 'termos_detalhes' in scoring_data:
                termos_json = json.dumps(scoring_data['termos_detalhes'], ensure_ascii=False)
            cursor.execute("DELETE FROM scoring WHERE noticia_id = ?", (noticia_id,))
            cursor.execute("""
                INSERT INTO scoring (
                    noticia_id, score_interesse, score_risco, relevancia,
                    eixo_principal, termos_encontrados, termos_detalhes
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                noticia_id,
                scoring_data.get('score_interesse_total', 0),
                scoring_data.get('score_risco_total', 0),
                scoring_data.get('relevancia', 'Baixa'),
                scoring_data.get('eixo_principal', ''),
                scoring_data.get('termos_encontrados', 0),
                termos_json
            ))
            conn.commit()

    def registrar_coleta(self, fonte, noticias_coletadas, noticias_novas, tempo_execucao, status='success', observacoes=None):
        """Registra metadata de uma execução de coleta"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            noticias_duplicadas = noticias_coletadas - noticias_novas
            cursor.execute("""
                INSERT INTO coletas (
                    data_execucao, fonte, noticias_coletadas, noticias_novas,
                    noticias_duplicadas, tempo_execucao, status, observacoes
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                datetime.now().isoformat(),
                fonte,
                noticias_coletadas,
                noticias_novas,
                noticias_duplicadas,
                tempo_execucao,
                status,
                observacoes
            ))

            conn.commit()
