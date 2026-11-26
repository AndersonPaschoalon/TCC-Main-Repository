# Parte 4: Pacotes e autenticação

**Objetivo desta parte:** instalar os pacotes do Slurm e do munge pelo playbook, criar os diretórios de estado e garantir que a autenticação entre os componentes funcione.

**Pré-requisito:** Parte 3 concluída. O playbook `site.yml` passa na checagem de sintaxe e a lista de tarefas aparece vazia.

**Esta é a primeira parte que altera o sistema.** Antes de cada execução real, rode a simulação com `--check`, como indicado na seção 3.6. Os comandos desta parte são executados a partir da raiz do projeto `slurm-lab`.

---

## 4.1 Instalação de pacotes (role `base`)

A role `base` é a primeira da lista do playbook. Ela instala os pacotes que todas as máquinas do cluster precisam e prepara os diretórios em que o Slurm guarda seu estado.

Os três pacotes têm papéis distintos:

| Pacote | Papel |
|---|---|
| `slurm-wlm` | Contém os daemons `slurmctld` (controlador) e `slurmd` (nó de computação), além de `slurmdbd` (histórico, usado mais adiante). |
| `slurm-client` | Contém os comandos que o usuário usa, como `sinfo`, `squeue`, `sbatch` e `srun`. |
| `munge` | Contém o serviço de autenticação e gera a chave compartilhada entre as máquinas. |

Os nomes dos pacotes podem mudar entre versões da distribuição. Para confirmar que existem na sua máquina, use `apt policy <nome>`, como visto na Parte 2.

O arquivo `roles/base/tasks/main.yml` fica assim:

```yaml
- name: Instalar pacotes do Slurm e do munge
  ansible.builtin.apt:
    name:
      - slurm-wlm
      - slurm-client
      - munge
    state: present
    update_cache: true

- name: Criar diretório de estado do controlador
  ansible.builtin.file:
    path: /var/spool/slurmctld
    state: directory
    owner: slurm
    group: slurm
    mode: "0755"

- name: Criar diretório de spool do nó de computação
  ansible.builtin.file:
    path: /var/spool/slurmd
    state: directory
    owner: root
    group: root
    mode: "0755"
```

Leitura da tarefa de instalação:

- **`update_cache: true`** atualiza a lista de pacotes antes de instalar, equivalente a `sudo apt update`. Sem isso, o Ansible pode tentar instalar uma versão antiga da lista local.
- **`state: present`** garante que os pacotes estejam instalados. Se já estiverem, nada muda. Esse comportamento é o que torna a tarefa idempotente (seção 3.6).
- A lista de `name` aceita vários pacotes em uma única chamada, o que é mais rápido e mais claro do que uma tarefa por pacote.

> **Atenção:** a instalação altera pacotes do sistema. Antes de executar, rode a simulação:
>
> ```bash
> ansible-playbook site.yml --check -K
> ```
>
> Na simulação, o Ansible mostra as tarefas que mudariam sem aplicá-las. Se algo não fizer sentido, interrompa antes da execução real.

Execução real, com a senha do `sudo` solicitada no início:

```bash
ansible-playbook site.yml -K
```

Nesta etapa, o playbook executa a role `base` e as roles `munge` e `slurm`. As duas últimas ainda estão vazias, então não fazem nada. Isso é esperado.

### Por que os diretórios têm donos diferentes

Os diretórios de estado do Slurm têm finalidades diferentes, e por isso não recebem o mesmo dono:

- **`/var/spool/slurmctld`** guarda o estado do controlador: a fila, os jobs em andamento e as alocações. Esse diretório pertence ao usuário `slurm`, que é o usuário sob o qual o `slurmctld` roda. Se o dono estiver errado, o controlador não consegue gravar o próprio estado e não inicia.
- **`/var/spool/slurmd`** guarda arquivos temporários do nó de computação. O `slurmd` roda como `root`, porque precisa criar isolamentos de processo e dispositivos. Por isso, o dono desse diretório é `root`.

A diferença entre `owner`, `group` e `mode` é a base das permissões de arquivos no Linux. Você pode ler as permissões de um diretório assim:

```bash
ls -ld /var/spool/slurmctld /var/spool/slurmd
```

A primeira coluna mostra as permissões (por exemplo, `drwxr-xr-x`), e as colunas seguintes mostram o dono e o grupo.

> **Referência:** Ubuntu. *Ubuntu Packages Search*. packages.ubuntu.com. Permite verificar nomes de pacotes e versões por distribuição.
> **Referência:** SchedMD. *Slurm Quick Start Administrator Guide*. slurm.schedmd.com/quickstart_admin.html. Descreve os daemons e os diretórios de estado.

---

## 4.2 Diretórios de estado e permissões

A tarefa de criação de diretório usa o módulo `file`. Esse módulo descreve o estado desejado de um caminho: se ele existe, qual o tipo, quem é o dono e quais são as permissões. Ele verifica o estado atual antes de agir, o que o torna idempotente.

Os campos da tarefa têm estes significados:

- **`path`:** o caminho do diretório.
- **`state: directory`:** o caminho deve ser um diretório. Se não existir, é criado.
- **`owner` e `group`:** quem é o dono e o grupo do diretório.
- **`mode: "0755"`:** permissões em notação octal. O primeiro dígito é o dono, o segundo o grupo e o terceiro os demais. Cada dígito soma os valores `4` (leitura), `2` (escrita) e `1` (execução). Assim, `7` significa leitura, escrita e execução, e `5` significa leitura e execução.

Por que as aspas em `"0755"`? Sem elas, o YAML pode interpretar o número como decimal, e a permissão sai errada. Sempre use aspas em permissões.

Se você alterar o dono de um diretório manualmente e executar o playbook de novo, o Ansible corrige o dono de volta para o valor declarado. Essa é a forma de manter a configuração consistente com o que está no repositório.

> **Referência:** Ansible. *ansible.builtin.file module*. docs.ansible.com. Parâmetros `path`, `state`, `owner`, `group` e `mode`.
> **Referência:** Kerrisk, M. *The Linux Programming Interface*. No Starch Press. Capítulo sobre permissões de arquivos e diretórios. (Verifique a edição antes de citar.)

---

## 4.3 munge: chave e serviço (role `munge`)

O munge autentica as mensagens trocadas entre os componentes do Slurm. Ele depende de uma **chave** compartilhada, guardada em `/etc/munge/munge.key`. Três fatos sobre essa chave orientam a configuração:

1. O pacote `munge` gera a chave automaticamente na instalação.
2. Todas as máquinas do cluster precisam ter **a mesma chave**. Com uma única máquina, isso é automático. Quando houver várias, a distribuição da chave é tratada na Parte 10.
3. A chave é um segredo. Quem a possui pode se passar por qualquer componente do cluster. Por isso, ela tem permissão restrita e **nunca deve ser copiada para o repositório do projeto**.

> **Atenção:** o arquivo `munge.key` não deve entrar no controle de versão. Se ele aparecer em `git status`, remova-o do índice antes de qualquer commit e revise o que já foi enviado a repositórios remotos.

O arquivo `roles/munge/tasks/main.yml` fica assim:

```yaml
- name: Garantir que o serviço munge está ativo
  ansible.builtin.systemd:
    name: munge
    state: started
    enabled: true

- name: Garantir dono e permissões da chave do munge
  ansible.builtin.file:
    path: /etc/munge/munge.key
    owner: munge
    group: munge
    mode: "0400"
```

Leitura:

- **`systemd` com `state: started` e `enabled: true`** faz o serviço rodar agora e ser iniciado no boot. Os dois valores são independentes: `started` trata do agora, e `enabled` trata do próximo boot.
- **`file` com `mode: "0400"`** restringe a chave a leitura apenas pelo dono. Nenhum outro usuário pode ler o arquivo.
- A tarefa de permissões não cria a chave. Ela apenas garante que, se a chave existir, o dono e as permissões estejam corretos. Se a chave não existir, a tarefa falha, o que é o comportamento desejado: sem chave, o munge não funciona e o problema precisa aparecer cedo.

Execute a simulação e depois a aplicação:

```bash
ansible-playbook site.yml --check -K
ansible-playbook site.yml -K
```

Confira o resultado com `ls`:

```bash
sudo ls -l /etc/munge/munge.key
```

A saída deve mostrar `-r--------` como permissão e `munge munge` como dono e grupo.

> **Referência:** Dun, C. *MUNGE Uid 'N' Gid Emporium*. Documentação oficial do projeto. dun.github.io/munge.
> **Referência:** Ansible. *ansible.builtin.systemd module*. docs.ansible.com. Parâmetros `state` e `enabled`.

---

## 4.4 Testando a autenticação com `munge -n | unmunge`

Até aqui, a configuração foi aplicada. Agora é preciso verificar se ela funciona. Esta seção faz dois testes: a autenticação do munge e a leitura do hardware pelo Slurm.

### Teste de autenticação

O comando abaixo cria uma credencial e a valida em seguida, sem envolver o Slurm:

```bash
munge -n | unmunge
```

Saída esperada (resumida):

```
STATUS:          Success (0)
ENCODE_HOST:     nome-da-maquina
UID:             usuario
```

`munge -n` cria a credencial, e `unmunge` a valida. Se aparecer `Success`, a chave local e o serviço estão corretos. Se aparecer um erro de conexão, o serviço não está ativo. Verifique com:

```bash
systemctl status munge
```

Se o serviço estiver ativo e a validação falhar, o problema mais comum é uma chave diferente entre máquinas. Com uma única máquina, isso não ocorre, mas o diagnóstico vale para a Parte 10.

### Verificando o hardware visto pelo Slurm

O pacote `slurm-wlm` foi instalado na seção 4.1. Ele inclui o comando `slurmd -C`, que mostra a configuração de hardware que o Slurm enxerga:

```bash
slurmd -C
```

Saída ilustrativa (resumida):

```
NodeName=nome-da-maquina CPUs=8 Boards=1 SocketsPerBoard=1 CoresPerSocket=4 ThreadsPerCore=2 RealMemory=7900
UpTime=0-01:23:45
```

Compare com os valores que você levantou na Parte 2:

- **CPUs:** o valor de `CPUs=` deve corresponder ao de `nproc`.
- **Memória:** o valor de `RealMemory=` é a memória que o Slurm vai usar. Ele costuma ser um pouco menor que o total de `free -m`, porque parte da memória é reservada pelo kernel.

Se houver diferença, prevalece o valor de `slurmd -C`. Atualize `cpus` e `real_memory` no inventário, no host correspondente, com o `RealMemory` como limite. Declarar mais memória do que a máquina tem é o erro mais comum, e ele faz o nó aparecer como indisponível na Parte 9.

> **Atenção:** os serviços `slurmctld` e `slurmd` podem já estar instalados e tentar iniciar com a configuração padrão do pacote. Nesta etapa, o projeto ainda não tem configuração própria do Slurm. Se `systemctl status slurmctld` mostrar falha, isso é esperado. A configuração correta é aplicada na Parte 8.

> **Referência:** SchedMD. *slurmd: Slurm compute node daemon*. Página de manual, disponível em slurm.schedmd.com. Descreve as opções, incluindo `-C`.

---

## Resumo da Parte 4

Ao final, você terá: os pacotes do Slurm e do munge instalados pelo playbook, os diretórios de estado com donos e permissões corretos, a chave do munge protegida, e a confirmação de que o munge autentica e de que o Slurm enxerga o hardware corretamente.

Nenhum serviço do Slurm foi configurado ainda. Essa configuração começa na Parte 5, com o estudo de cada componente, e é aplicada pelo playbook na Parte 8.

**Próxima:** Parte 5, Slurm, componente por componente.
