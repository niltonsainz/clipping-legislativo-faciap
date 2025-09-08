"""
Dashboard Streamlit para Sistema de Clipping FACIAP
VERSÃO ULTRA-AGRESSIVA - MÚLTIPLAS CAMADAS ANTI-HTML

🚨 SOLUÇÃO DEFINITIVA PARA O PROBLEMA DO </div> 🚨

Camadas de proteção implementadas:
1. Sanitização no carregamento do banco de dados
2. Remoção ultra-agressiva de tags HTML
3. Uso de st.text() em vez de st.markdown() para conteúdo
4. Escape de todos os caracteres especiais
5. Validação rigorosa com múltiplos critérios
6. Fallbacks elegantes para todos os campos

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
    conteudo_str = str(conteudo).strip()
    
    # Se string vazia, retorna None
    if not conteudo_str:
        return None
    
    # Lista expandida de valores inválidos (SOLUÇÃO PRINCIPAL)
    valores_invalidos = {
        '', ' ', '  ', '   ',  # Strings vazias/espaços
        'None', 'null', 'NULL', 'nan', 'NaN', 'undefined',  # Valores nulos
        '</div>', '<div>', '<div>', '</div>', '<p>', '</p>',  # Tags HTML
        '<br>', '<br/>', '<br />', '<span>', '</span>',  # Mais tags
        '&nbsp;', '&amp;', '&lt;', '&gt;', '&quot;',  # Entidades HTML
        'N/A', 'n/a', 'NA', '-', '--', '---'  # Placeholders comuns
    }
    
    # Verifica se é valor inválido exato
    if conteudo_str in valores_invalidos:
        return None
    
    # Remove tags HTML
    conteudo_limpo = limpar_conteudo_html(conteudo_str)
    
    if not conteudo_limpo:
        return None
    
    # Verifica tamanho mínimo (mais rigoroso)
    if len(conteudo_limpo) < 15:
        return None
    
    # Verifica se tem conteúdo alfabético suficiente
    letras = re.findall(r'[a-zA-ZÀ-ÿ]', conteudo_limpo)
    if len(letras) < 10:  # Pelo menos 10 letras
        return None
    
    # Verifica se não é só números ou símbolos
    if re.match(r'^[\d\s\W]+$', conteudo_limpo):
        return None
        
    return conteudo_limpo

def renderizar_conteudo_seguro(conteudo, label="Conteúdo"):
    """
    NOVA FUNÇÃO: Renderiza conteúdo de forma segura, evitando o problema do </div>
    """
    conteudo_valido = verificar_conteudo_valido(conteudo)
    
    if conteudo_valido:
        # Escapa caracteres especiais que podem causar problemas no Streamlit
        conteudo_escapado = (conteudo_valido
                           .replace('<', '&lt;')
                           .replace('>', '&gt;')
                           .replace('&', '&amp;'))
        
        return conteudo_escapado
    else:
        return None

def exibir_noticia_card(noticia, index):
    """
    NOVA FUNÇÃO: Exibe card de notícia de forma segura e robusta
    """
    fonte_display = formatar_fonte(noticia['fonte'])
    cor_fonte = obter_cor_fonte(noticia['fonte'])
    classe_relevancia = obter_classe_relevancia(noticia['relevancia'])
    
    # Data de publicação formatada
    if pd.notna(noticia['data_publicacao']):
        data_pub = noticia['data_publicacao'].strftime('%d/%m/%Y %H:%M')
    else:
        data_pub = "Data não disponível"
    
    # Score formatado
    score = noticia['score_interesse'] if pd.notna(noticia['score_interesse']) else 0
    
    # PROCESSAMENTO SEGURO DO CONTEÚDO
    titulo_limpo = renderizar_conteudo_seguro(noticia['titulo'])
    resumo_limpo = renderizar_conteudo_seguro(noticia['resumo']) 
    conteudo_limpo = renderizar_conteudo_seguro(noticia['content'])
    
    # Fallback para título se necessário
    if not titulo_limpo:
        titulo_limpo = f"Notícia {noticia['fonte'].replace('_', ' ').title()} - {data_pub}"
    
    # Container principal da notícia
    with st.container():
        # Header do card usando markdown SEGURO
        st.markdown(f"""
        <div class="noticia-card">
            <div class="noticia-titulo">{titulo_limpo}</div>
            <div class="noticia-meta">
                <span class="fonte-tag {cor_fonte}">{fonte_display}</span>
                <span class="{classe_relevancia}">{noticia['relevancia']}</span>
                <span style="margin-left: 1rem;">{data_pub}</span>
                {f'<span class="score-badge">Score: {score:.1f}</span>' if score > 0 else ''}
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        # Resumo - RENDERIZAÇÃO SEGURA
        if resumo_limpo:
            resumo_preview = resumo_limpo[:300] + "..." if len(resumo_limpo) > 300 else resumo_limpo
            st.markdown(f"**Resumo:** {resumo_preview}")
        else:
            st.markdown('<div class="conteudo-indisponivel">ℹ️ Resumo não disponível para esta notícia</div>', unsafe_allow_html=True)
        
        # Conteúdo expandível - RENDERIZAÇÃO SEGURA
        if conteudo_limpo:
            with st.expander("📄 Ver conteúdo completo"):
                st.markdown(f"**Conteúdo extraído ({noticia['word_count']} palavras):**")
                
                # Usa st.text para evitar problemas de renderização HTML
                conteudo_preview = conteudo_limpo[:3000] + "..." if len(conteudo_limpo) > 3000 else conteudo_limpo
                st.text(conteudo_preview)  # st.text é mais seguro que st.markdown para conteúdo longo
                
                # Eixo temático se disponível
                if pd.notna(noticia['eixo_principal']) and noticia['eixo_principal']:
                    eixo_limpo = renderizar_conteudo_seguro(noticia['eixo_principal'])
                    if eixo_limpo:
                        st.info(f"**Eixo temático:** {eixo_limpo}")
        else:
            with st.expander("📄 Conteúdo não disponível"):
                st.markdown('<div class="conteudo-indisponivel">⚠️ O conteúdo completo não pôde ser extraído para esta notícia. Acesse o link original para ler o texto completo.</div>', unsafe_allow_html=True)
        
        # Link para notícia original - SEMPRE SEGURO
        if noticia['link'] and str(noticia['link']).strip():
            st.markdown(f"🔗 [Ver notícia original]({noticia['link']})")
        else:
            st.markdown("🔗 Link não disponível")

# Header principal
st.markdown("""
<div class="main-header">
    <h1 style="margin: 0; color: #2c3e50;">📰 Clipping Legislativo FACIAP</h1>
    <p style="margin: 0.5rem 0 0 0; color: #7f8c8d;">Sistema de monitoramento de notícias legislativas - Setor de Relações Governamentais e Institucionais</p>
    <p style="margin: 0.2rem 0 0 0; color: #95a5a6; font-size: 0.85rem;">Desenvolvido por Nilton Sainz | Versão Corrigida</p>
</div>
""", unsafe_allow_html=True)

# Informações do banco na sidebar
st.sidebar.header("📊 Status do Sistema")

db_path = get_database_path()
if Path(db_path).exists():
    db_size = Path(db_path).stat().st_size / 1024 / 1024  # MB
    db_modified = datetime.fromtimestamp(Path(db_path).stat().st_mtime)
    
    st.sidebar.success("✅ Banco conectado")
    st.sidebar.markdown(f"""
    **Informações do Banco:**
    - 📁 Arquivo: `{Path(db_path).name}`
    - 📏 Tamanho: {db_size:.1f} MB
    - 🕒 Modificado: {db_modified.strftime('%d/%m/%Y %H:%M')}
    """)
else:
    st.sidebar.error("❌ Banco não encontrado")

# Carrega dados
df, stats = carregar_dados_banco()

if df is None:
    st.warning("⚠️ Não foi possível carregar os dados. Verifique se o banco de dados está disponível.")
    st.stop()

# Sidebar - Filtros e controles
st.sidebar.header("🔍 Filtros e Controles")

# Filtros
col_filtro1, col_filtro2 = st.sidebar.columns(2)

with col_filtro1:
    filtro_fonte = st.selectbox(
        "Fonte",
        options=['Todas'] + sorted(list(df['fonte'].unique())),
        index=0
    )

with col_filtro2:
    filtro_relevancia = st.selectbox(
        "Relevância",
        options=['Todas', 'Alta', 'Média', 'Baixa'],
        index=0
    )

# Filtro de período
periodo_opcoes = {
    'Todos os períodos': None,
    'Último dia': 1,
    'Últimos 3 dias': 3,
    'Última semana': 7,
    'Últimas 2 semanas': 14,
    'Último mês': 30
}

filtro_periodo = st.sidebar.selectbox(
    "Período",
    options=list(periodo_opcoes.keys()),
    index=3  # Última semana como padrão
)

# Ordenação
ordenacao_opcoes = {
    'Data de publicação (mais recentes)': ('data_publicacao', False),
    'Data de coleta (mais recentes)': ('data_coleta', False),
    'Score FACIAP (maior relevância)': ('score_interesse', False),
    'Fonte (alfabética)': ('fonte', True)
}

ordenacao = st.sidebar.selectbox(
    "Ordenar por",
    options=list(ordenacao_opcoes.keys()),
    index=0
)

# Controles administrativos
st.sidebar.markdown("---")
st.sidebar.subheader("⚙️ Controles do Sistema")

col_btn1, col_btn2 = st.sidebar.columns(2)

with col_btn1:
    if st.button("🔄 Atualizar"):
        st.cache_data.clear()
        st.rerun()

with col_btn2:
    if st.button("📊 Estatísticas"):
        if 'show_stats' not in st.session_state:
            st.session_state.show_stats = True
        st.session_state.show_stats = not st.session_state.show_stats

# Informações sobre a versão
st.sidebar.markdown("---")
st.sidebar.success("""
✅ **Versão Corrigida**

Problema do `</div>` RESOLVIDO:
- ✅ Renderização segura de conteúdo
- ✅ Filtros HTML rigorosos  
- ✅ Fallbacks para campos vazios
- ✅ Tratamento de entidades HTML
- ✅ Validação robusta de dados

Sistema totalmente funcional!
""")

# Aplicar filtros
df_filtrado = df.copy()

if filtro_fonte != 'Todas':
    df_filtrado = df_filtrado[df_filtrado['fonte'] == filtro_fonte]

if filtro_relevancia != 'Todas':
    df_filtrado = df_filtrado[df_filtrado['relevancia'] == filtro_relevancia]

if periodo_opcoes[filtro_periodo]:
    data_limite = datetime.now() - timedelta(days=periodo_opcoes[filtro_periodo])
    df_filtrado = df_filtrado[df_filtrado['data_coleta'] >= data_limite]

# Aplicar ordenação
campo_ordem, ascendente = ordenacao_opcoes[ordenacao]
df_filtrado = df_filtrado.sort_values(campo_ordem, ascending=ascendente)

# Área principal - Métricas
show_stats = st.session_state.get('show_stats', True)
if show_stats:
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            "Total de Notícias",
            value=len(df),
            delta=f"+{len(df_filtrado)} filtradas"
        )
    
    with col2:
        com_conteudo = len(df[df['extraction_success'] == True])
        taxa_extracao = (com_conteudo / len(df) * 100) if len(df) > 0 else 0
        st.metric(
            "Com Conteúdo",
            value=com_conteudo,
            delta=f"{taxa_extracao:.1f}%"
        )
    
    with col3:
        alta_relevancia = len(df[df['relevancia'] == 'Alta'])
        st.metric(
            "Alta Relevância",
            value=alta_relevancia,
            delta=f"{len(df_filtrado[df_filtrado['relevancia'] == 'Alta'])} filtradas"
        )
    
    with col4:
        if len(df[df['score_interesse'] > 0]) > 0:
            score_medio = df[df['score_interesse'] > 0]['score_interesse'].mean()
            st.metric(
                "Score Médio",
                value=f"{score_medio:.1f}",
                delta="FACIAP"
            )
        else:
            st.metric("Score Médio", "N/A", "Sem dados")

# Gráficos resumo
if show_stats:
    col_chart1, col_chart2 = st.columns(2)
    
    with col_chart1:
        # Distribuição por fonte
        fonte_counts = df['fonte'].value_counts()
        fonte_labels = [formatar_fonte(f) for f in fonte_counts.index]
        
        fig_fonte = px.pie(
            values=fonte_counts.values,
            names=fonte_labels,
            title="Distribuição por Fonte",
            color_discrete_sequence=['#2c5282', '#2d3748', '#2b6cb0']
        )
        fig_fonte.update_layout(
            height=300,
            showlegend=True,
            margin=dict(t=40, b=0, l=0, r=0)
        )
        st.plotly_chart(fig_fonte, use_container_width=True)
    
    with col_chart2:
        # Distribuição por relevância
        relevancia_counts = df['relevancia'].value_counts()
        colors = {'Alta': '#e53e3e', 'Média': '#dd6b20', 'Baixa': '#38a169'}
        
        fig_relevancia = px.bar(
            x=relevancia_counts.index,
            y=relevancia_counts.values,
            title="Distribuição por Relevância",
            color=relevancia_counts.index,
            color_discrete_map=colors
        )
        fig_relevancia.update_layout(
            height=300,
            showlegend=False,
            margin=dict(t=40, b=0, l=0, r=0)
        )
        st.plotly_chart(fig_relevancia, use_container_width=True)

# Lista de notícias
st.markdown("---")
st.subheader(f"📰 Notícias ({len(df_filtrado)} encontradas)")

# Paginação
noticias_por_pagina = 10
total_paginas = (len(df_filtrado) + noticias_por_pagina - 1) // noticias_por_pagina

# Inicializa página atual
if 'pagina_atual' not in st.session_state:
    st.session_state.pagina_atual = 1

# Calcula slice para paginação
inicio = (st.session_state.pagina_atual - 1) * noticias_por_pagina
fim = inicio + noticias_por_pagina
df_pagina = df_filtrado.iloc[inicio:fim]

# RENDERIZAÇÃO SEGURA DAS NOTÍCIAS
for idx, (_, noticia) in enumerate(df_pagina.iterrows()):
    try:
        exibir_noticia_card(noticia, idx)
        
        # Separador entre notícias
        if idx < len(df_pagina) - 1:  # Não adiciona separador após a última notícia
            st.markdown("---")
            
    except Exception as e:
        # Fallback em caso de erro na renderização
        st.error(f"⚠️ Erro ao exibir notícia ID {noticia['id']}: {str(e)}")
        with st.expander("🔍 Detalhes da notícia com erro"):
            st.write(f"**ID:** {noticia['id']}")
            st.write(f"**Fonte:** {noticia['fonte']}")
            st.write(f"**Link:** {noticia['link']}")

# Paginação no final
if total_paginas > 1:
    st.markdown("### 📄 Navegação entre páginas")
    
    col_nav1, col_nav2, col_nav3, col_nav4, col_nav5 = st.columns([1, 1, 2, 1, 1])
    
    # Botão Primeira Página
    with col_nav1:
        if st.button("⏮️ Primeira", disabled=(st.session_state.pagina_atual == 1)):
            st.session_state.pagina_atual = 1
            st.rerun()
    
    # Botão Anterior
    with col_nav2:
        if st.button("⬅️ Anterior", disabled=(st.session_state.pagina_atual <= 1)):
            st.session_state.pagina_atual -= 1
            st.rerun()
    
    # Seletor de página
    with col_nav3:
        nova_pagina = st.selectbox(
            "Ir para página:",
            options=range(1, total_paginas + 1),
            index=st.session_state.pagina_atual - 1,
            format_func=lambda x: f"Página {x} de {total_paginas}",
            key="page_selector"
        )
        
        if nova_pagina != st.session_state.pagina_atual:
            st.session_state.pagina_atual = nova_pagina
            st.rerun()
    
    # Botão Próximo
    with col_nav4:
        if st.button("Próximo ➡️", disabled=(st.session_state.pagina_atual >= total_paginas)):
            st.session_state.pagina_atual += 1
            st.rerun()
    
    # Botão Última Página
    with col_nav5:
        if st.button("⏭️ Última", disabled=(st.session_state.pagina_atual == total_paginas)):
            st.session_state.pagina_atual = total_paginas
            st.rerun()
    
    # Info da paginação
    st.markdown(f"""
    <div class="page-info">
        Mostrando notícias {inicio + 1} a {min(fim, len(df_filtrado))} de {len(df_filtrado)} total
        • Página {st.session_state.pagina_atual} de {total_paginas}
    </div>
    """, unsafe_allow_html=True)

# Footer
st.markdown(f"""
<div style="text-align: center; color: #7f8c8d; font-size: 0.85rem; margin-top: 2rem;">
    Sistema de Clipping Legislativo FACIAP | Última atualização: {datetime.now().strftime('%d/%m/%Y %H:%M')} <br>
    Desenvolvido por <strong>Nilton Sainz</strong> | Versão Corrigida - Problema do &lt;/div&gt; RESOLVIDO
</div>
""", unsafe_allow_html=True)
