"""Strategies to be used in the chunk improvements."""

from abc import ABC, abstractmethod
from pathlib import Path

from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import AzureChatOpenAI

from .models import ChunkEvaluation, ChunkReconstruction


def load_prompt(filename: str) -> str:
    """Load prompt template from file."""
    base_dir = Path(__file__).parent.resolve()
    prompt_path = base_dir / "prompts" / filename
    try:
        with Path(prompt_path).open(encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        # If file doesn't exist yet, return empty string
        # In production, you'd want to handle this differently
        return ""


class EvaluationStrategy(ABC):
    """Abstract base class for chunk evaluation strategies."""

    @abstractmethod
    def evaluate(self, document: str, chunk: str) -> ChunkEvaluation:
        """Evaluate a chunk and return evaluation results.

        Args:
            document: The full document text
            chunk: The chunk to evaluate

        Returns:
            ChunkEvaluation: Evaluation results

        """


class ReconstructionStrategy(ABC):
    """Abstract base class for chunk reconstruction strategies."""

    @abstractmethod
    def reconstruct(
        self,
        document: str,
        chunk: str,
        evaluation: ChunkEvaluation,
    ) -> ChunkReconstruction:
        """Reconstruct a chunk based on evaluation results.

        Args:
            document: The full document text
            chunk: The chunk to reconstruct
            evaluation: Evaluation results

        Returns:
            ChunkReconstruction: Reconstruction results

        """


class LLMEvaluationStrategy(EvaluationStrategy):
    """Evaluation strategy using LLM."""

    def __init__(self, llm: AzureChatOpenAI) -> None:
        """Initialize the LLM evaluation strategy."""
        # Set up LLM
        self.llm = llm

        # Load evaluation prompt
        prompt_template = load_prompt("evaluation_prompt.txt")
        self.evaluation_prompt = ChatPromptTemplate.from_template(prompt_template)

        # Create chain
        self.evaluation_chain = self.evaluation_prompt | self.llm | JsonOutputParser()

    def evaluate(self, document: str, chunk: str) -> ChunkEvaluation:
        """Evaluate a chunk using LLM."""
        try:
            # Invoke the chain
            result = self.evaluation_chain.invoke(
                {"document": document, "chunk": chunk},
            )

            # Create evaluation model
            evaluation = ChunkEvaluation.model_validate(result)

            # Calculate quality score
            self._calculate_quality_score(evaluation)

            return evaluation  # noqa: TRY300

        except Exception as e:  # noqa: BLE001
            # Handle errors
            return ChunkEvaluation(
                chunk_topic="Error during evaluation",
                error=str(e),
                quality_score=0.0,
                final_judgment={
                    "is_self_contained": False,
                    "critical_issues": ["Evaluation failed"],
                },
            )

    def _calculate_quality_score(self, evaluation: ChunkEvaluation) -> None:
        """Calculate quality score based on evaluation results."""
        # Get key metrics
        is_self_contained = evaluation.final_judgment.is_self_contained
        critical_issues = evaluation.final_judgment.critical_issues
        unresolved_refs = evaluation.reference_resolution.unresolved_references

        # Calculate score based on severity of issues
        base_score = 1.0 if is_self_contained else 0.5
        issue_penalty = min(0.4, len(critical_issues) * 0.1)
        ref_penalty = min(0.3, len(unresolved_refs) * 0.05)

        # Calculate final score
        evaluation.quality_score = max(0.0, base_score - issue_penalty - ref_penalty)


class LLMReconstructionStrategy(ReconstructionStrategy):
    """Reconstruction strategy using LLM."""

    def __init__(self, llm: AzureChatOpenAI) -> None:
        """Initialize the LLM reconstruction strategy."""
        # Set up LLM
        self.llm = llm

        # Load reconstruction prompt
        prompt_template = load_prompt("reconstruction_prompt.txt")
        self.reconstruction_prompt = ChatPromptTemplate.from_template(prompt_template)

        # Create chain
        self.reconstruction_chain = (
            self.reconstruction_prompt | self.llm | JsonOutputParser()
        )

    def reconstruct(
        self,
        document: str,
        chunk: str,
        evaluation: ChunkEvaluation,
    ) -> ChunkReconstruction:
        """Reconstruct a chunk based on evaluation results."""
        try:
            # Extract specific issues to address
            boundary_issues = evaluation.structural_integrity.boundary_issues
            missing_context = evaluation.contextual_completeness.missing_context

            unresolved_refs = [
                f"'{ref.reference}': {ref.missing_information}"
                for ref in evaluation.reference_resolution.unresolved_references
            ]

            missing_prereqs = evaluation.information_prerequisites.prerequisites
            recommendations = evaluation.final_judgment.improvement_recommendations

            # Invoke the chain
            result = self.reconstruction_chain.invoke(
                {
                    "document": document,
                    "chunk": chunk,
                    "boundary_issues": boundary_issues,
                    "missing_context": missing_context,
                    "unresolved_references": unresolved_refs,
                    "missing_prerequisites": missing_prereqs,
                    "recommendations": recommendations,
                },
            )

            # Create reconstruction model
            return ChunkReconstruction.model_validate(result)

        except Exception as e:  # noqa: BLE001
            # Handle errors
            return ChunkReconstruction(
                reconstructed_chunk=chunk,
                improvements_made=["Error occurred during reconstruction"],
                reasoning=f"Error: {e!s}",
            )
