# Apêndice A: Glossário rápido

Os termos estão em ordem alfabética. Cada definição é curta, e a parte da apostila onde o termo é tratado aparece entre parênteses.

**Accounting (contabilidade):** registro do histórico de jobs, com quem enviou, quando começou, quanto tempo durou e em que estado terminou. No Slurm, é mantido pelo `slurmdbd` (Partes 1 e 10).

**Ansible:** ferramenta de automação que aplica um estado desejado em máquinas a partir de arquivos YAML, sem exigir programa instalado nelas (Parte 3).

**apt:** gerenciador de pacotes do Debian e do Ubuntu, usado para instalar e atualizar programas (Parte 2).

**cgroups (*control groups*):** recurso do kernel Linux que limita e isola o uso de CPU, memória e dispositivos por grupo de processos (Partes 1 e 6).

**Cluster:** conjunto de máquinas conectadas em rede que se comportam como um sistema único para quem usa (Parte 1).

**Daemon:** processo que roda em segundo plano, sem interação direta com o usuário, como o `slurmctld` e o `munge` (Parte 5).

**Driver:** módulo do kernel que permite ao sistema operacional se comunicar com um dispositivo, como uma GPU (Parte 2).

**Fact (fato):** informação coletada automaticamente pelo Ansible sobre cada host, como o hostname e a quantidade de memória (Parte 3).

**File (`gres.conf`):** opção que aponta o arquivo de dispositivo de uma GPU, permitindo que o Slurm isole esse dispositivo por job (Parte 6).

**Fonte única da verdade:** princípio pelo qual cada valor de configuração existe em um único lugar, e os demais arquivos são gerados a partir dele (Partes 1 e 3).

**GPU (*Graphics Processing Unit*):** processador com muitos núcleos, adequado para executar muitas operações iguais em paralelo, como as do treinamento de modelos (Parte 2).

**GRES (*Generic RESource*):** recurso genérico com nome livre que o Slurm pode reservar por job. Neste tutorial, o recurso é `gpu` (Parte 6).

**Group (grupo de hosts):** conjunto nomeado de hosts no inventário, como `controller` e `compute`. As roles usam o grupo para decidir o que cada host executa (Parte 3).

**Handler:** tarefa que só executa quando uma tarefa a notifica de que algo mudou, geralmente para reiniciar um serviço (Parte 8).

**HPC (*High Performance Computing*):** computação de alto desempenho, que reúne máquinas para resolver problemas de cálculo intensivo (Parte 1).

**Idempotência:** propriedade de uma operação que, repetida, produz o mesmo resultado final. Uma automação idempotente pode ser executada várias vezes sem efeito colateral (Parte 3).

**Inventário:** arquivo que lista as máquinas gerenciadas pelo Ansible, organizadas em grupos, e guarda as variáveis de cada uma (Parte 3).

**IaC (*Infrastructure as Code*):** prática de descrever a configuração de máquinas em arquivos versionados, em vez de configurá-las manualmente (Parte 1).

**Jinja2:** linguagem de templates que gera texto a partir de variáveis, usando laços e condicionais. O Ansible a usa para produzir os arquivos de configuração (Parte 7).

**Job:** tarefa enviada a um gerenciador de filas para execução em um ou mais nós (Partes 5 e 9).

**journal:** registro de eventos mantido pelo systemd, consultado com `journalctl` (Parte 11).

**MariaDB:** sistema de banco de dados relacional, derivado do MySQL, usado para armazenar o histórico de jobs (Parte 10).

**munge:** serviço de autenticação que permite aos componentes do Slurm confiar uns nos outros, com base em uma chave compartilhada (Parte 4).

**NAS (*Network Attached Storage*):** servidor de arquivos acessado pela rede, que permite a várias máquinas usar os mesmos dados (Parte 1).

**NFS (*Network File System*):** protocolo que permite montar uma pasta remota como se fosse local (Parte 1).

**Nó:** máquina de computação que recebe e executa jobs, descrita no Slurm pela linha `NodeName` (Partes 5 e 9).

**Nó virtual (ou simulado):** processo `slurmd` adicional, rodando em um host real, que se apresenta ao Slurm como um nó separado. Serve para testar o escalonador, não para medir desempenho (Parte 10).

**Partição:** grupo de nós com regras comuns de acesso, escolhido pelo usuário ao enviar um job (Partes 5 e 9).

**Playbook:** arquivo do Ansible que lista as roles a aplicar, em quais hosts e com quais privilégios (Parte 3).

**Role:** pasta com estrutura padronizada de tarefas, handlers, templates e variáveis de um assunto, reutilizável em vários playbooks (Partes 3 e 8).

**Slurm (*Slurm Workload Manager*):** gerenciador de recursos e escalonador de jobs de código aberto, usado em clusters de computação (Parte 5).

**slurmctld:** daemon controlador do Slurm, que mantém a fila e decide as alocações (Parte 5).

**slurmd:** daemon de cada nó de computação, que executa os jobs e informa o estado do nó (Parte 5).

**slurmdbd:** daemon que grava o histórico de jobs em um banco de dados (Partes 5 e 10).

**Spool:** diretório de trabalho temporário de um serviço. No `slurmd`, guarda arquivos enquanto um job executa (Partes 4 e 10).

**sudo:** comando que executa uma ação com privilégio de administrador (Parte 2).

**systemd:** gerenciador de serviços do Linux, que inicia, para e monitora daemons (Partes 4 e 11).

**Template:** arquivo com espaços reservados para valores, que o Ansible transforma em arquivo final (Parte 7).

**Variável de host:** valor que pertence a uma máquina específica, definido no inventário (Parte 3).

**YAML:** formato de texto para dados estruturados, em que a indentação com espaços define a hierarquia (Parte 1).
