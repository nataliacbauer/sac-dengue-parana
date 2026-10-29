# Configuração oficial das 25 estações do modelo SAC Dengue Paraná
# Mapeamento estrito entre o Shapefile (cod_IBGE) e a API Simepar (api_city_id)

SAC_ESTACOES = [
    {
        "nome": "Apucarana",
        "cod_ibge": 4101408,
        "api_city_id": 4101408,
        "latitude": -23.551,
        "longitude": -51.461,
        "regional": "Norte Central"
    },
    {
        "nome": "Cambará",
        "cod_ibge": 4103701,
        "api_city_id": 4103602,
        "latitude": -23.046,
        "longitude": -50.074,
        "regional": "Norte Pioneiro"
    },
    {
        "nome": "Campo Mourão",
        "cod_ibge": 4104303,
        "api_city_id": 4104303,
        "latitude": -24.046,
        "longitude": -52.383,
        "regional": "Centro-Ocidental"
    },
    {
        "nome": "Cascavel",
        "cod_ibge": 4104808,
        "api_city_id": 4104808,
        "latitude": -24.957,
        "longitude": -53.459,
        "regional": "Oeste"
    },
    {
        "nome": "Cianorte",
        "cod_ibge": 4105508,
        "api_city_id": 4105508,
        "latitude": -23.663,
        "longitude": -52.607,
        "regional": "Noroeste"
    },
    {
        "nome": "Curitiba",
        "cod_ibge": 4106902,
        "api_city_id": 4106902,
        "latitude": -25.428,
        "longitude": -49.273,
        "regional": "Metropolitana"
    },
    {
        "nome": "Foz do Iguaçu",
        "cod_ibge": 4108304,
        "api_city_id": 4108304,
        "latitude": -25.546,
        "longitude": -54.588,
        "regional": "Oeste"
    },
    {
        "nome": "Francisco Beltrão",
        "cod_ibge": 4108403,
        "api_city_id": 4108403,
        "latitude": -26.081,
        "longitude": -53.055,
        "regional": "Sudoeste"
    },
    {
        "nome": "Guaíra",
        "cod_ibge": 4108809,
        "api_city_id": 4108809,
        "latitude": -24.080,
        "longitude": -54.256,
        "regional": "Oeste"
    },
    {
        "nome": "Guarapuava",
        "cod_ibge": 4109401,
        "api_city_id": 4109401,
        "latitude": -25.395,
        "longitude": -51.462,
        "regional": "Centro-Sul"
    },
    {
        "nome": "Guaratuba",
        "cod_ibge": 4109500,
        "api_city_id": 4109609,
        "latitude": -25.882,
        "longitude": -48.575,
        "regional": "Litoral"
    },
    {
        "nome": "Jaguariaíva",
        "cod_ibge": 4112009,
        "api_city_id": 4112009,
        "latitude": -24.250,
        "longitude": -49.706,
        "regional": "Campos Gerais"
    },
    {
        "nome": "Lapa",
        "cod_ibge": 4113205,
        "api_city_id": 4113205,
        "latitude": -25.769,
        "longitude": -49.716,
        "regional": "Metropolitana"
    },
    {
        "nome": "Laranjeiras do Sul",
        "cod_ibge": 4113403,
        "api_city_id": 4113304,
        "latitude": -25.408,
        "longitude": -52.416,
        "regional": "Centro-Sul"
    },
    {
        "nome": "Londrina",
        "cod_ibge": 4113700,
        "api_city_id": 4113700,
        "latitude": -23.310,
        "longitude": -51.162,
        "regional": "Norte Central"
    },
    {
        "nome": "Maringá",
        "cod_ibge": 4115209,
        "api_city_id": 4115200,
        "latitude": -23.420,
        "longitude": -51.933,
        "regional": "Norte Central"
    },
    {
        "nome": "Palmas",
        "cod_ibge": 4117601,
        "api_city_id": 4117602,
        "latitude": -26.484,
        "longitude": -51.989,
        "regional": "Sul"
    },
    {
        "nome": "Palmas - Horizonte",
        "cod_ibge": 4444444,
        "api_city_id": 4117602,
        "latitude": -26.583,
        "longitude": -51.521,
        "regional": "Sul"
    },
    {
        "nome": "Paranaguá",
        "cod_ibge": 4118203,
        "api_city_id": 4118204,
        "latitude": -25.520,
        "longitude": -48.509,
        "regional": "Litoral"
    },
    {
        "nome": "Paranavaí",
        "cod_ibge": 4118401,
        "api_city_id": 4118402,
        "latitude": -23.081,
        "longitude": -52.464,
        "regional": "Noroeste"
    },
    {
        "nome": "Ponta Grossa",
        "cod_ibge": 4119904,
        "api_city_id": 4119905,
        "latitude": -25.095,
        "longitude": -50.161,
        "regional": "Campos Gerais"
    },
    {
        "nome": "Santa Helena",
        "cod_ibge": 4124053,
        "api_city_id": 4123501,
        "latitude": -24.858,
        "longitude": -54.334,
        "regional": "Oeste"
    },
    {
        "nome": "Telêmaco Borba",
        "cod_ibge": 4127106,
        "api_city_id": 4127106,
        "latitude": -24.323,
        "longitude": -50.615,
        "regional": "Campos Gerais"
    },
    {
        "nome": "Umuarama",
        "cod_ibge": 4128104,
        "api_city_id": 4128104,
        "latitude": -23.766,
        "longitude": -53.325,
        "regional": "Noroeste"
    },
    {
        "nome": "União da Vitória",
        "cod_ibge": 4128203,
        "api_city_id": 4128203,
        "latitude": -26.229,
        "longitude": -51.087,
        "regional": "Sudeste"
    }
]

def get_estacoes_list():
    return SAC_ESTACOES
