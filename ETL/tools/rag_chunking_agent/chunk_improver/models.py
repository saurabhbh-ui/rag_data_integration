"""Models used along the tool."""

from __future__ import annotations

from pydantic import BaseModel, Field


class UnresolvedReference(BaseModel):
    """Model representing an unresolved reference in a chunk."""

    reference: str = Field(description="The reference text")
    missing_information: str = Field(description="What's needed to resolve it")


class StructuralIntegrity(BaseModel):
    """Model representing the structural integrity assessment."""

    has_structural_issues: bool = Field(default=False)
    boundary_issues: list[str] = Field(default_factory=list)
    missing_framing: list[str] = Field(default_factory=list)


class ContextualCompleteness(BaseModel):
    """Model representing the contextual completeness assessment."""

    is_complete: bool = Field(default=False)
    missing_context: list[str] = Field(default_factory=list)


class ReferenceResolution(BaseModel):
    """Model representing the reference resolution assessment."""

    unresolved_references: list[UnresolvedReference] = Field(default_factory=list)


class InformationPrerequisites(BaseModel):
    """Model representing the information prerequisites assessment."""

    prerequisites: list[str] = Field(default_factory=list)
    provided_in_chunk: bool = Field(default=False)


class FinalJudgment(BaseModel):
    """Model representing the final evaluation judgment."""

    is_self_contained: bool = Field(default=False)
    critical_issues: list[str] = Field(default_factory=list)
    improvement_recommendations: list[str] = Field(default_factory=list)


class ChunkEvaluation(BaseModel):
    """Model representing a complete chunk evaluation."""

    chunk_topic: str = Field(
        default="",
        description="Brief description of what this chunk contains",
    )
    contextual_completeness: ContextualCompleteness = Field(
        default_factory=ContextualCompleteness,
    )
    structural_integrity: StructuralIntegrity = Field(
        default_factory=StructuralIntegrity,
    )
    reference_resolution: ReferenceResolution = Field(
        default_factory=ReferenceResolution,
    )
    information_prerequisites: InformationPrerequisites = Field(
        default_factory=InformationPrerequisites,
    )
    final_judgment: FinalJudgment = Field(default_factory=FinalJudgment)
    quality_score: float = Field(default=0.0)
    error: str | None = Field(default=None)


class ChunkReconstruction(BaseModel):
    """Model representing a chunk reconstruction result."""

    reconstructed_chunk: str = Field(description="The improved chunk text")
    improvements_made: list[str] = Field(default_factory=list)
    reasoning: str = Field(description="Explanation of the reconstruction approach")


class ImprovementRecord(BaseModel):
    """Model representing an improvement made to a chunk."""

    iteration: int = Field(
        description="Iteration number when this improvement was made",
    )
    quality_score_before: float = Field(
        description="Quality score before the improvement",
    )
    improvements_made: list[str] = Field(default_factory=list)
    critical_issues: list[str] = Field(default_factory=list)


class ChunkState(BaseModel):
    """Model representing the complete state of a chunk improvement process."""

    # Document information
    document: str = Field(description="Full document text")
    chunk: str = Field(description="Current version of the chunk")
    original_chunk: str = Field(description="Original unmodified chunk")

    # Evaluation and improvements
    evaluation: ChunkEvaluation = Field(default_factory=ChunkEvaluation)
    improvements: list[ImprovementRecord] = Field(default_factory=list)
    chunk_versions: list[str] = Field(default_factory=list)

    # Control parameters
    iteration: int = Field(default=0, description="Current iteration number")
    max_iterations: int = Field(default=5, description="Maximum iterations to attempt")
    quality_threshold: float = Field(default=0.8, description="Target quality score")
    complete: bool = Field(default=False, description="Flag to indicate completion")

    # Results
    quality_improvement: float = Field(default=0.0)
    critical_issues_resolved: list[str] = Field(default_factory=list)

    # Debugging
    logs: list[str] = Field(default_factory=list)


class ImprovementResult(BaseModel):
    """Model representing the result of a chunk improvement process."""

    original_chunk: str
    improved_chunk: str
    quality_score: float
    is_self_contained: bool
    total_iterations: int
    improvement_history: list[ImprovementRecord]
    chunk_versions: list[str]
    quality_improvement: float
    critical_issues_resolved: list[str]
    final_evaluation: ChunkEvaluation
    logs: list[str]
