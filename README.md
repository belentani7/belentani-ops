# belentani-ops

Cadena de herramientas Python (solo libreria estandar) para operar el
ecosistema Belentani: disco, repos GitHub, secretos, backups, proveedores
LLM, uptime de sitios e informes.

## Requisitos

- Python 3.8+ (probado en 3.11.9)
- `git`, `gh` en PATH (opcional: `ipfs`, `huggingface-cli`)
- Sin `pip install`: no hay dependencias obligatorias

## Uso rapido

```powershell
cd C:\Users\USER\Documents\01_PROYECTOS\_HERRAMIENTAS\belentani-ops
.\run.ps1 doctor          # diagnostico
.\run.ps1 run             # cadena completa + informe JSON
.\run.ps1 system clean    # plan de limpieza (dry-run)
.\run.ps1 system clean --apply --yes
.\run.ps1 repos audit --limit 100 --deep
.\run.ps1 secrets scan
.\run.ps1 monitor
.\run.ps1 llm route --task coding
```

O directamente:

```powershell
$env:PYTHONPATH = "."
python -m belentani_ops report --deep --secrets
```

## Comandos

| Comando | Acciones |
|---|---|
| `doctor` | diagnostico de tools + disco |
| `system` | `disk`, `home`, `dotfiles`, `processes`, `clean`, `health` |
| `repos` | `list`, `audit`, `pages`, `deploy` |
| `secrets` | `scan`, `rotation`, `mask` |
| `backup` | `plan`, `run` |
| `llm` | `providers`, `health`, `route`, `costs` |
| `monitor` | uptime de los sitios |
| `report` | informe agregado |
| `run` | cadena completa |
| `config` | `show`, `init` |

## Configuracion

Se lee de `belentani_ops.config.json` (raiz del proyecto) o
`~/.belentani/belentani_ops.config.json`. Genera uno editable con:

```powershell
.\run.ps1 config init
```

Ajusta `disk_warn_gb`, `sites`, `providers`, `backup_repos`,
`clean_targets`, `github_user` y `alert_webhook`.

## Tareas programadas (24/7)

```powershell
.\schedule.ps1 register   # monitor horario, backup diario, informe semanal
.\schedule.ps1 list
.\schedule.ps1 remove
```

## Seguridad

- El scan de secretos solo enmascara; nunca imprime valores completos.
- `system clean` es dry-run por defecto; requiere `--apply` y `--yes`.
- `backup run` pide confirmacion salvo `--yes`.
- Respeta los umbrales de disco (<10GB avisa, <5GB bloquea, <2GB solo lectura).

## Tests

```powershell
$env:PYTHONPATH = "."
python -m unittest discover -s tests -v
```
