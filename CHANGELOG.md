# Mudanças

## 0.6.0

- **a variável conta a própria história.** Na linha onde ela nasce, a descrição diz o que ela é e cada
  mudança escrita depois, com a condição: *contador: variável de valor 0; depois, recebe +1, quando o
  resto de x por 2 é igual a 0, para cada x em lista*. Na linha que muda: *contador (que nasceu valendo
  0) recebe +1, quando…*. Apagou o `+=`? A história volta a ser só o nascimento — a cada tecla.
- **o else diz o que não aconteceu:** *quando nem self.size == 0, nem index < 0 or index >= self.size*.
- **sintaxe e lógica:** o `self` é o objeto; o atributo nasce no `__init__`; `[None] * n` é uma lista de
  n posições; `lista[i]` é o valor da posição i; `a.insert(10)` roda o método insert da sua classe com
  `value = 10`; um método sem `return` avisa que devolve None.
- corrigido: a posição de uma lista (`self.array[self.size - 1]`) era descrita como filtro de linhas do
  pandas, e `a.get(0)` de uma classe sua, como o `get` do dicionário.
- passar o mouse no fim da linha mostra a descrição inteira, quando ela passa da largura da tela.

## 0.5.1

- **o snippet do `compare` escreve só a chamada**, `compare(v1, v2)`, como o da `replacement`. O
  `a, b =` da 0.5.0 entrava onde o cursor estivesse e quebrava a linha: `y = comp` + Tab virava
  `y = a, b = compare(...)`, e `v.comp` virava `v.a, b = compare(...)`.
- **a leitura reconhece a viper com apelido:** `import viper as v` → `v.compare(...)`, e
  `from viper import compare as cmp` → `cmp(...)`.

## 0.5.0

- **o snippet do `compare`, da viper:** digite `compare` e aperte Tab — a chamada nasce desempacotada,
  `a, b = compare(v1, v2)`, porque ela devolve os dois lados.
- **a leitura conhece a viper:** com `from viper import replacement, compare`, a descrição diz o que
  elas fazem — *x recebe a lista [1, 2, 3, 4, 5] com 'par' no lugar de cada x em que o resto de x por 2
  é igual a 0*. Uma função sua com o mesmo nome, que não vem da viper, continua descrita pela forma.
- desempacotar diz quem recebe: *a, b recebem …*

## 0.4.0

- **a leitura: o que cada linha faz, a cada tecla.** Ao lado de cada linha, em cinza, a descrição em
  português — `def calculadora(a, b):` → *função calculadora, recebe a, b*; `return a + b` → *devolve a
  soma de a e b*. Não roda nada do seu código: só lê. Por isso vale para a função que ninguém chamou
  ainda, e aparece enquanto você digita, sem salvar.
- **o erro de escrita, traduzido e na linha.** `print(calculadora(1, 2)` → *✕ faltou fechar o '('*;
  `x = [1, 2, 3)` → *✕ abriu com '[' e fechou com ')': esperava-se ']'*; `if x = 3:` → *✕ '=' guarda um
  valor; para comparar é '=='*. Uma linha quebrada não apaga a descrição das outras.
- o Ctrl+S continua igual: os valores (`= › ↩ ↻`) vêm ao salvar, ao lado da descrição.
- o `print` de uma função aparece na linha do `print`, e não na última linha da função.
- `coral arquivo.py` mostra a descrição no fim de cada linha (`--sem-descricao` para tirar).

## 0.3.0

- **a extensão leva a configuração junto:** o snippet da viper (`replacement` + Tab, com o `lambda x:`
  já escrito), o nome dos parâmetros em cinza nas chamadas (Pylance) e os snippets primeiro na lista,
  em arquivos Python. Instalou a extensão, veio tudo; nada para exportar de máquina para máquina.
- ícone

## 0.2.0

Correções que a bateria de testes (`tests/bateria/`) encontrou:

- **laço dentro de laço**: o laço de fora contava as voltas do de dentro. Agora a volta é contada no
  próprio cabeçalho, e o laço que roda várias vezes diz quantas: `↻ 3 execuções · 9 voltas no total
  · saiu pelo break · linha 5 ×3`
- **laço só longo não é "infinito"**: um `for` que bate no limite de tempo diz "parou no limite antes
  de terminar"; o "laço infinito?" fica para o `while` cuja condição nunca deu False

Novidades:

- **erro tratado**: `⚡ ValueError → tratado na linha 4` onde o erro nasceu — o `try/except` deixa de ser
  invisível
- **o que a função devolveu**: `↩ 2 → 6 → 24 → 120` no `return` (e no `yield`), e `chamada 5×` no `def`
- listas e textos grandes são resumidos em tempo constante (`reprlib`): uma lista que cresce dentro do
  laço não é mais relida inteira a cada volta

## 0.1.0

O motor, o comando `coral` e a extensão do VS Code.
