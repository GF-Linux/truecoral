"""A leitura: o que cada linha faz, em português, e o erro de escrita traduzido — sem rodar nada.

O motor responde "o que a linha produziu", e para isso precisa rodar (ao salvar). A leitura
responde "o que a linha é", e para isso basta ler: roda a cada tecla, sobre o texto que ainda
nem foi salvo, e não executa uma linha sequer do seu código.

    python leitura.py arquivo.py        o JSON da leitura
    python leitura.py -                 o mesmo, lendo o código da entrada padrão (a extensão usa assim)

Três regras:
  - descreve, não conclui: diz o que a linha faz, nunca se ela está certa
  - o que não reconhece, diz pela forma ("chama f com x") — não inventa o que uma função faz
  - um erro de escrita por vez, como o Python; o resto do arquivo continua descrito

Só biblioteca padrão: roda com qualquer Python 3.9 ou mais novo.
"""
import ast
import json
import keyword
import re
import sys

try:                                     # dentro do pacote (o comando coral) ou ao lado (a extensão)
    from . import sugestoes as _sugestoes
except ImportError:
    try:
        import sugestoes as _sugestoes
    except ImportError:                  # sem o catálogo, a leitura segue sem sugestões
        _sugestoes = None

LIMITE = 120          # uma descrição maior que isto troca as partes de dentro pelo próprio código

# ── 1. o erro de escrita, traduzido ─────────────────────────────────────────

FECHA = {"(": ")", "[": "]", "{": "}"}
CORPO_DE = {"function definition": "da função", "class definition": "da classe",
            "'if' statement": "do if", "'elif' statement": "do elif", "'else' statement": "do else",
            "'for' statement": "do for", "'while' statement": "do while", "'try' statement": "do try",
            "'except' statement": "do except", "'finally' statement": "do finally",
            "'with' statement": "do with", "'match' statement": "do match", "'case' statement": "do case"}


def _linha_do_codigo(fonte, n):
    linhas = fonte.splitlines()
    return linhas[n - 1] if 0 < n <= len(linhas) else ""


def traduzir_sintaxe(e, fonte=""):
    """(linha, texto em português) para um SyntaxError. A mensagem original fica para o detalhe."""
    msg, n = e.msg or "", e.lineno or 1
    m = re.match(r"'(.)' was never closed", msg)
    if m:
        return n, f"faltou fechar o '{m.group(1)}'"
    m = re.match(r"closing parenthesis '(.)' does not match opening parenthesis '(.)'", msg)
    if m:
        fechou, abriu = m.groups()
        return n, f"abriu com '{abriu}' e fechou com '{fechou}': esperava-se '{FECHA.get(abriu, '?')}'"
    m = re.match(r"unmatched '(.)'", msg)
    if m:
        return n, f"fechou um '{m.group(1)}' que não foi aberto"
    if msg.startswith("expected ':'"):
        return n, "faltou o ':' no fim da linha"
    if msg.startswith("unterminated triple-quoted string"):
        return n, "o texto de três aspas não foi fechado"
    if msg.startswith("unterminated string literal"):
        codigo = _linha_do_codigo(fonte, n)
        aspa = next((c for c in codigo if c in "'\""), "'")
        return n, f"o texto não foi fechado: faltou a {aspa} do fim"
    if "Perhaps you forgot a comma" in msg:
        return n, "faltou vírgula entre os itens"
    if "Maybe you meant '==' or ':=' instead of '='" in msg:
        return n, "'=' guarda um valor; para comparar é '=='"
    m = re.match(r"expected an indented block after (.+?) on line (\d+)", msg)
    if m:
        de = CORPO_DE.get(m.group(1), "deste bloco")
        return int(m.group(2)), f"falta o corpo {de}: as linhas de dentro, com recuo"
    if msg.startswith("unexpected indent"):
        return n, "recuo a mais: esta linha não está dentro de nenhum bloco"
    if msg.startswith("unindent does not match"):
        return n, "o recuo desta linha não bate com o de nenhuma linha acima"
    if msg.startswith("inconsistent use of tabs and spaces"):
        return n, "o recuo mistura tab e espaço"
    if msg.startswith("expected an indented block"):
        return n, "falta o bloco com recuo depois da linha anterior"
    if msg.startswith("invalid decimal literal"):
        return n, "número mal escrito: há uma letra colada num número"
    m = re.match(r"invalid character '(.)'", msg)
    if m:
        return n, f"o caractere '{m.group(1)}' não existe em Python (copiado de algum lugar?)"
    if msg.startswith("cannot assign to"):
        oque = re.match(r"cannot assign to ([^.]+?)( here)?(\.|$)", msg)
        alvo = oque.group(1) if oque else "isto"
        alvo = {"function call": "uma chamada de função", "literal": "um valor escrito direto",
                "expression": "uma conta", "comparison": "uma comparação"}.get(alvo, alvo)
        dica = "; para comparar é '=='" if "'=='" in msg else ""
        return n, f"não dá para guardar valor em {alvo}{dica}"
    m = re.match(r"'(\w+)' outside (function|loop)", msg)
    if m:
        lugar = "de uma função" if m.group(2) == "function" else "de um laço"
        return n, f"'{m.group(1)}' fora {lugar}"
    if msg.startswith("Missing parentheses in call to"):
        return n, "faltaram os parênteses da chamada: print(...)"
    if msg.startswith("expected 'except' or 'finally' block"):
        return n, "o try precisa de um except (ou de um finally) logo depois do bloco dele"
    if msg.startswith("f-string"):
        return n, "erro dentro da f-string: confira as chaves { }"
    if msg.startswith("invalid syntax"):
        return n, _sintaxe_generica(_linha_do_codigo(fonte, n))
    return n, f"erro de escrita (o Python diz: {msg})"


def _sintaxe_generica(codigo):
    """O 'invalid syntax' puro não diz o motivo; a linha às vezes diz."""
    tirada = codigo.strip()
    palavra = re.match(r"[A-Za-z_]\w*", tirada)
    primeira = palavra.group(0) if palavra else ""
    if primeira in ("else", "elif", "except", "finally"):
        antes = {"else": "if, for, while ou try", "elif": "if", "except": "try", "finally": "try"}[primeira]
        return f"'{primeira}' sem um {antes} logo antes, no mesmo recuo"
    m = re.match(r"(\w+)\s*=(?!=)", tirada)
    if m and keyword.iskeyword(m.group(1)):
        return f"'{m.group(1)}' é palavra reservada do Python: não serve de nome"
    m = re.match(r"def\s+(\w+)", tirada)
    if m and keyword.iskeyword(m.group(1)):
        return f"'{m.group(1)}' é palavra reservada do Python: não serve de nome de função"
    if re.search(r"(\+|-|\*|/|%|\*\*|//|==|!=|<=|>=|<|>|\band|\bor|\bnot|,)\s*(#.*)?$", tirada):
        return "a linha termina num operador: falta o que vem depois dele"
    return "o Python não entendeu esta linha (confira o que vem logo antes do ponto marcado)"


# ── 2. a leitura das linhas ────────────────────────────────────────────────

ACAO_METODO = {   # chamadas usadas como frase inteira: o que fazem com o objeto
    "append": lambda o, a: f"acrescenta {a[0]} no fim de {o}",
    "extend": lambda o, a: f"acrescenta os itens de {a[0]} no fim de {o}",
    "insert": lambda o, a: f"insere {a[1]} na posição {a[0]} de {o}",
    "remove": lambda o, a: f"tira de {o} o primeiro {a[0]}",
    "sort": lambda o, a: f"ordena {o} no lugar (não devolve nada)",
    "reverse": lambda o, a: f"inverte {o} no lugar",
    "clear": lambda o, a: f"esvazia {o}",
    "update": lambda o, a: f"junta {a[0]} em {o}" if a else f"atualiza {o}",
    "add": lambda o, a: f"põe {a[0]} no conjunto {o}",
    "write": lambda o, a: f"escreve {a[0]} em {o}",
    "close": lambda o, a: f"fecha {o}",
}

VALOR_METODO = {  # métodos que devolvem algo: o que devolvem
    "split": lambda o, a: f"{o} separado em pedaços por {a[0]}" if a else f"{o} separado em palavras",
    "splitlines": lambda o, a: f"as linhas de {o}",
    "strip": lambda o, a: f"{o} sem espaços nas pontas" if not a else f"{o} sem {a[0]} nas pontas",
    "lstrip": lambda o, a: f"{o} sem espaços no começo",
    "rstrip": lambda o, a: f"{o} sem espaços no fim",
    "lower": lambda o, a: f"{o} em minúsculas",
    "upper": lambda o, a: f"{o} em maiúsculas",
    "capitalize": lambda o, a: f"{o} com só a primeira letra maiúscula",
    "title": lambda o, a: f"{o} com a primeira letra de cada palavra maiúscula",
    "replace": lambda o, a: f"{o} com {a[0]} trocado por {a[1]}" if len(a) > 1 else f"{o} com trocas",
    "startswith": lambda o, a: f"{o} começa com {a[0]}",
    "endswith": lambda o, a: f"{o} termina com {a[0]}",
    "join": lambda o, a: f"os itens de {a[0]} juntos, com {o} entre eles",
    "count": lambda o, a: f"quantas vezes {a[0]} aparece em {o}" if a else f"a contagem de {o}",
    "index": lambda o, a: f"a posição de {a[0]} em {o}",
    "find": lambda o, a: f"a posição de {a[0]} em {o} (-1 se não houver)",
    "get": lambda o, a: (f"o valor de {a[0]} em {o} ({a[1]} se não houver)" if len(a) > 1
                         else f"o valor de {a[0]} em {o} (None se não houver)"),
    "keys": lambda o, a: f"as chaves de {o}",
    "values": lambda o, a: f"os valores de {o}",
    "items": lambda o, a: f"os pares (chave, valor) de {o}",
    "copy": lambda o, a: f"uma cópia de {o}",
    "pop": lambda o, a: f"tira de {o} e devolve o item {a[0]}" if a else f"tira e devolve o último item de {o}",
    "format": lambda o, a: f"{o} preenchido com {', '.join(a)}",
    "isdigit": lambda o, a: f"{o} só tem dígitos",
    # pandas
    "head": lambda o, a: f"as primeiras {a[0] if a else 5} linhas de {o}",
    "tail": lambda o, a: f"as últimas {a[0] if a else 5} linhas de {o}",
    "sample": lambda o, a: f"{a[0] if a else 1} linha(s) sorteada(s) de {o}",
    "describe": lambda o, a: f"o resumo estatístico de {o}",
    "info": lambda o, a: f"o resumo das colunas de {o} (tipos e não vazios)",
    "isna": lambda o, a: f"onde {o} está vazio (True/False)",
    "isnull": lambda o, a: f"onde {o} está vazio (True/False)",
    "notna": lambda o, a: f"onde {o} não está vazio (True/False)",
    "dropna": lambda o, a: f"{o} sem as linhas vazias",
    "fillna": lambda o, a: f"{o} com os vazios trocados por {a[0]}" if a else f"{o} com os vazios preenchidos",
    "unique": lambda o, a: f"os valores distintos de {o}",
    "nunique": lambda o, a: f"quantos valores distintos {o} tem",
    "value_counts": lambda o, a: f"quantas vezes cada valor aparece em {o}",
    "duplicated": lambda o, a: f"onde {o} repete uma linha já vista (True/False)",
    "drop_duplicates": lambda o, a: f"{o} sem as linhas repetidas",
    "groupby": lambda o, a: f"{o} agrupado por {a[0]}" if a else f"{o} agrupado",
    "mean": lambda o, a: f"a média de {o}",
    "median": lambda o, a: f"a mediana de {o}",
    "sum": lambda o, a: f"a soma de {o}",
    "min": lambda o, a: f"o menor valor de {o}",
    "max": lambda o, a: f"o maior valor de {o}",
    "std": lambda o, a: f"o desvio-padrão de {o}",
    "sort_values": lambda o, a: f"{o} ordenado por {a[0]}" if a else f"{o} ordenado pelos valores",
    "reset_index": lambda o, a: f"{o} com o índice virando coluna e voltando a 0, 1, 2…",
    "merge": lambda o, a: f"{o} juntado com {a[0]}" if a else f"{o} juntado",
    "astype": lambda o, a: f"{o} convertido para {a[0]}" if a else f"{o} convertido",
    "to_csv": lambda o, a: f"grava {o} no CSV {a[0]}" if a else f"grava {o} em CSV",
    "agg": lambda o, a: f"{o} resumido por {a[0]}" if a else f"{o} resumido",
    "apply": lambda o, a: f"{o} com {a[0]} aplicado em cada item" if a else f"{o} com uma função aplicada",
    "map": lambda o, a: f"{o} com cada valor trocado por {a[0]}" if a else f"{o} com os valores trocados",
    "rename": lambda o, a: f"{o} com nomes trocados",
    "drop": lambda o, a: f"{o} sem {a[0]}" if a else f"{o} sem o que foi pedido",
    "corr": lambda o, a: f"a correlação entre as colunas de {o}",
    "read_csv": lambda o, a: f"o CSV lido de {a[0]}" if a else "o CSV lido",
}

FUNCAO = {        # funções embutidas e de módulo
    "print": lambda a: f"mostra na tela {', '.join(a)}" if a else "mostra uma linha em branco",
    "len": lambda a: f"o tamanho de {a[0]}",
    "sum": lambda a: f"a soma dos itens de {a[0]}",
    "max": lambda a: f"o maior entre {', '.join(a[:-1])} e {a[-1]}" if len(a) > 1 else f"o maior de {a[0]}",
    "min": lambda a: f"o menor entre {', '.join(a[:-1])} e {a[-1]}" if len(a) > 1 else f"o menor de {a[0]}",
    "sorted": lambda a: f"os itens de {a[0]} em ordem (numa lista nova)",
    "reversed": lambda a: f"os itens de {a[0]} de trás para frente",
    "abs": lambda a: f"o valor absoluto de {a[0]}",
    "round": lambda a: f"{a[0]} arredondado" + (f" com {a[1]} casas" if len(a) > 1 else ""),
    "str": lambda a: f"{a[0]} como texto" if a else "um texto vazio",
    "int": lambda a: f"{a[0]} como número inteiro" if a else "0",
    "float": lambda a: f"{a[0]} como número decimal" if a else "0.0",
    "bool": lambda a: f"{a[0]} como True/False",
    "list": lambda a: f"{a[0]} como lista" if a else "uma lista vazia",
    "tuple": lambda a: f"{a[0]} como tupla" if a else "uma tupla vazia",
    "set": lambda a: f"os itens distintos de {a[0]}" if a else "um conjunto vazio",
    "dict": lambda a: f"{a[0]} como dicionário" if a else "um dicionário vazio",
    "enumerate": lambda a: f"os pares (posição, item) de {a[0]}",
    "zip": lambda a: f"os itens de {' e '.join(a)} lado a lado (para no mais curto)",
    "type": lambda a: f"o tipo de {a[0]}",
    "isinstance": lambda a: f"{a[0]} é do tipo {a[1]}" if len(a) > 1 else "confere o tipo",
    "input": lambda a: f"o que for digitado depois de {a[0]}" if a else "o que for digitado",
    "open": lambda a: f"o arquivo {a[0]} aberto",
    "range": None,    # tratado à parte: de onde até onde
}


SUBST = ("soma|lista|tupla|média|mediana|forma|versão|sequência|correlação|posição|divisão|contagem|"
         "tamanho|maior|menor|resto|resumo|tipo|índice|valor|valores|texto|CSV|que|último|item|itens|"
         "campo|conjunto|dicionário|número|números|primeiro|primeiras|últimas|desvio|nomes|pares|"
         "chaves|arquivo|colunas|linhas|datas|cópia")
CONTRAI = re.compile(r"\b(de|em) (o|os|a|as) (?=(" + SUBST + r")\b)")


def contrair(texto):
    """'de o tamanho' → 'do tamanho'; só antes das palavras do próprio vocabulário, nunca antes de um nome seu."""
    return CONTRAI.sub(lambda m: {"de": "d", "em": "n"}[m.group(1)] + m.group(2) + " ", texto)


def _viper_replacement(leitor, no, p):
    lista, palavra, cond = no.args[0], no.args[1], no.args[2]
    if isinstance(cond, ast.Lambda) and cond.args.args:
        x = cond.args.args[0].arg
        quando = f"cada {x} em que {leitor.e(cond.body, p)}"
    else:
        quando = f"cada item em que {leitor.cod(cond)} diz True"
    return f"{leitor.e(lista, p)} com {leitor.cod(palavra)} no lugar de {quando}"


def _viper_compare(leitor, no, p):
    v1, v2 = no.args[0], no.args[1]
    return f"as versões {leitor.cod(v1)} e {leitor.cod(v2)} com o mesmo tamanho (completadas com zeros), como listas"


VIPER = {"replacement": _viper_replacement, "compare": _viper_compare}    # from viper import ...


class Leitor:
    def __init__(self, fonte):
        self.fonte = fonte
        self.linhas = fonte.splitlines()
        self.saida = {}
        self.curtas = {}       # linha → a frase sem a história e sem as condições (o mouse mostra a inteira)
        self.funcoes = {}      # nome → parâmetros, das funções definidas no próprio arquivo
        self.modulos = {}      # nome no código → módulo importado (import pandas as pd: pd → pandas)
        self.classes = {}      # nome da classe → {método: (parâmetros, tem return com valor)}
        self.vidas = {}        # a biografia de cada variável: chave → nascimento e mudanças
        self.tipos = {}        # chave da variável → a classe do arquivo de que ela é objeto
        self.func = None       # a função (ou método) onde a frase está
        self.classe = None     # a classe onde a frase está

    # ── as partes ──
    def segmento(self, no):
        """O texto de um pedaço do código. O ast.get_source_segment refaz a divisão do arquivo inteiro em
        linhas a cada chamada; aqui a divisão é feita uma vez por texto (a leitura roda a cada tecla)."""
        if getattr(self, "_dividido", (None,))[0] is not self.fonte:
            self._dividido = (self.fonte, [l.encode("utf-8") for l in self.fonte.split("\n")])
        linhas = self._dividido[1]
        a, b = getattr(no, "lineno", None), getattr(no, "end_lineno", None)
        if a is None or b is None or b > len(linhas):
            return None
        ca, cb = no.col_offset, no.end_col_offset
        if a == b:
            return linhas[a - 1][ca:cb].decode("utf-8", errors="replace")
        partes = [linhas[a - 1][ca:]] + linhas[a:b - 1] + [linhas[b - 1][:cb]]
        return b"\n".join(partes).decode("utf-8", errors="replace")

    def cod(self, no):
        texto = self.segmento(no)
        if texto is None:
            texto = ast.unparse(no)
        texto = " ".join(texto.split())
        return texto if len(texto) <= 60 else texto[:57] + "…"

    def e(self, no, prof=0):
        """A frase de uma expressão. Fundo demais, ou desconhecida: o próprio código."""
        if prof > 2:
            return self.cod(no)
        p = prof + 1
        if isinstance(no, (ast.Name, ast.Constant)):
            return self.cod(no)
        if isinstance(no, ast.BinOp) and isinstance(no.op, ast.Mult) and isinstance(no.left, ast.List) \
                and len(no.left.elts) == 1:                    # [None] * n: n posições iguais
            return f"uma lista de {self.cod(no.right)} posições, todas valendo {self.cod(no.left.elts[0])}"
        if isinstance(no, ast.BinOp):
            a, b = self.e(no.left, p), self.e(no.right, p)
            return {ast.Add: f"a soma de {a} e {b}", ast.Sub: f"{a} menos {b}", ast.Mult: f"{a} vezes {b}",
                    ast.Div: f"{a} dividido por {b}", ast.FloorDiv: f"a divisão inteira de {a} por {b}",
                    ast.Mod: f"o resto de {a} por {b}", ast.Pow: f"{a} elevado a {b}",
                    ast.BitAnd: f"{a} e {b}", ast.BitOr: f"{a} ou {b}"}.get(type(no.op), self.cod(no))
        if isinstance(no, ast.UnaryOp):
            if isinstance(no.op, ast.Not):
                return f"não {self.e(no.operand, p)}"
            return self.cod(no)
        if isinstance(no, ast.BoolOp):
            liga = " e " if isinstance(no.op, ast.And) else " ou "
            return liga.join(self.e(v, p) for v in no.values)
        if isinstance(no, ast.Compare):
            partes, esq = [], self.e(no.left, p)
            for op, dir_ in zip(no.ops, no.comparators):
                d = self.e(dir_, p)
                if isinstance(op, ast.Is) and isinstance(dir_, ast.Constant) and dir_.value is None:
                    partes.append(f"{esq} é None")
                elif isinstance(op, ast.IsNot) and isinstance(dir_, ast.Constant) and dir_.value is None:
                    partes.append(f"{esq} não é None")
                else:
                    verbo = {ast.Eq: "é igual a", ast.NotEq: "é diferente de", ast.Lt: "é menor que",
                             ast.LtE: "é menor ou igual a", ast.Gt: "é maior que", ast.GtE: "é maior ou igual a",
                             ast.In: "está em", ast.NotIn: "não está em", ast.Is: "é o mesmo objeto que",
                             ast.IsNot: "não é o mesmo objeto que"}[type(op)]
                    partes.append(f"{esq} {verbo} {d}")
                esq = d
            return " e ".join(partes)
        if isinstance(no, ast.Call):
            return self.chamada(no, p)
        if isinstance(no, ast.Attribute):
            o = self.e(no.value, p)
            if isinstance(no.value, ast.Name) and no.value.id == "sys" and no.attr == "version_info":
                return "a versão do Python que está rodando"
            nome = {"shape": f"a forma (linhas, colunas) de {o}", "dtypes": f"o tipo de cada coluna de {o}",
                    "columns": f"os nomes das colunas de {o}", "index": f"o índice de {o}",
                    "values": f"os valores de {o}", "T": f"{o} transposto",
                    "str": f"o texto de {o}", "dt": f"as datas de {o}"}.get(no.attr)
            return nome or self.cod(no)
        if isinstance(no, ast.Subscript):
            o, chave = self.e(no.value, p), no.slice
            if isinstance(chave, ast.Slice):
                ini = self.cod(chave.lower) if chave.lower else "o começo"
                fim = f"antes de {self.cod(chave.upper)}" if chave.upper else "o fim"
                return f"os itens de {o} de {ini} até {fim}"
            if isinstance(chave, ast.Constant) and isinstance(chave.value, int) and chave.value == -1:
                return f"o último item de {o}"
            if isinstance(chave, ast.Constant) and isinstance(chave.value, str):
                return f"o campo {self.cod(chave)} de {o}"
            if isinstance(chave, ast.List):
                return f"as colunas {self.cod(chave)} de {o}"
            if isinstance(chave, (ast.Compare, ast.BoolOp)) or (
                    isinstance(chave, ast.UnaryOp) and isinstance(chave.op, ast.Not)) or (
                    isinstance(chave, ast.BinOp) and isinstance(chave.op, (ast.BitAnd, ast.BitOr))):
                return f"as linhas de {o} em que {self.e(chave, p)}"      # o filtro do pandas
            if self.e_lista(no.value):
                return f"o valor da posição {self.cod(chave)} de {o}"
            return f"o item {self.cod(chave)} de {o}"
        if isinstance(no, (ast.ListComp, ast.SetComp, ast.GeneratorExp)):
            tipo = {ast.ListComp: "a lista", ast.SetComp: "o conjunto",
                    ast.GeneratorExp: "a sequência"}[type(no)]
            return f"{tipo} de {self.e(no.elt, p)}{self.geradores(no.generators, p)}"
        if isinstance(no, ast.DictComp):
            return f"o dicionário de {self.e(no.key, p)} → {self.e(no.value, p)}{self.geradores(no.generators, p)}"
        if isinstance(no, ast.IfExp):
            return f"{self.e(no.body, p)} se {self.e(no.test, p)}, senão {self.e(no.orelse, p)}"
        if isinstance(no, ast.Lambda):
            args = ", ".join(a.arg for a in no.args.args)
            return f"uma função curta que recebe {args} e devolve {self.e(no.body, p)}"
        if isinstance(no, ast.Tuple):
            return f"a tupla {self.cod(no)}"
        if isinstance(no, ast.List):
            return f"a lista {self.cod(no)}" if no.elts else "uma lista vazia"
        if isinstance(no, ast.Dict):
            return f"o dicionário {self.cod(no)}" if no.keys else "um dicionário vazio"
        if isinstance(no, ast.Set):
            return f"o conjunto {self.cod(no)}"
        if isinstance(no, ast.JoinedStr):
            return f"o texto {self.cod(no)}"
        if isinstance(no, ast.NamedExpr):
            return f"{self.e(no.value, p)}, guardado em {no.target.id}"
        return self.cod(no)

    def geradores(self, gens, p):
        texto = ""
        for g in gens:
            texto += f", para cada {self.cod(g.target)} em {self.e(g.iter, p)}"
            if g.ifs:
                texto += ", só quando " + " e ".join(self.e(c, p) for c in g.ifs)
        return texto

    def argumentos(self, no, p):
        args = [self.e(a, p) for a in no.args]
        for k in no.keywords:
            if k.arg is None:
                args.append(f"**{self.cod(k.value)}")
            else:
                args.append(f"{k.arg} = {self.cod(k.value)}")
        return args

    def intervalo(self, no):
        a = no.args
        if len(a) == 1:
            return f"de 0 até {self._menos_um(a[0])}"
        if len(a) >= 2:
            passo = f", de {self.cod(a[2])} em {self.cod(a[2])}" if len(a) > 2 else ""
            return f"de {self.cod(a[0])} até {self._menos_um(a[1])}{passo}"
        return "um intervalo"

    def _menos_um(self, fim):
        """range para antes do fim: range(1, n + 1) vai até n; range(n) vai até n - 1."""
        if isinstance(fim, ast.BinOp) and isinstance(fim.op, ast.Add) \
                and isinstance(fim.right, ast.Constant) and fim.right.value == 1:
            return self.cod(fim.left)
        if isinstance(fim, ast.Constant) and isinstance(fim.value, int):
            return str(fim.value - 1)
        return f"{self.cod(fim)} − 1"

    def chamada(self, no, p, como_frase=False):
        f = no.func
        if isinstance(f, ast.Name):
            if f.id == "range":
                return f"os números {self.intervalo(no)}"
            origem = self.modulos.get(f.id, "")               # from viper import compare (as cmp)
            if origem.startswith("viper.") and origem.split(".")[-1] in VIPER:
                try:
                    return VIPER[origem.split(".")[-1]](self, no, p)     # as funções do arsenal
                except (IndexError, AttributeError):
                    pass
            modelo = FUNCAO.get(f.id)
            args = self.argumentos(no, p)
            params = self.funcoes.get(f.id)
            if params and not modelo:
                args = [self.nomeados(no, params)] if (no.args or no.keywords) else []
            if modelo:
                try:
                    return modelo(args)
                except IndexError:
                    pass
            if f.id in self.classes:
                ps = self.classes[f.id].get("__init__", ([], False))[0]
                com = self.nomeados(no, ps)
                return f"um objeto {f.id} novo" + (f" (o __init__ roda com {com})" if com else "")
            if f.id[:1].isupper():
                return f"um {f.id} novo" + (f" com {', '.join(args)}" if args else "")
            return f"o que {f.id} devolve" + (f" com {', '.join(args)}" if args else "") if not como_frase \
                else f"chama {f.id}" + (f" com {', '.join(args)}" if args else "")
        if isinstance(f, ast.Attribute):
            # cadeias conhecidas do pandas, ditas de uma vez
            if f.attr == "sum" and isinstance(f.value, ast.Call) and isinstance(f.value.func, ast.Attribute):
                interno = f.value.func.attr
                o = self.e(f.value.func.value, p)
                if interno in ("isna", "isnull"):
                    return f"quantos vazios há em cada coluna de {o}"
                if interno == "duplicated":
                    sub = next((k for k in f.value.keywords if k.arg == "subset"), None)
                    por = f", olhando só {self.cod(sub.value)}" if sub else ""
                    return f"quantas linhas de {o} repetem uma já vista{por}"
            if isinstance(f.value, ast.Name) and self.modulos.get(f.value.id) == "viper" and f.attr in VIPER:
                try:
                    return VIPER[f.attr](self, no, p)            # import viper as v: v.compare(...)
                except (IndexError, AttributeError):
                    pass
            if isinstance(f.value, ast.Name) and f.value.id in self.modulos \
                    and not (self.modulos[f.value.id] == "pandas" and f.attr in VALOR_METODO):
                args = self.argumentos(no, p)       # função de módulo: não é método de lista nem de texto
                com = f" com {', '.join(args)}" if args else ""
                return f"chama {self.cod(f)}{com}" if como_frase else f"o que {self.cod(f)} devolve{com}"
            classe = self.classe_de(f.value)
            if classe and f.attr in self.classes.get(classe, {}):      # um método da classe que você escreveu
                ps, devolve = self.classes[classe][f.attr]
                com = self.nomeados(no, ps)
                com = f", com {com}" if com else ""
                if como_frase:
                    return f"chama o método {f.attr} do objeto {self.cod(f.value)}{com}"
                sem = "" if devolve else f" — {f.attr} não tem return: devolve None"
                return f"o que o método {f.attr} de {self.cod(f.value)} devolve{com}{sem}"
            o = self.e(f.value, p)
            if isinstance(f.value, ast.Attribute) and f.value.attr == "str":
                o = f"cada texto de {self.e(f.value.value, p)}"
            args = self.argumentos(no, p)
            if f.attr == "read_csv":
                extra = []
                for k in no.keywords:
                    v = self.cod(k.value)
                    extra.append({"sep": f"separado por {v}", "encoding": f"em {v}", "decimal": f"com decimal {v}",
                                  "thousands": f"com milhar {v}", "header": f"cabeçalho {v}",
                                  "skiprows": f"pulando {v} linhas", "nrows": f"só {v} linhas"}.get(
                        k.arg, f"{k.arg} = {v}"))
                fonte_csv = self.e(no.args[0], p) if no.args else "?"
                return f"o CSV lido de {fonte_csv}" + (f", {', '.join(extra)}" if extra else "")
            tabela = ACAO_METODO if como_frase and f.attr in ACAO_METODO else VALOR_METODO
            modelo = tabela.get(f.attr) or ACAO_METODO.get(f.attr)
            if modelo:
                try:
                    return modelo(o, args)
                except IndexError:
                    pass
            return f"chama .{f.attr}(" + ", ".join(args) + f") em {o}"
        return self.cod(no)

    # ── as variáveis e as suas biografias ──
    def chave(self, no):
        """De quem é esta variável: (função, nome), ou (classe, 'self.x') para um atributo."""
        if isinstance(no, ast.Name):
            if self.func is not None and (id(self.func), no.id) in self.vidas:
                return (id(self.func), no.id)
            if self.func is not None and self.e_parametro(no.id):
                return None
            return (id(self.func) if self.func is not None and self._local(no.id) else "mod", no.id)
        if isinstance(no, ast.Attribute) and isinstance(no.value, ast.Name) and no.value.id == "self" \
                and self.classe is not None:
            return (id(self.classe), f"self.{no.attr}")
        return None

    def _local(self, nome):
        """A função escreve nesta variável? (sem global, é dela)"""
        memo = self.__dict__.setdefault("_locais", {})
        if (id(self.func), nome) not in memo:
            memo[(id(self.func), nome)] = self._escreve(nome)
        return memo[(id(self.func), nome)]

    def _escreve(self, nome):
        for n in ast.walk(self.func):
            alvos = n.targets if isinstance(n, ast.Assign) else [n.target] if isinstance(
                n, (ast.AugAssign, ast.AnnAssign, ast.For)) else []
            for a in alvos:
                if any(isinstance(x, ast.Name) and x.id == nome for x in ast.walk(a)):
                    return True
        return False

    def e_parametro(self, nome):
        if self.func is None:
            return False
        a = self.func.args
        return nome in [x.arg for x in a.posonlyargs + a.args + a.kwonlyargs]

    def e_lista(self, no):
        k = self.chave(no) if isinstance(no, (ast.Name, ast.Attribute)) else None
        v = self.vidas.get(k, {}).get("valor") if k else None
        return isinstance(v, (ast.List, ast.ListComp)) or (
            isinstance(v, ast.BinOp) and isinstance(v.op, ast.Mult) and isinstance(v.left, ast.List)) or (
            isinstance(v, ast.Call) and isinstance(v.func, ast.Name) and v.func.id == "list")

    def classe_de(self, no):
        if isinstance(no, ast.Name) and no.id == "self" and self.classe is not None:
            return self.classe.name
        k = self.chave(no) if isinstance(no, (ast.Name, ast.Attribute)) else None
        return self.tipos.get(k) if k else None

    def nomeados(self, chamada, params):
        """'tamanho_maximo = 10'; quem passa o próprio nome ('pares = pares') aparece uma vez só: 'pares'."""
        pares = [(params[i] if i < len(params) else None, self.cod(a)) for i, a in enumerate(chamada.args)]
        pares += [(k.arg, self.cod(k.value)) for k in chamada.keywords if k.arg]
        return ", ".join(v if p is None or p == v else f"{p} = {v}" for p, v in pares)

    def nasceu(self, k):
        """'que nasceu valendo 0 no __init__' — de onde a variável veio, dito curto."""
        v = self.vidas.get(k)
        if not v:
            return ""
        onde = f" no {v['funcnome']}" if v["func"] is not self.func and v["funcnome"] else ""
        if v["const"] is not None:
            return f" (que nasceu valendo {v['const']}{onde})"
        return f" (que nasceu como {v['curto']}{onde})"

    def quando(self, conds):
        """A condição primeiro, o laço depois: ', quando x > 0, para cada x em lista'."""
        lacos = [c for c in conds if c.startswith(("para cada", "enquanto", "quando o laço"))]
        outras = [c for c in conds if c not in lacos]
        texto = f", quando {' e '.join(outras)}" if outras else ""
        return texto + (", " + ", ".join(lacos) if lacos else "")

    # a primeira passada: quem nasce onde, e o que muda depois — antes de descrever qualquer linha
    def colher(self, nos, conds):
        for no in nos:
            try:
                self._colher(no, conds)
            except Exception:
                pass

    def _colher(self, no, conds):
        n = getattr(no, "lineno", None)
        if isinstance(no, ast.ClassDef):
            antes, self.classe = self.classe, no
            self.classes[no.name] = {}
            for m in no.body:
                if isinstance(m, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    ps = [a.arg for a in m.args.posonlyargs + m.args.args][1:]
                    devolve = any(isinstance(r, ast.Return) and r.value is not None for r in ast.walk(m))
                    self.classes[no.name][m.name] = (ps, devolve)
            self.colher(no.body, conds)
            self.classe = antes
        elif isinstance(no, (ast.FunctionDef, ast.AsyncFunctionDef)):
            antes, self.func = self.func, no
            self.colher(no.body, [])
            self.func = antes
        elif isinstance(no, (ast.Assign, ast.AnnAssign)):
            alvos = no.targets if isinstance(no, ast.Assign) else [no.target]
            if no.value is None:
                return
            for alvo in alvos:
                if isinstance(alvo, ast.Subscript):
                    k = self.chave(alvo.value)
                    self.mudou(k, n, f"a posição {self.cod(alvo.slice)} passa a guardar {self.cod(no.value)}",
                               conds)
                    continue
                for x in (alvo.elts if isinstance(alvo, ast.Tuple) else [alvo]):
                    k = self.chave(x)
                    if k is None:
                        continue
                    if k not in self.vidas:
                        const = self.cod(no.value) if isinstance(no.value, ast.Constant) and not isinstance(alvo, ast.Tuple) else None
                        self.vidas[k] = {"nasce": n, "func": self.func, "valor": None if isinstance(alvo, ast.Tuple) else no.value,
                                         "funcnome": self.func.name if self.func is not None else "",
                                         "const": const, "curto": self.cod(no.value)[:40], "mudancas": []}
                        v = no.value
                        if isinstance(v, ast.Call) and isinstance(v.func, ast.Name) and v.func.id in self.classes:
                            self.tipos[k] = v.func.id
                    else:
                        self.mudou(k, n, f"passa a valer {self.cod(no.value)[:40]}", conds)
        elif isinstance(no, ast.AugAssign):
            k = self.chave(no.target)
            sinal = {ast.Add: "+", ast.Sub: "−", ast.Mult: "×", ast.Div: "÷"}.get(type(no.op))
            texto = f"recebe {sinal}{self.cod(no.value)}" if sinal else f"é atualizado com {self.cod(no.value)}"
            self.mudou(k, n, texto, conds)
        elif isinstance(no, ast.Expr) and isinstance(no.value, ast.Call) and isinstance(no.value.func, ast.Attribute):
            f = no.value.func
            if f.attr in ("append", "extend", "insert", "remove", "pop", "clear", "sort", "reverse", "update", "add"):
                a = [self.cod(x) for x in no.value.args]
                texto = {"append": lambda: f"ganha {a[0]} no fim", "extend": lambda: f"ganha os itens de {a[0]}",
                         "insert": lambda: f"ganha {a[1]} na posição {a[0]}", "remove": lambda: f"perde o primeiro {a[0]}",
                         "pop": lambda: f"perde o item {a[0]}" if a else "perde o último item",
                         "clear": lambda: "é esvaziada", "sort": lambda: "é ordenada", "reverse": lambda: "é invertida"
                         }.get(f.attr, lambda: f"muda com .{f.attr}()")
                try:
                    self.mudou(self.chave(f.value), n, texto(), conds)
                except IndexError:
                    pass
        elif isinstance(no, (ast.For, ast.AsyncFor)):
            for x in (no.target.elts if isinstance(no.target, ast.Tuple) else [no.target]):
                k = self.chave(x)
                if k is not None and k not in self.vidas:
                    self.vidas[k] = {"nasce": n, "func": self.func, "valor": None, "const": None, "mudancas": [],
                                     "funcnome": self.func.name if self.func is not None else "",
                                     "curto": f"cada item de {self.cod(no.iter)}"}
            it = no.iter
            if isinstance(it, ast.Call) and isinstance(it.func, ast.Name) and it.func.id == "range":
                cada = f"para cada {self.cod(no.target)} {self.intervalo(it)}"
            else:
                cada = f"para cada {self.cod(no.target)} em {self.e(it, 2)}"
            self.colher(no.body, conds + [cada])
            self.colher(no.orelse, conds + ["quando o laço terminou sem break"])
        elif isinstance(no, ast.While):
            self.colher(no.body, conds + [f"enquanto {self.e(no.test, 1)}"])
            self.colher(no.orelse, conds)
        elif isinstance(no, ast.If):
            self.colher(no.body, conds + [self.e(no.test, 1)])
            self._colher_senao(no, conds, [self.cod(no.test)])
        elif isinstance(no, (ast.With, ast.AsyncWith)):
            self.colher(no.body, conds)
        elif isinstance(no, ast.Try) or type(no).__name__ == "TryStar":
            self.colher(no.body, conds)
            for h in no.handlers:
                self.colher(h.body, conds + [f"se der {self.cod(h.type) if h.type else 'qualquer erro'}"])
            self.colher(no.orelse, conds + ["se não deu erro"])
            self.colher(no.finalbody, conds)

    def _colher_senao(self, no_if, conds, negadas):
        """elif e else: a condição deles inclui o que NÃO aconteceu acima."""
        nem = "nem " + ", nem ".join(negadas)
        if no_if.orelse and isinstance(no_if.orelse[0], ast.If) and len(no_if.orelse) == 1 and \
                self.linhas[no_if.orelse[0].lineno - 1].strip().startswith("elif"):
            prox = no_if.orelse[0]
            self.colher(prox.body, conds + [f"{self.e(prox.test, 1)} ({nem})"])
            self._colher_senao(prox, conds, negadas + [self.cod(prox.test)])
        elif no_if.orelse:
            self.colher(no_if.orelse, conds + [nem])

    def mudou(self, k, n, texto, conds):
        if k is None or k not in self.vidas:
            return
        self.vidas[k]["mudancas"].append({"linha": n, "texto": texto, "conds": list(conds), "func": self.func,
                                         "funcnome": self.func.name if self.func is not None else ""})

    def biografia(self, k):
        """O que veio depois do nascimento, para a linha onde a variável nasceu."""
        v = self.vidas.get(k)
        if not v or not v["mudancas"]:
            return ""
        partes = []
        for m in v["mudancas"][:3]:
            onde = f" no {m['funcnome']}" if m["func"] is not v["func"] and m["funcnome"] else ""
            partes.append(f"{m['texto']}{onde}{self.quando(m['conds'])}")
        mais = f"; e mais {len(v['mudancas']) - 3} mudança(s)" if len(v["mudancas"]) > 3 else ""
        return "; depois, " + "; ".join(partes) + mais

    def condicoes_da_linha(self, n, k):
        v = self.vidas.get(k)
        for m in (v["mudancas"] if v else []):
            if m["linha"] == n:
                return m["conds"]
        return []

    def anotar(self, texto, no):
        """Na condição de um if, cada variável diz com que valor nasceu: 'self.size (nasceu valendo 0)'."""
        feitas = set()
        for x in ast.walk(no):
            if isinstance(x, (ast.Name, ast.Attribute)):
                k = self.chave(x)
                v = self.vidas.get(k) if k else None
                if v and v["const"] is not None and k not in feitas:
                    nome = self.cod(x)
                    texto = re.sub(rf"(?<![\w.]){re.escape(nome)}(?![\w.(])",
                                   f"{nome} (nasceu valendo {v['const']})", texto, count=1)
                    feitas.add(k)
        return texto

    # ── as frases ──
    def por(self, n, texto, curta=None):
        if n and texto:
            texto = contrair(" ".join(texto.split()))
            self.saida.setdefault(n, texto)
            if curta:
                curta = contrair(" ".join(curta.split()))
                if curta != texto:
                    self.curtas.setdefault(n, curta)

    def caber(self, monta):
        """Monta a frase; se ficar comprida demais, monta de novo com menos fundo."""
        texto = monta(0)
        if len(texto) > LIMITE:
            texto = monta(2)
        if len(texto) > LIMITE:
            texto = monta(3)
        return texto

    def linha_com(self, inicio, fim, palavra):
        """A linha de um 'else', 'finally'… — que o ast não guarda — procurando entre inicio e fim."""
        for i in range(fim, inicio - 1, -1):
            if 0 < i <= len(self.linhas) and self.linhas[i - 1].strip().startswith(palavra):
                return i
        return None

    def corpo(self, nos):
        for no in nos:
            self.frase(no)

    def frase(self, no):
        n = getattr(no, "lineno", None)
        if isinstance(no, (ast.FunctionDef, ast.AsyncFunctionDef)):
            params = [a.arg for a in no.args.posonlyargs + no.args.args if a.arg not in ("self", "cls")]
            padroes = no.args.defaults
            if padroes:
                com = params[-len(padroes):] if len(padroes) <= len(params) else []
                params = params[:len(params) - len(com)] + [
                    f"{nome} (padrão {self.cod(d)})" for nome, d in zip(com, padroes)]
            if no.args.vararg:
                params.append(f"*{no.args.vararg.arg}")
            params += [a.arg for a in no.args.kwonlyargs]
            if no.args.kwarg:
                params.append(f"**{no.args.kwarg.arg}")
            metodo = no.args.args and no.args.args[0].arg == "self" and self.classe is not None
            if metodo and no.name == "__init__":
                vem = f"; {', '.join(params)} {'vêm' if len(params) > 1 else 'vem'} entre os parênteses" if params else ""
                self.por(n, f"o __init__ roda sozinho ao criar um {self.classe.name}(…): self é o objeto novo{vem}")
            elif metodo:
                vem = f"; {', '.join(params)} {'vêm' if len(params) > 1 else 'vem'} entre os parênteses" if params else ""
                self.por(n, f"método {no.name}: roda em objeto.{no.name}(…), e self é o próprio objeto{vem}")
            else:
                tipo = "método" if no.args.args and no.args.args[0].arg == "self" else "função"
                self.por(n, f"{tipo} {no.name}, recebe {', '.join(params)}" if params
                         else f"{tipo} {no.name}, sem parâmetros")
            primeira = no.body[0] if no.body else None
            if isinstance(primeira, ast.Expr) and isinstance(primeira.value, ast.Constant) \
                    and isinstance(primeira.value.value, str):
                self.por(primeira.lineno, f"a docstring: a documentação de {no.name}")
            antes, self.func = self.func, no
            self.corpo(no.body)
            self.func = antes
        elif isinstance(no, ast.ClassDef):
            metodos = [m for m in self.classes.get(no.name, {}) if m != "__init__"]
            com = f", com os métodos {', '.join(metodos)}" if metodos else ""
            self.por(n, f"cria a classe {no.name}: o molde dos objetos {no.name}{com}")
            antes, self.classe = self.classe, no
            self.corpo(no.body)
            self.classe = antes
        elif isinstance(no, ast.Return):
            if no.value is None:
                self.por(n, "sai da função sem devolver valor (None)")
            else:
                self.por(n, self.caber(lambda pr: f"devolve {self.e(no.value, pr)}"))
        elif isinstance(no, ast.Assign) and len(no.targets) == 1 and self.frase_de_variavel(no, n):
            pass
        elif isinstance(no, ast.Assign):
            alvos = " e ".join(self.cod(t) for t in no.targets)
            if isinstance(no.targets[0], ast.Tuple):
                self.por(n, self.caber(lambda pr: f"{alvos} recebem {self.e(no.value, pr)}"))
            elif isinstance(no.targets[0], ast.Subscript) and isinstance(no.targets[0].slice, ast.Constant) \
                    and isinstance(no.targets[0].slice.value, str):
                alvo = no.targets[0]
                self.por(n, self.caber(lambda pr: f"o campo {self.cod(alvo.slice)} de {self.cod(alvo.value)} "
                                                  f"recebe {self.e(no.value, pr)}"))
            else:
                self.por(n, self.caber(lambda pr: f"{alvos} recebe {self.e(no.value, pr)}"))
        elif isinstance(no, ast.AnnAssign):
            if no.value is not None:
                self.por(n, self.caber(lambda pr: f"{self.cod(no.target)} recebe {self.e(no.value, pr)}"))
        elif isinstance(no, ast.AugAssign):
            alvo, v = self.cod(no.target), self.e(no.value, 1)
            k = self.chave(no.target)
            if k in self.vidas:
                sinal = {ast.Add: "recebe +", ast.Sub: "recebe −", ast.Mult: "é multiplicado por ",
                         ast.Div: "é dividido por "}.get(type(no.op), "é atualizado com ")
                self.por(n, f"{alvo}{self.nasceu(k)} {sinal}{v}{self.quando(self.condicoes_da_linha(n, k))}",
                         curta=f"{alvo} {sinal}{v}")
            else:
                self.por(n, {ast.Add: f"soma {v} a {alvo}", ast.Sub: f"tira {v} de {alvo}",
                             ast.Mult: f"multiplica {alvo} por {v}", ast.Div: f"divide {alvo} por {v}"}.get(
                    type(no.op), f"atualiza {alvo} com {v}"))
        elif isinstance(no, ast.Expr):
            v = no.value
            if isinstance(v, ast.Constant) and isinstance(v.value, str):
                self.por(n, "texto solto, que não é guardado")
            elif isinstance(v, ast.Call):
                texto = self.caber(lambda pr: self.chamada(v, pr, como_frase=True))
                f = v.func
                k = self.chave(f.value) if isinstance(f, ast.Attribute) and isinstance(
                    f.value, (ast.Name, ast.Attribute)) else None
                curta = texto
                if k in self.vidas and any(m["linha"] == n for m in self.vidas[k]["mudancas"]):
                    texto = f"{self.cod(f.value)}{self.nasceu(k)}: {texto}{self.quando(self.condicoes_da_linha(n, k))}"
                self.por(n, texto, curta=curta)
            else:
                self.por(n, self.caber(lambda pr: f"calcula {self.e(v, pr)} (e não guarda)"))
        elif isinstance(no, (ast.For, ast.AsyncFor)):
            it = no.iter
            if isinstance(it, ast.Call) and isinstance(it.func, ast.Name) and it.func.id == "range":
                self.por(n, f"repete para cada {self.cod(no.target)} {self.intervalo(it)}")
            else:
                self.por(n, self.caber(lambda pr: f"repete para cada {self.cod(no.target)} em {self.e(it, pr)}"))
            self.corpo(no.body)
            self.senao(no, "senão (se o laço terminou sem break)")
        elif isinstance(no, ast.While):
            self.por(n, self.caber(lambda pr: f"repete enquanto {self.e(no.test, pr)}"))
            self.corpo(no.body)
            self.senao(no, "senão (se o laço terminou sem break)")
        elif isinstance(no, ast.If):
            eh_elif = n and self.linhas[n - 1].strip().startswith("elif")
            pergunta = self.caber(lambda pr: f"{'senão, se' if eh_elif else 'se'} {self.e(no.test, pr)}")
            self.por(n, self.anotar(pergunta, no.test), curta=pergunta)
            self.corpo(no.body)
            if no.orelse and isinstance(no.orelse[0], ast.If) and \
                    self.linhas[no.orelse[0].lineno - 1].strip().startswith("elif"):
                self.frase(no.orelse[0])
            else:
                self.senao(no, "senão")
        elif isinstance(no, ast.Try) or type(no).__name__ == "TryStar":
            self.por(n, "tenta o bloco abaixo")
            self.corpo(no.body)
            for h in no.handlers:
                if h.type is None:
                    oque = "qualquer erro"
                elif isinstance(h.type, ast.Tuple):
                    oque = " ou ".join(self.cod(t) for t in h.type.elts)
                else:
                    oque = self.cod(h.type)
                guarda = f" (guarda o erro em {h.name})" if h.name else ""
                self.por(h.lineno, f"se der {oque}, cai aqui{guarda}")
                self.corpo(h.body)
            self.senao(no, "se não deu erro nenhum")
            if no.finalbody:
                fim = self.linha_com(no.body[-1].end_lineno, no.finalbody[0].lineno - 1, "finally")
                self.por(fim, "no fim, sempre — com erro ou sem")
                self.corpo(no.finalbody)
        elif isinstance(no, ast.Raise):
            exc = no.exc
            if exc is None:
                self.por(n, "levanta o mesmo erro de novo, para quem chamou")
            elif isinstance(exc, ast.Call) and isinstance(exc.func, ast.Name) and exc.args and \
                    isinstance(exc.args[0], (ast.Constant, ast.JoinedStr)):
                self.por(n, f"para aqui e levanta o erro {exc.func.id}, com a mensagem {self.cod(exc.args[0])}")
            else:
                self.por(n, f"para aqui e levanta {self.cod(exc)}")
        elif isinstance(no, ast.Import):
            self.por(n, "importa " + ", ".join(
                f"{a.name} com o nome {a.asname}" if a.asname else a.name for a in no.names))
        elif isinstance(no, ast.ImportFrom):
            self.por(n, f"traz {', '.join(a.name for a in no.names)} de {no.module or '.'}")
        elif isinstance(no, (ast.With, ast.AsyncWith)):
            partes = [f"{self.e(i.context_expr, 1)}" + (f" como {self.cod(i.optional_vars)}" if i.optional_vars else "")
                      for i in no.items]
            self.por(n, f"abre {', '.join(partes)}; fecha sozinho no fim do bloco")
            self.corpo(no.body)
        elif isinstance(no, ast.Pass):
            self.por(n, "não faz nada (lugar reservado)")
        elif isinstance(no, ast.Break):
            self.por(n, "sai do laço")
        elif isinstance(no, ast.Continue):
            self.por(n, "pula para a próxima volta do laço")
        elif isinstance(no, ast.Delete):
            self.por(n, "apaga " + ", ".join(self.cod(t) for t in no.targets))
        elif isinstance(no, ast.Assert):
            self.por(n, self.caber(lambda pr: f"confere que {self.e(no.test, pr)} (senão, AssertionError)"))
        elif isinstance(no, (ast.Global, ast.Nonlocal)):
            self.por(n, "usa " + ", ".join(no.names) + " de fora da função")
        elif hasattr(ast, "Match") and isinstance(no, ast.Match):
            self.por(n, f"compara {self.cod(no.subject)} com os casos abaixo")
            for c in no.cases:
                self.por(c.pattern.lineno, f"caso {self.cod(c.pattern)}")
                self.corpo(c.body)

    def frase_de_variavel(self, no, n):
        """Nascimento ou mudança de uma variável (ou de uma posição dela). False: não é o caso."""
        alvo, valor = no.targets[0], no.value
        if isinstance(alvo, ast.Subscript):
            k = self.chave(alvo.value) if isinstance(alvo.value, (ast.Name, ast.Attribute)) else None
            if k not in self.vidas or (isinstance(alvo.slice, ast.Constant) and isinstance(alvo.slice.value, str)):
                return False
            lugar = f"na lista {self.cod(alvo.value)}" if self.e_lista(alvo.value) else f"em {self.cod(alvo.value)}"
            nucleo = self.caber(lambda pr: f"a posição {self.cod(alvo.slice)} passa a guardar {self.e(valor, pr)}")
            self.por(n, f"{lugar}{self.nasceu(k)}, {nucleo}{self.quando(self.condicoes_da_linha(n, k))}",
                     curta=f"{lugar}, {nucleo}")
            return True
        k = self.chave(alvo) if isinstance(alvo, (ast.Name, ast.Attribute)) else None
        v = self.vidas.get(k)
        if v is None:
            return False
        nome = self.cod(alvo)
        if v["nasce"] != n:                                   # já existia: mudou
            nucleo = self.caber(lambda pr: f"passa a valer {self.e(valor, pr)}")
            self.por(n, f"{nome}{self.nasceu(k)} {nucleo}{self.quando(self.condicoes_da_linha(n, k))}",
                     curta=f"{nome} {nucleo}")
            return True
        if isinstance(valor, ast.Constant):
            o_que = f"vale {self.cod(valor)}"
        elif isinstance(valor, ast.Name) and self.e_parametro(valor.id):
            o_que = f"guarda o parâmetro {valor.id} (o valor que chega entre os parênteses)"
        else:
            o_que = None
        if isinstance(alvo, ast.Attribute):                   # self.x = ...: o atributo nasce no objeto
            texto = self.caber(lambda pr: f"o objeto (self) ganha o atributo {alvo.attr}, que "
                                          f"{o_que or 'guarda ' + self.e(valor, pr)}")
        elif o_que and o_que.startswith("vale"):
            texto = f"{nome}: variável de valor {self.cod(valor)}"
        else:
            texto = self.caber(lambda pr: f"{nome}: variável que {o_que or 'guarda ' + self.e(valor, pr)}")
        self.por(n, texto + self.biografia(k), curta=texto)
        return True

    def senao(self, no, texto):
        if no.orelse:
            ultimo = (no.handlers[-1].body if isinstance(no, ast.Try) and no.handlers else no.body)[-1]
            linha = self.linha_com(ultimo.end_lineno, no.orelse[0].lineno - 1, "else")
            self.por(linha, texto)
            self.corpo(no.orelse)


# ── 2b. o fluxo: o que liga com o quê, para as setas ───────────────────────
#
# Só as ligações; onde cada seta passa na tela é a extensão quem decide (ela sabe o tamanho de cada
# linha, os valores ao lado e a fonte do editor). As colunas são em letras, não em bytes.

def _cai(corpo):
    """As linhas de onde a execução cai pelo fim deste bloco (sem return nem raise). [] = nunca cai."""
    if not corpo:
        return []
    ultimo = corpo[-1]
    if isinstance(ultimo, (ast.Return, ast.Raise, ast.Continue, ast.Break)):
        return []
    if isinstance(ultimo, ast.If):
        return _cai(ultimo.body) + (_cai(ultimo.orelse) if ultimo.orelse else [ultimo.lineno])
    if isinstance(ultimo, ast.While) and isinstance(ultimo.test, ast.Constant) and ultimo.test.value is True \
            and not any(isinstance(x, ast.Break) for x in ast.walk(ultimo)):
        return []
    if isinstance(ultimo, (ast.For, ast.AsyncFor, ast.While)):
        return [ultimo.lineno] + _cai(ultimo.orelse)
    if isinstance(ultimo, (ast.With, ast.AsyncWith)):
        return _cai(ultimo.body)
    if isinstance(ultimo, ast.Try) or type(ultimo).__name__ == "TryStar":
        caem = _cai(ultimo.orelse) if ultimo.orelse else _cai(ultimo.body)
        for h in ultimo.handlers:
            caem += _cai(h.body)
        if ultimo.finalbody and not _cai(ultimo.finalbody):
            return []
        return caem
    if hasattr(ast, "Match") and isinstance(ultimo, ast.Match):
        return [x for c in ultimo.cases for x in _cai(c.body)] + [ultimo.lineno]
    return [ultimo.end_lineno or ultimo.lineno]


def _pega(handler, nome):
    """Este except pega um erro com este nome? Os do Python, pela família: ValueError é um Exception."""
    if handler.type is None:
        return True
    import builtins
    tipos = handler.type.elts if isinstance(handler.type, ast.Tuple) else [handler.type]
    erro = getattr(builtins, nome, None) if nome else None
    for t in tipos:
        tn = t.id if isinstance(t, ast.Name) else None
        if tn and tn == nome:
            return True
        pai = getattr(builtins, tn, None) if tn else None
        if isinstance(erro, type) and isinstance(pai, type) and issubclass(erro, pai):
            return True
    return False


def fluxo(arvore, leitor):
    """{funcoes, lacos, decisoes, erros, inicio}: as ligações do arquivo, para as setas."""
    pai = {}
    for no in ast.walk(arvore):
        for filho in ast.iter_child_nodes(no):
            pai[filho] = no

    def dono(no):
        p = pai.get(no)
        while p is not None and not isinstance(p, (ast.FunctionDef, ast.AsyncFunctionDef)):
            p = pai.get(p)
        return p

    def classe_de_func(f):
        p = pai.get(f)
        return p.name if isinstance(p, ast.ClassDef) else None

    def letra(n, col):
        texto = leitor.linhas[n - 1] if 0 < n <= len(leitor.linhas) else ""
        return len(texto.encode("utf-8")[:col].decode("utf-8", errors="ignore"))

    defs = {}
    for no in ast.walk(arvore):
        if isinstance(no, (ast.FunctionDef, ast.AsyncFunctionDef)):
            cls = classe_de_func(no)
            defs.setdefault(f"{cls}.{no.name}" if cls else no.name, no)

    def alvo_da_chamada(c):
        f = c.func
        if isinstance(f, ast.Name):
            if f.id in defs:
                return f.id
            if f.id in leitor.classes and f"{f.id}.__init__" in defs:      # MyArray(10) roda o __init__
                return f"{f.id}.__init__"
            return None
        if isinstance(f, ast.Attribute) and isinstance(f.value, ast.Name):
            d = dono(c)
            if f.value.id == "self" and d is not None:
                cls = classe_de_func(d)
                return f"{cls}.{f.attr}" if cls and f"{cls}.{f.attr}" in defs else None
            cls = leitor.tipos.get((id(d) if d is not None else "mod", f.value.id)) or \
                leitor.tipos.get(("mod", f.value.id))
            return f"{cls}.{f.attr}" if cls and f"{cls}.{f.attr}" in defs else None
        return None

    chamadas = {}
    for no in ast.walk(arvore):
        if isinstance(no, ast.Call):
            alvo = alvo_da_chamada(no)
            if alvo and dono(no) is not defs[alvo]:              # recursão: fica sem seta
                chamadas.setdefault(alvo, []).append(no)

    funcoes = []
    for chave, f in defs.items():
        if chave not in chamadas:
            continue
        params = [a.arg for a in f.args.posonlyargs + f.args.args if a.arg not in ("self", "cls")]
        rets, pilha = [], list(f.body)
        while pilha:
            no = pilha.pop()
            if isinstance(no, ast.Return) and no.value is not None:
                rets.append(no)
            if not isinstance(no, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Lambda)):
                pilha.extend(ast.iter_child_nodes(no))
        rets.sort(key=lambda r: r.lineno)
        devolve = bool(rets) and f.name != "__init__"
        caem = []
        if devolve:
            em_except = set()
            for no in ast.walk(f):
                if isinstance(no, ast.ExceptHandler):
                    em_except.update(range(no.lineno, (no.end_lineno or no.lineno) + 1))
            caem = [{"linha": n, "motivo": "se deu erro" if n in em_except else "sem return"} for n in _cai(f.body)]
        funcoes.append({
            "nome": f.name, "chave": chave, "linha": f.lineno,
            "chamadas": [{"linha": c.lineno, "args": leitor.nomeados(c, params)}
                         for c in sorted(chamadas[chave], key=lambda c: (c.lineno, c.col_offset))],
            "retornos": [{"linha": r.lineno, "texto": leitor.cod(r.value)} for r in rets] if devolve else [],
            "caem": caem,
        })
    funcoes.sort(key=lambda x: x["linha"])

    lacos, decisoes, erros = [], [], []
    for no in ast.walk(arvore):
        if isinstance(no, (ast.For, ast.AsyncFor, ast.While)) and no.body:
            lacos.append({"linha": no.lineno, "col": letra(no.lineno, no.col_offset),
                          "fim": no.body[-1].end_lineno or no.body[-1].lineno})
        elif isinstance(no, ast.If) and no.body:
            d = {"linha": no.lineno, "col": letra(no.lineno, no.col_offset), "sim": no.body[0].lineno, "nao": None}
            elif_depois = no.orelse and isinstance(no.orelse[0], ast.If) and len(no.orelse) == 1 and \
                leitor.linhas[no.orelse[0].lineno - 1].strip().startswith("elif")
            if no.orelse and not elif_depois:
                d["nao"] = no.orelse[0].lineno
            decisoes.append(d)
        elif isinstance(no, ast.Try) or type(no).__name__ == "TryStar":
            pilha = list(no.body)
            while pilha:
                x = pilha.pop()
                if isinstance(x, ast.Raise) and x.exc is not None:
                    e = x.exc.func if isinstance(x.exc, ast.Call) else x.exc
                    nome = e.id if isinstance(e, ast.Name) else None
                    h = next((h for h in no.handlers if _pega(h, nome)), None)
                    if h is not None:
                        erros.append({"de": x.lineno, "col": letra(x.lineno, x.col_offset), "para": h.lineno,
                                      "col_try": letra(no.lineno, no.col_offset)})
                if not isinstance(x, (ast.Try, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Lambda)) \
                        and type(x).__name__ != "TryStar":
                    pilha.extend(ast.iter_child_nodes(x))

    inicio, viu_definicao = None, False
    for no in arvore.body:
        if isinstance(no, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            viu_definicao = True
        elif isinstance(no, (ast.Import, ast.ImportFrom)) or (
                isinstance(no, ast.Expr) and isinstance(no.value, ast.Constant) and isinstance(no.value.value, str)):
            continue
        else:
            inicio = no.lineno if viu_definicao else None
            break

    corpos = sorted(({"nome": f.name, "linha": f.lineno, "fim": f.end_lineno or f.lineno} for f in defs.values()),
                    key=lambda x: x["linha"])
    return {"funcoes": funcoes, "corpos": corpos,
            "lacos": sorted(lacos, key=lambda x: x["linha"]),
            "decisoes": sorted(decisoes, key=lambda x: x["linha"]),
            "erros": sorted(erros, key=lambda x: x["de"]),
            "inicio": inicio}


# ── 3. ler um arquivo que pode estar quebrado ──────────────────────────────

def _neutralizar(linhas, n, msg):
    """Tira a linha n do caminho para o resto do arquivo poder ser lido — sem mudar a numeração."""
    m = re.match(r"expected an indented block after .+? on line (\d+)", msg)
    if m:                                   # o bloco ainda sem corpo: o corpo vira um pass na própria linha
        k = int(m.group(1))
        linhas[k - 1] = linhas[k - 1].split("#")[0].rstrip() + " pass"
        return linhas
    if n > len(linhas):
        return linhas
    original = linhas[n - 1]
    recuo = original[:len(original) - len(original.lstrip())]
    if msg.startswith("unexpected indent") or not original.strip():
        linhas[n - 1] = ""
    elif msg.startswith("expected ':'") and not original.rstrip().endswith(":"):
        linhas[n - 1] = original.split("#")[0].rstrip() + ":"      # o ':' que faltou: o corpo segue legível
    else:
        linhas[n - 1] = recuo + "pass"
    return linhas


def ler(fonte):
    """{"linhas": {n: {"descricao"}}, "erro": {"linha", "texto", "original"} ou None}."""
    linhas = fonte.splitlines()
    erro, arvore, tentativas = None, None, 0
    vistos = set()
    while tentativas < 40:
        tentativas += 1
        try:
            arvore = ast.parse("\n".join(linhas) + "\n")
            break
        except SyntaxError as e:
            n_onde, texto = traduzir_sintaxe(e, "\n".join(linhas))
            if erro is None:
                erro = {"linha": n_onde, "texto": texto, "original": e.msg}
            n = e.lineno or len(linhas)
            if (n, e.msg) in vistos:            # não andou: apaga a linha de vez
                if n <= len(linhas):
                    linhas[n - 1] = ""
                else:
                    break
            vistos.add((n, e.msg))
            linhas = _neutralizar(linhas, n, e.msg)
    leitor = Leitor(fonte)
    ligacoes, sugestoes = None, []
    if arvore is not None:
        for no in ast.walk(arvore):
            if isinstance(no, ast.Import):
                for a in no.names:
                    leitor.modulos[a.asname or a.name.split(".")[0]] = a.name
            elif isinstance(no, ast.ImportFrom):
                for a in no.names:
                    leitor.modulos[a.asname or a.name] = f"{no.module}.{a.name}"
            if isinstance(no, (ast.FunctionDef, ast.AsyncFunctionDef)):
                leitor.funcoes[no.name] = [a.arg for a in no.args.posonlyargs + no.args.args
                                           if a.arg not in ("self", "cls")]
        leitor.linhas = linhas + [""] * 3
        leitor.fonte = "\n".join(linhas) + "\n"
        leitor.colher(arvore.body, [])
        leitor.func = leitor.classe = None
        for no in arvore.body:
            try:
                leitor.frase(no)
            except Exception:           # uma frase que a leitura não soube dizer não derruba as outras
                pass
        leitor.func = leitor.classe = None
        try:
            ligacoes = fluxo(arvore, leitor)
        except Exception:
            ligacoes = None
        try:
            sugestoes = _sugestoes.sugerir(arvore, leitor.fonte) if _sugestoes else []
        except Exception:
            sugestoes = []
    linhas_saida = {}
    for n, t in sorted(leitor.saida.items()):
        linhas_saida[str(n)] = {"descricao": t}
        if n in leitor.curtas:
            linhas_saida[str(n)]["curta"] = leitor.curtas[n]
    resultado = {"linhas": linhas_saida, "erro": erro, "fluxo": ligacoes, "sugestoes": sugestoes}
    if erro:
        resultado["linhas"].pop(str(erro["linha"]), None)
    return resultado


def main(args):
    if not args:
        print(__doc__)
        return 2
    fonte = sys.stdin.read() if args[0] == "-" else open(args[0], encoding="utf-8").read()
    print(json.dumps(ler(fonte), ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
