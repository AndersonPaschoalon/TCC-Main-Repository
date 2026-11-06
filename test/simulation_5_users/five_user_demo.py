"""
Cenario enxuto e ilustrativo: 5 usuarios (2 "pesados", 3 "leves").

1. Geramos os jobs de cada usuario (quantidade propria por usuario).
2. Rodamos o simulador do Slurm (slurm_like_schedule) sobre esses jobs --
   isso vira o "ground truth": os timestamps que, supostamente, teriam
   sido coletados de um Slurm real rodando essa carga.
3. A partir do MESMO conjunto de jobs (mesma duracao, mesma chegada,
   mesmo dono), inferimos o contrafactual: como teria sido uma fila FCFS
   pura, sem nenhum escalonador. Nao ha atrito de coordenacao manual aqui
   de proposito -- queremos isolar so o efeito da reordenacao.
4. Medimos fairness nos dois casos: espera media por usuario e por grupo
   (pesados vs. leve).

Sem tabelas, sem indice de Jain, sem penalidade/deadline -- so o que ja
validamos como defensavel: soma/media de espera e atraso por usuario.
"""
import random
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from schedulers import fcfs_schedule, slurm_like_schedule, spt_schedule, totals_by_user

TOTAL_GPUS = 2
SEED = 7


def generate_five_users(seed=SEED):
    rng = random.Random(seed)
    jobs = []
    job_id = 1

    pesado_users = ["pesado_1", "pesado_2"]
    leve_users = ["leve_1", "leve_2", "leve_3"]

    for user in pesado_users:
        fairshare = round(rng.uniform(0.7, 0.9), 2)  # ja usou bastante
        t = rng.choice([0, 1])
        n_jobs = rng.randint(4, 6)
        for _ in range(n_jobs):
            jobs.append({
                "job_id": f"j{job_id}", "user_id": user, "arrival_time": t,
                "duration": rng.randint(5, 9), "gpu_required": rng.choice([1, 2]),
                "user_fairshare_score": fairshare,
            })
            job_id += 1
            t += rng.choice([0, 1])  # rajada

    for user in leve_users:
        fairshare = round(rng.uniform(0.05, 0.25), 2)  # pouco uso recente
        t = rng.randint(0, 20)
        n_jobs = rng.randint(2, 4)
        for _ in range(n_jobs):
            jobs.append({
                "job_id": f"j{job_id}", "user_id": user, "arrival_time": t,
                "duration": rng.randint(1, 3), "gpu_required": 1,
                "user_fairshare_score": fairshare,
            })
            job_id += 1
            t += rng.randint(4, 10)  # espacado

    jobs.sort(key=lambda j: j["arrival_time"])
    return jobs, pesado_users, leve_users


def group_of(user_id):
    return "pesado" if user_id.startswith("pesado") else "leve"


def avg_wait_per_job_by_group(results):
    sums, counts = {}, {}
    for r in results:
        g = group_of(r["user_id"])
        sums[g] = sums.get(g, 0) + r["wait"]
        counts[g] = counts.get(g, 0) + 1
    return {g: sums[g] / counts[g] for g in sums}


def main():
    jobs, pesado_users, leve_users = generate_five_users()
    users_order = pesado_users + leve_users

    # "Ground truth": timestamps supostamente coletados de um Slurm real
    slurm_results = slurm_like_schedule(jobs, TOTAL_GPUS)
    # Contrafactual inferido: os MESMOS jobs, sem nenhum escalonador
    fcfs_results = fcfs_schedule(jobs, TOTAL_GPUS)
    # Teto teórico: os MESMOS jobs, ordenados por SPT (Problema 16-2 de Cormen)
    spt_results = spt_schedule(jobs, TOTAL_GPUS)

    print(f"Total de jobs: {len(jobs)} ({len(pesado_users)} pesados, {len(leve_users)} leves)")

    slurm_by_user = totals_by_user(slurm_results)
    fcfs_by_user = totals_by_user(fcfs_results)
    spt_by_user = totals_by_user(spt_results)
    n_jobs_by_user = {u: sum(1 for j in jobs if j["user_id"] == u) for u in users_order}

    print("\nEspera total por usuário (SPT = teto teórico | Slurm 'coletado' | FCFS inferido):")
    for u in users_order:
        print(f"  {u}: SPT={spt_by_user.get(u, 0):.1f}  Slurm={slurm_by_user.get(u, 0):.1f}  "
              f"FCFS={fcfs_by_user.get(u, 0):.1f}  ({n_jobs_by_user[u]} jobs)")

    slurm_group = avg_wait_per_job_by_group(slurm_results)
    fcfs_group = avg_wait_per_job_by_group(fcfs_results)
    spt_group = avg_wait_per_job_by_group(spt_results)
    print("\nEspera média por job, por grupo:")
    for g in ("pesado", "leve"):
        print(f"  {g}: SPT={spt_group[g]:.2f}  Slurm={slurm_group[g]:.2f}  FCFS={fcfs_group[g]:.2f}")

    total_wait_spt = sum(r["wait"] for r in spt_results)
    total_wait_slurm = sum(r["wait"] for r in slurm_results)
    total_wait_fcfs = sum(r["wait"] for r in fcfs_results)
    print(f"\nSoma total de espera: SPT (teto) = {total_wait_spt:.0f}  "
          f"Slurm = {total_wait_slurm:.0f}  FCFS = {total_wait_fcfs:.0f}")

    colors = {u: c for u, c in zip(users_order, plt.cm.tab10.colors)}

    # --- Gantt: SPT (teto teórico) vs. Slurm "coletado" vs. FCFS inferido ---
    fig, axes = plt.subplots(3, 1, figsize=(10, 8.5), sharex=True)
    for ax, results, title in ((axes[0], spt_results, "SPT — teto teórico (Problema 16-2 de Cormen)"),
                                 (axes[1], slurm_results, "Slurm (dados \"coletados\")"),
                                 (axes[2], fcfs_results, "FCFS (inferido sobre os mesmos jobs)")):
        for idx, r in enumerate(sorted(results, key=lambda r: r["start"])):
            ax.barh(idx, r["finish"] - r["start"], left=r["start"],
                    color=colors[r["user_id"]], height=0.8)
        ax.set_title(title)
        ax.set_ylabel("Jobs (ordenados por início)")
    axes[2].set_xlabel("Tempo")
    handles = [plt.Rectangle((0, 0), 1, 1, color=colors[u]) for u in users_order]
    fig.legend(handles, users_order, loc="upper center", ncol=5, bbox_to_anchor=(0.5, 1.06))
    plt.tight_layout(rect=[0, 0, 1, 0.95])
    plt.savefig("five_user_gantt.png", dpi=150, bbox_inches="tight")
    plt.close()

    # --- Espera total por usuário, nos três regimes ---
    width = 0.27
    x = list(range(len(users_order)))
    plt.figure(figsize=(9, 4.5))
    plt.bar([i - width for i in x], [spt_by_user.get(u, 0) for u in users_order],
            width=width, label="SPT (teto teórico)", color="#27ae60")
    plt.bar(x, [slurm_by_user.get(u, 0) for u in users_order],
            width=width, label="Slurm (coletado)", color="#2980b9")
    plt.bar([i + width for i in x], [fcfs_by_user.get(u, 0) for u in users_order],
            width=width, label="FCFS (inferido)", color="#c0392b")
    plt.xticks(x, users_order)
    plt.ylabel("Espera total (soma de todos os jobs do usuário)")
    plt.title("Espera total por usuário — 5 usuários (2 pesados, 3 leves)")
    plt.legend()
    plt.tight_layout()
    plt.savefig("five_user_wait_by_user.png", dpi=150)
    plt.close()

    # --- Espera média por job, por grupo (o resultado-chave de justiça) ---
    groups = ["pesado", "leve"]
    gx = [0, 1]
    plt.figure(figsize=(6.5, 4.5))
    plt.bar([i - width for i in gx], [spt_group[g] for g in groups],
            width=width, label="SPT (teto teórico)", color="#27ae60")
    plt.bar(gx, [slurm_group[g] for g in groups],
            width=width, label="Slurm (coletado)", color="#2980b9")
    plt.bar([i + width for i in gx], [fcfs_group[g] for g in groups],
            width=width, label="FCFS (inferido)", color="#c0392b")
    plt.xticks(gx, ["Pesados", "Leves"])
    plt.ylabel("Espera média por job")
    plt.title("Justiça: espera média por job, por grupo")
    plt.legend()
    plt.tight_layout()
    plt.savefig("five_user_fairness_by_group.png", dpi=150)
    plt.close()

    print("\nArquivos gerados: five_user_gantt.png, five_user_wait_by_user.png, "
          "five_user_fairness_by_group.png")


if __name__ == "__main__":
    main()
