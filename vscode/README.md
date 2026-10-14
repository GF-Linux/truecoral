# True Coral para VS Code

**A cada tecla**, sem rodar nada: o que cada linha **faz**, em português, numa coluna alinhada depois do
código, com a cara de um comentário (`# devolve a soma de a e b`); o mouse em cima mostra a frase inteira,
com a história da variável. E o erro de escrita traduzido (`✕ faltou fechar o '('`, `✕ abriu com '[' e
fechou com ')': esperava-se ']'`).

**As setas do fluxo, ao salvar**, desenhadas por cima do código: a chamada sobe até o `def` dizendo o que
chega (`vezes = 10 · vindo da linha 31`), o `return` volta tracejado para quem chamou, o laço volta
para o `for` (`repete`), cada decisão marca o `sim` e o `não`, e o `raise` cai no `except` em vermelho —
inclusive o caminho em que a função termina sem `return` e devolve `None`. Uma cor por função; a ordem das
faixas é a que menos se cruza; chamadas em linhas seguidas viram um pente. As setas acompanham as linhas
enquanto você digita e se refazem no próximo Ctrl+S. Num arquivo grande, aparecem as da função onde está
o cursor.

**As sugestões, ao salvar:** uma lâmpada discreta na margem, um pontilhado no pedaço e, numa linha vazia
ao lado, o que foi visto em cinza. O mouse em cima abre a ficha com o molde da documentação oficial do
Python: precisa de import? a sintaxe, o que devolve e um exemplo com a saída de cada linha — e o link.
A sugestão mostra o molde, nunca o seu código reescrito. Hoje o catálogo reconhece: a mesma lista contada
valor por valor (`collections.Counter`), a parte do retorno pega pela posição (`f(...)[0]`), a mesma
chamada de novo com os mesmos argumentos, e a função que devolve várias coisas juntas que seguem juntas
para as próximas (encadeamento).

**Ao salvar**, o que cada linha do seu código Python fez de verdade, ao lado da linha: o que ela guardou, quantas
voltas cada laço deu e por onde saiu, quantas vezes cada condição deu True ou False, o que o print
escreveu e, se der erro, onde e por quê — em português.

- **Quando:** ao salvar (Ctrl+S). Ao editar, as marcações somem até o próximo salvamento.
- **Detalhes:** passe o mouse na linha.
- **Erro:** chip vermelho, sublinhado e entrada no painel de Problemas.
- **O código roda de verdade**, com limite de tempo (padrão 10 s) para laço infinito. O `input()` fica desligado.

Comandos: `True Coral: analisar este arquivo` · `limpar as marcações` · `ligar ou desligar ao salvar` ·
`ligar ou desligar a descrição das linhas` · `ligar ou desligar as setas do fluxo` · `ligar ou desligar as sugestões`.
Configuração: `truecoral.pythonPath`, `truecoral.tempo`, `truecoral.aoSalvar`, `truecoral.descrever`,
`truecoral.setas`, `truecoral.sugestoes`.

As setas usam a fonte do editor para cair na coluna certa e as cores do tema (escuro, claro ou alto
contraste). Elas são desenhadas por um caminho que a API do VS Code aceita mas não documenta: se uma
atualização do VS Code quebrar esse caminho, as setas somem e o resto continua.

## Junto com a viper

A extensão traz também o que a [viper](https://github.com/GF-Linux/viper), a biblioteca de funções
próprias, precisa no editor. Assim nada é configurado à mão em cada máquina:

- **snippet:** digite `replacement` e aperte Tab. A chamada nasce como
  `replacement(lista, 'palavra', lambda x: condição)`, e o Tab passa de um campo para o próximo;
- **o nome dos parâmetros em cinza** dentro das chamadas, pelo Pylance
  (`python.analysis.inlayHints.callArgumentNames: all`);
- **os snippets primeiro** na lista de sugestões, só em arquivos Python. Sem isso, o Tab pegaria a
  sugestão do Pylance, sem o `lambda`.

São valores padrão: se você mudar qualquer um nas suas configurações, vale o seu.

Parte do projeto [True Coral](https://github.com/GF-Linux/truecoral).
