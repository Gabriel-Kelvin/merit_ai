from __future__ import annotations

from typing import Literal, TypedDict

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph

from app.assessment.evaluator import Evaluator
from app.assessment.models import (
    AdaptiveDecision,
    AssessmentSession,
    Question,
    ResponseEvaluation,
)
from app.assessment.questioning import QuestionPlanner, QuestionStrategy


class AssessmentGraphState(TypedDict, total=False):
    event: Literal["start", "answer"]
    session: AssessmentSession
    evaluation: ResponseEvaluation | None
    strategy: QuestionStrategy | None
    next_question: Question | None
    decision: AdaptiveDecision | None
    route: Literal["generate", "complete"]


class LangGraphAssessmentController:
    """Explicit, checkpointed state machine for adaptive assessment transitions."""

    def __init__(self, evaluator: Evaluator, planner: QuestionPlanner | None = None) -> None:
        self.evaluator = evaluator
        self.planner = planner or QuestionPlanner()
        builder = StateGraph(AssessmentGraphState)
        builder.add_node("plan_capabilities", self._plan_capabilities)
        builder.add_node("opening_question", self._opening_question)
        builder.add_node("update_memory", self._update_memory)
        builder.add_node("select_strategy", self._select_strategy)
        builder.add_node("generate_question", self._generate_question)
        builder.add_node("complete_assessment", self._complete_assessment)
        builder.add_conditional_edges(
            START,
            self._entry_route,
            {"start": "plan_capabilities", "answer": "update_memory"},
        )
        builder.add_edge("plan_capabilities", "opening_question")
        builder.add_edge("opening_question", END)
        builder.add_edge("update_memory", "select_strategy")
        builder.add_conditional_edges(
            "select_strategy",
            self._next_route,
            {"generate": "generate_question", "complete": "complete_assessment"},
        )
        builder.add_edge("generate_question", END)
        builder.add_edge("complete_assessment", END)
        self.graph = builder.compile(checkpointer=InMemorySaver())

    def initialize(self, session: AssessmentSession) -> Question:
        state = self.graph.invoke(
            {
                "event": "start",
                "session": session,
                "evaluation": None,
                "strategy": None,
                "next_question": None,
                "decision": None,
            },
            config={"configurable": {"thread_id": str(session.id)}},
        )
        return state["next_question"]

    def advance(
        self, session: AssessmentSession, evaluation: ResponseEvaluation
    ) -> tuple[Question | None, AdaptiveDecision]:
        state = self.graph.invoke(
            {
                "event": "answer",
                "session": session,
                "evaluation": evaluation,
                "strategy": None,
                "next_question": None,
                "decision": None,
            },
            config={"configurable": {"thread_id": str(session.id)}},
        )
        return state.get("next_question"), state["decision"]

    @staticmethod
    def _entry_route(state: AssessmentGraphState) -> Literal["start", "answer"]:
        return state["event"]

    def _plan_capabilities(self, state: AssessmentGraphState) -> AssessmentGraphState:
        session = state["session"]
        self.planner.plan(session, self.evaluator)
        session.memory.last_transition = "capabilities_planned"
        return {"session": session}

    def _opening_question(self, state: AssessmentGraphState) -> AssessmentGraphState:
        session = state["session"]
        question = self.planner.opening_question(session)
        session.memory.last_transition = "opening_question"
        return {"session": session, "next_question": question}

    def _update_memory(self, state: AssessmentGraphState) -> AssessmentGraphState:
        session = state["session"]
        self.planner.update_memory(session, state["evaluation"])
        return {"session": session}

    def _select_strategy(self, state: AssessmentGraphState) -> AssessmentGraphState:
        session = state["session"]
        strategy = self.planner.choose_strategy(session, state["evaluation"])
        route: Literal["generate", "complete"] = "generate" if strategy else "complete"
        session.memory.last_transition = route
        return {"session": session, "strategy": strategy, "route": route}

    @staticmethod
    def _next_route(state: AssessmentGraphState) -> Literal["generate", "complete"]:
        return state["route"]

    def _generate_question(self, state: AssessmentGraphState) -> AssessmentGraphState:
        session = state["session"]
        strategy = state["strategy"]
        question = self.planner.generate(session, self.evaluator, strategy)
        session.memory.last_transition = f"question_generated:{strategy.area.value}"
        return {
            "session": session,
            "next_question": question,
            "decision": strategy.decision,
        }

    def _complete_assessment(self, state: AssessmentGraphState) -> AssessmentGraphState:
        session = state["session"]
        session.memory.last_transition = "complete"
        return {
            "session": session,
            "next_question": None,
            "decision": self.planner.complete(
                "The evidence ceiling, coverage goals, or 20-question limit has been reached."
            ),
        }
