# 🚍 API de Visualização de Viagens (Zirix + BigQuery)

Este projeto permite visualizar trajetos de veículos (ônibus) a partir de dados de GPS armazenados no BigQuery.

A aplicação é composta por:

* 🔧 **Backend (FastAPI)** — consulta viagens e pontos
* 🗺️ **Frontend (Leaflet)** — exibe o trajeto no mapa
* ☁️ **BigQuery** — fonte de dados (viagens + posições GPS)

---

# 📌 Funcionalidades

* Buscar viagens por **ID do veículo**
* Filtrar viagens por **intervalo de data**
* Selecionar uma viagem real
* Visualizar:

  * 📍 pontos do trajeto
  * 🟢 início (buffer de 500m)
  * 🔴 fim (buffer de 500m)
  * 🔵 trajeto completo
* Limpeza automática de dados:

  * remoção de outliers (velocidade irreal)
  * remoção de pontos duplicados
  * amostragem inteligente

---

# 🧱 Estrutura do Projeto

```
simulador_ponto_v2/
│
├── main.py          # API FastAPI
├── index.html       # Interface com mapa
├── requirements.txt # Dependências (opcional)
└── README.md
```

---

# ⚙️ Pré-requisitos

* Python 3.10+
* Conta Google Cloud com acesso ao BigQuery
* Credenciais configuradas (ADC)

---

# 🔐 Configurar autenticação Google Cloud

Execute:

```bash
gcloud auth application-default login
```

Ou defina manualmente:

```bash
set GOOGLE_APPLICATION_CREDENTIALS=seu_arquivo.json
```

---

# 📦 Instalação

Clone o projeto:

```bash
git clone https://github.com/seu-usuario/seu-repo.git
cd seu-repo
```

Instale as dependências:

```bash
pip install fastapi uvicorn google-cloud-bigquery
```

---

# ▶️ Rodando o projeto

## 1. Subir a API

```bash
python -m uvicorn main:app --reload
```

API disponível em:

```
http://127.0.0.1:8000
```

Docs Swagger:

```
http://127.0.0.1:8000/docs
```

---

## 2. Subir o frontend

```bash
python -m http.server 5500
```

Acesse:

```
http://127.0.0.1:5500/index.html
```

---

# 🔍 Como usar

### 1. Buscar viagens

Digite o ID do veículo:

```
A29005
```

Clique em **Buscar viagens**

---

### 2. Selecionar viagem

Escolha uma viagem da lista:

```
A29005 | V | 2026-03-17 08:15:00
```

---

### 3. Visualizar mapa

Clique em **Carregar mapa**

---

# 🧠 Fonte de dados

BigQuery:

```
apis_fornecedores_v2.zirix_viagens_raw
apis_fornecedores_v2.zirix_posicoes_gps_raw
```

---

# 🧪 Endpoints

## 🔹 Buscar viagens

```
GET /api/viagens?id_veiculo=A29005
```

Com filtro de data:

```
GET /api/viagens?id_veiculo=A29005&data_inicio=2026-03-17 00:00:00
```

---

## 🔹 Buscar pontos da viagem

```
GET /api/pontos?id_veiculo=A29005&sentido=V&datetime_partida=2026-03-17 08:15:00
```

---

# 🧹 Tratamento de dados

A API aplica automaticamente:

* Remoção de pontos inválidos
* Filtro de velocidade (>120 km/h)
* Remoção de duplicados
* Redução de pontos:

  * 1 ponto a cada 30s
  * ou distância > 100m

---

# 🗺️ Visualização

* 🔵 Linha azul → trajeto
* 🟢 círculo verde → início (500m)
* 🔴 círculo vermelho → fim (500m)
* 🔘 pontos → posições GPS

---

# 🚀 Melhorias futuras

* [ ] Replay da viagem (animação)
* [ ] Filtro por velocidade
* [ ] Heatmap de trajetos
* [ ] Integração com Power BI
* [ ] Cache de viagens

---

# 👨‍💻 Autor

Wallace Magalhães

---

# 📄 Licença

Uso interno / técnico
