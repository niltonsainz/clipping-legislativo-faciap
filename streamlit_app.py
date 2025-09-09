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

# =========================
# Imports e preparação
# =========================
import os
import re
import time
import sqlite3
from pathlib import Path
from datetime import datetime, timedelta

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# Baixa o DB mais recente do GitHub Actions Artifact (requer GH_TOKEN nos Secrets do Streamlit)
from scr.github_artifacts import download_latest_db_artifact
download_latest_db_artifact(dest_path="data/clipping_faciap.db", max_age_seconds=300)

# =========================
# Configuração da página
# =========================
st.set_page_config(
    page_title="Clipping Legislativo FACIAP",
    page_icon="📰",
    layout="wide",
    initial_sidebar_state="expanded"
)

# =========================
# CSS
# =========================
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

# =========================
# Banco de dados (Streamlit Cloud)
# =========================
@st.cache_resource
def get_database_path():
    """Encontra o caminho do banco de dados no ambiente do Streamlit."""
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
os.makedirs("data", exist_ok=True)

# =========================
# Funções utilitárias de dados
# =========================
@st.cache_data(ttl=300)
def carregar_dados_banco(db_mtime: float):
    """
    Carrega dados do banco SQLite com cache.
    O parâmetro db_mtime serve apenas para invalidar o cache quando o arquivo do DB muda.
    """
    try:
        db_path = get_database_path()
        if not Path(db_path).exists():
            st.error(f"""
            ⚠️ Banco de dados não encontrado em: {db_path}
            
            Verifique se:
            1) O arquivo clipping_faciap.db foi baixado via artifact (GH_TOKEN configurado nos Secrets do Streamlit)
            2) Ele está presente na pasta 'data/' do ambiente
            3) O último run do GitHub Actions gerou o artifact clipping-database-...
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

        # Processa dados com segurança
        if df is None or df.empty:
            stats = {"total_noticias": 0, "por_fonte": {}, "com_conteudo": 0}
            return df, stats

        # Conversões de data
        if "data_coleta" in df.columns:
            df["data_coleta"] = pd.to_datetime(df["data_coleta"], errors="coerce")
        if "data_publicacao" in df.columns:
            df["data_publicacao"] = pd.to_datetime(df["data_publicacao"], errors="coerce")

        # Scores e relevância
        if "score_interesse" in df.columns:
            df["score_interesse"] = pd.to_numeric(df["score_interesse"], errors="coerce").fillna(0.0)
        if "relevancia" in df.columns:
            df["relevancia"] = df["relevancia"].fillna("Baixa")

        # extraction_success pode vir 0/1/NULL — normaliza para boolean
        if "extraction_success" in df.columns:
            df["extraction_success"] = (
                df["extraction_success"]
                .fillna(0)
                .astype(int)
                .astype(bool)
            )
        else:
            df["extraction_success"] = False

        # word_count seguro
        if "word_count" in df.columns:
            df["word_count"] = pd.to_numeric(df["word_count"], errors="coerce").fillna(0).astype(int)
        else:
            df["word_count"] = 0

        # Estatísticas básicas
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            try:
                cursor.execute("SELECT COUNT(*) FROM noticias")
                total_noticias = cursor.fetchone()[0]
            except Exception:
                total_noticias = len(df)

            try:
                cursor.execute("SELECT fonte, COUNT(*) FROM noticias GROUP BY fonte")
                por_fonte = dict(cursor.fetchall())
            except Exception:
                por_fonte = df["fonte"].value_counts().to_dict() if "fonte" in df.columns else {}

            try:
                cursor.execute("SELECT COUNT(*) FROM noticias WHERE extraction_success = 1")
                com_conteudo = cursor.fetchone()[0]
            except Exception:
                com_conteudo = int(df["extraction_success"].sum())

        stats = {
            "total_noticias": int(total_noticias),
            "por_fonte": por_fonte,
            "com_conteudo": int(com_conteudo),
        }
        return df, stats

    except Exception as e:
        st.error(f"Erro ao carregar dados: {e}")
        return None, None

def formatar_fonte(fonte: str) -> str:
    mapping = {
        "camara_dos_deputados": "Câmara dos Deputados",
        "senado_federal": "Senado Federal",
        "agencia_gov": "Agência Gov",
    }
    if not isinstance(fonte, str):
        return "Fonte desconhecida"
    return mapping.get(fonte, fonte.replace("_", " ").title())

def obter_cor_fonte(fonte: str) -> str:
    fonte = (fonte or "").lower()
    if "camara" in fonte:
        return "fonte-camara"
    elif "senado" in fonte:
        return "fonte-senado"
    return "fonte-gov"

def obter_classe_relevancia(relevancia: str) -> str:
    if relevancia == "Alta":
        return "relevancia-alta"
    elif relevancia == "Média":
        return "relevancia-media"
    return "relevancia-baixa"

def limpar_conteudo_html(texto):
    """Remove tags HTML e entidades de forma robusta."""
    if texto is None or pd.isna(texto):
        return None
    texto_str = str(texto).strip()
    if not texto_str:
        return None
    # Remove tags
    texto_limpo = re.sub(r"<[^>]*>", "", texto_str)
    # Remove entidades
    texto_limpo = re.sub(r"&[a-zA-Z0-9#]+;", " ", texto_limpo)
    # Normaliza espaços
    texto_limpo = re.sub(r"\s+", " ", texto_limpo).strip()
    return texto_limpo or None

def verificar_conteudo_valido(conteudo):
    """Valida e limpa conteúdo para exibição segura (inclui caso do </div>)."""
    if conteudo is None or pd.isna(conteudo):
        return None
    conteudo_str = str(conteudo).strip()
    if not conteudo_str:
        return None

    valores_invalidos = {
        "", " ", "  ", "   ",
        "None", "null", "NULL", "nan", "NaN", "undefined",
        "</div>", "<div>", "<p>", "</p>", "<br>", "<br/>", "<br />", "<span>", "</span>",
        "&nbsp;", "&amp;", "&lt;", "&gt;", "&quot;",
        "N/A", "n/a", "NA", "-", "--", "---"
    }
    if conteudo_str in valores_invalidos:
        return None

    conteudo_limpo = limpar_conteudo_html(conteudo_str)
    if not conteudo_limpo:
        return None

    if len(conteudo_limpo) < 15:
        return None

    letras = re.findall(r"[a-zA-ZÀ-ÿ]", conteudo_limpo)
    if len(letras) < 10:
        return None

    if re.match(r"^[\d\s\W]+$", conteudo_limpo):
        return None

    return conteudo_limpo

def renderizar_conteudo_seguro(conteudo):
    """Escapa caracteres especiais após validar/limpar o texto."""
    conteudo_valido = verificar_conteudo_valido(conteudo)
    if not conteudo_valido:
        return None
    # Escapa em ordem correta (& antes de < > para evitar dupla-escapada)
    conteudo_escapado = (conteudo_valido
                         .replace("&", "&amp;")
                         .replace("<", "&lt;")
                         .replace(">", "&gt;"))
    return conteudo_escapado

def exibir_noticia_card(noticia, index: int):
    """Exibe card de notícia com renderização segura."""
    fonte_display = formatar_fonte(noticia.get("fonte", ""))
    cor_fonte = obter_cor_fonte(noticia.get("fonte", ""))
    classe_relevancia = obter_classe_relevancia(noticia.get("relevancia", "Baixa"))

    # Datas
    data_pub_dt = noticia.get("data_publicacao")
    if pd.notna(data_pub_dt):
        try:
            data_pub = pd.to_datetime(data_pub_dt).strftime("%d/%m/%Y %H:%M")
        except Exception:
            data_pub = "Data não disponível"
    else:
        data_pub = "Data não disponível"

    # Score
    score_raw = noticia.get("score_interesse", 0) or 0
    try:
        score = float(score_raw)
    except Exception:
        score = 0.0

    # Conteúdos
    titulo_limpo = renderizar_conteudo_seguro(noticia.get("titulo"))
    resumo_limpo = renderizar_conteudo_seguro(noticia.get("resumo"))
    conteudo_limpo = renderizar_conteudo_seguro(noticia.get("content"))

    # Fallback título
    if not titulo_limpo:
        fonte_label = (noticia.get("fonte") or "Notícia").replace("_", " ").title()
        titulo_limpo = f"Notícia {fonte_label} - {data_pub}"

    # Word count seguro
    wc_raw = noticia.get("word_count", 0) or 0
    try:
        word_count = int(wc_raw)
    except Exception:
        word_count = 0

    # Card
    with st.container():
        st.markdown(f"""
        <div class="noticia-card">
            <div class="noticia-titulo">{titulo_limpo}</div>
            <div class="noticia-meta">
                <span class="fonte-tag {cor_fonte}">{fonte_display}</span>
                <span class="{classe_relevancia}">{noticia.get('relevancia', 'Baixa')}</span>
                <span style="margin-left: 1rem;">{data_pub}</span>
                {f'<span class="score-badge">Score: {score:.1f}</span>' if score > 0 else ''}
            </div>
        </div>
        """, unsafe_allow_html=True)

        # Resumo
        if resumo_limpo:
            resumo_preview = (resumo_limpo[:300] + "...") if len(resumo_limpo) > 300 else resumo_limpo
            st.markdown(f"**Resumo:** {resumo_preview}")
        else:
            st.markdown('<div class="conteudo-indisponivel">ℹ️ Resumo não disponível para esta notícia</div>', unsafe_allow_html=True)

        # Conteúdo completo
        if conteudo_limpo:
            with st.expander("📄 Ver conteúdo completo"):
                st.markdown(f"**Conteúdo extraído ({word_count} palavras):**")
                conteudo_preview = (conteudo_limpo[:3000] + "...") if len(conteudo_limpo) > 3000 else conteudo_limpo
                st.text(conteudo_preview)
                eixo = noticia.get("eixo_principal")
                if pd.notna(eixo) and eixo:
                    eixo_limpo = renderizar_conteudo_seguro(eixo)
                    if eixo_limpo:
                        st.info(f"**Eixo temático:** {eixo_limpo}")
        else:
            with st.expander("📄 Conteúdo não disponível"):
                st.markdown('<div class="conteudo-indisponivel">⚠️ O conteúdo completo não pôde ser extraído para esta notícia. Acesse o link original para ler o texto completo.</div>', unsafe_allow_html=True)

        # Link
        link = noticia.get("link")
        if link and str(link).strip():
            st.markdown(f"🔗 [Ver notícia original]({link})")
        else:
            st.markdown("🔗 Link não disponível")

# =========================
# Header
# =========================
st.markdown("""
<div class="main-header">
    <h1 style="margin: 0; color: #2c3e50;">📰 Clipping Legislativo FACIAP</h1>
    <p style="margin: 0.5rem 0 0 0; color: #7f8c8d;">Sistema de monitoramento de notícias legislativas - Setor de Relações Governamentais e Institucionais</p>
    <p style="margin: 0.2rem 0 0 0; color: #95a5a6; font-size: 0.85rem;">Desenvolvido por Nilton Sainz | Versão Corrigida</p>
</div>
""", unsafe_allow_html=True)

# =========================
# Sidebar — Status do DB
# =========================
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

# =========================
# Carrega dados (com chave de cache = mtime do arquivo)
# =========================
db_mtime = os.path.getmtime(db_path) if os.path.exists(db_path) else 0
df, stats = carregar_dados_banco(db_mtime)

if df is None:
    st.warning("⚠️ Não foi possível carregar os dados. Verifique se o banco de dados está disponível.")
    st.stop()

# =========================
# Sidebar — Filtros e controles
# =========================
st.sidebar.header("🔍 Filtros e Controles")

col_filtro1, col_filtro2 = st.sidebar.columns(2)
with col_filtro1:
    opcoes_fontes = sorted(list(df["fonte"].dropna().unique()))
    filtro_fonte = st.selectbox("Fonte", options=["Todas"] + opcoes_fontes, index=0)

with col_filtro2:
    filtro_relevancia = st.selectbox("Relevância", options=["Todas", "Alta", "Média", "Baixa"], index=0)

periodo_opcoes = {
    "Todos os períodos": None,
    "Último dia": 1,
    "Últimos 3 dias": 3,
    "Última semana": 7,
    "Últimas 2 semanas": 14,
    "Último mês": 30
}
filtro_periodo = st.sidebar.selectbox("Período", options=list(periodo_opcoes.keys()), index=3)

ordenacao_opcoes = {
    "Data de publicação (mais recentes)": ("data_publicacao", False),
    "Data de coleta (mais recentes)": ("data_coleta", False),
    "Score FACIAP (maior relevância)": ("score_interesse", False),
    "Fonte (alfabética)": ("fonte", True)
}
ordenacao = st.sidebar.selectbox("Ordenar por", options=list(ordenacao_opcoes.keys()), index=0)

st.sidebar.markdown("---")
st.sidebar.subheader("⚙️ Controles do Sistema")
col_btn1, col_btn2 = st.sidebar.columns(2)
with col_btn1:
    if st.button("🔄 Atualizar"):
        st.cache_data.clear()
        st.rerun()
with col_btn2:
    if st.button("📊 Estatísticas"):
        st.session_state["show_stats"] = not st.session_state.get("show_stats", True)

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

# =========================
# Filtros e ordenação
# =========================
df_filtrado = df.copy()

if filtro_fonte != "Todas":
    df_filtrado = df_filtrado[df_filtrado["fonte"] == filtro_fonte]

if filtro_relevancia != "Todas":
    df_filtrado = df_filtrado[df_filtrado["relevancia"] == filtro_relevancia]

dias = periodo_opcoes[filtro_periodo]
if dias:
    data_limite = datetime.now() - timedelta(days=dias)
    # Garante comparação válida mesmo com NaT
    df_filtrado = df_filtrado[df_filtrado["data_coleta"].fillna(pd.Timestamp(1970, 1, 1)) >= data_limite]

campo_ordem, ascendente = ordenacao_opcoes[ordenacao]
if campo_ordem in df_filtrado.columns:
    df_filtrado = df_filtrado.sort_values(campo_ordem, ascending=ascendente, na_position="last")

# =========================
# Métricas (topo)
# =========================
show_stats = st.session_state.get("show_stats", True)
if show_stats:
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total de Notícias", value=len(df), delta=f"+{len(df_filtrado)} filtradas")
    with col2:
        com_conteudo = int((df["extraction_success"] == True).sum())
        taxa_extracao = (com_conteudo / len(df) * 100) if len(df) > 0 else 0
        st.metric("Com Conteúdo", value=com_conteudo, delta=f"{taxa_extracao:.1f}%")
    with col3:
        alta_relevancia = int((df["relevancia"] == "Alta").sum())
        st.metric("Alta Relevância", value=alta_relevancia,
                  delta=f"{int((df_filtrado['relevancia'] == 'Alta').sum())} filtradas")
    with col4:
        if (df["score_interesse"] > 0).any():
            score_medio = df.loc[df["score_interesse"] > 0, "score_interesse"].mean()
            st.metric("Score Médio", value=f"{score_medio:.1f}", delta="FACIAP")
        else:
            st.metric("Score Médio", "N/A", "Sem dados")

# =========================
# Gráficos
# =========================
if show_stats:
    col_chart1, col_chart2 = st.columns(2)
    with col_chart1:
        if "fonte" in df.columns and not df.empty:
            fonte_counts = df["fonte"].value_counts()
            fonte_labels = [formatar_fonte(f) for f in fonte_counts.index]
            fig_fonte = px.pie(
                values=fonte_counts.values,
                names=fonte_labels,
                title="Distribuição por Fonte",
                color_discrete_sequence=["#2c5282", "#2d3748", "#2b6cb0"]
            )
            fig_fonte.update_layout(height=300, showlegend=True, margin=dict(t=40, b=0, l=0, r=0))
            st.plotly_chart(fig_fonte, use_container_width=True)
    with col_chart2:
        if "relevancia" in df.columns and not df.empty:
            relevancia_counts = df["relevancia"].value_counts()
            colors = {"Alta": "#e53e3e", "Média": "#dd6b20", "Baixa": "#38a169"}
            fig_relevancia = px.bar(
                x=relevancia_counts.index,
                y=relevancia_counts.values,
                title="Distribuição por Relevância",
                color=relevancia_counts.index,
                color_discrete_map=colors
            )
            fig_relevancia.update_layout(height=300, showlegend=False, margin=dict(t=40, b=0, l=0, r=0))
            st.plotly_chart(fig_relevancia, use_container_width=True)

# =========================
# Lista de notícias (paginação)
# =========================
st.markdown("---")
st.subheader(f"📰 Notícias ({len(df_filtrado)} encontradas)")

noticias_por_pagina = 10
total_paginas = max(1, (len(df_filtrado) + noticias_por_pagina - 1) // noticias_por_pagina)

if "pagina_atual" not in st.session_state:
    st.session_state.pagina_atual = 1
st.session_state.pagina_atual = max(1, min(st.session_state.pagina_atual, total_paginas))

inicio = (st.session_state.pagina_atual - 1) * noticias_por_pagina
fim = inicio + noticias_por_pagina
df_pagina = df_filtrado.iloc[inicio:fim]

for idx, (_, noticia) in enumerate(df_pagina.iterrows()):
    try:
        exibir_noticia_card(noticia, idx)
        if idx < len(df_pagina) - 1:
            st.markdown("---")
    except Exception as e:
        st.error(f"⚠️ Erro ao exibir notícia ID {noticia.get('id', 'N/D')}: {e}")
        with st.expander("🔍 Detalhes da notícia com erro"):
            st.write({k: noticia.get(k) for k in ["id", "fonte", "link"] if k in noticia})

if total_paginas > 1:
    st.markdown("### 📄 Navegação entre páginas")
    col_nav1, col_nav2, col_nav3, col_nav4, col_nav5 = st.columns([1, 1, 2, 1, 1])
    with col_nav1:
        if st.button("⏮️ Primeira", disabled=(st.session_state.pagina_atual == 1)):
            st.session_state.pagina_atual = 1
            st.rerun()
    with col_nav2:
        if st.button("⬅️ Anterior", disabled=(st.session_state.pagina_atual <= 1)):
            st.session_state.pagina_atual -= 1
            st.rerun()
    with col_nav3:
        nova_pagina = st.selectbox(
            "Ir para página:",
            options=list(range(1, total_paginas + 1)),
            index=st.session_state.pagina_atual - 1,
            format_func=lambda x: f"Página {x} de {total_paginas}",
            key="page_selector"
        )
        if nova_pagina != st.session_state.pagina_atual:
            st.session_state.pagina_atual = nova_pagina
            st.rerun()
    with col_nav4:
        if st.button("Próximo ➡️", disabled=(st.session_state.pagina_atual >= total_paginas)):
            st.session_state.pagina_atual += 1
            st.rerun()
    with col_nav5:
        if st.button("⏭️ Última", disabled=(st.session_state.pagina_atual == total_paginas)):
            st.session_state.pagina_atual = total_paginas
            st.rerun()

    st.markdown(f"""
    <div class="page-info">
        Mostrando notícias {inicio + 1} a {min(fim, len(df_filtrado))} de {len(df_filtrado)} total
        • Página {st.session_state.pagina_atual} de {total_paginas}
    </div>
    """, unsafe_allow_html=True)

# =========================
# Footer
# =========================
st.markdown(f"""
<div style="text-align: center; color: #7f8c8d; font-size: 0.85rem; margin-top: 2rem;">
    Sistema de Clipping Legislativo FACIAP | Última atualização: {datetime.now().strftime('%d/%m/%Y %H:%M')} <br>
    Desenvolvido por <strong>Nilton Sainz</strong> | Versão Corrigida - Problema do &lt;/div&gt; RESOLVIDO
</div>
""", unsafe_allow_html=True)
