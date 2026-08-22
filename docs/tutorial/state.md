# 1. Estado e rebuilds

Uma UI viva = estado + uma função do estado para a árvore. O **`App`** segura o
estado, roda sua `view(app)` e, quando o estado muda, reconstrói e diffa — emitindo
patches por um callback `apply_patches`.

```python
from dataclasses import dataclass

from tempest_core import App, Column, Text, Widget


@dataclass
class Estado:
    valor: int = 0


patches_emitidos = []


def view(app: App[Estado]) -> Widget:
    return Column(children=[Text(content=f"Contagem: {app.state.valor}", key="lbl")])


app = App(state=Estado(), view=view, apply_patches=patches_emitidos.append)  # (1)!
app.start()  # (2)!
app.set_state(lambda s: setattr(s, "valor", 1))  # (3)!
```

1. `apply_patches` recebe a lista de patches de cada tick. Um renderizador a
   aplica; aqui só guardamos.
2. `start()` constrói a cena inicial.
3. `set_state` muta o estado e **agenda um rebuild coalescido** — várias mudanças
   no mesmo tick viram um único diff.

!!! note "A view é pura"
    `view()` só **lê** `app.state` e descreve a UI. Mudar estado é trabalho dos
    handlers, via `set_state`. A view nunca muta nada.

## Navegação também é estado

A navegação vive no próprio `App`: `app.push(route)` / `app.pop()` /
`app.replace(route)` / `app.reset(stack)` mudam a rota no topo da pilha e agendam
rebuild. O `app.nav` é a `NavStack` só de leitura — a `view` lê `app.nav.top`
(e `app.nav.can_pop`) e desenha a tela. Sem nó de IR novo: trocar de rota é a view
produzindo uma árvore diferente.

## Recapitulando

- `App(state, view, apply_patches)` + `start()` inicia a UI.
- `set_state(mutator)` agenda um rebuild coalescido → diff → patches.
- `app.push` / `app.pop` / `app.reset` é navegação como estado (rota lida em `app.nav.top`).
- Próximo: [estilo](style.md).
