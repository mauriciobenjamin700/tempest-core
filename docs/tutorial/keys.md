# 4. Chaves e identidade

Toda interação chega no core como **chave + evento**: o renderizador diz “o nó
`quality-segments-item-1` recebeu um clique” e o runtime procura esse nó na
árvore para achar o handler. A chave é, portanto, a identidade do nó — para o
diff e para o roteamento de evento.

Por isso a regra: **uma chave, um nó.** Duas chaves iguais na mesma tela e o
handler que responde é o do primeiro nó que a busca encontrar — não
necessariamente aquele que o usuário tocou.

## O problema, medido

Dois `SegmentedControl` na mesma tela: um para tema, um para qualidade.

```python
from tempest_core import Column, Node, SegmentedControl, build

tema: list[int] = []
qualidade: list[int] = []

tela = Column(
    key="root",
    children=[
        SegmentedControl(
            key="theme-segments",
            options=["Sistema", "Claro", "Escuro"],
            on_select=tema.append,
        ),
        SegmentedControl(
            key="quality-segments",
            options=["Baixa", "Média", "Alta"],
            on_select=qualidade.append,
        ),
    ],
)


def chaves(node: Node) -> list[str]:  # (1)!
    """Devolve as chaves do nó e de todos os descendentes."""
    encontradas = [node.key] if node.key is not None else []
    for filho in node.children:
        encontradas.extend(chaves(filho))
    return encontradas


print(chaves(build(tela)))
```

1. Um walk simples da árvore construída, só para olhar as chaves emitidas.

```text
['root',
 'theme-segments', 'theme-segments-item-0', 'theme-segments-item-1', 'theme-segments-item-2',
 'quality-segments', 'quality-segments-item-0', 'quality-segments-item-1', 'quality-segments-item-2']
```

Nenhuma repetida. Antes da versão 0.15.0 os dois controles emitiam `seg-0`,
`seg-1`, `seg-2` **cada um** — clicar em “Claro” no controle de tema mudava a
qualidade, e o controle de tema ficava inerte.

## As três peças

Todo componente ganhou uma identidade explícita:

| Peça | O que é |
|---|---|
| `default_key` | O nome do componente, usado quando quem chama não passa `key` (`"segmented"`, `"navbar"`, `"card"`…). |
| `base_key` | `self.key or self.default_key` — a chave da raiz que o componente emite. |
| `child_key(sufixo)` | `f"{base_key}-{sufixo}"` — a chave de cada nó interno. |

```python
from tempest_core import SegmentedControl

controle = SegmentedControl(key="quality", options=[], on_select=lambda i: None)

controle.base_key            # "quality"
controle.child_key("item-0") # "quality-item-0"

sem_chave = SegmentedControl(options=[], on_select=lambda i: None)

sem_chave.base_key            # "segmented"
sem_chave.child_key("item-0") # "segmented-item-0"
```

!!! warning "Duas instâncias sem `key` ainda colidem"
    O `default_key` resolve o caso comum de **um** controle por tela e mantém a
    árvore legível num dump. Ele não pode inventar identidade: duas instâncias
    sem `key` do mesmo componente caem na mesma base. Numa tela com dois,
    **passe `key`** — é exatamente o que `key` significa.

## Escrevendo o seu componente

O mesmo contrato vale para componente próprio: declare o `default_key` e passe
todo nó interno por `child_key`.

```python
from typing import ClassVar

from tempest_core import Button, Column, Component, Text, Widget, build


class Contador(Component):
    """Um rótulo com um botão de incremento."""

    default_key: ClassVar[str] = "contador"  # (1)!

    valor: int = 0

    def render(self) -> Widget:
        """Baixa o contador para primitivas."""
        return Column(
            key=self.base_key,  # (2)!
            children=[
                Text(content=str(self.valor), key=self.child_key("valor")),  # (3)!
                Button(label="+1", on_click=lambda: None, key=self.child_key("mais")),
            ],
        )


print([n.key for n in build(Contador(key="carrinho", valor=2)).children])
# -> ['carrinho-valor', 'carrinho-mais']
```

1. O nome do componente. Sem ele, uma instância sem `key` herdaria
   `"component"` — e colidiria com qualquer outro componente igualmente
   distraído.
2. A raiz usa `base_key`, nunca `self.key or "..."` escrito à mão.
3. O sufixo descreve o **papel** do nó dentro do componente (`valor`, `mais`,
   `item-0`), sem repetir o nome do componente — a base já o carrega.

!!! tip "O teste que segura isso"
    `tests/test_child_keys.py` monta duas instâncias de cada componente
    interativo, afirma que a árvore não tem chave repetida e dispara o handler
    pela chave — do jeito que o runtime faria. Um componente novo sem
    `default_key` próprio falha o guard parametrizado.

## Migrando de 0.14.x

As chaves internas mudaram de forma junto com o conserto: além do prefixo, o
sufixo perdeu a repetição do nome do componente. Se o seu código (ou o seu teste,
ou a sua fixture de renderizador) procura nó por chave literal, atualize:

| Componente | Antes | Agora |
|---|---|---|
| `SegmentedControl` | `seg-1` | `<key>-item-1` |
| `RadioGroup` | `radio-1` | `<key>-item-1` |
| `NavBar` | `nav-1` | `<key>-item-1` |
| `Tabs` | `tab-1` | `<key>-item-1` |
| `Breadcrumb` | `crumb-1` / `sep-1` | `<key>-item-1` / `<key>-sep-1` |
| `Rating` | `star-1` | `<key>-star-1` |
| `Card` | `card-body` / `card-col` | `<key>-body` / `<key>-col` |
| `DataTable` | `dt-next` / `dt-row-0` | `<key>-next` / `<key>-row-0` |
| `Stepper` | `step-up` / `step-value` | `<key>-up` / `<key>-value` |
| `SearchBar` | `search-input` | `<key>-input` |
| `EmailInput` (e irmãos BR) | `email-field` / `field-label` | `<key>-field` / `<key>-field-label` |

Onde `<key>` é o `key` que você passou — ou o `default_key` do componente
(`segmented`, `navbar`, `card`, `data-table`, `stepper`, `searchbar`,
`email-input`…) quando você não passou nenhum. Para um componente sem `key`,
`AppBar`, `Header`, `Card` e companhia caem exatamente na chave antiga
(`appbar-title`, `header-subtitle`, `card-body`), porque o sufixo já repetia o
nome do componente.

## Recapitulando

- Evento roteia por chave; chave repetida entrega o evento ao nó errado.
- `base_key` é a raiz do componente, `child_key(sufixo)` é cada nó interno.
- `default_key` nomeia o componente para a instância sem `key` — duas na mesma
  tela ainda precisam de `key` explícita.
- Componente próprio segue o mesmo contrato, e o guard parametrizado cobra isso.
