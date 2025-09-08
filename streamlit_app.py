# Substitua estas funções no seu streamlit_app.py

import re
import html
import pandas as pd
import streamlit as st

def verificar_conteudo_valido(conteudo):
    """
    Verifica se o conteúdo é válido e devolve a versão limpa (texto sem tags).
    Rejeita entradas que sejam apenas tags ou entidades representando tags,
    ou strings muito curtas/ruído.
    """
    if conteudo is None or pd.isna(conteudo):
        return None

    texto = str(conteudo).strip()
    if not texto:
        return None

    # Rejeita se for exatamente uma entidade/tag curta
    tag_like_pattern = r'^(?:&lt;|<)\s*\/?\s*[\w:-]+(?:\s+[^&<>]*)?(?:\/)?\s*(?:&gt;|>)$'
    only_tags_pattern = r'^(?:\s*(?:<[^>]+>|\&lt;[^&]+&gt;)\s*)+$'
    if re.match(tag_like_pattern, texto, flags=re.IGNORECASE) or re.match(only_tags_pattern, texto, flags=re.IGNORECASE):
        return None

    # Remove tags HTML e entidades para avaliação do conteúdo real
    # Remove tags reais
    s = re.sub(r'<[^>]*>', ' ', texto)
    # Remove entidades do tipo &nome; e &#[0-9]+;
    s = re.sub(r'&[a-zA-Z0-9#]+;', ' ', s)
    s = re.sub(r'\s+', ' ', s).strip()

    if not s:
        return None

    # Rejeita conteúdos muito curtos ou sem letras suficientes
    if len(s) < 15:
        return None
    if len(re.findall(r'[a-zA-ZÀ-ÿ]', s)) < 8:
        return None

    # Remove quaisquer sinais < ou > restantes (defensivo)
    s = s.replace('<', '').replace('>', '')

    return s


def renderizar_conteudo_seguro(conteudo):
    """
    Retorna texto limpo pronto para exibição (SEM entidades HTML).
    Não retorna texto com &lt;/div&gt; — se inválido retorna None.
    """
    conteudo_limpo = verificar_conteudo_valido(conteudo)
    if not conteudo_limpo:
        return None

    # Garantir que não existam caracteres angulares que possam ser interpretados como HTML
    conteudo_limpo = conteudo_limpo.replace('<', '').replace('>', '')

    # Opcional: escape para qualquer caracter especial se for inserir em contexto RAW,
    # mas preferimos devolver texto plano para usar st.write/st.text.
    return conteudo_limpo


def exibir_noticia_card(noticia, index):
    """
    Renderização segura: NÃO injeta conteúdo do DB dentro de blocos raw HTML.
    Usa elementos Streamlit (st.markdown/st.text/st.info) para evitar problemas.
    """
    fonte_display = formatar_fonte(noticia['fonte'])
    cor_fonte = obter_cor_fonte(noticia['fonte'])
    classe_relevancia = obter_classe_relevancia(noticia['relevancia'])

    # Data
    data_pub = noticia['data_publicacao'].strftime('%d/%m/%Y %H:%M') if pd.notna(noticia['data_publicacao']) else "Data não disponível"
    score = noticia['score_interesse'] if pd.notna(noticia['score_interesse']) else 0

    # Conteúdos limpos (texto plano)
    titulo_limpo = renderizar_conteudo_seguro(noticia.get('titulo')) or f"Notícia {noticia.get('fonte', '')} - {data_pub}"
    resumo_limpo = renderizar_conteudo_seguro(noticia.get('resumo'))
    conteudo_limpo = renderizar_conteudo_seguro(noticia.get('content'))

    # Renderiza header com texto (não HTML bruto). Se quiser estilizar mais, use st.markdown com markdown normal.
    with st.container():
        st.markdown(f"**{titulo_limpo}**")
        meta = f"{fonte_display} • {noticia.get('relevancia', '')} • {data_pub}"
        if score > 0:
            meta += f" • Score: {score:.1f}"
        st.markdown(f"_{meta}_")

        # Resumo
        if resumo_limpo:
            resumo_preview = resumo_limpo[:300] + "..." if len(resumo_limpo) > 300 else resumo_limpo
            st.markdown(f"**Resumo:** {resumo_preview}")
        else:
            st.markdown('<div class="conteudo-indisponivel">ℹ️ Resumo não disponível para esta notícia</div>', unsafe_allow_html=True)

        # Conteúdo expandido
        if conteudo_limpo:
            with st.expander("📄 Ver conteúdo completo"):
                st.markdown(f"**Conteúdo extraído ({noticia.get('word_count', 'N/A')} palavras):**")
                conteudo_preview = conteudo_limpo[:3000] + "..." if len(conteudo_limpo) > 3000 else conteudo_limpo
                st.text(conteudo_preview)
                if noticia.get('eixo_principal'):
                    eixo_limpo = renderizar_conteudo_seguro(noticia.get('eixo_principal'))
                    if eixo_limpo:
                        st.info(f"**Eixo temático:** {eixo_limpo}")
        else:
            with st.expander("📄 Conteúdo não disponível"):
                st.markdown('<div class="conteudo-indisponivel">⚠️ O conteúdo completo não pôde ser extraído para esta notícia. Acesse o link original para ler o texto completo.</div>', unsafe_allow_html=True)

        # Link
        if noticia.get('link') and str(noticia.get('link')).strip():
            st.markdown(f"🔗 [Ver notícia original]({noticia.get('link')})")
        else:
            st.markdown("🔗 Link não disponível")
