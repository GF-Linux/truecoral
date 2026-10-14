"""As sugestões: uma forma reconhecida no seu código, e o molde da literatura do Python que resolve aquela forma.

Nada aqui é "pensado". Cada regra é um par:
  - o detector: uma forma da árvore do código (o ast), reconhecida por comparação
  - a ficha: o molde da documentação oficial (docs.python.org), com o link, a citação e um exemplo

A ficha responde sempre as mesmas perguntas: precisa de import? qual a sintaxe? o que devolve? e um
exemplo para entender olhando, com a saída de cada linha ao lado. O exemplo é o da documentação, sem
mudar nada; o português fica só nos comentários. As saídas foram conferidas rodando cada exemplo.

A sugestão mostra o molde, nunca o seu código reescrito: quem adapta é você.

O catálogo cresce com o estudo: cada código que confundir vira uma regra nova, com o molde e a fonte.
"""
import ast

# ── as fichas: o molde de cada sugestão, tirado da documentação oficial ─────

FICHAS = {
    "contagem": {
        "titulo": "Contar valor por valor",
        "fonte": ("collections.Counter", "https://docs.python.org/3/library/collections.html#collections.Counter"),
        "exemplo": (
            "from collections import Counter          # import: vem com o Python, não precisa instalar\n"
            "c = Counter(['eggs', 'ham'])             # sintaxe: Counter(o que contar)\n"
            "c                                        # → Counter({'eggs': 1, 'ham': 1})\n"
            "c['bacon']                               # → 0: o que não apareceu vale zero\n"
            "Counter('abracadabra').most_common(3)    # → [('a', 5), ('b', 2), ('r', 2)]"),
        "devolve": "um `dict`: cada item é uma chave, e quantas vezes ele apareceu é o valor.",
        "citacao": "It is a collection where elements are stored as dictionary keys and their counts are "
                   "stored as dictionary values.",
        "traducao": "Os itens ficam como chaves do dicionário, e as contagens como valores.",
        "nota": "Exemplos da documentação; saídas conferidas rodando no Python 3.14.",
    },
    "posicao": {
        "titulo": "Pegar pelo número o que a função devolveu",
        "fonte": ("Tuples and Sequences", "https://docs.python.org/3/tutorial/datastructures.html#tuples-and-sequences"),
        "exemplo": (
            "t = 12345, 54321, 'hello!'    # uma sequência com 3 partes\n"
            "x, y, z = t                   # sintaxe: um nome para cada parte, na ordem (sem import)\n"
            "x                             # → 12345\n"
            "z                             # → 'hello!'\n"
            "a, b = t                      # → ValueError: too many values to unpack (expected 2, got 3)"),
        "devolve": "nada; cria uma variável para cada parte. O número de nomes tem que ser igual ao de partes.",
        "citacao": "This is called, appropriately enough, *sequence unpacking* and works for any sequence on "
                   "the right-hand side.",
        "traducao": "Isso se chama desempacotamento de sequência, e funciona com qualquer sequência do lado direito.",
        "nota": "Exemplo do tutorial; saídas conferidas rodando no Python 3.14.",
    },
    "repetida": {
        "titulo": "A mesma chamada, de novo",
        "fonte": ("An Informal Introduction to Python", "https://docs.python.org/3/tutorial/introduction.html#numbers"),
        "exemplo": (
            "width = 20            # guarda 20 no nome width (sem import)\n"
            "height = 5 * 9        # a conta roda uma vez; o resultado fica guardado em height\n"
            "width * height        # usa os nomes: nada é calculado de novo → 900"),
        "devolve": "nada; o nome passa a guardar o valor, e quem usa o nome usa o valor guardado.",
        "citacao": "The equal sign (`=`) is used to assign a value to a variable.",
        "traducao": "O sinal de igual (=) guarda um valor numa variável.",
        "nota": "Exemplo do tutorial; saída conferida rodando no Python 3.14.",
    },
    "encadeamento": {
        "titulo": "Encadeamento: a saída de uma função é a entrada da próxima",
        "fonte": ("Functional Programming HOWTO", "https://docs.python.org/3/howto/functional.html"),
        "exemplo": (
            "xvec = [10, 20, 30]\n"
            "yvec = [7, 5, 3]\n"
            "list(zip(xvec, yvec))                  # → [(10, 7), (20, 5), (30, 3)]\n"
            "sum(x*y for x,y in zip(xvec, yvec))    # a saída de zip entra na conta, e a conta em sum → 260"),
        "devolve": "o que a última função da cadeia devolve. Sem import: é só chamar uma dentro da outra, f(g(x)).",
        "citacao": "In a functional program, input flows through a set of functions. Each function operates on "
                   "its input and produces some output.",
        "traducao": "Num programa funcional, a entrada flui por um conjunto de funções. Cada uma opera sobre a "
                    "sua entrada e produz uma saída.",
        "nota": "Citação do HOWTO; exemplo do tutorial (Generator Expressions); saídas conferidas rodando no "
                "Python 3.14.",
    },
}

ORDEM = ["encadeamento", "repetida", "posicao", "contagem"]     # numa linha com duas, a primeira desta lista vem antes


def ficha(tipo, viu):
    """O texto do mouse em cima: o que eu vi, o exemplo, o que devolve, a citação e a fonte."""
    f = FICHAS[tipo]
    nome, url = f["fonte"]
    return "\n".join([
        f"**{f['titulo']}** · [docs.python.org › {nome} ↗]({url})", "",
        f"**O que eu vi:** {viu}", "",
        "```python\n" + f["exemplo"] + "\n```", "",
        f"**Devolve:** {f['devolve']}", "",
        "---", "",
        f"> {f['citacao']}  \n> *({f['traducao']})*", "",
        f"*{f['nota']}*",
    ])


# ── os detectores ──────────────────────────────────────────────────────────

ORDINAL = {0: "primeira", 1: "segunda", 2: "terceira", 3: "quarta", 4: "quinta", -1: "última"}
QUANTAS = {2: "duas", 3: "três", 4: "quatro", 5: "cinco"}
QUANTOS = {2: "dois", 3: "três", 4: "quatro", 5: "cinco"}


def _sempre_sai(corpo):
    """Este trecho sempre sai antes do fim (return, raise, continue, break, em todos os caminhos)?"""
    for st in corpo:
        if isinstance(st, (ast.Return, ast.Raise, ast.Continue, ast.Break)):
            return True
        if isinstance(st, ast.If) and st.orelse and _sempre_sai(st.body) and _sempre_sai(st.orelse):
            return True
        if isinstance(st, (ast.With, ast.AsyncWith)) and _sempre_sai(st.body):
            return True
        if (isinstance(st, ast.Try) or type(st).__name__ == "TryStar") and _sempre_sai(st.body + st.orelse) \
                and all(_sempre_sai(h.body) for h in st.handlers):
            return True
    return False


def _lista(nums):
    nums = [str(n) for n in nums]
    return nums[0] if len(nums) == 1 else ", ".join(nums[:-1]) + " e " + nums[-1]


class Detector:
    def __init__(self, arvore, fonte):
        self.arvore, self.fonte = arvore, fonte
        self.linhas = fonte.splitlines()
        self.bytes = [l.encode("utf-8") for l in fonte.split("\n")]     # para recortar pedaços sem dividir de novo
        self.achados = []
        self.pai, self.campo = {}, {}
        for no in ast.walk(arvore):
            for nome, valor in ast.iter_fields(no):
                for filho in (valor if isinstance(valor, list) else [valor]):
                    if isinstance(filho, ast.AST):
                        self.pai[filho] = no
                        self.campo[filho] = (no, nome)
        self.funcoes = {}           # nome → o def (só as funções de fora de classe, chamadas pelo nome)
        for no in ast.walk(arvore):
            if isinstance(no, (ast.FunctionDef, ast.AsyncFunctionDef)) and not isinstance(self.pai.get(no), ast.ClassDef):
                self.funcoes.setdefault(no.name, no)

    def cod(self, no):
        a, b = getattr(no, "lineno", None), getattr(no, "end_lineno", None)
        texto = None
        if a is not None and b is not None and b <= len(self.bytes):
            ca, cb = no.col_offset, no.end_col_offset
            partes = [self.bytes[a - 1][ca:cb]] if a == b else \
                [self.bytes[a - 1][ca:]] + self.bytes[a:b - 1] + [self.bytes[b - 1][:cb]]
            texto = b"\n".join(partes).decode("utf-8", errors="replace")
        return " ".join((texto or ast.unparse(no)).split())

    def letra(self, n, col):
        """O ast conta a coluna em bytes (UTF-8); o editor conta em letras: 'posição' tem 7 letras e 9 bytes."""
        texto = self.linhas[n - 1] if 0 < n <= len(self.linhas) else ""
        return len(texto.encode("utf-8")[:col].decode("utf-8", errors="ignore"))

    def achou(self, tipo, no_linha, col, col_fim, cinza, viu, linha=None):
        n = linha or no_linha.lineno
        col, col_fim = self.letra(n, col), self.letra(n, col_fim)
        self.achados.append({"tipo": tipo, "linha": n, "col": col, "col_fim": col_fim,
                             "cinza": cinza, "ficha": ficha(tipo, viu)})

    def retornos(self, func):
        """Os return com valor da própria função (não os das funções de dentro dela)."""
        achados, pilha = [], list(func.body)
        while pilha:
            no = pilha.pop()
            if isinstance(no, ast.Return) and no.value is not None:
                achados.append(no)
            if not isinstance(no, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Lambda)):
                pilha.extend(ast.iter_child_nodes(no))
        return sorted(achados, key=lambda r: r.lineno)

    def tupla_devolvida(self, nome):
        """Se a função devolve sempre várias coisas juntas (return a, b): o primeiro desses return."""
        func = self.funcoes.get(nome)
        rets = self.retornos(func) if func else []
        if rets and all(isinstance(r.value, ast.Tuple) and len(r.value.elts) >= 2 for r in rets):
            return rets[0]
        return None

    def chamadas_do_arquivo(self):
        """As chamadas f(...) das funções definidas no próprio arquivo, fora da própria função (sem recursão)."""
        saida = []
        for no in ast.walk(self.arvore):
            if isinstance(no, ast.Call) and isinstance(no.func, ast.Name) and no.func.id in self.funcoes:
                dono, p = None, self.pai.get(no)
                while p is not None:
                    if isinstance(p, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        dono = p
                        break
                    p = self.pai.get(p)
                if dono is None or dono.name != no.func.id:
                    saida.append(no)
        return sorted(saida, key=lambda c: (c.lineno, c.col_offset))

    def escopo(self, no):
        """A função onde o nó está (ou o módulo)."""
        p = self.pai.get(no)
        while p is not None and not isinstance(p, (ast.FunctionDef, ast.AsyncFunctionDef)):
            p = self.pai.get(p)
        return p if p is not None else self.arvore

    def instrucao(self, no):
        p = no
        while p is not None and not isinstance(p, ast.stmt):
            p = self.pai.get(p)
        return p

    # 1. a mesma lista contada valor por valor: X.count(1), X.count(2)…
    def contagem(self):
        vistos = []
        for st in ast.walk(self.arvore):
            if not isinstance(st, ast.stmt) or isinstance(st, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef,
                                                               ast.If, ast.For, ast.While, ast.Try, ast.With)):
                continue
            grupos = {}
            for no in ast.walk(st):
                if isinstance(no, ast.Call) and isinstance(no.func, ast.Attribute) and no.func.attr == "count" \
                        and len(no.args) == 1 and not no.keywords and isinstance(no.args[0], ast.Constant):
                    grupos.setdefault(self.cod(no.func.value), []).append(no)
            for alvo, chamadas in grupos.items():
                if len(chamadas) >= 2:
                    vistos.append((st, alvo, sorted(chamadas, key=lambda c: (c.lineno, c.col_offset))))
        vistos.sort(key=lambda v: v[0].lineno)
        usados = set()
        for i, (st, alvo, chamadas) in enumerate(vistos):
            if id(st) in usados:
                continue
            # as linhas seguidas com a mesma forma viram uma sugestão só, na primeira
            irmaos, fim = [], st.end_lineno
            for st2, alvo2, _ in vistos[i + 1:]:
                if st2.lineno == fim + 1 and id(st2) not in usados:
                    irmaos.append((st2, alvo2))
                    usados.add(id(st2))
                    fim = st2.end_lineno
            mostradas = ", ".join(f"`{self.cod(c)}`" for c in chamadas[:4]) + (", …" if len(chamadas) > 4 else "")
            viu = f"{mostradas}: `{alvo}` é percorrido uma vez para cada valor contado."
            for st2, alvo2 in irmaos:
                viu += f" Na linha {st2.lineno}, o mesmo com `{alvo2}`."
            c = chamadas[0]
            self.achou("contagem", c, c.col_offset, c.end_col_offset,
                       "contado valor por valor: collections.Counter conta tudo de uma vez", viu)

    # 2. f(...)[0]: a parte do retorno pega pela posição
    def posicao(self):
        for no in ast.walk(self.arvore):
            if not (isinstance(no, ast.Subscript) and isinstance(no.value, ast.Call)
                    and isinstance(no.value.func, ast.Name) and isinstance(no.slice, ast.Constant)
                    and isinstance(no.slice.value, int) and not isinstance(no.slice.value, bool)):
                continue
            ret = self.tupla_devolvida(no.value.func.id)
            if ret is None:
                continue
            k = no.slice.value
            n = len(ret.value.elts)
            qual = ORDINAL.get(k, f"parte {k}")
            viu = (f"`{self.cod(no)}`: `{no.value.func.id}` devolve {QUANTAS.get(n, n)} coisas "
                   f"(linha {ret.lineno}: `return {self.cod(ret.value)}`), e aqui a {qual} é pega pela posição. "
                   f"Quem lê precisa voltar à linha {ret.lineno} para saber o que é `[{k}]`.")
            self.achou("posicao", no, no.value.end_col_offset, no.end_col_offset,
                       f"[{k}] não diz o que é: desempacote e dê um nome", viu, linha=no.end_lineno)

    # 3. a mesma chamada, de novo, no mesmo lugar do código, com os mesmos argumentos que não mudaram no meio
    def exclusivas(self, a, b):
        """Só uma das duas pode rodar? Uma no if e a outra no else; em dois except; em dois case; ou a
        primeira num bloco que sempre sai (return, raise, continue, break) antes de chegar na segunda."""
        lado, cadeia = {}, []
        filho = a
        while filho in self.campo:
            pai, nome = self.campo[filho]
            lado[id(pai)] = (nome, filho)
            cadeia.append((filho, pai, nome))
            filho = pai
        filho = b
        while filho in self.campo:
            pai, nome = self.campo[filho]
            if id(pai) in lado:
                for x, p, campo in cadeia:              # abaixo do ponto em comum, do lado da primeira
                    if p is pai:
                        break
                    bloco = getattr(p, campo)
                    if isinstance(bloco, list) and isinstance(x, ast.stmt) and _sempre_sai(bloco[bloco.index(x):]):
                        return True
                nome_a, filho_a = lado[id(pai)]
                if isinstance(pai, (ast.If, ast.IfExp)):
                    return nome_a != nome and {nome_a, nome} <= {"body", "orelse"}
                if isinstance(pai, ast.Try) or type(pai).__name__ == "TryStar":
                    if nome_a == nome == "handlers":
                        return filho_a is not filho
                    return {nome_a, nome} == {"handlers", "orelse"}
                if hasattr(ast, "Match") and isinstance(pai, ast.Match):
                    return nome_a == nome == "cases" and filho_a is not filho
                return False
            filho = pai
        return False

    def mudou_entre(self, escopo, nomes, de, ate):
        """Algum destes nomes recebe valor novo entre as duas linhas?"""
        for no in ast.walk(escopo):
            alvos = []
            if isinstance(no, ast.Assign):
                alvos = no.targets
            elif isinstance(no, (ast.AugAssign, ast.AnnAssign, ast.For, ast.AsyncFor)):
                alvos = [no.target]
            elif isinstance(no, ast.NamedExpr):
                alvos = [no.target]
            if de < getattr(no, "lineno", 0) <= ate:
                for alvo in alvos:
                    if any(isinstance(x, ast.Name) and x.id in nomes for x in ast.walk(alvo)):
                        return True
        return False

    def numa_volta(self, no):
        """Dentro de uma compreensão ou de um lambda: cada volta tem a sua variável."""
        p = self.pai.get(no)
        while p is not None and not isinstance(p, ast.stmt):
            if isinstance(p, (ast.ListComp, ast.SetComp, ast.DictComp, ast.GeneratorExp, ast.Lambda)):
                return True
            p = self.pai.get(p)
        return False

    def repetida(self):
        grupos = {}
        for c in self.chamadas_do_arquivo():
            if self.numa_volta(c):
                continue
            nomes = {x.id for a in c.args + [k.value for k in c.keywords] for x in ast.walk(a) if isinstance(x, ast.Name)}
            if not nomes or not self.retornos(self.funcoes[c.func.id]):
                continue        # só valores escritos direto (fonte(8)): chamar de novo é escolha de estilo, não repetição
            escopo = self.escopo(c)
            grupos.setdefault((id(escopo), self.cod(c)), []).append((c, nomes, escopo))
        todas = {}
        for c in self.chamadas_do_arquivo():
            todas.setdefault(self.cod(c), []).append(c)
        for (_, texto), chamadas in grupos.items():
            for i, (c2, nomes, escopo) in enumerate(chamadas):
                antes = next((c1 for c1, _, _ in chamadas[:i]
                              if not self.exclusivas(c1, c2) and not self.mudou_entre(escopo, nomes, c1.lineno, c2.lineno)), None)
                if antes is None:
                    continue
                viu = (f"`{texto}` na linha {antes.lineno} e de novo aqui, na {c2.lineno}, com os mesmos argumentos "
                       f"(nenhum deles recebe valor novo entre as duas linhas).")
                fora = [c for c in todas.get(texto, []) if c not in [x for x, _, _ in chamadas]]
                for c in fora:
                    st = self.instrucao(c)
                    if isinstance(st, ast.Assign) and st.value is c:
                        alvos = " e ".join(self.cod(t) for t in st.targets)
                        viu += f" Na linha {st.lineno}, a mesma chamada foi guardada em `{alvos}`."
                        break
                self.achou("repetida", c2, c2.col_offset, c2.end_col_offset,
                           f"a mesma chamada da linha {antes.lineno}, com os mesmos argumentos", viu)

    # 4. a função devolve várias coisas juntas, e elas seguem juntas para as próximas funções
    def encadeamento(self):
        for nome in self.funcoes:
            ret = self.tupla_devolvida(nome)
            if ret is None:
                continue
            for st in ast.walk(self.arvore):
                if not (isinstance(st, ast.Assign) and len(st.targets) == 1 and isinstance(st.targets[0], ast.Tuple)
                        and isinstance(st.value, ast.Call) and isinstance(st.value.func, ast.Name)
                        and st.value.func.id == nome):
                    continue
                nomes = [t.id for t in st.targets[0].elts if isinstance(t, ast.Name)]
                if len(nomes) < 2:
                    continue
                seguem = []
                for c in self.chamadas_do_arquivo():
                    usados = {a.id for a in c.args if isinstance(a, ast.Name)} | {
                        k.value.id for k in c.keywords if isinstance(k.value, ast.Name)}
                    if c.lineno > st.lineno and set(nomes) <= usados and c.func.id != nome:
                        seguem.append(c)
                if not seguem:
                    continue
                juntos = " e ".join(f"`{n}`" for n in nomes)
                para = ", ".join(f"`{c.func.id}` (linha {c.lineno})" for c in seguem[:4])
                q = QUANTAS.get(len(nomes), str(len(nomes)))
                viu = (f"`{nome}` devolve {juntos} juntos. Na linha {st.lineno} eles são separados, e depois seguem "
                       f"juntos para {para}: cada função seguinte recebe os {QUANTOS.get(len(nomes), len(nomes))}.")
                v = ret.value
                self.achou("encadeamento", ret, v.col_offset, v.end_col_offset,
                           f"devolve {q} coisas juntas: cada função seguinte vai ter que carregar as {q}", viu)
                break


def sugerir(arvore, fonte):
    """[{tipo, linha, col, col_fim, cinza, ficha}], ordenadas pela linha; numa linha, pela ORDEM."""
    d = Detector(arvore, fonte)
    for regra in (d.encadeamento, d.repetida, d.posicao, d.contagem):
        try:
            regra()
        except Exception:           # uma regra que falhou não derruba as outras
            pass
    return sorted(d.achados, key=lambda a: (a["linha"], ORDEM.index(a["tipo"]), a["col"]))
