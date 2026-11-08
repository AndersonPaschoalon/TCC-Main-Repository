# Apostila: Cluster Pequeno com Slurm, GPU e Infraestrutura como Código

**Público:** iniciantes em gerenciamento de recursos computacionais e em Infraestrutura como Código (IaC), com experiência básica em programação.

**Objetivo:** ensinar a montar, de forma automatizada e reproduzível, um cluster pequeno de computação em que as tarefas são enfileiradas e executadas em máquinas com GPU.

**Ambiente de referência:** Linux baseado em Ubuntu 24.04, incluindo distribuições derivadas (como o Linux Mint 22), com acesso `sudo` e, opcionalmente, uma GPU NVIDIA. Sem GPU, todas as partes continuam válidas, exceto as que dependem de acelerador.

**Princípio de leitura:** esta apostila ensina conceitos antes de comandos. Nomes de campos, pacotes e opções mudam entre versões. Quando isso acontecer, o conceito continua válido, e a própria ferramenta (`--help`, `man`, `ansible-doc`) indica a forma atual. Os exemplos de saída são ilustrativos, e os valores da sua máquina serão diferentes.

---

## Sumário

### Parte 1: Introdução
- **1.1** O que é um cluster de computação e por que usar um
- **1.2** Sistema operacional Linux e o gerenciador de pacotes apt
- **1.3** GPU, driver e ferramentas de estado
- **1.4** O que é Infraestrutura como Código (IaC)
- **1.5** O que é Ansible
- **1.6** O que são YAML e Jinja2
- **1.7** O que é Slurm
- **1.8** O que é munge
- **1.9** O que são GRES e cgroups
- **1.10** O que é Multipass
- **1.11** O que são MariaDB e slurmdbd
- **1.12** O que é NAS e o protocolo NFS
- **1.13** Como as peças se encaixam

### Parte 2: Preparando o ambiente
- **2.1** Verificando o acelerador (GPU)
- **2.2** Levantando os dados de hardware
- **2.3** Instalando o Ansible
- **2.4** Criando a estrutura do projeto

### Parte 3: Ansible na prática
- **3.1** Configuração do Ansible (`ansible.cfg`)
- **3.2** Inventário: quais máquinas existem
- **3.3** Variáveis: a fonte única da verdade
- **3.4** Playbook: a receita de configuração
- **3.5** Tarefas e módulos
- **3.6** Idempotência: executar de novo sem efeito colateral

### Parte 4: Pacotes e autenticação
- **4.1** Instalação de pacotes (role `base`)
- **4.2** Diretórios de estado e permissões
- **4.3** munge: chave e serviço (role `munge`)
- **4.4** Testando a autenticação com `munge -n | unmunge`

### Parte 5: Slurm, componente por componente
- **5.1** Arquitetura: `slurmctld`, `slurmd`, `slurmdbd` e os comandos do usuário
- **5.2** `slurm.conf`: o arquivo principal de configuração
- **5.3** Nós (`NodeName`) e partições (`PartitionName`)
- **5.4** Escalonador e seleção de recursos

### Parte 6: GPU como recurso agendável
- **6.1** GRES: declarando GPUs (`gres.conf`)
- **6.2** Pedindo GPUs em um job (`--gres=gpu:1`)
- **6.3** cgroups e isolamento de dispositivos (`cgroup.conf`)

### Parte 7: Templates: gerando configuração a partir de variáveis
- **7.1** Jinja2: variáveis, laços e condicionais
- **7.2** `slurm.conf.j2` passo a passo
- **7.3** `gres.conf.j2` e a diferença entre nó com GPU física e nó sem GPU física
- **7.4** Por que nunca editar arquivos gerados

### Parte 8: Integração do playbook ao cluster funcionando
- **8.1** Como o playbook percorre as roles
- **8.2** Handlers: reiniciar serviços só quando a configuração muda
- **8.3** Ordem de execução e dependências entre serviços
- **8.4** Fluxo completo de uma mudança de configuração

### Parte 9: Validação do cluster
- **9.1** `sinfo`, `scontrol show node` e `squeue`
- **9.2** Primeiro job: `srun` e `sbatch`
- **9.3** Verificando a GPU dentro de um job

### Parte 10: Expansão
- **10.1** Nós simulados no mesmo host e o diretório de spool
- **10.2** Múltiplas máquinas virtuais e distribuição da chave munge
- **10.3** Accounting com slurmdbd e MariaDB

### Parte 11: Solução de problemas
- **11.1** Tabela de sintomas e causas
- **11.2** Como ler logs (`journalctl` e logs do Slurm)
- **11.3** Hábitos de depuração

### Parte 12: Conclusão
- **12.1** O que foi construído
- **12.2** Boas práticas para reutilizar a automação em outras máquinas
- **12.3** Próximos passos

### Apêndices
- **A.** Glossário rápido
- **B.** Comandos de referência em uma página
- **C.** Referências para aprofundamento (fontes públicas e científicas)