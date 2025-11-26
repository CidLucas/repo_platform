# Smoke Test Logs

Date: 2025-11-26

Summary: migration fixes were applied, migrations ran, DB tables created, and seeder executed successfully. Logs below capture key commands and outputs.

---

1) Postgres tables after migrations (psql `\dt`):

```
                    List of relations
 Schema |              Name              | Type  | Owner 
--------+--------------------------------+-------+-------
 public | alembic_version                | table | user
 public | alembic_version_backup         | table | user
 public | cliente_final                  | table | user
 public | cliente_vizu                   | table | user
 public | configuracao_negocio           | table | user
 public | credencial_servico_externo     | table | user
 public | fonte_de_dados                 | table | user
 public | pm_dados_faturamento_cliente_x | table | user
(8 rows)
```

2) Seeder output (successful run via `poetry run python seed_all.py`):

```
--- INICIANDO POPULAÇÃO DE CLIENTES E CONFIGURAÇÕES ---

[*] Processando cliente: Oficina Mendes...
  [1/2] Criando cliente base...
      ID: 2cb6fb64-f4e4-43a2-941b-518626925bf7
      API Key: 81d5dcda2f5508d8cbecc607b9ea8b99530aa5156664d6de2adda8bcb16e4e82
  [2/2] Enviando configuração de contexto...
  [+] SUCESSO! Configuração criada e associada ao cliente.

[*] Processando cliente: Studio J...
  [1/2] Criando cliente base...
      ID: 5befbe5b-e23d-4b2a-805b-5d156ead35ae
      API Key: ef4f2877bae04e877637c65942a7d3189413b8c9bbc2742494b6c603adcd6243
  [2/2] Enviando configuração de contexto...
  [+] SUCESSO! Configuração criada e associada ao cliente.

[*] Processando cliente: Casa com Alma...
  [1/2] Criando cliente base...
      ID: 8dbc45a7-e25b-4b0a-8303-8497180d10a3
      API Key: 73607a1b7e554f2fb2dae26e202d4d64454ecb9f779f44b84e2e8736fdab3456
  [2/2] Enviando configuração de contexto...
  [+] SUCESSO! Configuração criada e associada ao cliente.

[*] Processando cliente: Consultório Odontológico Dra. Beatriz Almeida...
  [1/2] Criando cliente base...
      ID: f16a94bb-e7c7-4a09-97d0-ce06ec9cfb96
      API Key: e00b197427debf273c505fa1c0a94c23cd06360eec53566a24dfe581f2b5f0a4
  [2/2] Enviando configuração de contexto...
  [+] SUCESSO! Configuração criada e associada ao cliente.

[*] Processando cliente: Marcos Eletricista...
  [1/2] Criando cliente base...
      ID: cf57e65e-7c5f-41e1-adc9-949bdfde8547
      API Key: dec95b40df6e2d5ea2f17cf61f49361abe97cacee4dde11a858083994334f4d6
  [2/2] Enviando configuração de contexto...
  [+] SUCESSO! Configuração criada e associada ao cliente.

=================================================
=== POPULAÇÃO FINALIZADA: CHAVES PARA TESTE ===
=================================================
| Oficina Mendes                           | Key: 81d5dcda2f5508d8cbecc607b9ea8b99530aa5156664d6de2adda8bcb16e4e82
| Studio J                                 | Key: ef4f2877bae04e877637c65942a7d3189413b8c9bbc2742494b6c603adcd6243
| Casa com Alma                            | Key: 73607a1b7e554f2fb2dae26e202d4d64454ecb9f779f44b84e2e8736fdab3456
| Consultório Odontológico Dra. Beatriz Almeida | Key: e00b197427debf273c505fa1c0a94c23cd06360eec53566a24dfe581f2b5f0a4
| Marcos Eletricista                       | Key: dec95b40df6e2d5ea2f17cf61f49361abe97cacee4dde11a858083994334f4d6
=================================================
```

3) Important fix steps performed (summary)

- Found placeholder value in `alembic_version`: `<ID_GERADO_PELO_ALEMBIC>` which caused Alembic to fail.
- Backed up the value to `alembic_version_backup` and removed the invalid row from `alembic_version`.
- Added missing Alembic template `script.py.mako` to allow `alembic revision --autogenerate` to write revision files.
- Adjusted `migration_runner` to change working dir to the directory containing `alembic.ini` and to run only `alembic upgrade head` (no runtime autogenerate).
- Rebuilt `migration_runner` image and executed migrations; applied `upgrade head` and created the required tables.
- Re-ran the seeder against the migrated DB — all clients and configurations were created successfully.

4) PR with changes

PR: https://github.com/vizubr/vizu-mono/pull/3

---

If you want, I can now request explicit GitHub reviewers on the PR (please list the GitHub usernames), or I can request an automated Copilot review and attach this file to the PR (already added to the branch). Which do you prefer?
