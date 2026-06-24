"""`GuardrailSuite`: casos-armadilha do Anexo B sobre o pipeline real.

Executa os casos críticos do PRD (G-01, G-03, G-05, G-06, G-07/G-08) e verifica a
camada **determinística** (retrieval + montagem de prompt): grounding presente,
conflito detectado com alerta, abstenção acionada. A camada **não-determinística**
(o texto gerado) é avaliada à parte por `llm_judge` (rubrica), reconhecendo que a
geração varia. A separação segue a nota do `references/guardrails.md`: o que é
determinístico vira asserção direta; o que é geração vira grau de rubrica.

`run` é puro (CQS): consulta retriever/assembler e devolve os desfechos.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from enum import Enum

from ..interfaces import PromptAssembler, Retriever
from ..models import AssembledPrompt, RetrievalBundle

__all__ = [
    "GuardrailKind",
    "GuardrailCase",
    "GuardrailOutcome",
    "GuardrailSuite",
    "GUARDRAIL_CASES",
    "ABSTAIN_OPERATING_SCORE",
]

# Acima do maior score observado para perguntas fora da base (~0.54 com o modelo
# anglófono); calibra a abstenção (G-03). Ver evidência 1.3 para a análise do
# trade-off recall × abstenção sob esse modelo.
ABSTAIN_OPERATING_SCORE = 0.55
# Grounding/conflito medem cobertura no top-N independentemente do threshold —
# o objetivo é "o documento certo foi recuperado?", não filtrar por score.
_COVERAGE_MIN_SCORE = 0.0
_GROUNDED_TOP_K = 5
_CONFLICT_TOP_K = 10
_PROMPT_TOKEN_BUDGET = 8_000
_CONFLICT_ALERT_MARKER = "DIVERGÊNCIA"
_ABSTENTION_MARKER = "Não encontrei informação"


class GuardrailKind(str, Enum):
    """Como o caso é verificado na camada determinística."""

    GROUNDED = "grounded"
    CONFLICT = "conflict"
    ABSTAIN = "abstain"


@dataclass(frozen=True)
class GuardrailCase:
    """Caso-armadilha: pergunta + comportamento esperado + guardrail associado."""

    name: str
    guardrail: str
    question: str
    kind: GuardrailKind
    expected_doc_ids: frozenset[str] = field(default_factory=frozenset)
    critical: bool = False


@dataclass(frozen=True)
class GuardrailOutcome:
    """Resultado determinístico de um caso: passou ou não, com o detalhe medido."""

    case: GuardrailCase
    passed: bool
    detail: dict[str, object]


# Casos-armadilha do Anexo B / PRD. Os 10 fora-da-base exercem o G-03 (≥9/10).
GUARDRAIL_CASES: tuple[GuardrailCase, ...] = (
    GuardrailCase("platinum", "G-06", "Qual o SLA do cliente Platinum?",
                  GuardrailKind.GROUNDED, frozenset({"SLA-2024"}), critical=True),
    GuardrailCase("carga_perigosa", "G-05", "Posso devolver carga perigosa?",
                  GuardrailKind.GROUNDED, frozenset({"POL-001"}), critical=True),
    GuardrailCase("proc_042_conflito", "G-07/G-08",
                  "Qual o multiplicador regional Sul do PROC-042?",
                  GuardrailKind.CONFLICT,
                  frozenset({"PROC-042-v1", "PROC-042-v2"}), critical=True),
    GuardrailCase("citacao", "G-01", "Qual o prazo de devolução de mercadorias?",
                  GuardrailKind.GROUNDED, frozenset({"POL-001"})),
    *(
        GuardrailCase(f"fora_da_base_{index}", "G-03", question, GuardrailKind.ABSTAIN)
        for index, question in enumerate(
            (
                "qual a capital da França",
                "como faço um bolo de chocolate",
                "qual o horário de funcionamento da loja",
                "quem ganhou a copa do mundo de 2022",
                "qual a previsão do tempo para amanhã",
                "como configurar uma impressora wifi",
                "qual o telefone do presidente",
                "o que é fotossíntese",
                "quanto custa um carro novo",
                "qual o melhor restaurante da cidade",
            ),
            start=1,
        )
    ),
)


class GuardrailSuite:
    """Roda os casos-armadilha sobre o pipeline real e devolve os desfechos."""

    def __init__(
        self,
        retriever: Retriever,
        assembler: PromptAssembler,
        abstain_min_score: float = ABSTAIN_OPERATING_SCORE,
    ) -> None:
        self._retriever = retriever
        self._assembler = assembler
        self._abstain_min_score = abstain_min_score

    def run(self, cases: Sequence[GuardrailCase] = GUARDRAIL_CASES) -> list[GuardrailOutcome]:
        return [self._check(case) for case in cases]

    def _check(self, case: GuardrailCase) -> GuardrailOutcome:
        if case.kind is GuardrailKind.ABSTAIN:
            return self._check_abstain(case)
        if case.kind is GuardrailKind.CONFLICT:
            return self._check_conflict(case)
        return self._check_grounded(case)

    def _check_grounded(self, case: GuardrailCase) -> GuardrailOutcome:
        bundle = self._retriever.retrieve(
            case.question, top_k=_GROUNDED_TOP_K, min_score=_COVERAGE_MIN_SCORE
        )
        retrieved = self._doc_ids(bundle)
        passed = case.expected_doc_ids <= set(retrieved)
        return GuardrailOutcome(
            case=case,
            passed=passed,
            detail={"retrieved_doc_ids": retrieved, "expected": sorted(case.expected_doc_ids)},
        )

    def _check_conflict(self, case: GuardrailCase) -> GuardrailOutcome:
        bundle = self._retriever.retrieve(
            case.question, top_k=_CONFLICT_TOP_K, min_score=_COVERAGE_MIN_SCORE
        )
        assembled = self._assemble(case.question, bundle)
        retrieved = self._doc_ids(bundle)
        alert_present = self._has_marker(assembled, _CONFLICT_ALERT_MARKER)
        passed = (
            bool(bundle.conflicts)
            and alert_present
            and case.expected_doc_ids <= set(retrieved)
        )
        return GuardrailOutcome(
            case=case,
            passed=passed,
            detail={
                "conflicts": sorted(group.doc_id for group in bundle.conflicts),
                "alert_present": alert_present,
                "retrieved_doc_ids": retrieved,
            },
        )

    def _check_abstain(self, case: GuardrailCase) -> GuardrailOutcome:
        bundle = self._retriever.retrieve(
            case.question, top_k=_GROUNDED_TOP_K, min_score=self._abstain_min_score
        )
        assembled = self._assemble(case.question, bundle)
        abstained = bundle.below_threshold and self._has_marker(assembled, _ABSTENTION_MARKER)
        return GuardrailOutcome(
            case=case,
            passed=abstained,
            detail={"below_threshold": bundle.below_threshold},
        )

    def _assemble(self, question: str, bundle: RetrievalBundle) -> AssembledPrompt:
        return self._assembler.assemble(question, bundle, token_budget=_PROMPT_TOKEN_BUDGET)

    def _has_marker(self, assembled: AssembledPrompt, marker: str) -> bool:
        return any(marker in block for block in assembled.context_blocks)

    def _doc_ids(self, bundle: RetrievalBundle) -> list[str]:
        ordered: list[str] = []
        for result in bundle.results:
            if result.chunk.metadata.doc_id not in ordered:
                ordered.append(result.chunk.metadata.doc_id)
        return ordered
