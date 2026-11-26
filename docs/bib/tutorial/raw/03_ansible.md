# Parte 3: Ansible na prática

**Objetivo desta parte:** configurar o Ansible para o projeto e entender os quatro pilares do Ansible (inventário, variáveis, playbook e módulos), aprendendo a verificar cada um antes de aplicar qualquer mudança no sistema.

**Pré-requisito:** Parte 2 concluída, com a pasta do projeto `slurm-lab` criada.

**Nesta parte, nada é instalado no sistema.** Os exemplos são de leitura, verificação ou execução em pasta temporária. A instalação real começa na Parte 4.

**Todos os comandos desta parte são executados a partir da raiz do projeto `slurm-lab`.** O motivo é explicado na seção 3.1.

---

## 3.1 Configuração do Ansible: `ansible.cfg`

O arquivo `ansible.cfg` ajusta o comportamento do Ansible para um projeto específico. Sem ele, o Ansible usa valores globais, que podem variar de máquina para máquina. Por isso, a configuração fica na própria pasta do projeto e acompanha o projeto.

Ele vem primeiro porque os demais comandos desta parte dependem dele: é o `ansible.cfg` que diz ao Ansible onde estão o inventário e as variáveis do projeto.

```ini
[defaults]
inventory = inventory/hosts.yml
playbook_dir = .
interpreter_python = auto_silent
retry_files_enabled = False
```

Cada linha:

- **`inventory`:** caminho do inventário, apresentado na seção 3.2. Assim, não é preciso passar a opção `-i` em cada comando.
- **`playbook_dir`:** pasta de referência do projeto. O Ansible carrega automaticamente a pasta `group_vars/` (seção 3.3) quando ela está ao lado do playbook. Comandos avulsos, que não usam playbook, não têm essa referência. Esta linha indica a raiz do projeto como referência, e as variáveis passam a ser encontradas em qualquer comando.
- **`interpreter_python = auto_silent`:** o Ansible detecta o Python da máquina automaticamente, sem exibir avisos sobre isso.
- **`retry_files_enabled = False`:** desativa a criação de arquivos `.retry` quando uma execução falha. Esses arquivos poluem a pasta do projeto.

### Verificando qual configuração está em uso

```bash
ansible --version
```

A linha `config file = ...` deve apontar para o `ansible.cfg` do projeto, e não para `None`.

O Ansible procura o `ansible.cfg` apenas no diretório atual, sem subir para os diretórios pais. Um comando executado de dentro de `inventory/`, por exemplo, não encontra a configuração do projeto. Por isso, os comandos são executados a partir da raiz do projeto.

Para listar apenas as configurações que diferem do padrão:

```bash
ansible-config dump --only-changed
```

Cada linha mostra o nome interno de uma opção, o arquivo de onde ela veio e o valor. As quatro opções do arquivo devem aparecer. Os nomes internos nem sempre coincidem com os nomes usados no `ansible.cfg`: a opção `inventory`, por exemplo, aparece como `DEFAULT_HOST_LIST`. Para descobrir a correspondência, consulte `ansible-config list`.

> **Referência:** Ansible. *Configuring Ansible*. docs.ansible.com. Lista de opções do `ansible.cfg` e ordem de precedência entre fontes de configuração.

---

## 3.2 Inventário: quais máquinas existem

O inventário lista as máquinas gerenciadas pelo Ansible, organizadas em **grupos**, e guarda as variáveis de cada máquina. Ele fica em `inventory/hosts.yml`.

Há uma regra de nomes que sustenta toda a configuração: **o nome de cada host no inventário é o nome curto da máquina**, o que `hostname -s` retorna. O Slurm também identifica cada nó pelo nome da máquina, então usar o mesmo nome nos dois lugares elimina uma fonte de erro.

Exemplo com uma única máquina, usada ao mesmo tempo como controlador e como nó de computação:

```yaml
all:
  children:
    controller:
      hosts:
        <hostname>:
          ansible_connection: local
    compute:
      hosts:
        <hostname>:
          ansible_connection: local
          cpus: 8
          real_memory: 7800
          gpu_count: 1
          gpu_device: /dev/nvidia0
```

Leitura de dentro para fora:

- `all` é o grupo que contém todos os outros. `children` lista os subgrupos.
- `controller` e `compute` são grupos. Um host pode pertencer a mais de um grupo, e é por isso que a mesma máquina aparece nos dois.
- `<hostname>` é um marcador. Substitua pelo resultado de `hostname -s`.
- `ansible_connection: local` executa as tarefas na própria máquina, sem SSH.
- `cpus`, `real_memory`, `gpu_count` e `gpu_device` são **variáveis de host**. Elas pertencem à máquina, então ficam junto dela. Foram definidas no grupo `compute` porque só os nós de computação as usam. Os valores são ilustrativos.

Por que separar em grupos, se a máquina é a mesma? As roles usam os grupos para decidir o que fazer em cada host. O controlador só é iniciado em hosts do grupo `controller`, e o serviço de nó só nos do grupo `compute`. Quando houver máquinas diferentes, a lógica é a mesma: muda apenas a lista de hosts de cada grupo.

### Verificando o inventário

Para ver a estrutura, como o Ansible a interpreta:

```bash
ansible-inventory --graph
```

Saída ilustrativa:

```
@all:
  |--@controller:
  |  |--node01
  |--@compute:
  |  |--node01
```

Para ver as variáveis de um host:

```bash
ansible-inventory --host <hostname>
```

Os valores de `cpus`, `real_memory`, `gpu_count` e `gpu_device` devem aparecer com os números que você definiu.

> **Referência:** Ansible. *How to build your inventory*. docs.ansible.com, seções sobre inventários estáticos em YAML e variáveis de host.

---

## 3.3 Variáveis: a fonte única da verdade

Variáveis são valores nomeados que as tarefas e os templates usam. Para que a configuração não se repita, cada valor deve existir em um único lugar. Neste tutorial há dois lugares para isso:

- **`group_vars/all.yml`** guarda valores que valem para o cluster inteiro.
- **O inventário** guarda valores que pertencem a cada máquina.

### Valores do cluster: `group_vars/all.yml`

O nome `all` indica que as variáveis valem para todos os hosts. O Ansible carrega esse arquivo sozinho, porque a pasta `group_vars/` está na pasta de referência do projeto (seção 3.1).

```yaml
cluster_name: mini-cluster
slurmd_port: 6818
```

O módulo `debug` mostra o valor de uma variável sem alterar nada. O padrão `all` indica que o comando vale para todos os hosts do inventário:

```bash
ansible all -m ansible.builtin.debug -a "var=cluster_name"
```

Saída ilustrativa:

```
<hostname> | SUCCESS => {
    "cluster_name": "mini-cluster"
}
```

Se a saída mostrar `VARIABLE IS NOT DEFINED!`, o Ansible não encontrou o arquivo. Confira a linha `playbook_dir` do `ansible.cfg` (seção 3.1).

### Topologia: duas formas de declarar os nós

Os nós do cluster podem ser declarados de duas formas. Ambas funcionam com uma máquina. A diferença aparece quando há várias, e por isso as duas são apresentadas.

#### Abordagem A: lista de nós em `group_vars`

Nesta forma, `group_vars/all.yml` contém uma lista com um item por nó:

```yaml
controller_host: <hostname>

slurm_nodes:
  - name: <hostname>
    addr: 127.0.0.1
    cpus: 8
    real_memory: 7800
    gpu_count: 1
    gpu_device: /dev/nvidia0
```

A forma é simples e fácil de ler, porque toda a topologia está em um único arquivo. O limite aparece quando o cluster cresce. Cada máquina precisa ser descrita duas vezes: no inventário, para existir como host, e na lista `slurm_nodes`, para existir como nó. Nada verifica se as duas descrições batem. Se uma máquina for adicionada a uma das listas e esquecida na outra, a configuração gerada fica errada sem nenhum aviso.

Os nomes dos itens devem ser literais, como acima. Não use `"{{ ansible_hostname }}"`: esse valor é coletado de cada host e muda conforme o host processado, o que faz a lista variar entre máquinas.

#### Abordagem B: lista derivada do inventário (recomendada)

Nesta forma, a topologia não é repetida. `group_vars/all.yml` tem apenas os valores do cluster:

```yaml
cluster_name: mini-cluster
slurmd_port: 6818
controller_host: "{{ groups['controller'][0] }}"
```

A lista de nós vem do próprio inventário, e o hardware de cada nó vem das variáveis do host correspondente. Os templates fazem essa leitura com duas construções:

- **`groups['compute']`** é a lista de hosts do grupo `compute`. Ela é a mesma, qualquer que seja o host que está sendo processado.
- **`hostvars[nome]`** permite ler as variáveis de qualquer host, a partir de qualquer outro. Por exemplo, `hostvars[h].cpus` lê o número de CPUs do host `h`.

O valor de `controller_host` também não depende do host processado. `groups` é global, então `groups['controller'][0]` resolve para o mesmo nome em todas as máquinas. Essa é a diferença essencial em relação ao `ansible_hostname`, que muda de uma máquina para outra.

Quando a topologia cresce, o trabalho se resume a adicionar a máquina ao inventário, com suas variáveis. Nenhum outro arquivo precisa ser editado.

#### Quadro comparativo

| Critério | Abordagem A: lista em `group_vars` | Abordagem B: derivada do inventário |
|---|---|---|
| Onde a topologia fica | Em `group_vars/all.yml`, separada das máquinas | No inventário, junto de cada máquina |
| Esforço para adicionar uma máquina | Descrever a máquina em dois lugares | Adicionar a máquina ao inventário |
| Risco de divergência | Alto: as duas descrições podem não bater | Baixo: há uma única fonte |
| Dependência de fatos coletados | Nenhuma, se os nomes forem literais | Nenhuma |
| Legibilidade para quem começa | Alta, tudo em um arquivo | Média: exige entender grupos e `hostvars` |
| Adequação a várias máquinas | Funciona, com disciplina manual | Adequada por construção |

A abordagem A é uma boa forma de começar, porque mostra a topologia de maneira direta. A abordagem B é a recomendada, porque remove a repetição que causa a divergência. A recomendação segue a orientação da documentação oficial do Ansible, que trata o inventário como a fonte da topologia e as variáveis de host como o lugar dos valores que pertencem a cada máquina.

> **Referência:** Ansible. *Using variables*. docs.ansible.com. Seções sobre `group_vars`, `host_vars` e precedência de variáveis.
> **Referência:** Ansible. *Magic variables, and how to access information about other hosts*. docs.ansible.com. Explica `groups`, `group_names` e `hostvars`.
> **Referência:** Ansible. *Variables: Facts*. docs.ansible.com. Explica as variáveis coletadas automaticamente, como `ansible_hostname`, e por que elas dependem do host.

---

## 3.4 Playbook: a receita de configuração

O playbook é o arquivo que diz **quais roles aplicar, em quais hosts e com quais privilégios**. Por convenção, chama-se `site.yml`.

```yaml
- name: Configuração mínima do cluster
  hosts: all
  become: true
  roles:
    - base
    - munge
    - slurm
```

Leitura:

- **`name`:** descrição livre, exibida na saída da execução.
- **`hosts: all`:** aplica o playbook a todos os hosts do inventário.
- **`become: true`:** equivale a usar `sudo`. Necessário para instalar pacotes e editar arquivos em `/etc/`.
- **`roles`:** lista de roles, executadas **na ordem em que aparecem**. A ordem importa: `base` instala os pacotes, `munge` depende deles, e `slurm` depende dos dois.

### O que é uma role

Uma role é uma pasta com estrutura fixa. O Ansible procura cada parte no lugar previsto:

```
roles/slurm/
├── tasks/main.yml        # o que fazer (lista de tarefas)
├── handlers/main.yml     # o que fazer quando algo muda
└── templates/            # arquivos com variáveis, gerados no host
    ├── slurm.conf.j2
    ├── gres.conf.j2
    └── cgroup.conf.j2
```

Ao ver `roles: - slurm`, o Ansible lê `roles/slurm/tasks/main.yml`, e assim por diante.

### Verificando o playbook

Confira a sintaxe antes de aplicar qualquer coisa:

```bash
ansible-playbook site.yml --syntax-check
```

Saída esperada: `playbook: site.yml`. Erros de indentação aparecem aqui, com o número da linha.

Para listar as tarefas que seriam executadas, sem executá-las:

```bash
ansible-playbook site.yml --list-tasks
```

Nesta etapa, as tarefas ainda estão vazias (`[]`). A saída mostra o nome do playbook, mas nenhuma tarefa abaixo de `tasks:`. É o comportamento esperado.

> **Referência:** Ansible. *Playbooks*. docs.ansible.com. Seções sobre `hosts`, `become` e ordem de execução.
> **Referência:** Ansible. *Using roles*. docs.ansible.com. Estrutura de diretórios de roles.

---

## 3.5 Tarefas e módulos

Cada tarefa dentro de uma role usa um **módulo**: uma função pronta do Ansible. Você descreve o resultado desejado, e o módulo cuida de como alcançá-lo. Os módulos mais usados nesta apostila:

| Módulo | Para que serve | Exemplo |
|---|---|---|
| `apt` | Instalar ou remover pacotes | Instalar o `slurm-wlm` |
| `file` | Criar pastas e ajustar permissões e donos | Criar `/var/spool/slurmd` |
| `template` | Gerar um arquivo a partir de um `.j2` | Gerar `slurm.conf` |
| `systemd` | Iniciar, parar ou habilitar serviços | Iniciar `slurmctld` |

Exemplo de tarefa, na forma que aparece nas próximas partes:

```yaml
- name: Instalar munge
  ansible.builtin.apt:
    name: munge
    state: present
```

Cada parte tem um significado:

- **`name`:** texto exibido na saída. Escreva algo que faça sentido quando você ler o log.
- **`ansible.builtin.apt`:** o módulo. O prefixo `ansible.builtin` indica que ele vem junto com o Ansible.
- **`name: munge`:** argumento do módulo, o nome do pacote.
- **`state: present`:** estado desejado. Pode ser `present` (instalado), `absent` (removido) ou `latest` (versão mais recente).

Documentação de um módulo, direto no terminal:

```bash
ansible-doc ansible.builtin.apt
```

Você verá os parâmetros aceitos e exemplos de uso. É o caminho mais rápido para descobrir o que um módulo faz, sem decorar nada.

### Exercício de leitura

Sem executar nada, responda: qual combinação de parâmetros garante que um serviço esteja em execução e seja iniciado automaticamente no boot? Dica: os parâmetros estão em `ansible-doc ansible.builtin.systemd`.

> **Referência:** Ansible. *Module Index*. docs.ansible.com. Índice de módulos, com a documentação de cada um.

---

## 3.6 Idempotência: executar de novo sem efeito colateral

Idempotência é a propriedade mais importante de uma automação de infraestrutura. Uma operação é idempotente quando, aplicada várias vezes, produz o mesmo resultado final que na primeira vez.

Teste com um módulo inofensivo, que cria uma pasta em `/tmp`:

```bash
ansible localhost -m ansible.builtin.file -a "path=/tmp/apostila-demo state=directory"
```

Execute o mesmo comando de novo:

```bash
ansible localhost -m ansible.builtin.file -a "path=/tmp/apostila-demo state=directory"
```

Compare a saída:

- Na **primeira** execução: `changed` (a pasta foi criada).
- Na **segunda** execução: `ok` (a pasta já existia, então nada mudou).

O módulo verifica o estado atual e age apenas se for necessário.

Agora um comando que **não** é idempotente:

```bash
ansible localhost -m ansible.builtin.command -a "mkdir /tmp/apostila-demo-2"
```

Execute duas vezes. Na segunda, o `mkdir` falha, porque a pasta já existe. O módulo `command` executa o que for pedido, sem verificar o estado. Por isso, a apostila recomenda evitar `command` e `shell` sempre que existir um módulo específico.

Limpeza:

```bash
rm -rf /tmp/apostila-demo /tmp/apostila-demo-2
```

### Simulação antes de aplicar

O modo `--check` simula a execução sem alterar nada e mostra o que mudaria:

```bash
ansible-playbook site.yml --check -K
```

O playbook declara `become: true` (seção 3.4), então até a simulação é executada com privilégio de administrador. A opção `-K` (forma curta de `--ask-become-pass`) faz o Ansible pedir a senha do `sudo` antes de começar. Sem ela, a execução falha logo na coleta de fatos, com a mensagem `sudo: a password is required`.

Com as roles ainda vazias, a simulação executa apenas a coleta de fatos. Nas próximas partes, ela será a primeira verificação antes de qualquer execução real.

> **Referência:** Ansible. *Validating tasks: check mode and diff mode*. docs.ansible.com.
> **Referência:** Ansible. *Understanding privilege escalation: become*. docs.ansible.com. Explica `become` e a opção `--ask-become-pass`.
> **Referência:** Morris, K. *Infrastructure as Code: Managing Servers in the Cloud*. O'Reilly. Capítulos sobre idempotência e a diferença entre scripts imperativos e declarações de estado. (Verifique a edição antes de citar.)

---

**Próxima:** Parte 4, pacotes e autenticação.
