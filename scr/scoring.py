"""
Sistema de scoring FACIAP para classificação de relevância
"""
import pandas as pd
import re
import json
from typing import Dict, List, Optional
from scr.config import Config

class FACIAPScoring:
    """Sistema de pontuação FACIAP para notícias legislativas"""
    
    def __init__(self, dictionary_path: Optional[str] = None):
        self.dictionary_path = dictionary_path or Config.DICTIONARY_FILE
        self.dictionary_df = self._load_dictionary()
        
        # Mapeamento de acentos para normalização
        self.normalization_map = {
            'à': 'a', 'á': 'a', 'ã': 'a', 'â': 'a',
            'è': 'e', 'é': 'e', 'ê': 'e',
            'ì': 'i', 'í': 'i', 'î': 'i',
            'ò': 'o', 'ó': 'o', 'õ': 'o', 'ô': 'o',
            'ù': 'u', 'ú': 'u', 'û': 'u',
            'ç': 'c'
        }
    
    def _load_dictionary(self) -> Optional[pd.DataFrame]:
        """Carrega o dicionário FACIAP"""
        try:
            df = pd.read_csv(self.dictionary_path, sep=';', encoding='utf-8')
            print(f"📚 Dicionário FACIAP carregado: {len(df)} termos")
            return df
        except FileNotFoundError:
            print("⚠️ ATENÇÃO: Dicionário FACIAP não encontrado!")
            print(f"   • Arquivo esperado: {self.dictionary_path}")
            return None
        except Exception as e:
            print(f"❌ Erro ao carregar dicionário: {e}")
            return None
    
    def score_content(self, titulo: str, conteudo: str) -> Dict:
        """Calcula scoring de interesse e risco para o conteúdo"""
        resultado_padrao = {
            'score_interesse_total': 0,
            'score_risco_total': 0,
            'eixo_principal': '',
            'relevancia': 'Baixa',
            'termos_encontrados': 0,
            'termos_detalhes': []
        }
        
        if self.dictionary_df is None or self.dictionary_df.empty:
            return resultado_padrao
        
        # Prepara texto para análise
        texto_completo = f"{titulo} {conteudo}".lower()
        texto_normalizado = self._normalize_text(texto_completo)
        
        # Análise termo por termo
        termos_encontrados = []
        eixos_scores = {}
        
        for _, row in self.dictionary_df.iterrows():
            termo_info = self._analyze_term(row, texto_normalizado)
            
            if termo_info and termo_info['count'] > 0:
                termos_encontrados.append(termo_info)
                
                # Acumula scores por eixo
                eixo = termo_info['eixo']
                if eixo not in eixos_scores:
                    eixos_scores[eixo] = {'interesse': 0, 'risco': 0, 'termos': 0}
                
                eixos_scores[eixo]['interesse'] += termo_info['score_contribuicao']
                eixos_scores[eixo]['risco'] += termo_info['count'] * termo_info['peso_risco']
                eixos_scores[eixo]['termos'] += 1
        
        # Cálculos finais
        score_interesse_total = sum(t['score_contribuicao'] for t in termos_encontrados)
        score_risco_total = sum(t['count'] * t['peso_risco'] for t in termos_encontrados)
        
        # Eixo principal (com maior score de interesse)
        eixo_principal = ""
        if eixos_scores:
            eixo_principal = max(eixos_scores.items(), key=lambda x: x[1]['interesse'])[0]
        
        # Classificação de relevância
        relevancia = self._classify_relevance(score_interesse_total)
        
        return {
            'score_interesse_total': score_interesse_total,
            'score_risco_total': score_risco_total,
            'eixo_principal': eixo_principal,
            'relevancia': relevancia,
            'termos_encontrados': len(termos_encontrados),
            'termos_detalhes': termos_encontrados[:10],  # Limita para evitar dados muito grandes
            'eixos_scores': eixos_scores
        }
    
    def _normalize_text(self, text: str) -> str:
        """Normaliza texto removendo acentos"""
        for acento, normal in self.normalization_map.items():
            text = text.replace(acento, normal)
        return text
    
    def _analyze_term(self, row: pd.Series, texto: str) -> Optional[Dict]:
        """Analisa um termo específico no texto"""
        try:
            termo = str(row['palavra_chave']).lower()
            eixo = str(row.get('eixo_temat', 'Geral'))
            peso_interesse = float(row.get('peso_interesse', 1))
            peso_risco = float(row.get('peso_risco', 1))
            tipo = str(row.get('tipo', 'palavra'))
            
            # Normaliza o termo
            termo_normalizado = self._normalize_text(termo)
            
            # Contagem de ocorrências baseada no tipo
            if tipo == 'expressão' or ' ' in termo_normalizado:
                # Para expressões, busca exata
                count = len(re.findall(re.escape(termo_normalizado), texto))
            else:
                # Para palavras, busca com fronteira
                pattern = r'\b' + re.escape(termo_normalizado) + r'\b'
                count = len(re.findall(pattern, texto))
            
            if count > 0:
                return {
                    'termo': termo,
                    'eixo': eixo,
                    'count': count,
                    'peso_interesse': peso_interesse,
                    'peso_risco': peso_risco,
                    'score_contribuicao': count * peso_interesse
                }
            
            return None
            
        except Exception:
            return None
    
    def _classify_relevance(self, score: float) -> str:
        """Classifica relevância baseada no score"""
        if score >= 15:
            return 'Alta'
        elif score >= 8:
            return 'Média'
        elif score >= 3:
            return 'Baixa-Média'
        else:
            return 'Baixa'

# Função utilitária para manter compatibilidade
def score_content_faciap(titulo: str, conteudo: str, dicionario_df: pd.DataFrame) -> Dict:
    """Função utilitária para scoring compatível com código existente"""
    if dicionario_df is None:
        return {
            'score_interesse_total': 0,
            'score_risco_total': 0,
            'eixo_principal': '',
            'relevancia': 'Baixa',
            'termos_encontrados': 0,
            'termos_detalhes': []
        }
    
    # Cria instância temporária do scoring
    scoring = FACIAPScoring()
    scoring.dictionary_df = dicionario_df
    return scoring.score_content(titulo, conteudo)

def load_dictionary() -> Optional[pd.DataFrame]:
    """Carrega dicionário FACIAP"""
    try:
        return pd.read_csv(Config.DICTIONARY_FILE)
    except:

        return None
