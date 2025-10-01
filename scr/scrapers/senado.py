#!/usr/bin/env python3
"""
Script para testar o SenadoScraper melhorado
"""
import sys
import os
from datetime import datetime

# Adiciona o diretório do projeto ao path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Importe seu scraper (ajuste o caminho conforme sua estrutura)
# from scrapers.senado import SenadoScraper

def test_scraper():
    """Testa o scraper e mostra os resultados"""
    print("🚀 Iniciando teste do SenadoScraper...")
    print("=" * 60)
    
    try:
        # Inicializa o scraper
        scraper = SenadoScraper()
        
        # Coleta apenas 1 página para teste rápido
        print("📰 Coletando notícias do Senado (1 página)...")
        news = scraper.scrape(max_pages=1)
        
        print(f"\n✅ Coletadas {len(news)} notícias!")
        print("=" * 60)
        
        # Mostra as primeiras 5 notícias
        for i, item in enumerate(news[:5], 1):
            print(f"\n📋 NOTÍCIA {i}:")
            print(f"Título: {item['titulo']}")
            print(f"Data Pub: {item['data_publicacao']}")
            print(f"Resumo: {item['resumo'][:100]}{'...' if len(item['resumo']) > 100 else ''}")
            print(f"Link: {item['link']}")
            print("-" * 40)
        
        # Estatísticas
        print(f"\n📊 ESTATÍSTICAS:")
        com_data = sum(1 for item in news if item['data_publicacao'])
        com_resumo = sum(1 for item in news if item['resumo'])
        
        print(f"Total de notícias: {len(news)}")
        print(f"Com data de publicação: {com_data} ({com_data/len(news)*100:.1f}%)")
        print(f"Com resumo: {com_resumo} ({com_resumo/len(news)*100:.1f}%)")
        
        # Verifica se há títulos com datas
        titulos_com_data = []
        for item in news:
            if re.search(r'\d{2}/\d{2}/\d{4}', item['titulo']):
                titulos_com_data.append(item['titulo'])
        
        if titulos_com_data:
            print(f"\n⚠️ ATENÇÃO: {len(titulos_com_data)} títulos ainda contêm datas:")
            for titulo in titulos_com_data[:3]:
                print(f"  - {titulo[:80]}...")
        else:
            print("\n✅ Nenhum título contém datas! Perfeito!")
        
        # Salva resultado em JSON para análise
        save_results(news)
        
    except Exception as e:
        print(f"❌ Erro durante o teste: {e}")
        import traceback
        traceback.print_exc()

def save_results(news):
    """Salva os resultados em um arquivo JSON"""
    import json
    
    filename = f"test_senado_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(news, f, indent=2, ensure_ascii=False)
        
        print(f"💾 Resultados salvos em: {filename}")
        
    except Exception as e:
        print(f"⚠️ Erro ao salvar: {e}")

def test_individual_functions():
    """Testa funções específicas do scraper"""
    print("\n🔧 TESTANDO FUNÇÕES INDIVIDUAIS:")
    print("=" * 60)
    
    try:
        import re
        scraper = SenadoScraper()
        
        # Teste de limpeza de título
        test_titles = [
            "04/09/2025 20h38 CPMI: presidente da Conafer nega irregularidades e apela ao silêncio",
            "04/09/2025 19h25 CPMI aprova rastrear visitas do 'careca do INSS' ao Congresso",
            "04/09/2025 18h38 À CPMI, diretora aponta que CGU audita todas as entidades ligadas ao INSS",
            "Proposto pelo Senado, Estatuto do Pantanal vai à sanção"
        ]
        
        print("📝 Teste de limpeza de títulos:")
        for title in test_titles:
            clean = scraper._clean_title(title)
            date = scraper._extract_date_from_title(title)
            print(f"\nOriginal: {title}")
            print(f"Limpo:    {clean}")
            print(f"Data:     {date}")
            print("-" * 40)
        
        # Teste de extração de data da URL
        print("\n🔗 Teste de extração de data da URL:")
        test_urls = [
            "/noticias/materias/2025/09/04/cpmi-ex-presidente-do-inss",
            "/noticias/materias/2024/12/15/projeto-aprovado-senado"
        ]
        
        for url in test_urls:
            date = scraper._extract_date_from_url(url)
            print(f"URL:  {url}")
            print(f"Data: {date}")
            print("-" * 40)
            
    except Exception as e:
        print(f"❌ Erro nos testes individuais: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    import re
    
    print("🧪 TESTE DO SENADO SCRAPER")
    print("=" * 60)
    
    # Teste principal
    test_scraper()
    
    # Teste de funções individuais
    test_individual_functions()
    
    print("\n✨ Teste finalizado!")
    print("\n💡 Próximo passo: Atualize o código no GitHub e monitore os resultados!")
