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
    assert d[2] == "df: variável que guarda o CSV lido de arquivo, separado por ';', em 'latin-1'"
    assert d[3] == "quantos vazios há em cada coluna de df"
    assert d[4] == "mostra na tela a forma (linhas, colunas) de df"
    assert d[5] == "mostra na tela quantas linhas de df repetem uma já vista, olhando só ['brinco']"


def test_comprehension_e_contracao():
    d, _ = _d("nomes = [c for c in df.columns if c.startswith('peso')]\nx = max(len(a), len(b))\n")
    assert d[1] == "nomes: variável que guarda a lista de c, para cada c nos nomes das colunas de df, só quando c começa com 'peso'"
    assert d[2] == "x: variável que guarda o maior entre o tamanho de a e o tamanho de b"


def test_contracao_nao_mexe_no_nome_dele():
    d, _ = _d("x = a + o\n")
    assert d[1] == "x: variável que guarda a soma de a e o"


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
    assert d[1] == "função calculadora, recebe a, b" and d[2] == "devolve a soma de a e b" and d[5] == "x: variável de valor 3"
    assert 4 not in d


def test_dois_pontos_faltando_mantem_o_corpo():
    d, erro = _d("def calculadora(a, b)\n    return a + b\n")
    assert erro["linha"] == 1 and d[2] == "devolve a soma de a e b"


def test_nao_roda_nada():
    d, erro = _d("import os\nos.remove('nao-apague-isto')\nraise SystemExit(1)\n")
    assert erro is None and d[2] == "chama os.remove com 'nao-apague-isto'"



def test_as_funcoes_da_viper():
    d, _ = _d("from viper import replacement, compare\n"
              "x = replacement([1, 2, 3, 4, 5], 'par', lambda x: x % 2 == 0)\n"
              "a, b = compare('3.12', '3.12.0.1')\n"
              "y = compare(1, 2)\n")
    assert d[1] == "traz replacement, compare de viper"
    assert d[2] == "x: variável que guarda a lista [1, 2, 3, 4, 5] com 'par' no lugar de cada x em que o resto de x por 2 é igual a 0"
    assert d[3] == ("a, b recebem as versões '3.12' e '3.12.0.1' com o mesmo tamanho (completadas com zeros), "
                    "como listas")


def test_funcao_com_o_mesmo_nome_que_nao_e_da_viper():
    d, _ = _d("def compare(a, b):\n    return a\n\nx = compare(1, 2)\n")
    assert d[4] == "x: variável que guarda o que compare devolve com a = 1, b = 2"


def test_viper_com_apelido():
    d, _ = _d("import viper as v\nfrom viper import compare as cmp\n"
              "a, b = v.compare('3.12', '3.13')\nx = v.replacement([1, 2], 'x', lambda x: x == 2)\n"
              "c, e = cmp(1, 2)\n")
    assert d[3] == ("a, b recebem as versões '3.12' e '3.13' com o mesmo tamanho (completadas com zeros), "
                    "como listas")
    assert d[4] == "x: variável que guarda a lista [1, 2] com 'x' no lugar de cada x em que x é igual a 2"
    assert d[5].startswith("c, e recebem as versões 1 e 2")


def test_a_variavel_conta_a_propria_historia():
    d, _ = _d("contador = 0\nfor x in lista:\n    if x % 2 == 0:\n        contador += 1\n")
    assert d[1] == "contador: variável de valor 0; depois, recebe +1, quando o resto de x por 2 é igual a 0, para cada x em lista"
    assert d[4] == "contador (que nasceu valendo 0) recebe +1, quando o resto de x por 2 é igual a 0, para cada x em lista"
    d, _ = _d("contador = 0\n")                    # apagou o += : a história volta a ser só o nascimento
    assert d[1] == "contador: variável de valor 0"


def test_o_else_diz_o_que_nao_aconteceu():
    d, _ = _d("x = 3\nif y:\n    x = 5\nelif z:\n    x = 6\nelse:\n    x = 7\n")
    assert d[7] == "x (que nasceu valendo 3) passa a valer 7, quando nem y, nem z"
    assert d[5] == "x (que nasceu valendo 3) passa a valer 6, quando z (nem y)"


def test_a_classe_do_estudo1():
    d, _ = _d("class MyArray:\n"
              "    def __init__(self, tamanho_maximo):\n"
              "        self.array = [None] * tamanho_maximo\n"
              "        self.size = 0\n"
              "    def insert(self, value):\n"
              "        if self.size < len(self.array):\n"
              "            self.array[self.size] = value\n"
              "            self.size += 1\n"
              "    def get(self, index):\n"
              "        self.size -= 1\n"
              "a = MyArray(10)\n"
              "a.insert(10)\n"
              "print(a.get(0))\n")
    assert d[1] == "cria a classe MyArray: o molde dos objetos MyArray, com os métodos insert, get"
    assert d[2] == "o __init__ roda sozinho ao criar um MyArray(…): self é o objeto novo; tamanho_maximo vem entre os parênteses"
    assert d[3].startswith("o objeto (self) ganha o atributo array, que guarda uma lista de tamanho_maximo posições, todas valendo None; depois,")
    assert d[4] == ("o objeto (self) ganha o atributo size, que vale 0; depois, recebe +1 no insert, quando self.size é menor "
                    "que o tamanho de self.array; recebe −1 no get")
    assert d[6] == "se self.size (nasceu valendo 0) é menor que o tamanho de self.array"
    assert d[7].startswith("na lista self.array (que nasceu como [None] * tamanho_maximo no __init__), a posição self.size passa a guardar value")
    assert d[8] == "self.size (que nasceu valendo 0 no __init__) recebe +1, quando self.size é menor que o tamanho de self.array"
    assert d[11] == "a: variável que guarda um objeto MyArray novo (o __init__ roda com tamanho_maximo = 10)"
    assert d[12] == "chama o método insert do objeto a, com value = 10"
    assert d[13] == "mostra na tela o que o método get de a devolve, com index = 0 — get não tem return: devolve None"

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
