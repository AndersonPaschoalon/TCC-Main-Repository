# Parte 8: Integração do playbook ao cluster funcionando

**Objetivo desta parte:** escrever as tarefas e os handlers da role `slurm`, entender a ordem em que o playbook executa as roles e as tarefas, e percorrer o fluxo completo de uma mudança, da edição das variáveis até a verificação.

**Pré-requisito:** Partes 3 a 7 concluídas. A role `base` e a role `munge` têm suas tarefas escritas, e os três templates (`slurm.conf.j2`, `gres.conf.j2` e `cgroup.conf.j2`) existem em `roles/slurm/templates/`.

**Esta parte altera o sistema.** Antes de cada execução real, rode a simulação com `--check --diff`, como indicado na seção 7.2. Esta é a primeira parte em que os arquivos de configuração do Slurm são gravados em `/etc/slurm/`.

---

## 8.1 Como o playbook percorre as roles

O playbook `site.yml` lista três roles na ordem `base`, `munge` e `slurm`. Cada role contém tarefas e handlers, e o Ansible executa tudo isso em uma sequência previsível.

Uma regra do Ansible explica a sequência: por padrão, a estratégia de execução é `linear`. Ela executa a primeira tarefa em todos os hosts antes de passar para a segunda, e assim por diante. Com um único host, a diferença não aparece. Com vários hosts, ela garante que todas as máquinas concluam uma etapa antes de todas iniciarem a seguinte.

A role `slurm` tem a seguinte estrutura, já criada pela Parte 2:

```
roles/slurm/
├── tasks/main.yml        # renderiza os arquivos e garante os serviços
├── handlers/main.yml     # reinicia os serviços quando um arquivo muda
└── templates/
    ├── slurm.conf.j2
    ├── gres.conf.j2
    └── cgroup.conf.j2
```

Ao executar a role, o Ansible lê primeiro `tasks/main.yml`, de cima para baixo. Os handlers só são executados depois, no fim da role ou do playbook, e só se uma tarefa os tiver notificado.

### As tarefas da role `slurm`

O arquivo `roles/slurm/tasks/main.yml` fica assim:

```yaml
- name: Renderizar slurm.conf
  ansible.builtin.template:
    src: slurm.conf.j2
    dest: /etc/slurm/slurm.conf
    owner: root
    group: root
    mode: "0644"
  notify:
    - restart slurmctld
    - restart slurmd

- name: Renderizar gres.conf
  ansible.builtin.template:
    src: gres.conf.j2
    dest: /etc/slurm/gres.conf
    owner: root
    group: root
    mode: "0644"
  notify:
    - restart slurmctld
    - restart slurmd

- name: Renderizar cgroup.conf
  ansible.builtin.template:
    src: cgroup.conf.j2
    dest: /etc/slurm/cgroup.conf
    owner: root
    group: root
    mode: "0644"
  notify:
    - restart slurmctld
    - restart slurmd

- name: Garantir que slurmctld está ativo
  ansible.builtin.systemd:
    name: slurmctld
    state: started
    enabled: true
  when: "'controller' in group_names"

- name: Garantir que slurmd está ativo
  ansible.builtin.systemd:
    name: slurmd
    state: started
    enabled: true
  when: "'compute' in group_names"
```

Leitura:

- **`template`** lê o arquivo `.j2` da pasta `templates/`, substitui as variáveis pelos valores de `group_vars/all.yml` e grava o resultado em `dest`. Se o conteúdo gerado for igual ao que já existe no sistema, a tarefa reporta `ok`, e nada é gravado.
- **`notify`** avisa os handlers de que o arquivo mudou. A notificação só ocorre quando a tarefa reporta `changed`. Se o arquivo já estiver correto, nenhum handler é disparado.
- **`when: "'controller' in group_names"`** executa a tarefa apenas em hosts que pertencem ao grupo `controller`. `group_names` é uma variável especial, criada pelo Ansible, com a lista de grupos do host atual. Esse é o mecanismo que decide quais serviços cada máquina executa, a partir do inventário da Parte 3.

Note que os três arquivos de configuração são notificados aos dois handlers. Um nó de computação recebe o `slurm.conf` completo, que contém todos os nós, e não apenas a sua parte. Isso é intencional: todos os daemons precisam enxergar a mesma configuração do cluster.

> **Referência:** Ansible. *ansible.builtin.template module*. docs.ansible.com. Parâmetros `src`, `dest`, `owner`, `group` e `mode`.
> **Referência:** Ansible. *Conditionals: group_names and when*. docs.ansible.com. Uso de `group_names` para executar tarefas por grupo do inventário.

---

## 8.2 Handlers: reiniciar serviços só quando a configuração muda

Um **handler** é uma tarefa que só executa quando é notificada por outra tarefa que mudou alguma coisa. Ele evita reinícios desnecessários: um serviço que não precisa ser reiniciado continua rodando sem interrupção.

O arquivo `roles/slurm/handlers/main.yml` fica assim:

```yaml
- name: restart slurmctld
  ansible.builtin.systemd:
    name: slurmctld
    state: restarted
  when: "'controller' in group_names"

- name: restart slurmd
  ansible.builtin.systemd:
    name: slurmd
    state: restarted
  when: "'compute' in group_names"
```

Pontos importantes:

- **O nome do handler precisa coincidir exatamente com o nome usado em `notify`.** Um erro de digitação faz o Ansible falhar com a mensagem `the requested handler could not be found`. Esse erro é fácil de cometer e fácil de corrigir: compare os nomes.
- **Cada handler tem a mesma guarda `when` das tarefas de início.** Assim, um host de computação não tenta reiniciar `slurmctld`, e um host controlador não tenta reiniciar `slurmd`. Como ambos os handlers são notificados pelas três tarefas de renderização, a guarda é o que impede a execução do serviço errado.
- **`state: restarted`** para o serviço e o inicia de novo. Se o serviço não estava rodando, ele é iniciado.

### Reinício duplicado na primeira execução

Na primeira execução, as tarefas de renderização mudam os arquivos e notificam os handlers. Em seguida, a tarefa `Garantir que ... está ativo` inicia o serviço com a configuração nova. Ao final da role, os handlers são executados e reiniciam o serviço que acabou de iniciar. O resultado é um reinício a mais do que o necessário.

Esse reinício duplicado é inofensivo. O serviço termina no estado correto. Se quiser evitá-lo, o módulo `meta` permite forçar a execução dos handlers antes da tarefa de início:

```yaml
- name: Executar handlers pendentes antes de iniciar os serviços
  ansible.builtin.meta: flush_handlers
```

Essa tarefa, colocada antes das tarefas de início, executa os handlers imediatamente. Neste tutorial, ela não é usada, porque o reinício extra não causa problema e a sequência fica mais simples de ler.

> **Referência:** Ansible. *Handlers: running operations on change*. docs.ansible.com. Como handlers são notificados, executados e ordenados.
> **Referência:** Ansible. *ansible.builtin.meta module*. docs.ansible.com. Ação `flush_handlers`.

---

## 8.3 Ordem de execução e dependências entre serviços

A ordem de execução importa porque cada etapa depende da anterior. Os pares abaixo mostram as dependências do projeto:

| Etapa | Depende de | Motivo |
|---|---|---|
| `base` instala os pacotes | nada | É a base de tudo. |
| `munge` garante o serviço e a chave | `base` | O pacote `munge` é instalado pela role `base`. Sem ele, não há serviço nem chave. |
| `slurm` renderiza a configuração | `base` e `munge` | Os templates dependem dos pacotes instalados e da chave de autenticação. |
| `slurmctld` inicia | `slurm.conf` válido | Se a configuração tiver erro de sintaxe, o controlador não inicia. |
| `slurmd` inicia | `munge` ativo e `slurm.conf` válido | O nó precisa autenticar as mensagens do controlador. |

### Ordem dentro da role `slurm`

Dentro da role, a sequência correta é: primeiro gravar a configuração, depois iniciar os serviços. As tarefas de renderização vêm antes das tarefas de início, e isso garante que o serviço só sobe com a configuração já gravada.

Se a ordem fosse invertida, o serviço subiria com uma configuração antiga ou inexistente. Ele falharia, o que atrasaria o diagnóstico.

### Ordem entre hosts

Com uma única máquina, todas as tarefas acontecem na mesma máquina, na ordem da role. Com várias máquinas, o controlador deve estar pronto antes dos nós de computação se registrarem. O Ansible não garante essa relação apenas pela ordem das roles, porque as tarefas de cada etapa rodam em paralelo nos hosts.

A solução usual é colocar o controlador em um play separado, executado antes do play dos nós. Como esta apostila usa um único playbook, o efeito é atenuado pela opção `ReturnToService=2` (Parte 5): um nó que chega antes do controlador fica indisponível até conseguir se registrar. Esse comportamento é esperado e não exige intervenção. A divisão em plays é tratada na Parte 10.

> **Referência:** Ansible. *Controlling playbook execution: strategies*. docs.ansible.com. Estratégia `linear` e o comportamento de execução entre hosts.
> **Referência:** SchedMD. *slurm.conf: ReturnToService*. slurm.schedmd.com/slurm.conf.html. Comportamento de retorno de nós ao serviço.

---

## 8.4 Fluxo completo de uma mudança de configuração

Este é o procedimento que se repete sempre que a configuração muda. Ele é o mesmo para uma mudança pequena, como ajustar a memória de um nó, e para uma grande, como adicionar um nó.

### Passo 1: editar a fonte

Altere `group_vars/all.yml`, e não os arquivos gerados. Por exemplo, para reduzir a memória declarada de um nó, altere `real_memory`:

```yaml
slurm_nodes:
  - name: node01
    addr: 127.0.0.1
    port: 6818
    cpus: 8
    real_memory: 7800
    gpu_count: 1
    gpu_device: /dev/nvidia0
```

### Passo 2: validar a sintaxe

```bash
ansible-playbook site.yml --syntax-check
```

Erros de indentação em YAML são detectados aqui.

### Passo 3: simular

```bash
ansible-playbook site.yml --check --diff -K
```

A saída mostra, para cada arquivo que mudaria, as linhas acrescentadas e removidas. Leia com atenção antes de seguir. Na simulação, os handlers não são executados, então nenhum serviço é reiniciado.

### Passo 4: aplicar

```bash
ansible-playbook site.yml -K
```

Ao final, o Ansible mostra um resumo chamado `PLAY RECAP`, com a contagem de tarefas `ok`, `changed`, `skipped` e `failed` para cada host. Uma execução sem falhas tem `failed=0`.

### Passo 5: verificar a idempotência

Execute o playbook de novo, sem nenhuma mudança:

```bash
ansible-playbook site.yml -K
```

Na segunda execução, o `PLAY RECAP` deve mostrar `changed=0`, ou no máximo a tarefa de atualização de cache de pacotes. Se houver outras tarefas marcadas como `changed`, algum estado não é estável, e a causa deve ser investigada antes de seguir.

### Passo 6: registrar a mudança

Depois de validar, registre a mudança no controle de versão. Se o projeto usa Git, por exemplo:

```bash
git add group_vars/all.yml roles/slurm/templates/
git commit -m "Declara novo nó no cluster"
```

A validação de que o cluster funciona, com `sinfo` e jobs de teste, é feita na Parte 9.

### Limite desta abordagem: nomes de nós com `ansible_hostname`

Em `group_vars/all.yml`, o nome do nó e o do controlador foram definidos com `"{{ ansible_hostname }}"`. Com uma única máquina, esse valor é o próprio nome do host, e está correto.

Com várias máquinas, o problema aparece. Variáveis definidas em `group_vars` são avaliadas no contexto do host que está sendo processado. Assim, ao processar o controlador, `ansible_hostname` vale o nome do controlador para todas as entradas da lista `slurm_nodes`, inclusive as que deveriam ser de outros nós. O mesmo ocorre com `controller_host` em um nó de computação.

A correção, tratada na Parte 10, é usar nomes literais nas entradas da lista, por exemplo `name: node01`, e manter o hostname real apenas como verificação. Por enquanto, com uma única máquina, o valor atual funciona.

> **Atenção:** antes de adicionar uma segunda máquina ao inventário, troque `"{{ ansible_hostname }}"` por nomes literais em `group_vars/all.yml`. Sem essa troca, o `slurm.conf` gerado no controlador terá nomes de nós errados.

> **Referência:** Ansible. *Using variables: variable precedence and scope*. docs.ansible.com. Como variáveis de `group_vars` são avaliadas e a precedência entre fontes.

---

## Resumo da Parte 8

Ao final, a role `slurm` está completa: renderiza os três arquivos de configuração, notifica os handlers quando eles mudam, e inicia o `slurmctld` ou o `slurmd` conforme o grupo do host. Você entende a ordem de execução entre as roles e dentro da role, a função dos handlers, e o fluxo de seis passos para qualquer mudança: editar a fonte, validar, simular, aplicar, verificar a idempotência e registrar.

Você também conhece um limite do projeto atual: os nomes derivados de `ansible_hostname` funcionam para uma única máquina, mas precisam ser literais quando houver mais de uma.

A configuração está aplicada, mas ainda não foi verificada pelo próprio Slurm. Essa verificação é feita na Parte 9.

**Próxima:** Parte 9, Validação do cluster.
