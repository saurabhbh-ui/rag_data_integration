"""Core module for the ChunkImprover agent."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from langchain_openai import AzureChatOpenAI
from langgraph.graph import END, StateGraph

from .models import ChunkEvaluation, ChunkState, ImprovementRecord, ImprovementResult
from .strategies import (
    EvaluationStrategy,
    LLMEvaluationStrategy,
    LLMReconstructionStrategy,
    ReconstructionStrategy,
)


class ChunkImprover:
    """Agent for evaluating and improving document chunks.

    Uses LangGraph for workflow management and state tracking.
    """

    def __init__(
        self,
        llm: AzureChatOpenAI,
        evaluator: EvaluationStrategy | None = None,
        reconstructor: ReconstructionStrategy | None = None,
    ) -> None:
        """Initialize the chunk improver agent.

        Args:
            llm: the large language model to use
            evaluator: Strategy for chunk evaluation
            reconstructor: Strategy for chunk reconstruction

        """
        # Set up evaluator and reconstructor
        self.evaluator = (
            evaluator if evaluator is not None else LLMEvaluationStrategy(llm)
        )
        self.reconstructor = (
            reconstructor
            if reconstructor is not None
            else LLMReconstructionStrategy(llm)
        )

        # Build the workflow graph
        self.workflow = self._build_graph()

    # LangGraph node functions
    def _evaluate_chunk(self, state: dict[str, Any]) -> dict[str, Any]:
        """Evaluate the current chunk."""
        # Convert dict to Pydantic model for type safety
        state_model = ChunkState.model_validate(state)

        # Log the operation
        log_message = f"[Iteration {state_model.iteration}] Evaluating chunk"

        try:
            # Perform evaluation using the strategy
            evaluation = self.evaluator.evaluate(
                document=state_model.document,
                chunk=state_model.chunk,
            )

            # Update state with evaluation result and increment iteration
            state_model.evaluation = evaluation
            state_model.iteration += 1
            state_model.logs.append(log_message)

            # Convert back to dict for LangGraph
            return state_model.model_dump()

        except Exception as e:  # noqa: BLE001
            error_msg = f"Error evaluating chunk: {e}"

            # Create error evaluation
            error_evaluation = ChunkEvaluation(
                chunk_topic="Error during evaluation",
                error=str(e),
                quality_score=0.0,
                final_judgment={
                    "is_self_contained": False,
                    "critical_issues": ["Evaluation failed"],
                },
            )

            # Update state
            state_model.evaluation = error_evaluation
            state_model.iteration += 1
            state_model.logs.append(log_message)
            state_model.logs.append(f"ERROR: {error_msg}")

            # Convert back to dict for LangGraph
            return state_model.model_dump()

    def _decide_next_step(self, state: dict[str, Any]) -> tuple[dict[str, Any], str]:
        """Decide whether to continue improving or finish."""
        # Convert dict to Pydantic model
        state_model = ChunkState.model_validate(state)

        # Get evaluation metrics
        quality_score = state_model.evaluation.quality_score
        is_self_contained = state_model.evaluation.final_judgment.is_self_contained

        # Log the decision criteria
        log_message = (
            f"[Iteration {state_model.iteration}] Deciding next step: "
            f"quality={quality_score:.2f}, self_contained={is_self_contained}, "
            f"iteration={state_model.iteration}/{state_model.max_iterations}"
        )

        # Make decision
        if (
            quality_score >= state_model.quality_threshold and is_self_contained
        ) or state_model.iteration >= state_model.max_iterations:
            decision = "finish"
            reason = (
                "Target quality reached"
                if is_self_contained
                else "Maximum iterations reached"
            )
        else:
            decision = "improve"
            reason = "Quality still needs improvement"

        # Log the decision
        decision_log = (
            f"[Iteration {state_model.iteration}] Decision: {decision} ({reason})"
        )

        # Update logs
        state_model.logs.append(log_message)
        state_model.logs.append(decision_log)

        # Return updated state and decision
        return state_model.model_dump(), decision

    def _reconstruct_chunk(self, state: dict[str, Any]) -> dict[str, Any]:
        """Reconstruct the chunk based on evaluation."""
        # Convert dict to Pydantic model
        state_model = ChunkState.model_validate(state)

        # Log the operation
        log_message = f"[Iteration {state_model.iteration}] Reconstructing chunk"

        try:
            # Perform reconstruction using the strategy
            reconstruction = self.reconstructor.reconstruct(
                document=state_model.document,
                chunk=state_model.chunk,
                evaluation=state_model.evaluation,
            )

            # Create improvement record
            improvement = ImprovementRecord(
                iteration=state_model.iteration,
                quality_score_before=state_model.evaluation.quality_score,
                improvements_made=reconstruction.improvements_made,
                critical_issues=state_model.evaluation.final_judgment.critical_issues,
            )

            # Update state with new chunk and improvement history
            state_model.chunk = reconstruction.reconstructed_chunk
            state_model.improvements.append(improvement)
            state_model.chunk_versions.append(reconstruction.reconstructed_chunk)

            # Update logs
            state_model.logs.append(log_message)
            for imp in reconstruction.improvements_made:
                state_model.logs.append(f"Improvement: {imp}")

            # Convert back to dict for LangGraph
            return state_model.model_dump()

        except Exception as e:  # noqa: BLE001
            error_msg = f"Error reconstructing chunk: {e}"

            # Update logs with error
            state_model.logs.append(log_message)
            state_model.logs.append(f"ERROR: {error_msg}")

            # Convert back to dict for LangGraph
            return state_model.model_dump()

    def _finish(self, state: dict[str, Any]) -> dict[str, Any]:
        """Complete the improvement process and calculate final metrics."""
        # Convert dict to Pydantic model
        state_model = ChunkState.model_validate(state)

        # Log the operation
        log_message = (
            f"[Iteration {state_model.iteration}] Finishing improvement process"
        )

        # Calculate quality improvement
        initial_score = 0.0
        if state_model.improvements and len(state_model.improvements) > 0:
            initial_score = state_model.improvements[0].quality_score_before

        final_score = state_model.evaluation.quality_score
        state_model.quality_improvement = final_score - initial_score

        # Extract critical issues that were resolved
        if len(state_model.improvements) > 0:
            # Get issues from first evaluation
            initial_issues = state_model.improvements[0].critical_issues

            # Get current issues
            final_issues = state_model.evaluation.final_judgment.critical_issues

            # Find resolved issues
            state_model.critical_issues_resolved = [
                issue for issue in initial_issues if issue not in final_issues
            ]

        # Update state completion status
        state_model.complete = True

        # Update logs
        state_model.logs.append(log_message)
        state_model.logs.append(
            f"Quality improvement: {state_model.quality_improvement:.2f}",
        )

        # Convert back to dict for LangGraph
        return state_model.model_dump()

    def _build_graph(self) -> StateGraph:
        """Build the LangGraph workflow."""
        # Create the graph
        # Note: LangGraph now expects a Dict instead of a Pydantic model
        graph = StateGraph(dict)

        # Add nodes
        graph.add_node("evaluate", self._evaluate_chunk)
        graph.add_node("reconstruct", self._reconstruct_chunk)
        graph.add_node("finish", self._finish)

        # Set the entry point
        graph.set_entry_point("evaluate")

        # Add conditional edges
        graph.add_conditional_edges(
            "evaluate",
            lambda x: self._decide_next_step(x)[1],  # Extract only the decision
            {"improve": "reconstruct", "finish": "finish"},
        )

        # Add the edge from reconstruct back to evaluate to create the loop
        graph.add_edge("reconstruct", "evaluate")

        # Add the final edge to end the graph
        graph.add_edge("finish", END)

        # Compile the graph
        return graph.compile()

    def improve_chunk(
        self,
        document: str,
        chunk: str,
        max_iterations: int | None = 2,
        quality_threshold: float | None = 0.8,
        *,
        return_only_result: bool = False,
    ) -> ImprovementResult | str:
        """Improve a document chunk through iterative evaluation and reconstruction.

        Args:
            document: Full document text
            chunk: The chunk to improve
            max_iterations: Maximum number of improvement iterations
            quality_threshold: Target quality score (0-1)
            verbose: Whether to print verbose output during processing
            return_only_result: if true return onl;y the improved chunk

        Returns:
            ImprovementResult: The improvement results

        """
        # Initialize the state
        initial_state = ChunkState(
            document=document,
            chunk=chunk,
            original_chunk=chunk,
            evaluation=ChunkEvaluation(),
            improvements=[],
            chunk_versions=[chunk],
            iteration=0,
            max_iterations=max_iterations,
            quality_threshold=quality_threshold,
            complete=False,
            logs=[],
        )

        # Execute the workflow - convert to dict for LangGraph
        final_state_dict = self.workflow.invoke(initial_state.model_dump())

        # Convert back to Pydantic model for type safety
        final_state = ChunkState.model_validate(final_state_dict)

        if return_only_result:
            return final_state.chunk

        # Format results
        return ImprovementResult(
            original_chunk=final_state.original_chunk,
            improved_chunk=final_state.chunk,
            quality_score=final_state.evaluation.quality_score,
            is_self_contained=final_state.evaluation.final_judgment.is_self_contained,
            total_iterations=final_state.iteration,
            improvement_history=final_state.improvements,
            chunk_versions=final_state.chunk_versions,
            quality_improvement=final_state.quality_improvement,
            critical_issues_resolved=final_state.critical_issues_resolved,
            final_evaluation=final_state.evaluation,
            logs=final_state.logs,
        )
