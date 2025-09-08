"""
Dashboard Streamlit para Sistema de Clipping FACIAP
VERSÃO DE DEBUG - Para identificar problema do </div>

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
    page_title="Clipping FACIAP - DEBUG",
    page_icon="🐛",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS personalizado
st.markdown("""
<style>
    .debug-box {
        background-color: #fff3cd;
        border: 1px solid #ffeaa7;
        border-radius: 0.25rem;
        padding: 0.75rem;
        margin: 0.5rem 0;
        font-family: monospace;
        font-size: 0.8rem;
    }
    .error-box {
        background-color: #f8d7da;
        border: 1px solid #f5c6cb;
        border-radius: 0.25rem;
        padding: 0.75rem;
        margin: 0.5rem 0;
        font-family: monospace;
        font-size: 0.8rem;
    }
    .main-header {
        background-color: #f8f9fa;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #e74c3c;
        margin-bottom: 1rem;
    }
</style>
""", unsafe_allow_html=True)

# Configuração do banco de dados
@st.cache_resource
def get_database_path():
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

# Funções de debug
def debug_database_content():
    """Analisa o conteúdo do banco em busca de problemas"""
    db_path = get_database_path()
    
    if not Path(db_path).exists():
        st.error("Banco de dados não encontrado!")
        return
    
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        
        # Busca especificamente por registros com </div>
        cursor.execute("""
            SELECT id, titulo, resumo, content, fonte, data_coleta
            FROM noticias 
            WHERE titulo LIKE '%</div>%' 
               OR resumo LIKE '%</div>%' 
               OR content LIKE '%</div>%'
            LIMIT 10
        """)
        
        problematic_records = cursor.fetchall()
        
        if problematic_records:
            st.error(f"🐛 ENCONTRADOS {len(problematic_records)} REGISTROS COM </div>")
            
            for record in problematic_records:
                id_noticia, titulo, resumo, content, fonte, data_coleta = record
                
                st.markdown(f"""
                <div class="error-box">
                <strong>REGISTRO PROBLEMÁTICO - ID: {id_noticia}</strong><br>
                <strong>Fonte:</strong> {fonte}<br>
                <strong>Data:</strong> {data_coleta}<br>
                <strong>Título:</strong> {repr(titulo)}<br>
                <strong>Resumo:</strong> {repr(resumo)}<br>
                <strong>Content (primeiros 200 chars):</strong> {repr(str(content)[:200]) if content else 'NULL'}<br>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.success("✅ Nenhum registro com </div> encontrado no banco!")
            
        # Estatísticas gerais
        cursor.execute("SELECT COUNT(*) FROM noticias WHERE titulo IS NULL OR titulo = ''")
        titulos_vazios = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM noticias WHERE resumo IS NULL OR resumo = ''")
        resumos_vazios = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM noticias WHERE content IS NULL OR content = ''")
        content_vazio = cursor.fetchone()[0]
        
        st.markdown(f"""
        <div class="debug-box">
        <strong>ESTATÍSTICAS DO BANCO:</strong><br>
        • Títulos vazios/nulos: {titulos_vazios}<br>
        • Resumos vazios/nulos: {resumos_vazios}<br>
        • Conteúdo vazio/nulo: {content_vazio}<br>
        </div>
        """, unsafe_allow_html=True)

def debug_specific_record(record_id):
    """Debug detalhado de um registro específico"""
    db_path = get_database_path()
    
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT n.*, s.relevancia, s.score_interesse 
            FROM noticias n 
            LEFT JOIN scoring s ON n.id = s.noticia_id 
            WHERE n.id = ?
        """, (record_id,))
        
        record = cursor.fetchone()
        if record:
            cols = [desc[0] for desc in cursor.description]
            record_dict = dict(zip(cols, record))
            
            st.markdown("### 🔍 DEBUG DETALHADO DO REGISTRO")
            
            for field, value in record_dict.items():
                if value is not None:
                    display_value = repr(str(value)[:100]) if len(str(value)) > 100 else repr(value)
                    st.markdown(f"**{field}:** {display_value}")

# Função de limpeza com debug
def limpar_texto_com_debug(texto, campo_nome="campo"):
    """Limpa texto e mostra debug do processo"""
    if not texto or pd.isna(texto):
        return "", f"[{campo_nome}] Texto vazio ou NaN"
    
    original = str(texto)
    debug_info = []
    
    # Log do valor original
    debug_info.append(f"[{campo_nome}] Original: {repr(original[:50])}")
    
    # Verificação específica para </div>
    if '</div>' in original:
        debug_info.append(f"[{campo_nome}] ⚠️ CONTÉM </div>!")
    
    # Limpeza
    texto = str(texto).strip()
    
    # Lista de strings inválidas
    strings_invalidas = [
        '</div>', '<div>', '<p>', '</p>', '<br>', '<br/>', '<br />',
        '<span>', '</span>', '<em>', '</em>', '<strong>', '</strong>',
        '&nbsp;', '&amp;', '&lt;', '&gt;', '&quot;', '&#39;',
        '', ' ', '  ', '   '
    ]
    
    if texto in strings_invalidas:
        debug_info.append(f"[{campo_nome}] ❌ String inválida detectada: {repr(texto)}")
        return "", "\n".join(debug_info)
    
    # Remove HTML
    texto_antes_html = texto
    texto = re.sub(r'<[^>]*?>', '', texto)
    if texto != texto_antes_html:
        debug_info.append(f"[{campo_nome}] HTML removido: {repr(texto[:50])}")
    
    # Normaliza espaços
    texto = re.sub(r'\s+', ' ', texto).strip()
    
    # Verificação final
    if len(texto) < 10:
        debug_info.append(f"[{campo_nome}] ❌ Muito curto após limpeza: {len(texto)} chars")
        return "", "\n".join(debug_info)
    
    debug_info.append(f"[{campo_nome}] ✅ Limpo: {repr(texto[:50])}")
    return texto, "\n".join(debug_info)

# Header principal
st.markdown("""
<div class="main-header">
    <h1 style="margin: 0; color: #e74c3c;">🐛 DEBUG - Clipping Legislativo FACIAP</h1>
    <p style="margin: 0.5rem 0 0 0; color: #7f8c8d;">Versão de Debug para identificar problemas</p>
</div>
""", unsafe_allow_html=True)

# Controles de debug
st.sidebar.header("🐛 Controles de Debug")

if st.sidebar.button("🔍 Analisar Banco Completo"):
    debug_database_content()

record_id_debug = st.sidebar.number_input("ID do Registro para Debug Detalhado:", min_value=1, value=1)
if st.sidebar.button("🔍 Debug Registro Específico"):
    debug_specific_record(record_id_debug)

mostrar_debug = st.sidebar.checkbox("Mostrar Debug de Limpeza", value=True)

# Carrega dados para teste
@st.cache_data(ttl=60)  # Cache menor para debug
def carregar_dados_debug():
    try:
        db_path = get_database_path()
        
        if not Path(db_path).exists():
            return None, None
        
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
            LIMIT 10
        """
        
        with sqlite3.connect(db_path) as conn:
            df = pd.read_sql_query(query, conn)
        
        if not df.empty:
            df['data_coleta'] = pd.to_datetime(df['data_coleta'])
            df['data_publicacao'] = pd.to_datetime(df['data_publicacao'])
            df['score_interesse'] = df['score_interesse'].fillna(0)
            df['relevancia'] = df['relevancia'].fillna('Baixa')
        
        return df, {"total": len(df)}
        
    except Exception as e:
        st.error(f"Erro ao carregar dados: {str(e)}")
        return None, None

# Carrega dados
df, stats = carregar_dados_debug()

if df is not None:
    st.markdown("---")
    st.subheader(f"🧪 Teste com {len(df)} Notícias")
    
    # Debug de cada notícia
    for idx, (_, noticia) in enumerate(df.iterrows()):
        st.markdown(f"### 📰 Notícia {idx + 1} - ID: {noticia['id']}")
        
        # Debug do título
        titulo_limpo, titulo_debug = limpar_texto_com_debug(noticia['titulo'], 'TÍTULO')
        
        # Debug do resumo  
        resumo_limpo, resumo_debug = limpar_texto_com_debug(noticia['resumo'], 'RESUMO')
        
        # Debug do conteúdo
        content_limpo, content_debug = limpar_texto_com_debug(noticia['content'], 'CONTENT')
        
        # Mostra os dados brutos
        st.markdown("**📋 DADOS BRUTOS:**")
        st.markdown(f"""
        <div class="debug-box">
        <strong>Título:</strong> {repr(str(noticia['titulo'])[:100])}<br>
        <strong>Resumo:</strong> {repr(str(noticia['resumo'])[:100])}<br>
        <strong>Content:</strong> {repr(str(noticia['content'])[:100]) if pd.notna(noticia['content']) else 'NULL'}<br>
        </div>
        """, unsafe_allow_html=True)
        
        # Mostra debug da limpeza se ativado
        if mostrar_debug:
            st.markdown("**🔧 DEBUG DA LIMPEZA:**")
            st.code(titulo_debug, language="text")
            st.code(resumo_debug, language="text") 
            st.code(content_debug, language="text")
        
        # Mostra resultado final
        st.markdown("**✅ RESULTADO FINAL:**")
        if titulo_limpo:
            st.success(f"Título: {titulo_limpo[:100]}")
        else:
            st.warning("Título: (vazio após limpeza)")
            
        if resumo_limpo:
            st.info(f"Resumo: {resumo_limpo[:100]}")
        else:
            st.warning("Resumo: (vazio após limpeza)")
            
        if content_limpo:
            st.info(f"Conteúdo: {len(content_limpo)} caracteres")
        else:
            st.warning("Conteúdo: (vazio após limpeza)")
        
        st.markdown("---")
        
        # Para na primeira notícia para não sobrecarregar se houver muitas
        if idx >= 2:  # Mostra apenas 3 notícias para debug
            st.warning("Debug limitado a 3 notícias para performance")
            break

else:
    st.error("Não foi possível carregar dados para debug")

# Footer de debug
st.markdown("""
---
### 🎯 O que este debug revela:

1. **Dados Brutos**: Mostra exatamente o que está no banco
2. **Processo de Limpeza**: Rastreia cada passo da limpeza
3. **Registros Problemáticos**: Identifica onde está o `</div>`
4. **Resultado Final**: Mostra o que sobra após limpeza

**Se o `</div>` aparecer nos dados brutos, o problema está no backend (coleta/extração).**
**Se aparecer só no resultado final, o problema está na função de limpeza.**
""")
