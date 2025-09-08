"""
Dashboard Streamlit para Sistema de Clipping FACIAP
VERSÃO CORRIGIDA - Problema do </div> RESOLVIDO DEFINITIVAMENTE

Desenvolvido por: Nilton Sainz
Para: FACIAP - Federação das Associações Comerciais e Industriais do Paraná
"""

import streamlit as st
import pandas as pd
import sqlite3
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import time
from pathlib import Path
import os
import re

# Configuração da página
st.set_page_config(
    page_title="Clipping Legislativo FACIAP",
    page_icon="📰",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS personalizado para design sóbrio
st.markdown("""
<style>
    .main-header {
        background-color: #f8f9fa;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #2c3e50;
        margin-bottom: 1rem;
    }
    
    .metric-card {
        background-color: white;
        padding: 1rem;
        border-radius: 0.5rem;
        border: 1px solid #e9ecef;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
    }
    
    .fonte-tag {
        display: inline-block;
        padding: 0.25rem 0.5rem;
        border-radius: 0.25rem;
        font-size: 0.75rem;
        font-weight: 600;
        color: white;
        margin-right: 0.5rem;
    }
    
    .fonte-camara { background-color: #2c5282; }
    .fonte-senado { background-color: #2d3748; }
    .fonte-gov { background-color: #2b6cb0; }
    
    .relevancia-alta { color: #e53e3e; font-weight: 600; }
    .relevancia-media { color: #dd6b20; font-weight: 600; }
    .relevancia-baixa { color: #38a169; font-weight: 600; }
    
    .noticia-card {
        border: 1px solid #e2e8f0;
        border-radius: 0.5rem;
        padding: 1rem;
        margin-bottom: 1rem;
        background-color: white;
    }
    
    .noticia-titulo {
        font-size: 1.1rem;
        font-weight: 600;
        color: #2d3748;
        margin-bottom: 0.5rem;
        line-height: 1.4;
    }
    
    .noticia-meta {
        font-size: 0.85rem;
        color: #718096;
        margin-bottom: 0.5rem;
    }
    
    .score-badge {
        display: inline-block;
        padding: 0.2rem 0.5rem;
        border-radius: 1rem;
        font-size: 0.75rem;
        font-weight: 600;
        background-color: #edf2f7;
        color: #4a5568;
    }
    
    .page-info {
        text-align: center;
        color: #718096;
        font-size: 0.9rem;
        margin-top: 1rem;
    }
    
    .conteudo-indisponivel {
        background-color: #f7fafc;
        border: 1px solid #e2e8f0;
        border-radius: 0.375rem;
        padding: 0.75rem;
        color: #4a5568;
        font-style: italic;
        margin: 0.5rem 0;
    }
</style>
""", unsafe_allow_html=True)

# Configuração do banco de dados para Streamlit Cloud
@st.cache_resource
def get_database_path():
    """Encontra o caminho do banco de dados no Streamlit Cloud"""
    possible_paths = [
        "data/clipping_faciap.db",
        "./data/clipping_faciap.db",
        "clipping_faciap.db",
        "./clipping_faciap.db"
    ]
    
    for path in possible_paths:
        if Path(path).exists():
            return path
    
    return "data/clipping_faciap.db"

# Garante que o diretório data existe
if not os.path.exists("data"):
    os.makedirs("data")

# Funções utilitárias
@st.cache_data(ttl=300)  # Cache por 5 minutos
def carregar_dados_banco():
    """Carrega dados do banco SQLite com cache"""
    try:
        db_path = get_database_path()
        
        if not Path(db_path).exists():
            st.error(f"""
            ⚠️ Banco de dados não encontrado em: {db_path}
            
            Verifique se:
            1. O arquivo clipping_faciap.db foi enviado para o repositório
            2. Está na pasta 'data/' do repositório
            3. O deploy foi feito corretamente
            """)
            return None, None
        
        # Consulta principal
        query = """
            SELECT 
                n.id, n.titulo, n.link, n.resumo, n.fonte, n.content,
                n.data_coleta, n.data_publicacao, n.word_count,
                n.extraction_success,
                s.score_interesse, s.score_risco, s.relevancia, 
                s.eixo_principal, s.termos_encontrados
            FROM noticias n
            LEFT JOIN scoring s ON n.id = s.noticia_id
            ORDER BY n.data_publicacao DESC, n.data_coleta DESC
        """
        
        with sqlite3.connect(db_path) as conn:
            df = pd.read_sql_query(query, conn)
        
        # Processa dados
        if not df.empty:
            df['data_coleta'] = pd.to_datetime(df['data_coleta'])
            df['data_publicacao'] = pd.to_datetime(df['data_publicacao'])
            df['score_interesse'] = df['score_interesse'].fillna(0)
            df['relevancia'] = df['relevancia'].fillna('Baixa')
        
        # Estatísticas básicas
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute("SELECT COUNT(*) FROM noticias")
            total_noticias = cursor.fetchone()[0]
            
            cursor.execute("SELECT fonte, COUNT(*) FROM noticias GROUP BY fonte")
            por_fonte = dict(cursor.fetchall())
            
            cursor.execute("SELECT COUNT(*) FROM noticias WHERE extraction_success = 1")
            com_conteudo = cursor.fetchone()[0]
            
            stats = {
                'total_noticias': total_noticias,
                'por_fonte': por_fonte,
                'com_conteudo': com_conteudo
            }
        
        return df, stats
        
    except Exception as e:
        st.error(f"Erro ao carregar dados: {str(e)}")
        return None, None

def formatar_fonte(fonte):
    """Converte nome da fonte para display"""
    mapping = {
        'camara_dos_deputados': 'Câmara dos Deputados',
        'senado_federal': 'Senado Federal',
        'agencia_gov': 'Agência Gov'
    }
    return mapping.get(fonte, fonte.replace('_', ' ').title())

def obter_cor_fonte(fonte):
    """Retorna classe CSS para cor da fonte"""
    if 'camara' in fonte:
        return 'fonte-camara'
    elif 'senado' in fonte:
        return 'fonte-senado'
    else:
        return 'fonte-gov'

def obter_classe_relevancia(relevancia):
    """Retorna classe CSS para relevância"""
    if relevancia == 'Alta':
        return 'relevancia-alta'
    elif relevancia == 'Média':
        return 'relevancia-media'
    else:
        return 'relevancia-baixa'

def limpar_conteudo_html(texto):
    """
    VERSÃO MELHORADA: Remove tags HTML e entidades de forma mais robusta
    """
    if not texto or pd.isna(texto):
        return None
    
    # Converte para string
    texto_str = str(texto).strip()
    
    if not texto_str:
        return None
    
    # Remove tags HTML completamente
    texto_limpo = re.sub(r'<[^>]*>', '', texto_str)
    
    # Remove entidades HTML
    texto_limpo = re.sub(r'&[a-zA-Z0-9#]+;', ' ', texto_limpo)
    
    # Remove múltiplos espaços e quebras de linha
    texto_limpo = re.sub(r'\s+', ' ', texto_limpo).strip()
    
    return texto_limpo if texto_limpo else None

def verificar_conteudo_valido(conteudo):
    """
    VERSÃO FINAL CORRIGIDA: Verifica se o conteúdo é válido para exibição
    Trata especificamente o problema do </div> no Streamlit
    """
    # Primeiro, verifica se é None, NaN ou vazio
    if conteudo is None or pd.isna(conteudo):
        return None
    
    # Converte para string e limpa
