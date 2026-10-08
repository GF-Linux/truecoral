# True Coral

**A coral verdadeira.** A falsa coral imita a perigosa e engana quem olha; a verdadeira é o que
parece. O True Coral mostra, linha por linha, o que o seu código fez de verdade: o que cada linha
guardou, quantas voltas cada laço deu e por onde saiu, quantas vezes cada condição deu True ou
False, o que o print escreveu e, se der erro, onde e por quê — em português.

Duas camadas na mesma linha:

- **a leitura, a cada tecla** — o que a linha **faz**, em português, e o erro de escrita traduzido.
  Não roda nada: só lê. Vale para a função que ninguém chamou ainda.

  ```
  def calculadora(a, b):       — função calculadora, recebe a, b
      return a + b             — devolve a soma de a e b
  print(calculadora(1, 2)      ✕ faltou fechar o '('
  ```
- **o motor, ao salvar** — o que a linha **produziu**: os valores, os laços, as condições, as saídas.

  ```
  def calculadora(a, b):       chamada 1×   — função calculadora, recebe a, b
      return a + b             ↩ 3 · int    — devolve a soma de a e b
  print(calculadora(1, 2))     › 3          — mostra na tela o que calculadora devolve com a = 1, b = 2
  ```

Dois jeitos de ver, os mesmos programas por trás:

- **no VS Code** — a leitura enquanto você digita; os valores ao salvar; o detalhe ao passar o mouse;
  erro vira sublinhado vermelho e entra no painel de Problemas (`vscode/`);
- **no terminal** — `coral arquivo.py` desenha o arquivo com os valores e a descrição.

| marcação | o que diz |
|---|---|
| `= valor · tipo` | o que a linha guardou; num laço, a evolução até o valor final |
| `↻ N voltas · …` | quantas voltas o laço deu e por onde saiu: fim, condição falsa, break ou limite |
| `True ×a · False ×b` | quantas vezes a condição deu cada resposta |
| `↩ valor` | o que a função devolveu (`return`, `yield`); no `def`, quantas vezes foi chamada |
| `⚡ Erro → tratado na linha N` | um erro que aconteceu e foi tratado por um `try/except` |
| `› texto` | o que o print escreveu (e `retorna None`, apagado, à parte) |
| `! …` | um fato que merece atenção: vazios (NaN) num DataFrame, um NaN |
| `✕ Erro` | onde parou, com a explicação em português e a mensagem original |
| `· não rodou` | linha que o caminho do programa nunca alcançou |
| `— …` | **a leitura**: o que a linha faz, a cada tecla, sem rodar |
| `✕ …` (a cada tecla) | **a leitura**: o erro de escrita traduzido — `faltou fechar o '('`, `esperava-se ']'`, `faltou o ':'` |

**O código roda de verdade.** Se ele apaga ou grava arquivo, isso acontece. Há limite de tempo
(padrão 10 s): um laço infinito para ali e é marcado como tal. O `input()` fica desligado.

## Como funciona

```
leitura.py  (só lê, a cada tecla)  ─┐
motor.py    (roda, ao salvar)      ─┴→  JSON  →  coral, no terminal
                                              →  a extensão do VS Code, que só desenha
```

A leitura e o motor são Python, só biblioteca padrão. A leitura nunca executa o seu código: ela
olha a estrutura de cada linha (o `ast` do Python) e diz o que ela é. O que não reconhece, ela diz
pela forma — "chama f com x" —, sem inventar o que uma função faz.

O motor roda com o Python do seu projeto (o `.venv` da pasta, o ambiente escolhido no VS Code ou
o `python3`) e acompanha cada linha com `sys.settrace`. A extensão é fina de propósito: se o
Python mudar, o conserto é no motor — que é Python e tem teste.

Status: 0.4.0, em teste. O que mudou: [CHANGELOG](CHANGELOG.md). Testado no Fedora 44 com Python 3.14 e VS Code 1.140.
