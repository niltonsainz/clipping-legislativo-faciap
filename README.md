# 📰 Clipping Legislativo FACIAP

Sistema de monitoramento de notícias legislativas desenvolvido para a **FACIAP** (Federação das Associações Comerciais e Industriais do Paraná).

## 🎯 Sobre o Projeto

O sistema coleta, analiza e pontua automaticamente notícias de fontes legislativas brasileiras, fornecendo um dashboard intuitivo para monitoramento de temas relevantes para o setor empresarial paranaense.

### ✨ Funcionalidades

- 📊 **Dashboard interativo** com métricas em tempo real
- 🔍 **Filtros avançados** por fonte, relevância e período
- 📈 **Score de relevância FACIAP** para priorização de notícias
- 📱 **Interface responsiva** para desktop e mobile
- 🗄️ **Banco de dados SQLite** para armazenamento eficiente
- 📰 **Múltiplas fontes** (Câmara, Senado, Agência Gov)

## 🚀 Acesso Online

### Versão de Teste
**🔗 Link:** [https://clipping-legislativo-faciap.streamlit.app](https://clipping-legislativo-faciap.streamlit.app)

> **Nota:** Esta é uma versão de teste para colegas da FACIAP. Funcionalidades de coleta automática estão em desenvolvimento.

## 📋 Estrutura do Projeto

```
clipping-legislativo-faciap/
├── streamlit_app.py          # Aplicação principal
├── requirements.txt          # Dependências Python
├── data/
│   └── clipping_faciap.db   # Banco de dados SQLite
├── README.md                # Documentação
└── .gitignore              # Arquivos a ignorar
```

## 🛠️ Instalação Local

### Pré-requisitos
- Python 3.8+
- pip

### Passos para instalação

1. **Clone o repositório**
```bash
git clone https://github.com/seu-usuario/clipping-legislativo-faciap.git
cd clipping-legislativo-faciap
```

2. **Instale as dependências**
```bash
pip install -r requirements.txt
```

3. **Execute a aplicação**
```bash
streamlit run streamlit_app.py
```

4. **Acesse no navegador**
```
http://localhost:8501
```

## 📊 Funcionalidades do Dashboard

### Métricas Principais
- Total de notícias coletadas
- Taxa de extração de conteúdo
- Notícias de alta relevância
- Score médio FACIAP

### Filtros Disponíveis
- **Fonte:** Câmara, Senado, Agência Gov
- **Relevância:** Alta, Média, Baixa
- **Período:** Último dia, semana, mês
- **Ordenação:** Data, score, fonte

### Visualizações
- Gráfico de distribuição por fonte
- Gráfico de distribuição por relevância
- Lista paginada de notícias
- Preview expandível de conteúdo

## 🔧 Tecnologias Utilizadas

- **Python 3.8+**
- **Streamlit** - Framework web
- **Pandas** - Manipulação de dados
- **Plotly** - Visualizações interativas
- **SQLite** - Banco de dados
- **GitHub** - Controle de versão
- **Streamlit Cloud** - Deploy

## 👥 Para Testadores

### Como Usar
1. Acesse o link do sistema
2. Use os filtros na barra lateral
3. Explore as métricas e gráficos
4. Clique nas notícias para ver detalhes
5. Use a paginação para navegar

### Feedback
Para reportar bugs ou sugestões:
- 📧 Entre em contato com **Nilton Sainz**
- 🐛 Ou abra uma issue neste repositório

## 🔄 Roadmap

### Próximas Funcionalidades
- [ ] Coleta automática diária
- [ ] Melhorias no algoritmo de score
- [ ] Notificações por email
- [ ] API para integração
- [ ] Dashboard administrativo
- [ ] Exportação de relatórios

### Em Desenvolvimento
- [x] Interface web responsiva
- [x] Sistema de scoring
- [x] Filtros avançados
- [ ] Coleta automatizada
- [ ] Títulos completos Agência Gov

## 📝 Licença

Este projeto é de propriedade da **FACIAP** e foi desenvolvido por **Nilton Sainz**.

## 📞 Contato

**Desenvolvedor:** Nilton Sainz  
**Organização:** FACIAP - Federação das Associações Comerciais e Industriais do Paraná

---
