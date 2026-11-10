from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt
BASE_DIRETORIO = Path(__file__).resolve().parent
DATA_DIRETORIO = BASE_DIRETORIO / "Data"
GRAFICOS_DIRETORIO = BASE_DIRETORIO / "graficos"
tarifa = pd.read_csv(DATA_DIRETORIO / "tarifa_media_sp.csv", sep=";", decimal=",")
aparelho = pd.read_csv(DATA_DIRETORIO / "aparelhos_consumo_energia.csv", sep=";", decimal=",")
bandeira = pd.read_csv(DATA_DIRETORIO / "bandeira_tarifaria_adicional.csv", sep=";", decimal=",", parse_dates=["DatVigencia"])
TARIFA = float(tarifa.iloc[0, 0])  # R$/kWh
# Dados para a energia solar (alternativa B)
MESES = ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun", "Jul", "Ago", "Set", "Out", "Nov", "Dez"]
DIAS_MES = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
IRRADIACAO = [4.72, 5.22, 4.83, 4.70, 4.24, 4.13, 4.12, 4.99, 4.50, 4.64, 4.70, 5.05]  # kWh/m²/dia, SunData São Paulo
RENDIMENTO = 0.80  # hipótese: o sistema aproveita 80% da energia do sol
DISPONIBILIDADE = 50  # kWh/mês que a distribuidora cobra mesmo com solar (premissa)
CO2_KG_KWH = 0.0385  # kg de CO2 por kWh (SIN 2023, MCTI/SIRENE)
# Trocas por modelo mais eficiente (alternativa A). Lâmpada: equivalência do Idec (60 W = LED 9 W)
TROCAS = {
    "Lâmpada incandescente 60 W": "Lâmpada LED 9 W",
    "Geladeira 2 portas": "Geladeira inverter",
    "Ar-condicionado split 10.001 a 15.000 BTU": "Ar-condicionado split inverter 12.000 BTU",
}
PRECOS_SOLAR = [(2, 10000, 14000), (4, 16000, 22000), (8, 30000, 40000)]  # (kWp, preço mínimo, preço máximo) Olhar Digital
bandeira = bandeira[bandeira["DatVigencia"] == bandeira["DatVigencia"].max()]  # só a vigência mais recente

def buscar_eletro(nome):
    # Procura pelo nome (ou parte dele) sem diferenciar maiúscula de minúscula
    nome = nome.strip().lower()
    if nome == "":
        raise IndexError
    achados = aparelho[aparelho["nome"].str.lower().str.contains(nome, regex=False)]
    if achados.empty:
        raise IndexError
    if len(achados) > 1:
        for i, n in enumerate(achados["nome"], start=1):
            print(f" {i}. {n}")
        escolha = int(input("Foram encontrados vários, digite o número do aparelho: "))
        if escolha < 1 or escolha > len(achados):
            raise IndexError
        return achados.iloc[escolha - 1]
    return achados.iloc[0]

def calcular_um_eletro():
    # Pergunta os dados de UM eletrodoméstico e devolve um dicionário com o consumo (ou None se der erro)
    try:
        eletro = buscar_eletro(input("Digite seu eletrodoméstico: "))
        if pd.isna(eletro["potencia_W"]):
            print(f"{eletro['nome']} não tem potência cadastrada.")
            return None
        quantidade = int(input("Digite a quantidade desse eletrodoméstico na sua casa: "))
        uso_mes = int(input("Digite a quantidade de dias de uso: "))
        horas = float(input("Digite o tempo de uso do seu equipamento em horas por dia: ").replace(",", "."))
        if quantidade < 1 or uso_mes < 1 or uso_mes > 31 or horas < 0 or horas > 24:
            print("Valores fora do limite (quantidade 1 ou mais, dias de 1 a 31, horas de 0 a 24).")
            return None
        potencia = eletro["potencia_W"]
        resultado = (potencia * horas * uso_mes * quantidade) / 1000
        print(f"\n \n Os gastos mensais com {eletro['nome']} é de {resultado:.2f} kWh por mes! \n")
        # guarda todos os dados do aparelho, a alternativa A precisa deles
        return {"nome": eletro["nome"], "kwh": resultado, "potencia": potencia,
                "horas": horas, "dias": uso_mes, "quantidade": quantidade}
    except ValueError:
        print("O valor digitado está incorreto, tente novamente!")
        return None
    except IndexError:
        print("Eletrodoméstico não encontrado, tente novamente!")
        return None

def simulacao():
    # Pergunta quantos eletrodomésticos serão inseridos e repete a pergunta com um for
    try:
        repeticao = int(input("Digite a quantidade de eletrodomésticos diferentes que deseja inserir na lista: "))
    except ValueError:
        print("Digite apenas numeros!")
        return []
    if repeticao < 1 or repeticao > 20:
        print("Digite uma quantidade entre 1 e 20.")
        return []
    conta = []
    for i in range(repeticao):
        print(f"\n--- Eletrodoméstico {i + 1} de {repeticao} ---")
        resultado = None
        while resultado is None:
            resultado = calcular_um_eletro()
            if resultado is None:
                tentar = str(input("Deseja tentar este eletrodoméstico de novo? Digite [S ou N]: ")).upper()
                if tentar != "S":
                    break
        if resultado is not None:
            conta.append(resultado)
    if conta:
        print(f"Consumo total da lista: {consumo_total(conta):.2f} kWh por mes")
    return conta

def consumo_total(conta):
    # Soma o consumo (kWh por mês) de todos os aparelhos da lista
    total = 0
    for item in conta:
        total += item["kwh"]
    return total

def pedir_bandeira():
    # Devolve o adicional da bandeira em R$/kWh (0 se não houver)
    bandeira_adicional = str(input("Existe alguma bandeira adicional na sua região? Digite [S ou N]: ")).upper()
    if bandeira_adicional != "S":
        return 0
    cor = str(input("Digite a cor da bandeira: ")).strip().lower()
    if cor == "verde":  # a verde não tem adicional e não está no CSV
        return 0
    # o CSV está em R$/MWh, então divide por 1000 para ter R$/kWh
    return bandeira.loc[bandeira["NomBandeiraAcionada"].str.lower() == cor, "VlrAdicionalBandeiraRSMWh"].iloc[0] / 1000

def conta_mensal():
    try:
        potencia_acomulada = simulacao()
        if not potencia_acomulada:
            return
        total = consumo_total(potencia_acomulada)
        taxa = pedir_bandeira()
        print(f"A conta de energia aproximada desse mes é de R${total * (TARIFA + taxa):.2f}")
    except IndexError:
        print("Bandeira não encontrada!")

def preco_instalacao(kwp):
    # Devolve (preço mínimo, preço máximo) do sistema solar, interpolando a tabela do Olhar Digital
    primeiro = PRECOS_SOLAR[0]
    ultimo = PRECOS_SOLAR[-1]
    if kwp <= primeiro[0]:  # abaixo da tabela: proporcional ao menor sistema
        return primeiro[1] * kwp / primeiro[0], primeiro[2] * kwp / primeiro[0]
    if kwp >= ultimo[0]:  # acima da tabela: proporcional ao maior sistema
        return ultimo[1] * kwp / ultimo[0], ultimo[2] * kwp / ultimo[0]
    for i in range(len(PRECOS_SOLAR) - 1):
        k1, min1, max1 = PRECOS_SOLAR[i]
        k2, min2, max2 = PRECOS_SOLAR[i + 1]
        if k1 <= kwp <= k2:
            fracao = (kwp - k1) / (k2 - k1)
            return min1 + fracao * (min2 - min1), max1 + fracao * (max2 - max1)

def escolher_economias(conta):
    # Para cada aparelho o usuário escolhe manter, reduzir as horas de uso ou trocar por um modelo eficiente
    # Devolve (kWh economizados por mês, investimento em R$)
    economia_kwh = 0
    investimento = 0  # reduzir horas não custa nada, só as trocas custam
    for item in conta:
        print(f"\n{item['nome']}: {item['kwh']:.2f} kWh por mês")
        print(" 0. Manter como está")
        print(" 1. Reduzir as horas de uso por dia")
        if item["nome"] in TROCAS:
            print(f" 2. Trocar por {TROCAS[item['nome']]}")
        try:
            opc = int(input("Digite uma opção: "))
        except ValueError:
            print("Digite apenas numeros! Esse aparelho foi mantido.")
            continue
        if opc == 1:
            try:
                novas_horas = float(input(f"Digite as novas horas por dia (hoje {item['horas']}) Horas: ").replace(",", "."))
            except ValueError:
                print("O valor digitado está incorreto! Esse aparelho foi mantido.")
                continue
            if novas_horas < 0 or novas_horas >= item["horas"]:
                print("As novas horas precisam ser menores que as atuais. Esse aparelho foi mantido.")
                continue
            kwh_novo = item["potencia"] * novas_horas * item["dias"] * item["quantidade"] / 1000
            economia_kwh += item["kwh"] - kwh_novo
        elif opc == 2 and item["nome"] in TROCAS:
            novo = aparelho[aparelho["nome"] == TROCAS[item["nome"]]].iloc[0]
            if pd.isna(novo["potencia_W"]):
                # geladeira e ar-condicionado inverter: o consumo está na etiqueta do Inmetro
                try:
                    por_unidade = float(input("Digite o consumo do modelo novo em kWh por mês, por unidade (etiqueta do Inmetro): ").replace(",", "."))
                except ValueError:
                    print("O valor digitado está incorreto! Esse aparelho foi mantido.")
                    continue
                kwh_novo = por_unidade * item["quantidade"]
            else:
                kwh_novo = novo["potencia_W"] * item["horas"] * item["dias"] * item["quantidade"] / 1000
            if kwh_novo >= item["kwh"]:
                print("Essa troca não gera economia. Esse aparelho foi mantido.")
                continue
            economia_kwh += item["kwh"] - kwh_novo
            investimento += novo["preco_mediana_RS"] * item["quantidade"]
        elif opc != 0:
            print("Opção inválida. Esse aparelho foi mantido.")
    return economia_kwh, investimento

def calcular_solar(total):
    # Devolve o tamanho do sistema (kWp), a geração de cada mês e os kWh cobrados em cada mês
    geracao_1kwp = 0  # quanto 1 kWp gera em um ano
    for i in range(12):
        geracao_1kwp += IRRADIACAO[i] * DIAS_MES[i] * RENDIMENTO
    kwp = (total - DISPONIBILIDADE) * 12 / geracao_1kwp  # cobre o consumo anual menos o mínimo cobrado
    geracoes = []
    cobrados = []
    credito = 0  # energia que sobra e vale para os próximos meses
    for i in range(12):
        geracao = kwp * IRRADIACAO[i] * DIAS_MES[i] * RENDIMENTO
        saldo = total - geracao - credito
        if saldo > 0:
            credito = 0
        else:
            credito = -saldo
        geracoes.append(geracao)
        cobrados.append(max(saldo, DISPONIBILIDADE))
    return kwp, geracoes, cobrados

def anos_retorno(investimento, economia_anual):
    # Anos para a economia pagar o investimento (None se não houver economia)
    if economia_anual <= 0:
        return None
    return investimento / economia_anual

def texto_retorno(anos):
    if anos is None:
        return "não volta"
    if anos == 0:
        return "na hora"
    if anos < 1:
        return f"{anos * 12:.1f} meses".replace(".", ",")
    return f"{anos:.1f} anos".replace(".", ",")

def reais(valor):
    # R$ 1.234,56 (padrão brasileiro)
    return "R$ " + f"{valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

def alternativa_a():
    try:
        conta = simulacao()
        if not conta:
            return
        taxa = pedir_bandeira()
    except IndexError:
        print("Bandeira não encontrada!")
        return
    tarifa_total = TARIFA + taxa
    total = consumo_total(conta)
    print("\n--- Alternativa A: economia ---")
    economia_kwh, investimento = escolher_economias(conta)
    if economia_kwh == 0:
        print("\nNenhuma economia foi escolhida.")
        return
    economia_mes = economia_kwh * tarifa_total
    print("\n----- Resultado da alternativa A -----")
    print(f"Consumo: de {total:.2f} para {total - economia_kwh:.2f} kWh por mês")
    print(f"Economia: {economia_kwh:.2f} kWh por mês, R${economia_mes:.2f} por mês, R${economia_mes * 12:.2f} por ano")
    print(f"Investimento: R${investimento:.2f}")
    print(f"Tempo de retorno: {texto_retorno(anos_retorno(investimento, economia_mes * 12))}")
    print(f"CO2 evitado: {economia_kwh * 12 * CO2_KG_KWH:.1f} kg por ano")
    print("Fontes: ANEEL (tarifa e bandeira), pesquisa de preços em lojas (08/11/2026), Idec (equivalência das lâmpadas), MCTI/SIRENE (CO2).")
    print("Ressalva: estimativa com valores médios. O preço varia por loja e o consumo real depende dos seus hábitos de uso.")

def alternativa_b():
    try:
        consumos = simulacao()
        if not consumos:
            return
        total = consumo_total(consumos)
        taxa = pedir_bandeira()
    except IndexError:
        print("Bandeira não encontrada!")
        return
    tarifa_total = TARIFA + taxa
    if total <= DISPONIBILIDADE:
        print(f"Seu consumo ({total:.2f} kWh/mês) não passa do mínimo cobrado ({DISPONIBILIDADE} kWh/mês): a energia solar não compensa.")
        return
    kwp, geracoes, cobrados = calcular_solar(total)
    print(f"\nSistema sugerido: {kwp:.2f} kWp")
    print("Mês   Geração(kWh)  Cobrado(kWh)  Sem solar(R$)  Com solar(R$)")
    for i in range(12):
        print(f"{MESES[i]:<6}{geracoes[i]:>10.1f}{cobrados[i]:>14.1f}{total * tarifa_total:>15.2f}{cobrados[i] * tarifa_total:>15.2f}")
    custo_sem = total * tarifa_total * 12
    custo_com = sum(cobrados) * tarifa_total
    print(f"Total{'':<2}{'':>10}{sum(cobrados):>14.1f}{custo_sem:>15.2f}{custo_com:>15.2f}")
    economia = custo_sem - custo_com
    preco_min, preco_max = preco_instalacao(kwp)
    print(f"\nEconomia estimada: R${economia:.2f} por ano")
    print(f"Investimento estimado: R${preco_min:.2f} a R${preco_max:.2f}")
    print(f"Tempo de retorno: {texto_retorno(anos_retorno(preco_min, economia))} a {texto_retorno(anos_retorno(preco_max, economia))}")
    print(f"CO2 evitado: {(total * 12 - sum(cobrados)) * CO2_KG_KWH:.1f} kg por ano")
    print("Fontes: ANEEL (tarifa e bandeira), CRESESB SunData (irradiação), Olhar Digital (preço), MCTI/SIRENE (CO2).")
    print("Ressalva: estimativa com valores médios. O rendimento de 80% é hipótese, o preço é estimado,")
    print("o Fio B da Lei 14.300 não foi incluído (a economia real pode ser menor) e não há reajuste de tarifa.")

# ---------- Gráficos simples, pensados para uma criança entender ----------
FUNDO = "#fffbea"
COR_HOJE = "#e76f51"
COR_A = "#2a9d8f"
COR_B = "#f4a100"

def preparar_figura(titulo, dica):
    # Figura grande, fundo claro, título em forma de pergunta e uma dica embaixo
    figura = plt.figure(figsize=(9, 6), facecolor=FUNDO)
    eixo = figura.add_subplot(111)
    eixo.set_facecolor(FUNDO)
    eixo.set_title(titulo, fontsize=21, fontweight="bold", pad=18)
    figura.text(0.5, 0.03, dica, ha="center", fontsize=14, color="#444444")
    for lado in ["top", "right", "left"]:
        eixo.spines[lado].set_visible(False)
    eixo.set_yticks([])  # os números ficam escritos em cima das barras
    return figura, eixo

def grafico_barras(titulo, dica, nomes, valores, cores, textos, arquivo):
    figura, eixo = preparar_figura(titulo, dica)
    eixo.bar(nomes, valores, color=cores, width=0.6)
    maior = max(valores) if max(valores) > 0 else 1
    eixo.set_ylim(0, maior * 1.25)
    for i in range(len(nomes)):
        eixo.text(i, valores[i] + maior * 0.03, textos[i], ha="center", fontsize=20, fontweight="bold")
    eixo.tick_params(axis="x", labelsize=16)
    figura.subplots_adjust(bottom=0.2)
    GRAFICOS_DIRETORIO.mkdir(exist_ok=True)
    figura.savefig(GRAFICOS_DIRETORIO / arquivo, dpi=150, facecolor=FUNDO)

def grafico_quem_gasta_mais(conta, tarifa_total):
    # Barras deitadas: cada aparelho com quanto custa por mês; o que mais gasta fica em vermelho
    ordenada = sorted(conta, key=lambda item: item["kwh"])
    figura, eixo = preparar_figura("Quem gasta mais luz na sua casa?", "A barra vermelha é o aparelho que mais pesa na conta!")
    nomes = [item["nome"] for item in ordenada]
    valores = [item["kwh"] * tarifa_total for item in ordenada]
    cores = ["#8ecae6"] * len(ordenada)
    cores[-1] = COR_HOJE
    eixo.barh(nomes, valores, color=cores, height=0.6)
    eixo.set_xlim(0, max(valores) * 1.35)
    for i in range(len(valores)):
        eixo.text(valores[i] + max(valores) * 0.02, i, reais(valores[i]) + " por mês", va="center", fontsize=15, fontweight="bold")
    eixo.set_yticks(range(len(nomes)))  # volta a escrever o nome de cada aparelho
    eixo.set_yticklabels(nomes)
    eixo.tick_params(axis="y", labelsize=14, length=0)
    eixo.set_xticks([])
    figura.subplots_adjust(left=0.38, bottom=0.12)
    GRAFICOS_DIRETORIO.mkdir(exist_ok=True)
    figura.savefig(GRAFICOS_DIRETORIO / "grafico_2_quem_gasta_mais.png", dpi=150, facecolor=FUNDO)

def comparar():
    # Compara a situação atual, a alternativa A e a alternativa B em 12 meses e faz os gráficos
    try:
        conta = simulacao()
        if not conta:
            return
        taxa = pedir_bandeira()
    except IndexError:
        print("Bandeira não encontrada!")
        return
    tarifa_total = TARIFA + taxa
    total = consumo_total(conta)

    print("\n--- Alternativa A: economia (escolha o que fazer com cada aparelho) ---")
    economia_kwh, investimento_a = escolher_economias(conta)

    if total > DISPONIBILIDADE:
        kwp, geracoes, cobrados = calcular_solar(total)
        preco_min, preco_max = preco_instalacao(kwp)
    else:
        print(f"\nSeu consumo não passa do mínimo cobrado ({DISPONIBILIDADE} kWh/mês): a energia solar não se aplica.")
        kwp, cobrados, preco_min, preco_max = 0, [total] * 12, 0, 0
    investimento_b = (preco_min + preco_max) / 2

    # Custo de cada mês nas três situações
    custo_hoje = [total * tarifa_total] * 12
    custo_a = [(total - economia_kwh) * tarifa_total] * 12
    custo_b = [kwh * tarifa_total for kwh in cobrados]

    print("\n----- Comparação em 12 meses (R$ por mês) -----")
    print("Mês        Hoje    A: economia    B: solar")
    for i in range(12):
        print(f"{MESES[i]:<6}{custo_hoje[i]:>10.2f}{custo_a[i]:>14.2f}{custo_b[i]:>12.2f}")
    ano_hoje, ano_a, ano_b = sum(custo_hoje), sum(custo_a), sum(custo_b)
    print(f"Total{ano_hoje:>11.2f}{ano_a:>14.2f}{ano_b:>12.2f}")

    economia_a = ano_hoje - ano_a
    economia_b = ano_hoje - ano_b
    retorno_a = anos_retorno(investimento_a, economia_a)
    retorno_b = anos_retorno(investimento_b, economia_b)
    co2_a = economia_kwh * 12 * CO2_KG_KWH
    co2_b = (total * 12 - sum(cobrados)) * CO2_KG_KWH

    print("\nResumo:")
    print(f" A: economiza {reais(economia_a)} por ano | investe {reais(investimento_a)} | retorno: {texto_retorno(retorno_a)} | CO2 evitado: {co2_a:.1f} kg por ano")
    if kwp > 0:
        print(f" B: economiza {reais(economia_b)} por ano | investe {reais(preco_min)} a {reais(preco_max)} (sistema de {kwp:.2f} kWp) | retorno: {texto_retorno(retorno_b)} (preço médio) | CO2 evitado: {co2_b:.1f} kg por ano")

    # Gráficos
    grafico_barras("Quanto eu pago de luz em 1 ano?", "Quanto menor a barra, melhor para o bolso!",
                   ["Hoje", "Economizando", "Energia do sol"], [ano_hoje, ano_a, ano_b], [COR_HOJE, COR_A, COR_B],
                   [reais(ano_hoje), reais(ano_a), reais(ano_b)], "grafico_1_conta_do_ano.png")
    grafico_quem_gasta_mais(conta, tarifa_total)
    anos_a = retorno_a if retorno_a is not None else 0
    anos_b = retorno_b if retorno_b is not None else 0
    grafico_barras("Em quanto tempo o dinheiro volta?", "Gastei para comprar, e a conta menor devolve o dinheiro com o tempo.",
                   ["Economizando", "Energia do sol"], [anos_a, anos_b], [COR_A, COR_B],
                   [texto_retorno(retorno_a), texto_retorno(retorno_b)], "grafico_3_dinheiro_volta.png")
    grafico_barras("Quanta poluição eu deixo de soltar?", "Em 1 ano, em quilos de CO2. Quanto maior a barra, melhor para o planeta!",
                   ["Economizando", "Energia do sol"], [co2_a, co2_b], [COR_A, COR_B],
                   [f"{co2_a:.0f} kg".replace(".", ","), f"{co2_b:.0f} kg".replace(".", ",")], "grafico_4_ar_limpo.png")
    print(f"\nOs gráficos foram salvos na pasta: {GRAFICOS_DIRETORIO}")
    abrir = str(input("Deseja abrir os gráficos agora? Digite [S ou N]: ")).upper()
    if abrir == "S":
        plt.show()
    plt.close("all")

    print("Fontes: ANEEL (tarifa e bandeira), CRESESB SunData, Olhar Digital, pesquisa de preços em lojas (08/11/2026), Idec, MCTI/SIRENE.")
    print("Ressalva: estimativas com valores médios; sem Fio B (Lei 14.300), reajuste de tarifa ou degradação dos painéis.")

def consulta():
    try:
        eletro = buscar_eletro(input("Digite o eletrodomestico que deseja consultar: "))
        print(" 1.Consumo \n 2.Media de preço no mercado")
        opc = int(input("Digite uma opçao: "))
        if opc == 1:
            if pd.isna(eletro["potencia_W"]):
                print("Esse produto não tem potência cadastrada.")
            else:
                print(f"A potência de {eletro['nome']} é {eletro['potencia_W']:.0f} W")
        elif opc == 2:
            if pd.isna(eletro["preco_mediana_RS"]):
                print("Esse produto não tem preço cadastrado.")
            else:
                print(f"O preço mediano desse produto {eletro['nome']} é R$ {eletro['preco_mediana_RS']:.2f}")
        else:
            print("Opção inválida, digite 1 ou 2.")
    except ValueError:
        print("Digite apenas numeros")
    except IndexError:
        print("Eletrodoméstico não encontrado, tente novamente!")

while True:
    print("-------Menu-------")
    print("1-Consultar Informações de eletrodomesticos")
    print("2-Consultar a tarifa atual")
    print("3-Simular sua conta mensal")
    print("4-Alternativa A: economia")
    print("5-Alternativa B: energia solar")
    print("6-Comparar as alternativas A e B em 12 meses (com gráficos)")
    print("0-Digite 0 para encerrar programa")
    try:
        opcao = int(input("Digite uma opção válida: "))
    except ValueError:
        print("Digite apenas numeros!")
        continue

    if opcao == 1:
        consulta()
    elif opcao == 2:
        print(f"A tarifa atual é de {TARIFA:.3f} R$/kWh no Estado de São Paulo")
    elif opcao == 3:
        conta_mensal()
    elif opcao == 4:
        alternativa_a()
    elif opcao == 5:
        alternativa_b()
    elif opcao == 6:
        comparar()
    elif opcao == 0:
        break
    else:
        print("Entrada invalida, digite as opções entre 0 e 6!")