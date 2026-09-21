"""
core/attack_path.py
Attack Path simplificado — cadeias de risco em 3 elos:

    🌐 EXPOSIÇÃO  →  🔓 VULNERABILIDADE  →  💥 IMPACTO

ESCOPO E LIMITAÇÕES (importante para não superestimar o que isso faz):
Isto NÃO é um attack path de verdade como o de ASPMs comerciais (Wiz, Palo
Alto), que constroem grafos reais de infraestrutura a partir de topologia de
rede, permissões IAM e telemetria de runtime. Aqui não existe nenhuma dessas
fontes de dado.

O que existe é uma correlação determinística entre:
  - dados que as ferramentas já reportaram (tipo de scan, severidade, módulo)
  - o contexto declarado do Ativo (core/asset.py), preenchido manualmente

Ou seja: cada "caminho" é uma inferência baseada em regras explícitas, não uma
rota de ataque observada ou validada. Serve para dar leitura de risco
combinado — "esses dois achados juntos, neste ativo, são piores que separados"
— e não deve ser apresentado como prova de explorabilidade real.
"""
from dataclasses import dataclass, field
from collections import defaultdict

from core.models import Vulnerability, Severity, ScanType
from core.asset import Asset

# Severidade da cadeia (não da vulnerabilidade isolada)
CHAIN_SEVERITY_ORDER = {"critical": 0, "high": 1, "medium": 2}


@dataclass
class AttackPath:
    """Uma cadeia de risco de 3 elos."""
    rule_id: str                              # qual regra gerou (A, B, C, D)
    severity: str                             # critical | high | medium
    exposure: str                             # elo 1 — como se chega
    vulnerability: str                        # elo 2 — o que se explora
    impact: str                               # elo 3 — o que se consegue
    explanation: str                          # por que isso é um caminho
    asset_name: str | None = None             # ativo envolvido, se houver
    vulns: list[Vulnerability] = field(default_factory=list)  # achados que compõem a cadeia


def _module_of(v: Vulnerability) -> str:
    """Agrupa por módulo — mesma lógica usada em ai/anomaly_detector.py."""
    key = v.file_path or v.url or "desconhecido"
    parts = key.replace("\\", "/").split("/")
    return "/".join(parts[:2]) if len(parts) > 1 else key


def _worst_severity(vulns: list[Vulnerability]) -> str:
    for sev in ("critical", "high", "medium", "low", "info"):
        if any(v.severity.value == sev for v in vulns):
            return sev
    return "info"


def detect(vulns: list[Vulnerability],
           assets: dict[str, Asset] | None = None) -> list[AttackPath]:
    """Detecta caminhos de ataque. Totalmente determinístico — não depende de IA.
    Considera apenas vulnerabilidades em aberto (corrigidas/aceitas não formam
    caminho de risco ativo)."""
    assets = assets or {}
    vulns = [v for v in vulns if v.status.value == "open"]
    if not vulns:
        return []

    paths: list[AttackPath] = []
    paths.extend(_rule_a_dast_confirms_code(vulns))
    paths.extend(_rule_b_exposed_asset_secret(vulns, assets))
    paths.extend(_rule_c_iac_plus_secret(vulns, assets))
    paths.extend(_rule_d_critical_asset_sensitive(vulns, assets))

    paths.sort(key=lambda p: CHAIN_SEVERITY_ORDER.get(p.severity, 9))
    return paths


# ── Regra A: DAST + SAST/SCA no mesmo módulo ────────────────────────────────

def _rule_a_dast_confirms_code(vulns: list[Vulnerability]) -> list[AttackPath]:
    """Se o DAST achou algo explorável remotamente E existe falha de código no
    mesmo módulo, o caminho de fora até o código está evidenciado pelas duas
    pontas."""
    by_module: dict[str, list[Vulnerability]] = defaultdict(list)
    for v in vulns:
        by_module[_module_of(v)].append(v)

    paths = []
    for module, mod_vulns in by_module.items():
        dast = [v for v in mod_vulns if v.scan_type == ScanType.DAST]
        code = [v for v in mod_vulns if v.scan_type in (ScanType.SAST, ScanType.SCA)]
        if dast and code:
            envolvidos = dast + code
            paths.append(AttackPath(
                rule_id="A",
                severity=_worst_severity(envolvidos) if _worst_severity(envolvidos) in CHAIN_SEVERITY_ORDER else "medium",
                exposure=f"Alcançável remotamente ({dast[0].title[:45]})",
                vulnerability=f"{len(code)} falha(s) de código no mesmo módulo",
                impact=f"Comprometimento de {module}",
                explanation=(
                    f"O DAST confirmou que {module} responde a requisições externas, e o SAST/SCA "
                    f"encontrou falha de código no mesmo módulo. As duas pontas do caminho — o acesso "
                    f"externo e a falha explorável — foram evidenciadas por ferramentas diferentes."
                ),
                vulns=envolvidos,
            ))
    return paths


# ── Regra B: ativo internet-facing + segredo exposto ────────────────────────

def _rule_b_exposed_asset_secret(vulns: list[Vulnerability],
                                  assets: dict[str, Asset]) -> list[AttackPath]:
    """Segredo exposto num ativo acessível pela internet: credencial válida +
    porta de entrada aberta."""
    paths = []
    by_asset: dict[str, list[Vulnerability]] = defaultdict(list)
    for v in vulns:
        if v.asset_id:
            by_asset[v.asset_id].append(v)

    for asset_id, asset_vulns in by_asset.items():
        asset = assets.get(asset_id)
        if not asset or not asset.internet_facing:
            continue
        secrets = [v for v in asset_vulns if v.scan_type == ScanType.SECRETS]
        if not secrets:
            continue

        impacto = ("Acesso a dados sensíveis" if asset.contains_sensitive_data
                   else "Acesso não autorizado ao sistema")
        sev = "critical" if asset.contains_sensitive_data else "high"
        paths.append(AttackPath(
            rule_id="B",
            severity=sev,
            exposure=f"Ativo exposto à internet ({asset.label})",
            vulnerability=f"{len(secrets)} segredo(s) exposto(s) no código",
            impact=impacto,
            explanation=(
                f"O ativo \"{asset.label}\" está acessível pela internet e tem credencial exposta "
                f"no código. Um segredo válido dispensa a exploração de qualquer outra falha: "
                f"quem encontrar a credencial entra diretamente."
                + (" Como o ativo processa dados sensíveis, um acesso desses já configura risco de vazamento."
                   if asset.contains_sensitive_data else "")
            ),
            asset_name=asset.label,
            vulns=secrets,
        ))
    return paths


# ── Regra C: má configuração de IaC + segredo no mesmo ativo ────────────────

def _rule_c_iac_plus_secret(vulns: list[Vulnerability],
                             assets: dict[str, Asset]) -> list[AttackPath]:
    """Container/infra mal configurado (root, privileged) somado a segredo
    exposto: o segredo dá o acesso inicial, a má configuração amplia até o host."""
    paths = []
    by_asset: dict[str, list[Vulnerability]] = defaultdict(list)
    for v in vulns:
        key = v.asset_id or f"__module__{_module_of(v)}"
        by_asset[key].append(v)

    for key, group in by_asset.items():
        iac = [v for v in group if v.scan_type == ScanType.IAC]
        secrets = [v for v in group if v.scan_type == ScanType.SECRETS]
        if not (iac and secrets):
            continue

        asset = assets.get(key) if not key.startswith("__module__") else None
        escopo = asset.label if asset else key.replace("__module__", "")
        paths.append(AttackPath(
            rule_id="C",
            severity="high",
            exposure=f"{len(secrets)} segredo(s) exposto(s)",
            vulnerability=f"{len(iac)} má(s) configuração(ões) de infraestrutura",
            impact="Escalação de privilégio no container/host",
            explanation=(
                f"Em {escopo} há segredo exposto e infraestrutura mal configurada ao mesmo tempo. "
                f"O segredo dá o acesso inicial; a má configuração (execução como root, container "
                f"privilegiado ou rede do host) transforma esse acesso em controle mais amplo do "
                f"ambiente, em vez de ficar contido na aplicação."
            ),
            asset_name=asset.label if asset else None,
            vulns=iac + secrets,
        ))
    return paths


# ── Regra D: ativo crítico com dados sensíveis + achado grave ───────────────

def _rule_d_critical_asset_sensitive(vulns: list[Vulnerability],
                                      assets: dict[str, Asset]) -> list[AttackPath]:
    """Qualquer achado crítico/alto num ativo que é crítico E guarda dados
    sensíveis: caminho curto até o que mais importa."""
    paths = []
    by_asset: dict[str, list[Vulnerability]] = defaultdict(list)
    for v in vulns:
        if v.asset_id:
            by_asset[v.asset_id].append(v)

    for asset_id, asset_vulns in by_asset.items():
        asset = assets.get(asset_id)
        if not asset or not (asset.critical_asset and asset.contains_sensitive_data):
            continue
        graves = [v for v in asset_vulns if v.severity in (Severity.CRITICAL, Severity.HIGH)]
        if not graves:
            continue

        # Evita duplicar a leitura da regra B, que já cobre secrets em ativo exposto
        if asset.internet_facing and all(v.scan_type == ScanType.SECRETS for v in graves):
            continue

        paths.append(AttackPath(
            rule_id="D",
            severity="critical" if any(v.severity == Severity.CRITICAL for v in graves) else "high",
            exposure=f"Ativo crítico com dados sensíveis ({asset.label})",
            vulnerability=f"{len(graves)} vulnerabilidade(s) de severidade alta ou crítica",
            impact="Comprometimento de dados sensíveis em sistema crítico",
            explanation=(
                f"\"{asset.label}\" foi marcado como ativo crítico e guarda dados sensíveis, e "
                f"concentra {len(graves)} achado(s) de severidade alta ou crítica. Mesmo sem uma "
                f"cadeia técnica específica, a combinação de criticidade declarada e achados graves "
                f"coloca esse ativo no topo da fila de correção."
            ),
            asset_name=asset.label,
            vulns=graves,
        ))
    return paths
