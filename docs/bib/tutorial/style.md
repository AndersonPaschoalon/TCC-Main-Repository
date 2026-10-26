# SPEC: Requisitos do Documento da Apostila


## 1. Propósito

A apostila ensina, a partir do zero, como montar e automatizar um cluster pequeno de computação com gerenciador de filas (Slurm) e aceleradores (GPU), usando Infraestrutura como Código (Ansible). Seu leitor-alvo é alguém que conhece programação, mas não conhece administração de cluster, GPU nem IaC.

Propósito secundário: servir como material de consulta reutilizável, válido mesmo quando ferramentas e versões mudarem.

---

## 2. Premissas

| ID | Premissa |
|---|---|
| **P-01** | O leitor sabe programar e usar um terminal, mas pode nunca ter administrado um servidor. |
| **P-02** | O leitor tem acesso `sudo` em pelo menos uma máquina Linux. |
| **P-03** | A GPU é opcional. A apostila precisa funcionar, com ressalvas claras, sem GPU. |
| **P-04** | O ambiente de referência é Ubuntu 24.04 e distribuições derivadas. Outras distribuições Debian/Ubuntu devem ser compatíveis, com ajustes indicados quando necessário. |

---

## 3. Requisitos de conteúdo (RC)

| ID | Requisito | Justificativa |
|---|---|---|
| **RC-01** | A apostila deve cobrir a pilha tecnológica completa do cluster: sistema operacional, driver de GPU, Ansible, Slurm (com seus componentes), munge, GRES, cgroups, Jinja2, Multipass, MariaDB/slurmdbd e NAS/NFS. | Cobertura da pilha pedida pelo autor. |
| **RC-02** | Cada item da pilha deve ser explicado individualmente, antes de ser usado. | Permite que o leitor entenda cada peça isoladamente. |
| **RC-03** | A integração entre os componentes deve ser explicada em detalhe em uma parte própria, com o fluxo completo. | O valor da apostila está na combinação das peças. |
| **RC-04** | A apostila deve terminar com uma conclusão e apêndices úteis (glossário, comandos de referência, referências). | Fechamento e consulta futura. |
| **RC-05** | Os trechos de código do plano técnico devem ser preservados como exemplos, após correções de erros identificados. | Continuidade do material técnico já validado. |

---

## 4. Requisitos didáticos (RD)

| ID | Requisito | Critério de verificação |
|---|---|---|
| **RD-01** | Cada conceito deve ser apresentado **antes** do comando que o utiliza. | Em toda seção com comando, há uma explicação anterior do que se quer obter. |
| **RD-02** | A apostila deve ensinar conceitos antes de comandos. Comandos são instrumentos para um objetivo declarado. | Nenhum bloco de comando aparece sem uma frase explicando seu propósito. |
| **RD-03** | Cada item da introdução deve responder a: o que é, qual problema resolve, como se usa e um exemplo de código ou comando. | Itens 1.1 a 1.13 seguem essa estrutura. |
| **RD-04** | Linguagem acessível a iniciantes. Termos técnicos devem ser definidos na primeira ocorrência. | Glossário (apêndice A) cobre os termos introduzidos. |
| **RD-05** | Exemplos devem ser pequenos e focados em um conceito por vez. | Blocos de código com foco único, sem excesso de opções. |
| **RD-06** | Saídas de comando devem ser mostradas como ilustração, com aviso de que os valores reais serão diferentes. | Presente no sumário e nas seções com saída. |
| **RD-07** | O leitor deve ser incentivado a ler a saída, não a decorar comandos. A própria ferramenta (`--help`, `man`, `ansible-doc`) deve ser indicada como caminho de descoberta. | Presente na introdução e em cada parte prática. |
| **RD-08** | Preferir automação (scripts, playbooks) a sequências manuais longas, quando a sequência for repetível. | Ex.: script `bootstrap-estrutura.sh` na Parte 2. |

---

## 5. Requisitos de generalidade e agnosticismo (RG)

Estes são os requisitos mais restritivos. Todo o conteúdo deve ser válido para qualquer cluster pequeno, e não para um projeto, pessoa ou máquina específica.

| ID | Requisito | Critério de verificação |
|---|---|---|
| **RG-01** | A apostila não deve referenciar projeto, instituição, curso, orientador, laboratório, nem trabalho acadêmico específico. | Busca por termos desses tipos retorna zero resultados. |
| **RG-02** | Nomes de máquinas devem ser genéricos (`<hostname>`, `node01`, `ctl`). Nenhum nome real de equipamento deve aparecer. | Busca por nomes de máquinas reais retorna zero resultados. |
| **RG-03** | Não devem aparecer dados de hardware de uma máquina real. Os exemplos são ilustrativos. | Valores de CPU, memória e GPU nos exemplos são genéricos e marcados como ilustrativos. |
| **RG-04** | Não devem existir referências a decisões tomadas em conversas, versões anteriores ou revisões. | Ausência de expressões como "conforme discutido", "decidimos", "versão anterior", "a SPEC" ou "reconsiderar". |
| **RG-05** | A apostila deve ser válida para múltiplas distribuições Debian/Ubuntu e para diferentes fabricantes de GPU. | Procedimentos indicam alternativas quando o fabricante muda (ex.: `rocm-smi`, `intel_gpu_top`). |
| **RG-06** | Ferramentas de IaC alternativas devem ser apresentadas de forma neutra, sem julgamento de adequação ao projeto. | Item 1.4 lista alternativas sem recomendação comparativa. |
| **RG-07** | Alternativas de gerenciador de filas e de armazenamento devem ser citadas de forma neutra. | Itens 1.7 e 1.13 apresentam alternativas sem veredito. |
| **RG-08** | A apostila não deve conter o plano de execução de um trabalho específico (cronogramas, etapas, fases do projeto). | Ausência de cronograma e de termos como "fase 1 do projeto". |

---

## 6. Requisitos de estrutura (RE)

| ID | Requisito | Critério de verificação |
|---|---|---|
| **RE-01** | Estrutura obrigatória: Introdução, Partes práticas, Integração, Validação, Expansão, Solução de problemas, Conclusão e Apêndices. | Sumário contém todas as seções. |
| **RE-02** | Cada parte prática deve ter: objetivo, pré-requisito, conteúdo e resumo ou próximo passo. | Estrutura presente em cada arquivo de parte. |
| **RE-03** | Cada arquivo deve cobrir um conjunto coerente de partes, para leitura em sessões curtas. | Nenhum arquivo ultrapassa o escopo de duas a três partes. |
| **RE-04** | Numeração estável: partes e itens devem manter a numeração do sumário. | Títulos e sumário coincidem. |
| **RE-05** | Cada arquivo deve ser autocontido o suficiente para ser lido com o anterior, sem depender de conteúdo não referenciado. | Referências cruzadas apontam para partes existentes. |

---

## 7. Requisitos de exemplos e código (RX)

| ID | Requisito | Critério de verificação |
|---|---|---|
| **RX-01** | Todo código deve ser copiável e executável no ambiente de referência, sem edição além das indicadas. | Comandos e arquivos são válidos. |
| **RX-02** | Blocos de código devem indicar a linguagem (`bash`, `yaml`, `ini`, `jinja`). | Presente em todos os blocos. |
| **RX-03** | Código que altera o sistema deve ser precedido de uma forma de verificação segura (leitura, `--syntax-check`, `--check`, ou execução em pasta temporária). | Cada seção com alteração tem um passo de verificação antes. |
| **RX-04** | Comandos de leitura devem ser distinguidos de comandos que alteram o sistema. | Comandos de alteração aparecem explicitamente com `sudo` ou em contexto de execução. |
| **RX-05** | Os valores a substituir pelo leitor devem estar marcados (`<hostname>`, valores ilustrativos com comentário). | Nenhum valor real de ambiente sem marcação. |
| **RX-06** | Código de automação deve seguir boas práticas: idempotência, fonte única da verdade e configuração versionada. | Consistente com princípios da Parte 3. |
| **RX-07** | Arquivos gerados por templates não devem ser editados à mão, e a apostila deve dizer isso. | Presente nas partes de Slurm e templates. |

---

## 8. Requisitos de referências (RR)

| ID | Requisito | Critério de verificação |
|---|---|---|
| **RR-01** | Referências devem ser apenas fontes públicas (documentação oficial, livros publicados, artigos científicos, sites públicos). | Nenhuma fonte privada, interna ou de origem não verificável. |
| **RR-02** | Referências de aprendizagem devem seguir um modelo simples: autor, título, editora ou site, e ano quando disponível. Não é exigido o rigor de citação acadêmica. | Formato uniforme `> **Referência:** ...`. |
| **RR-03** | Cada assunto novo relevante deve ter pelo menos uma referência. | Cada parte prática tem referências. |
| **RR-04** | Títulos e edições de livros citados de memória devem ser marcados para verificação antes de uso formal. | Marcação "verifique a edição antes de citar" presente quando aplicável. |
| **RR-05** | Documentação de ferramentas deve apontar para a versão correspondente, quando possível. | Indicação de "use a versão do guia correspondente". |

---

## 9. Requisitos de linguagem e formato (RL)

| ID | Requisito | Critério de verificação |
|---|---|---|
| **RL-01** | Idioma: português do Brasil. Termos técnicos consagrados em inglês podem ser mantidos, com definição na primeira ocorrência. | Revisão ortográfica e de termos. |
| **RL-02** | Formato Markdown, com títulos hierárquicos, tabelas para comparações, e blocos de código para comandos e arquivos. | Renderização correta. |
| **RL-03** | Tom neutro e direto, sem coloquialismos e sem referência ao diálogo com o autor. | Ausência de frases de conversa dirigidas ao leitor como interlocutor do autor. |
| **RL-04** | Cada parte prática deve começar com o objetivo em uma frase. | Presente em todas as partes. |
| **RL-05** | Notas de cautela (segurança, perda de dados, mudanças irreversíveis) devem ser destacadas. | Ex.: Secure Boot, alterações em `/etc/`. |

---

## 10. Requisitos de entrega (RS)

Estes requisitos são de processo. Eles não alteram o conteúdo, mas governam como a apostila é produzida.

| ID | Requisito | Critério de verificação |
|---|---|---|
| **RS-01** | A apostila é entregue em janelas de duas a três partes, com verificação do material antes da janela seguinte. | Histórico de entregas por janela. |
| **RS-02** | Antes de cada nova janela, o material anterior deve ser revisado contra esta SPEC. | Registro da revisão (esta própria seção). |

---

## 11. Não escopo

Itens explicitamente fora da apostila:

- Cronogramas, planos de trabalho e etapas de execução de qualquer projeto específico.
- Perguntas de pesquisa, hipóteses e matrizes de decisão para escolha de tecnologia.
- Medição de desempenho de treinamento de modelos (a apostila ensina a infraestrutura, não avalia modelos).
- Implantação em ambiente de produção específico.
- Fontes não públicas, como materiais internos, conversas e vídeos sem autoria verificável.

