"""Os testes da leitura: o que cada linha faz e o erro de escrita traduzido, sem rodar nada.

    python -m pytest tests          (ou)          python tests/test_leitura.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src" / "truecoral"))
from leitura import ler  # noqa: E402


def _d(codigo):
    r = ler(codigo)
    return {int(k): v["descricao"] for k, v in r["linhas"].items()}, r["erro"]


def test_a_calculadora_do_exemplo():
    d, erro = _d("def calculadora(a, b):\n    return a + b\n\nprint(calculadora(1, 2))\n")
    assert erro is None
    assert d[1] == "função calculadora, recebe a, b"
    assert d[2] == "devolve a soma de a e b"
    assert d[4] == "mostra na tela o que calculadora devolve com a = 1, b = 2"


def test_laco_condicao_e_metodos():
    d, _ = _d("for x in range(1, n + 1):\n    if x % 3 == 0:\n        lista.append('Fizz')\n"
              "    elif x % 5 == 0:\n        pass\n    else:\n        lista.append(str(x))\n")
    assert d[1] == "repete para cada x de 1 até n"
    assert d[2] == "se o resto de x por 3 é igual a 0"
    assert d[3] == "acrescenta 'Fizz' no fim de lista"
    assert d[4].startswith("senão, se")
    assert d[6] == "senão"
    assert d[7] == "acrescenta x como texto no fim de lista"


def test_try_except_e_raise():
    d, _ = _d("try:\n    v = f()\nexcept (SystemExit, KeyboardInterrupt):\n    raise\n"
              "except Exception as e:\n    pass\nfinally:\n    pass\n")
    assert d[1] == "tenta o bloco abaixo"
    assert d[3] == "se der SystemExit ou KeyboardInterrupt, cai aqui"
    assert d[4] == "levanta o mesmo erro de novo, para quem chamou"
    assert d[5] == "se der Exception, cai aqui (guarda o erro em e)"
    assert d[7].startswith("no fim, sempre")


def test_pandas_do_arquivo_2():
    d, _ = _d("import pandas as pd\ndf = pd.read_csv(arquivo, sep=';', encoding='latin-1')\n"
              "df.isna().sum()\nprint(df.shape)\nprint(df.duplicated(subset=['brinco']).sum())\n")
    assert d[1] == "importa pandas com o nome pd"
    assert d[2] == "df recebe o CSV lido de arquivo, separado por ';', em 'latin-1'"
    assert d[3] == "quantos vazios há em cada coluna de df"
    assert d[4] == "mostra na tela a forma (linhas, colunas) de df"
    assert d[5] == "mostra na tela quantas linhas de df repetem uma já vista, olhando só ['brinco']"


def test_comprehension_e_contracao():
    d, _ = _d("nomes = [c for c in df.columns if c.startswith('peso')]\nx = max(len(a), len(b))\n")
    assert d[1] == "nomes recebe a lista de c, para cada c nos nomes das colunas de df, só quando c começa com 'peso'"
    assert d[2] == "x recebe o maior entre o tamanho de a e o tamanho de b"


def test_contracao_nao_mexe_no_nome_dele():
    d, _ = _d("x = a + o\n")
    assert d[1] == "x recebe a soma de a e o"


def test_erros_de_escrita_traduzidos():
    casos = {
        "print(calculadora(1, 2)\n": (1, "faltou fechar o '('"),
        "x = [1, 2, 3)\n": (1, "abriu com '[' e fechou com ')': esperava-se ']'"),
        "def f(a)\n    return a\n": (1, "faltou o ':' no fim da linha"),
        "nome = 'nelore\n": (1, "o texto não foi fechado: faltou a ' do fim"),
        "x = [1 2 3]\n": (1, "faltou vírgula entre os itens"),
        "if x = 3:\n    pass\n": (1, "'=' guarda um valor; para comparar é '=='"),
        "def f():\n": (1, "falta o corpo da função: as linhas de dentro, com recuo"),
        "x = (1 + 2))\n": (1, "fechou um ')' que não foi aberto"),
        "x = 1\n    y = 2\n": (2, "recuo a mais: esta linha não está dentro de nenhum bloco"),
        "x = 1\nelse:\n    pass\n": (2, "'else' sem um if, for, while ou try logo antes, no mesmo recuo"),
        "x = 1 +\n": (1, "a linha termina num operador: falta o que vem depois dele"),
    }
    for codigo, (linha, texto) in casos.items():
        erro = ler(codigo)["erro"]
        assert erro and erro["linha"] == linha and erro["texto"] == texto, (codigo, erro)


def test_linha_quebrada_nao_apaga_o_resto():
    d, erro = _d("def calculadora(a, b):\n    return a + b\n\nprint(calculadora(1, 2)\nx = 3\n")
    assert erro["linha"] == 4
    assert d[1] == "função calculadora, recebe a, b" and d[2] == "devolve a soma de a e b" and d[5] == "x recebe 3"
    assert 4 not in d


def test_dois_pontos_faltando_mantem_o_corpo():
    d, erro = _d("def calculadora(a, b)\n    return a + b\n")
    assert erro["linha"] == 1 and d[2] == "devolve a soma de a e b"


def test_nao_roda_nada():
    d, erro = _d("import os\nos.remove('nao-apague-isto')\nraise SystemExit(1)\n")
    assert erro is None and d[2] == "chama os.remove com 'nao-apague-isto'"


if __name__ == "__main__":
    falhas = 0
    for nome, f in list(globals().items()):
        if nome.startswith("test_") and callable(f):
            try:
                f()
                print(f"ok     {nome}")
            except AssertionError as e:
                falhas += 1
                print(f"FALHOU {nome}\n{e}")
    raise SystemExit(1 if falhas else 0)
