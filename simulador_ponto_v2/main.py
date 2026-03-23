from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from google.cloud import bigquery
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
from math import radians, sin, cos, sqrt, atan2

app = FastAPI(title="API de Pontos - Zirix")

# =========================
# CORS
# =========================
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:5500",
        "http://localhost:5500",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# =========================
# BIGQUERY
# =========================
client = bigquery.Client(project="ro-areatecnica-monitoramentov2")

TABELA_VIAGENS = "ro-areatecnica-monitoramentov2.apis_fornecedores_v2.zirix_viagens_raw"
TABELA_POSICOES = "ro-areatecnica-monitoramentov2.apis_fornecedores_v2.zirix_posicoes_gps_raw"


# =========================
# UTIL
# =========================

def formatar_datetime(valor):
    if valor is None:
        return None
    if isinstance(valor, datetime):
        return valor.isoformat()
    return str(valor)


def parse_dt(valor):
    if valor is None:
        return None

    if isinstance(valor, datetime):
        dt = valor
    else:
        texto = str(valor).replace("T", " ").strip()

        try:
            dt = datetime.fromisoformat(texto)
        except:
            return None

    if dt.tzinfo:
        dt = dt.astimezone(timezone.utc).replace(tzinfo=None)

    return dt


def haversine_metros(lat1, lon1, lat2, lon2):
    R = 6371000

    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])

    dlat = lat2 - lat1
    dlon = lon2 - lon1

    a = sin(dlat/2)**2 + cos(lat1)*cos(lat2)*sin(dlon/2)**2
    c = 2 * atan2(sqrt(a), sqrt(1-a))

    return R * c


# =========================
# LIMPEZA
# =========================

def limpar_e_amostrar_pontos(registros):
    if not registros:
        return []

    registros = sorted(registros, key=lambda x: str(x["datetime"]))

    limpos = []
    anterior = None

    for r in registros:
        lat = r["latitude"]
        lon = r["longitude"]
        dt = parse_dt(r["datetime"])

        if not lat or not lon or not dt:
            continue

        if anterior is None:
            limpos.append(r)
            anterior = r
            continue

        lat_ant = anterior["latitude"]
        lon_ant = anterior["longitude"]
        dt_ant = parse_dt(anterior["datetime"])

        if lat == lat_ant and lon == lon_ant:
            continue

        dist = haversine_metros(lat_ant, lon_ant, lat, lon)
        delta = max((dt - dt_ant).total_seconds(), 1)

        vel = (dist / delta) * 3.6

        if vel > 120:
            continue

        limpos.append(r)
        anterior = r

    if len(limpos) <= 2:
        return limpos

    amostrados = [limpos[0]]
    ultimo = limpos[0]

    for r in limpos[1:-1]:
        dt = parse_dt(r["datetime"])
        dt_ult = parse_dt(ultimo["datetime"])

        if not dt or not dt_ult:
            continue

        delta = (dt - dt_ult).total_seconds()
        dist = haversine_metros(
            ultimo["latitude"], ultimo["longitude"],
            r["latitude"], r["longitude"]
        )

        if delta >= 30 or dist >= 100:
            amostrados.append(r)
            ultimo = r

    amostrados.append(limpos[-1])

    return amostrados


# =========================
# GEOJSON
# =========================

def montar_geojson(registros):
    features = []
    linha = []

    for i, r in enumerate(registros):
        tipo = "ponto"
        if i == 0:
            tipo = "inicio"
        elif i == len(registros) - 1:
            tipo = "fim"

        lon = float(r["longitude"])
        lat = float(r["latitude"])

        linha.append([lon, lat])

        features.append({
            "type": "Feature",
            "properties": {
                "id_veiculo": r["id_veiculo"],
                "velocidade": r.get("velocidade"),
                "datetime": formatar_datetime(r["datetime"]),
                "tipo": tipo
            },
            "geometry": {
                "type": "Point",
                "coordinates": [lon, lat]
            }
        })

    features.append({
        "type": "Feature",
        "properties": {"tipo": "trajeto"},
        "geometry": {
            "type": "LineString",
            "coordinates": linha
        }
    })

    return {"type": "FeatureCollection", "features": features}


# =========================
# API VIAGENS
# =========================

@app.get("/api/viagens")
def get_viagens(
    id_veiculo: str = Query(...),
    data_inicio: Optional[str] = Query(None),
    data_fim: Optional[str] = Query(None)
):
    try:
        query = f"""
        SELECT
          id_veiculo,
          sentido,
          datetime_partida,
          datetime_chegada
        FROM `{TABELA_VIAGENS}`
        WHERE id_veiculo = @id_veiculo
          AND datetime_partida IS NOT NULL
          AND datetime_chegada IS NOT NULL
          AND (@data_inicio IS NULL OR TIMESTAMP(datetime_partida) >= TIMESTAMP(@data_inicio))
          AND (@data_fim IS NULL OR TIMESTAMP(datetime_partida) <= TIMESTAMP(@data_fim))
        ORDER BY TIMESTAMP(datetime_partida) DESC
        LIMIT 200
        """

        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("id_veiculo", "STRING", id_veiculo),
                bigquery.ScalarQueryParameter("data_inicio", "STRING", data_inicio),
                bigquery.ScalarQueryParameter("data_fim", "STRING", data_fim),
            ]
        )

        results = client.query(query, job_config=job_config).result()

        viagens = []
        for r in results:
            viagens.append({
                "id_veiculo": r["id_veiculo"],
                "sentido": r["sentido"],
                "datetime_partida": formatar_datetime(r["datetime_partida"]),
                "datetime_chegada": formatar_datetime(r["datetime_chegada"]),
            })

        return {"total": len(viagens), "viagens": viagens}

    except Exception as e:
        raise HTTPException(500, str(e))


# =========================
# API PONTOS
# =========================

@app.get("/api/pontos")
def get_pontos(
    id_veiculo: str,
    sentido: str,
    datetime_partida: str
):
    try:
        print("PARAMS:", id_veiculo, sentido, datetime_partida)

        viagem_query = f"""
        SELECT *
        FROM `{TABELA_VIAGENS}`
        WHERE id_veiculo = @id_veiculo
          AND sentido = @sentido
        ORDER BY ABS(
          TIMESTAMP_DIFF(
            TIMESTAMP(datetime_partida),
            TIMESTAMP(@dt),
            SECOND
          )
        )
        LIMIT 1
        """

        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("id_veiculo", "STRING", id_veiculo),
                bigquery.ScalarQueryParameter("sentido", "STRING", sentido),
                bigquery.ScalarQueryParameter("dt", "STRING", datetime_partida),
            ]
        )

        viagem = list(client.query(viagem_query, job_config=job_config).result())

        if not viagem:
            raise HTTPException(404, "Viagem não encontrada")

        viagem = viagem[0]

        print("VIAGEM:", dict(viagem.items()))

        pontos_query = f"""
        SELECT
          id_veiculo,
          latitude,
          longitude,
          velocidade,
          direcao,
          datetime
        FROM `{TABELA_POSICOES}`
        WHERE id_veiculo = @id_veiculo
          AND TIMESTAMP(datetime)
              BETWEEN TIMESTAMP(@inicio) - INTERVAL 5 MINUTE
                  AND TIMESTAMP(@fim) + INTERVAL 5 MINUTE
          AND latitude IS NOT NULL
          AND longitude IS NOT NULL
        ORDER BY TIMESTAMP(datetime)
        """

        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("id_veiculo", "STRING", id_veiculo),
                bigquery.ScalarQueryParameter("inicio", "STRING", viagem["datetime_partida"]),
                bigquery.ScalarQueryParameter("fim", "STRING", viagem["datetime_chegada"]),
            ]
        )

        pontos_result = client.query(pontos_query, job_config=job_config).result()

        registros = []
        for r in pontos_result:
            registros.append({
                "id_veiculo": r["id_veiculo"],
                "latitude": float(r["latitude"]),
                "longitude": float(r["longitude"]),
                "velocidade": r["velocidade"],
                "direcao": r["direcao"],
                "datetime": r["datetime"]
            })

        if not registros:
            raise HTTPException(404, "Nenhum ponto encontrado")

        pontos = limpar_e_amostrar_pontos(registros)

        return {
            "viagem": {
                "id_veiculo": viagem["id_veiculo"],
                "sentido": viagem["sentido"],
                "datetime_partida": formatar_datetime(viagem["datetime_partida"]),
                "datetime_chegada": formatar_datetime(viagem["datetime_chegada"]),
                "pontos_brutos": len(registros),
                "pontos_filtrados": len(pontos)
            },
            "geojson": montar_geojson(pontos)
        }

    except Exception as e:
        print("ERRO:", e)
        raise HTTPException(500, str(e))