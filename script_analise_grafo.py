
# 0. Pacotes
import pandas as pd
from unicodedata import normalize
from bs4 import BeautifulSoup
import urllib.request
import networkx as nx
import matplotlib.pyplot as plt
import operator


# 1. Dados
df_reembolsos = pd.read_csv("reembolsos.csv")  # junção de tabelas baixadas em http://www2.camara.leg.br/transparencia/cota-para-exercicio-da-atividade-parlamentar/dados-abertos-cota-parlamentar
df_reembolsos = df_reembolsos[df_reembolsos.cnpj_cpf.notnull()]  # desprezando casos em que o cnpj da empresa é nulo.
df_reembolsos = df_reembolsos[df_reembolsos["Ano"] > 2012]  # focando nos reembolsos a partir de 2012

df_receitas = pd.read_csv("Receitas_2014/receitas_candidatos_2014.csv")  # csv baixado em http://www.tse.jus.br/eleicoes/estatisticas/repositorio-de-dados-eleitorais
df_receitas = df_receitas[df_receitas["cargo"] == "Deputado Federal"] # somente deputados federais


# 1.1. Criando dicionário com identificador e nome completo do deputado (será necessário porque a tabela de reembolsos não tem o nome completo, só o apelido)
page = urllib.request.urlopen("http://www.camara.leg.br/SitCamaraWS/Deputados.asmx/ObterDeputados")  # link com os dados básicos dos deputados
soup = BeautifulSoup(page)
lista_dados_deputados = soup.find_all("deputado")
def remover_acentos(txt):
    return normalize("NFKD", txt).encode("ASCII", "ignore").decode("ASCII")

deputados_dict = {}
for i in range(0,len(lista_dados_deputados)):
    deputados_dict[lista_dados_deputados[i].idecadastro.string] = [remover_acentos(lista_dados_deputados[i].nome.string), lista_dados_deputados[i].urlfoto.string]


# 1.2. Tratamento dos dados
# 1.2.1. Ajustando nomes dos campos
df_reembolsos.columns = ["ano_reembolso", 'num_agente_politico', 'cod_documento_reembolso', 'valor_total_liq_reembolso', 'cod_reembolso', 'nome_agente_politico', 'doc_do_parlamentar', 'doc_parlamentar', 'mandato', 'uf', 'sigla_partido', 'cod_mandato', 'num_subquota', 'desc_subquota', 'cod_subquota', 'desc_grupo_subquota', 'nome_empresa', 'cpf_cnpj_empresa', 'num_documento_reembolso', 'tipo_documento_reembolso', 'data_emissao_doc', 'valor_doc_reembolso', 'valor_remarcado_reembolso', 'valor_liq_reembolso', 'mes', 'parcelado', 'passageiro', 'percurso_viagem', 'num_lote']

df_receitas.columns = ["seq_candidato", "uf", "sigla_partido", "num_agente_politico", "cargo", "nome_agente_politico", "cpf_agente_politico", "num_recibo_eleitoral", "num_documento", "cpf_cnpj_empresa", "nome_empresa", "cod_setor_economico", "nome_setor_economico", "data_receita", "valor_receita", "tipo_receita", "especie_recurso", "descricao_receita"]


# 1.2.2. Criando tabelas agregadas
df_reembolsos_resumo = df_reembolsos.groupby(["sigla_partido", "uf", "doc_do_parlamentar", "nome_empresa", "cpf_cnpj_empresa"]).agg({"valor_liq_reembolso": ["sum", "count"]}).reset_index()
df_reembolsos_resumo.columns = ["sigla_partido", "uf", "doc_do_parlamentar", "nome_empresa", "cpf_cnpj_empresa", "soma_valor_reesmbolsos", "qtde_reembolsos"]

df_receitas_resumo = df_receitas.groupby(["sigla_partido", "uf", "nome_agente_politico", "nome_empresa", "cpf_cnpj_empresa"]).agg({"valor_receita": ["sum", "count"]}).reset_index()
df_receitas_resumo.columns = ["sigla_partido", "uf", "nome_agente_politico", "nome_empresa", "cpf_cnpj_empresa", "soma_valor_receitas", "qtde_receitas"]
df_receitas_resumo["nome_completo"] = df_receitas_resumo["nome_agente_politico"].map(remover_acentos)

# 1.2.3. Ajuste do Nome dos deputados (na tabela de reembolsos só tem o apelido)

def nome_completo(x):
    if str(int(x)) in list(deputados_dict.keys()):
        y = deputados_dict[str(int(x))][0]
    else:
        y = "sem_info"
    return y

df_reembolsos_resumo["nome_completo"] = df_reembolsos_resumo["doc_do_parlamentar"].map(nome_completo)

# 1.2.4. Ajuste do formato do cnpj/cpf dos geradores do reembolso
df_reembolsos_resumo["cpf_cnpj_empresa"] = df_reembolsos_resumo.cpf_cnpj_empresa.apply(int)

# 1.3. Modelando como grafo
# 1.3.1. Criando tabelas de vínculos
df_vinculos_receitas = df_receitas_resumo.iloc[:,3:]
df_vinculos_receitas.columns = ["nome_empresa","id_empresa","valor","qtde", "nome_deputado"]
df_vinculos_receitas["tipo"] = "doacao"

df_vinculos_reembolsos = df_reembolsos_resumo.iloc[:,3:]
df_vinculos_reembolsos.columns = ["nome_empresa", "id_empresa", "valor", "qtde", "nome_deputado"]
df_vinculos_reembolsos = df_vinculos_reembolsos[df_vinculos_reembolsos["nome_deputado"] != "sem_info"].reset_index()
df_vinculos_reembolsos["tipo"] = "reembolso"

df_vinculos_agregado = pd.DataFrame()
df_vinculos_agregado["id_entidade_a"] = list(df_vinculos_receitas["id_empresa"]) + list(df_vinculos_reembolsos["nome_deputado"])
df_vinculos_agregado["id_entidade_b"] = list(df_vinculos_receitas["nome_deputado"]) + list(df_vinculos_reembolsos["id_empresa"])
df_vinculos_agregado["tipo"] = list(df_vinculos_receitas["tipo"]) + list(df_vinculos_reembolsos["tipo"])
df_vinculos_agregado["valor"] = list(df_vinculos_receitas["valor"]) + list(df_vinculos_reembolsos["valor"])
df_vinculos_agregado["qtde"] = list(df_vinculos_receitas["qtde"]) + list(df_vinculos_reembolsos["qtde"])
df_vinculos_agregado["nome_empresa"] = list(df_vinculos_receitas["nome_empresa"]) + list(df_vinculos_reembolsos["nome_empresa"])


# 1.3.2. Criando grafo
G = nx.from_pandas_dataframe(df_vinculos_agregado, "id_entidade_a", 'id_entidade_b', ["tipo","valor","qtde"], create_using=nx.DiGraph())
G.nodes()

# agregando atributos aos vértices
dict_nomes = {}
for i in range(0, len(df_vinculos_agregado)):
    if i < len(list(df_vinculos_receitas["nome_empresa"])):
        dict_nomes[df_vinculos_agregado.iloc[i]["id_entidade_a"]] = df_vinculos_agregado.iloc[i]["nome_empresa"]
    else:
        dict_nomes[df_vinculos_agregado.iloc[i]["id_entidade_b"]] = df_vinculos_agregado.iloc[i]["nome_empresa"]
    print(i)

nx.set_node_attributes(G, 'nome_entidade', dict_nomes)

# 1.4. Mapeando os ciclos
ciclos = list(nx.simple_cycles(G))
tam_ciclos = {}
for i in range(0, len(ciclos)):
    tam_ciclos[i] = len(ciclos[i])
    print(i)

max(tam_ciclos.items(), key=operator.itemgetter(1))[0]

# contando quantidade de ciclos por tamanho
list(tam_ciclos.values())
tam_ciclos_group = {}
for i in set(list(tam_ciclos.values())):
    tam_ciclos_group[i] = list(tam_ciclos.values()).count(i)

print("Ciclos por tamanho: " + str(tam_ciclos_group))

# 1.4.1. Criando tabela com resumo dos ciclos (ciclo, tipo)
df_ciclos_resumo = pd.DataFrame()
df_ciclos_resumo["ciclo"] = ciclos
df_ciclos_resumo["tamanho"] = list(tam_ciclos.values())

def tipo_ciclo (x):
    if x == 2:
        y = "direto"
    elif x == 4:
        y = "indireto cruzado"
    else:
        y = "indireto amplo"
    return y

df_ciclos_resumo["tipo"] = df_ciclos_resumo["tamanho"].map(tipo_ciclo)
df_ciclos_resumo_agregado = df_ciclos_resumo.groupby("tipo").agg([{"ciclo": "count"}])

# 1.4.2. Criando tabela com detalhamento dos ciclos diretos (tipo empresa -> deputado, deputado -> empresa)
lista_ciclos_diretos = []
count = 0
for i in ciclos:
    if len(i) == 2:
        dict_i = {}
        if len(G.node[i[0]]) == 1:
            dict_i["1_id_empresa"] = i[0]
            dict_i["2_nome_empresa"] = G.node[i[0]]["nome_entidade"]
            dict_i["3_nome_deputado"] = i[1]
            dict_i["4_valor_doado"] = G[i[0]][i[1]]["valor"]
            dict_i["5_qtde_doacoes"] = G[i[0]][i[1]]["qtde"]
            dict_i["6_valor_reembolsado"] = G[i[1]][i[0]]["valor"]
            dict_i["7_qtde_reembolsos"] = G[i[1]][i[0]]["qtde"]
            dict_i["8_percentual_retorno"] = (str(100*G[i[1]][i[0]]["valor"]/G[i[0]][i[1]]["valor"]) + "%")
        else:
            dict_i["1_id_empresa"] = i[1]
            dict_i["2_nome_empresa"] = G.node[i[1]]["nome_entidade"]
            dict_i["3_nome_deputado"] = i[0]
            dict_i["4_valor_doado"] = G[i[1]][i[0]]["valor"]
            dict_i["5_qtde_doacoes"] = G[i[1]][i[0]]["qtde"]
            dict_i["6_valor_reembolsado"] = G[i[0]][i[1]]["valor"]
            dict_i["7_qtde_reembolsos"] = G[i[0]][i[1]]["qtde"]
            dict_i["8_percentual_retorno"] = (str(100 * G[i[0]][i[1]]["valor"] / G[i[1]][i[0]]["valor"]) + "%")
        lista_ciclos_diretos.append(dict_i)
    count += 1
    print(count)

df_ciclos_diretos = pd.DataFrame(lista_ciclos_diretos)
df_ciclos_diretos.to_csv("df_ciclos_diretos.csv", encoding = "utf-8")
df_ciclos_diretos.iloc[:,0:7].to_csv("df_ciclos_diretos.csv", encoding = "utf-8")

# 1.4.2.1. Criando tabela agregada por deputado
df_ciclos_diretos_por_deputado = df_ciclos_diretos.groupby(["3_nome_deputado"]).agg({"2_nome_empresa": "count", "4_valor_doado": "sum", "6_valor_reembolsado": "sum"}).reset_index()

# 1.4.2.2. Plotando rede de ciclos diretos para um deputado específico
deputado = "RUBENS OTONI GOMIDE"
lista_subset_graph = list(df_ciclos_diretos[df_ciclos_diretos["3_nome_deputado"] == deputado]["1_id_empresa"]) + [deputado]
H = G.subgraph(lista_subset_graph)
nx.draw(H, style = "solid", with_labels = True)
plt.savefig("ciclos.png")  # save as png
plt.show()  # display

# 1.4.3. Plotando ciclos indiretos cruzados
ciclo_cruzado = df_ciclos_resumo[df_ciclos_resumo["tipo"] == "indireto cruzado"].iloc[3]["ciclo"]
H = G.subgraph(ciclo_cruzado)
nx.draw(H, style = "solid", with_labels = True)
plt.savefig("ciclos.png")  # save as png
plt.show()  # display

# 1.4.3.1. Criando tabela com resumo dos ciclos indiretos cruzados
lista_ciclos_cruzados = []
count = 0
for i in ciclos:
    if len(i) == 4:
        dict_i = {}
        if len(G.node[i[0]]) == 1:
            dict_i["1_id_empresa_a"] = i[0]
            dict_i["2_nome_empresa_a"] = G.node[i[0]]["nome_entidade"]
            dict_i["3_nome_deputado_x"] = i[1]
            dict_i["4_valor_doado_ax"] = G[i[0]][i[1]]["valor"]
            dict_i["5_qtde_doacoes_ax"] = G[i[0]][i[1]]["qtde"]
            dict_i["6_id_empresa_b"] = i[2]
            dict_i["7_nome_empresa_b"] = G.node[i[2]]["nome_entidade"]
            dict_i["8_valor_reembolsado_xb"] = G[i[1]][i[2]]["valor"]
            dict_i["9_qtde_reembolsos_xb"] = G[i[1]][i[2]]["qtde"]
            dict_i["10_nome_deputado_y"] = i[3]
            dict_i["11_valor_doado_by"] = G[i[2]][i[3]]["valor"]
            dict_i["12_qtde_doacoes_by"] = G[i[2]][i[3]]["qtde"]
            dict_i["13_valor_reembolsado_ya"] = G[i[3]][i[0]]["valor"]
            dict_i["14_qtde_reembolsos_ya"] = G[i[3]][i[0]]["qtde"]
        else:
            dict_i["1_id_empresa_a"] = i[3]
            dict_i["2_nome_empresa_a"] = G.node[i[3]]["nome_entidade"]
            dict_i["3_nome_deputado_x"] = i[0]
            dict_i["4_valor_doado_ax"] = G[i[3]][i[0]]["valor"]
            dict_i["5_qtde_doacoes_ax"] = G[i[3]][i[0]]["qtde"]
            dict_i["6_id_empresa_b"] = i[1]
            dict_i["7_nome_empresa_b"] = G.node[i[1]]["nome_entidade"]
            dict_i["8_valor_reembolsado_xb"] = G[i[0]][i[1]]["valor"]
            dict_i["9_qtde_reembolsos_xb"] = G[i[0]][i[1]]["qtde"]
            dict_i["10_nome_deputado_y"] = i[2]
            dict_i["11_valor_doado_by"] = G[i[1]][i[2]]["valor"]
            dict_i["12_qtde_doacoes_by"] = G[i[1]][i[2]]["qtde"]
            dict_i["13_valor_reembolsado_ya"] = G[i[2]][i[3]]["valor"]
            dict_i["14_qtde_reembolsos_ya"] = G[i[2]][i[3]]["qtde"]
        lista_ciclos_cruzados.append(dict_i)
    count += 1
    print(count)

df_ciclos_cruzados = pd.DataFrame(lista_ciclos_cruzados)
df_ciclos_cruzados.to_csv("df_ciclos_cruzados.csv")

# 1.5. Criando tabela de resumo das empresas (Empresa, Doado, Reembolsado)
df_resumo_empresas_inner = pd.merge(df_vinculos_receitas.groupby(["id_empresa", "nome_empresa"]).agg({"valor": "sum"}).reset_index(), df_vinculos_reembolsos.groupby(["id_empresa"]).agg({"valor": "sum"}).reset_index(), on='id_empresa', how='inner')
df_resumo_empresas_inner.columns = ['id_empresa', 'nome_empresa', 'valor_doado', 'valor_reembolsado']
df_resumo_empresas_inner["percentual_de_retorno"] = 100*df_resumo_empresas_inner["valor_reembolsado"]/df_resumo_empresas_inner["valor_doado"]
def percent(x):
    y = (str(x) + "%")
    return y

df_resumo_empresas_inner["percentual_de_retorno"] = df_resumo_empresas_inner["percentual_de_retorno"].map(percent)
df_resumo_empresas_inner.to_csv("df_resumo_empresas_inner.csv")

df_resumo_empresas_left = pd.merge(df_vinculos_receitas.groupby(["id_empresa", "nome_empresa"]).agg({"valor": "sum", "nome_deputado": "count"}).reset_index(), df_vinculos_reembolsos.groupby(["id_empresa"]).agg({"valor": "sum", "nome_deputado": "count"}).reset_index(), on='id_empresa', how='left')
df_resumo_empresas_left.columns = ['id_empresa', 'nome_empresa', 'valor_doado',"qtde_deputados_recebedores", 'valor_reembolsado', "qtde_deputados_pagadores"]


for i in ["valor_doado","qtde_deputados_recebedores","valor_reembolsado","qtde_deputados_pagadores"]:
    def escala(x):
        y = (x - df_resumo_empresas_left[i].min())/(df_resumo_empresas_left[i].max() - df_resumo_empresas_left[i].min())
        return y
    nome_coluna_escala = (i + "_escala")
    df_resumo_empresas_left[nome_coluna_escala] = df_resumo_empresas_left[i].map(escala)
    print(i)

df_resumo_empresas_left["indice_de_influencia"] = df_resumo_empresas_left["valor_doado_escala"] + df_resumo_empresas_left["qtde_deputados_recebedores_escala"] + df_resumo_empresas_left["valor_reembolsado_escala"] + df_resumo_empresas_left["qtde_deputados_pagadores_escala"]
df_resumo_empresas_left.to_csv("df_resumo_empresas_left.csv")

# 1.6. Criando tabela de resumo dos deputados (Empresa, Recebido, Reembolsado)
df_resumo_deputados_left = pd.merge(df_vinculos_receitas.groupby(["nome_deputado"]).agg({"valor": "sum", "id_empresa": pd.Series.nunique}).reset_index(), df_vinculos_reembolsos.groupby(["nome_deputado"]).agg({"valor": "sum", "id_empresa": pd.Series.nunique}).reset_index(), on='nome_deputado', how='left')
df_resumo_deputados_left.columns = ['nome_deputado', 'valor_recebido_doacoes', 'qtde_empresas_doadoras',"valor_pago_despesas", 'qtde_empresas_recebedoras']


for i in ["valor_recebido_doacoes","qtde_empresas_doadoras","valor_pago_despesas","qtde_empresas_recebedoras"]:
    def escala(x):
        y = (x - df_resumo_deputados_left[i].min())/(df_resumo_deputados_left[i].max() - df_resumo_deputados_left[i].min())
        return y
    nome_coluna_escala = (i + "_escala")
    df_resumo_deputados_left[nome_coluna_escala] = df_resumo_deputados_left[i].map(escala)
    print(i)

df_resumo_deputados_left["indice_de_influencia"] = df_resumo_deputados_left["valor_recebido_doacoes_escala"] + df_resumo_deputados_left["qtde_empresas_doadoras_escala"] + df_resumo_deputados_left["valor_pago_despesas_escala"] + df_resumo_deputados_left["qtde_empresas_recebedoras_escala"]
df_resumo_deputados_left.to_csv("df_resumo_deputados_left.csv")


############ Gerando grafo em d3 para visualizar em HTML ###############
# Neste caso é necessátio utilizar o arquivo HTML de template

import json
import os
import re

# montar dicionario de nós e arestas
deputado = "SILAS CAMARA"
lista_subset_graph = list(df_ciclos_diretos[df_ciclos_diretos["3_nome_deputado"] == deputado]["1_id_empresa"]) + [deputado]
H = G.subgraph(lista_subset_graph)

json_txt = dict()
json_txt["nodes"] = []
json_txt["links"] = []

for i in lista_subset_graph:
    dict_i = {}
    dict_i["id"] = str(i)
    dict_i["group"] = str(1)
    dict_i["size"] = str(3)
    json_txt["nodes"].append(dict_i)

for j in H.edges():
    dict_j = {}
    dict_j["source"] = str(j[0])
    dict_j["target"] = str(j[1])
    dict_j["value"] = str(H[j[0]][j[1]]["valor"])
    json_txt["links"].append(dict_j)


html = ''
with open(os.path.join('visualizar_grafo_template.html'), 'r', encoding='utf-8') as arq:
    html = ''.join(arq.readlines())

path_html_final = os.path.join('visualizar_grafo.html')
with open(path_html_final, 'w', encoding='utf-8') as arq:
    json_str = json.dumps(json_txt)
    html = re.sub('"{{json_data}}"', json_str, html)
    arq.write(html)

import webbrowser
webbrowser.open('file://' + os.path.realpath(path_html_final))

######################

