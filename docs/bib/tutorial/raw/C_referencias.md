# Apêndice C: Referências para aprofundamento

As referências estão agrupadas por tipo. Todas são fontes públicas: documentação oficial dos projetos, artigos científicos publicados e livros de editora. Para cada assunto, a documentação oficial é a fonte de consulta mais atualizada, porque acompanha as versões. Os livros e artigos complementam a compreensão dos conceitos.

---

## Documentação oficial

**Slurm (SchedMD).** Documentação do gerenciador de filas, incluindo o guia de administração, as páginas de configuração e as páginas de comandos. Disponível em slurm.schedmd.com.

- *Slurm Quick Start Administrator Guide*. slurm.schedmd.com/quickstart_admin.html
- *slurm.conf: Slurm configuration file*. slurm.schedmd.com/slurm.conf.html
- *gres.conf: Generic Resource configuration file*. slurm.schedmd.com/gres.conf.html
- *cgroup.conf: Slurm cgroup support configuration file*. slurm.schedmd.com/cgroup.conf.html
- *slurmdbd.conf: Slurm Database Daemon configuration file*. slurm.schedmd.com
- *Generic Resource (GRES) Scheduling*. slurm.schedmd.com/gres.html
- *sbatch*, *srun*, *scancel*, *sinfo*, *squeue*, *scontrol* e *sacctmgr*. slurm.schedmd.com
- *Multifactor Priority Plugin*. slurm.schedmd.com

**Ansible.** Documentação do Ansible, com guias, referência de módulos e de variáveis. Disponível em docs.ansible.com.

- *How to build your inventory*
- *Using variables* e *Magic variables, and how to access information about other hosts*
- *Playbooks* e *Using roles*
- *Handlers: running operations on change*
- *Templating (Jinja2)*
- *Validating tasks: check mode and diff mode*
- *Using Ansible Vault to encrypt sensitive data*
- *Best Practices*

**Ansible Community: community.mysql.** Módulos para bancos e usuários MySQL e MariaDB, em docs.ansible.com.

**Jinja2 (Pallets).** Documentação da linguagem de templates, incluindo variáveis, laços, condicionais e filtros. Disponível em jinja.palletsprojects.com.

**munge.** Documentação do serviço de autenticação, em dun.github.io/munge.

**Linux kernel.** Documentação da versão unificada dos cgroups, em docs.kernel.org/admin-guide/cgroup-v2.html.

**systemd.** Documentação das unidades de serviço e do registro de eventos, em freedesktop.org (páginas `systemd.service(5)` e `journalctl(1)`).

**NVIDIA.** Guia do usuário do `nvidia-smi`, em docs.nvidia.com.

**Ubuntu.** Consulta de pacotes por distribuição, em packages.ubuntu.com.

**Multipass (Canonical).** Documentação de criação de máquinas virtuais e uso de `cloud-init`, em multipass.run.

**MariaDB Foundation.** Documentação do servidor de banco de dados, em mariadb.org.

**Prometheus.** Documentação do sistema de coleta de séries temporais, em prometheus.io.

**Git.** Documentação e o livro *Pro Git*, de Chacon e Straub, disponível gratuitamente em git-scm.com.

---

## Artigos científicos

**Yoo, A. B.; Jette, M. A.; Grondona, M.** *SLURM: Simple Linux Utility for Resource Management*. In: Job Scheduling Strategies for Parallel Processing (JSSPP), Springer, 2003. Descreve a arquitetura original do Slurm.

**Feitelson, D. G.; Rudolph, L.; Schwiegelshohn, U.; Sevcik, K. C.; Wong, P.** *Theory and Practice in Parallel Job Scheduling*. In: Job Scheduling Strategies for Parallel Processing (JSSPP), Springer, 1997. Trata a teoria das políticas de escalonamento, como FIFO e backfill.

---

## Livros

**Ansible e automação.**

- Geerling, J. *Ansible for DevOps*. Leanpub.
- Morris, K. *Infrastructure as Code: Managing Servers in the Cloud*. O'Reilly.

**Linux e sistemas.**

- Kerrisk, M. *The Linux Programming Interface*. No Starch Press.
- Shotts, W. *The Linux Command Line*. No Starch Press.
- Gregg, B. *Systems Performance: Enterprise and the Cloud*. Addison-Wesley.

**Depuração.**

- Zeller, A. *Why Programs Fail: A Guide to Systematic Debugging*. Morgan Kaufmann.

---

## Como usar esta lista

Para um assunto específico, comece pela documentação oficial da ferramenta, na versão que você instalou. Quando o conceito precisar de mais profundidade, recorra ao livro ou ao artigo indicado na seção de cada parte. Os artigos científicos são úteis para entender a origem das ideias, como o escalonamento por backfill e a arquitetura do Slurm.
