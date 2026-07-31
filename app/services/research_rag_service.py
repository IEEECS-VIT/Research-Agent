import json
import logging
from typing import Any

from app.core.config import get_settings
from app.schemas.chat import Source

logger = logging.getLogger(__name__)
settings = get_settings()

try:
    from GraphEngine.analytics.clustering import (
        find_contradiction_clusters,
        find_low_confidence_regions,
        find_verifier_failure_patterns,
    )
    from GraphEngine.analytics.consensus import (
        consensus_breakdown,
        find_consensus_papers,
        find_unstable_claims,
    )
    from GraphEngine.analytics.graph_builder import build_graph_from_sqlite
    from GraphEngine.analytics.graph_summary import graph_summary
    from GraphEngine.analytics.traversal import (
        find_claim_neighbors,
        find_review_required_claims,
        get_high_confidence_contradictions,
    )
    from GraphEngine.engines.retrieval_engine import retrieve_chunks

    GRAPH_ENGINE_AVAILABLE = True
except ImportError as e:
    GRAPH_ENGINE_AVAILABLE = False
    logger.warning("GraphEngine not fully available: %s", e)

try:
    from google import genai
    from google.genai import types

    LLM_AVAILABLE = True
except ImportError:
    LLM_AVAILABLE = False


INTENT_CLASSIFICATION_PROMPT = """Classify the user's research question into exactly one intent category.

Categories:
- graph_contradictions: Questions about contradictions, disagreements, conflicting claims in the knowledge graph
- graph_consensus: Questions about overall agreement, consensus, what most papers agree on
- graph_claim_reliability: Questions about reliability, trustworthiness of specific claims or papers
- graph_summary: Questions asking for a summary or overview of the entire knowledge graph
- literature_search: Questions asking to find papers, evidence, or support for a specific claim or topic
- graph_explore: Questions about relationships between specific papers, claims, or findings
- general: Questions that don't fit the above or are conversational

Return ONLY a JSON object with key "intent" and value being one of the above strings.

User question: {question}"""


LITERATURE_SEARCH_PROMPT = """You are a research analysis assistant. Based on the retrieved document chunks and graph data below, answer the user's question.

Provide a literature-review-style answer that:
1. Directly addresses the user's question
2. Cites specific sources from the provided evidence
3. Mentions confidence scores and relation types where relevant
4. Highlights any contradictions or disagreements found

Retrieved Evidence:
{evidence}

Graph Context:
{graph_context}

User Question: {question}

Return a JSON object with:
{{
  "answer": "Your detailed literature-review-style answer here",
  "sources": [
    {{
      "doc_id": "...",
      "filename": "...",
      "section": "...",
      "text": "relevant excerpt",
      "confidence": 0.0,
      "relation_type": "SUPPORT|CONTRADICT|MIXED"
    }}
  ]
}}"""


GRAPH_ANSWER_PROMPT = """You are a research analysis assistant. Based on the following knowledge graph analysis data, answer the user's question.

Present the information clearly with:
1. Direct answer to the question
2. Specific data points and evidence from the graph
3. Confidence assessments where available
4. Notable patterns or anomalies

Graph Data:
{graph_data}

User Question: {question}

Return a JSON object with:
{{
  "answer": "Your detailed answer here with specific numbers and findings",
  "sources": [
    {{
      "doc_id": "...",
      "filename": "...",
      "section": "...",
      "text": "relevant excerpt",
      "confidence": 0.0,
      "relation_type": "SUPPORT|CONTRADICT|MIXED"
    }}
  ]
}}"""


GENERAL_CHAT_PROMPT = """You are a helpful research analysis assistant. Answer the user's question conversationally.

You have access to a knowledge graph of research papers and claims with:
- Support/contradiction relationships between claims
- Confidence scores for each relationship
- Trust and reliability metrics for claims and papers
- Document chunk embeddings for semantic search

User Question: {question}

Return a JSON object with:
{{
  "answer": "Your helpful response here",
  "sources": []
}}"""


class RAGAgent:
    def __init__(self):
        self._graph = None
        self._llm_client = None

    def _get_llm_client(self) -> Any:
        if self._llm_client is None and LLM_AVAILABLE:
            self._llm_client = genai.Client(api_key=settings.gemini_api_key)
        return self._llm_client

    def _get_graph(self) -> Any:
        if self._graph is None and GRAPH_ENGINE_AVAILABLE:
            try:
                self._graph = build_graph_from_sqlite()
            except Exception as e:
                logger.warning("Failed to build graph: %s", e)
        return self._graph

    def invalidate_graph(self):
        self._graph = None

    async def classify_intent(self, question: str) -> str:
        if not LLM_AVAILABLE:
            return self._rule_based_intent(question)

        client = self._get_llm_client()
        if not client:
            return self._rule_based_intent(question)

        prompt = INTENT_CLASSIFICATION_PROMPT.format(question=question)
        try:
            response = await client.aio.models.generate_content(
                model=settings.gemini_model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0.1,
                    response_mime_type="application/json",
                ),
            )
            result = json.loads(response.text or "{}")
            intent = result.get("intent", "general")
            valid_intents = {
                "graph_contradictions",
                "graph_consensus",
                "graph_claim_reliability",
                "graph_summary",
                "literature_search",
                "graph_explore",
                "general",
            }
            return intent if intent in valid_intents else "general"
        except Exception as e:
            logger.warning("Intent classification failed: %s", e)
            return self._rule_based_intent(question)

    def _rule_based_intent(self, question: str) -> str:
        q = question.lower()
        if any(w in q for w in ["contradict", "disagree", "conflict", "discrep", "inconsisten"]):
            return "graph_contradictions"
        if any(w in q for w in ["consensus", "agree", "common ground", "most paper"]):
            return "graph_consensus"
        if any(w in q for w in ["reliable", "trust", "confidence", "how strong", "how sure"]):
            return "graph_claim_reliability"
        if any(
            w in q
            for w in ["summar", "overview", "what is in", "describe the graph", "tell me about"]
        ):
            return "graph_summary"
        if any(
            w in q
            for w in [
                "find",
                "search",
                "papers about",
                "evidence",
                "support",
                "claim that",
                "causes",
            ]
        ):
            return "literature_search"
        if any(w in q for w in ["relation", "between", "compare", "link", "connect"]):
            return "graph_explore"
        return "general"

    async def answer_question(
        self, question: str, user_id: str | None = None
    ) -> tuple[str, list[Source]]:
        intent = await self.classify_intent(question)
        logger.info("Classified intent: %s for question: %s", intent, question[:100])

        if intent == "literature_search":
            return await self._literature_search(question)
        elif intent in (
            "graph_contradictions",
            "graph_consensus",
            "graph_claim_reliability",
            "graph_summary",
            "graph_explore",
        ):
            return await self._graph_query(question, intent)
        else:
            return await self._general_chat(question)

    async def _literature_search(self, question: str) -> tuple[str, list[Source]]:
        graph_context = ""
        evidence_chunks: list[dict[str, Any]] = []
        sources: list[Source] = []

        if GRAPH_ENGINE_AVAILABLE:
            try:
                graph = self._get_graph()
                if graph:
                    summary = graph_summary(graph)
                    graph_context = json.dumps(summary, indent=2)
            except Exception as e:
                logger.warning("Graph summary failed: %s", e)

        if LLM_AVAILABLE:
            try:
                client = self._get_llm_client()
                if client:
                    response = await client.aio.models.embed_content(
                        model=settings.gemini_embedding_model,
                        contents=question,
                    )
                    if response.embeddings:
                        embedding = [float(v) for v in response.embeddings[0].values]

                        try:
                            chroma_results = retrieve_chunks(
                                query_embedding=embedding,
                                n_results=8,
                            )
                            if chroma_results and chroma_results.get("documents"):
                                for i, doc_list in enumerate(chroma_results["documents"]):
                                    for j, text in enumerate(doc_list):
                                        meta = {}
                                        if (
                                            chroma_results.get("metadatas")
                                            and len(chroma_results["metadatas"]) > i
                                        ):
                                            meta = (
                                                chroma_results["metadatas"][i][j]
                                                if j < len(chroma_results["metadatas"][i])
                                                else {}
                                            )

                                        distance = None
                                        if (
                                            chroma_results.get("distances")
                                            and len(chroma_results["distances"]) > i
                                        ):
                                            distance = (
                                                chroma_results["distances"][i][j]
                                                if j < len(chroma_results["distances"][i])
                                                else None
                                            )

                                        confidence = max(
                                            0.0, min(1.0, 1.0 - (distance or 0.0) / 2.0)
                                        )

                                        evidence_chunks.append(
                                            {
                                                "text": text[:500],
                                                "filename": meta.get("filename", "unknown"),
                                                "section": meta.get("section_name", ""),
                                                "doc_id": meta.get("doc_id", ""),
                                                "confidence": round(confidence, 3),
                                                "source_type": meta.get("source_type", ""),
                                            }
                                        )

                                        sources.append(
                                            Source(
                                                doc_id=meta.get("doc_id", ""),
                                                filename=meta.get("filename", "unknown"),
                                                section=meta.get("section_name", ""),
                                                text=text[:300],
                                                confidence=round(confidence, 3),
                                            )
                                        )

                                        if len(sources) >= 8:
                                            break
                        except Exception as e:
                            logger.warning("ChromaDB retrieval failed: %s", e)
            except Exception as e:
                logger.warning("Literature search failed: %s", e)

        if GRAPH_ENGINE_AVAILABLE:
            try:
                graph = self._get_graph()
                if graph and graph.number_of_edges() > 0:
                    consensus = consensus_breakdown(graph)
                    for rel_type, count in consensus.items():
                        evidence_chunks.append(
                            {
                                "text": f"Graph contains {count} edges with relation type: {rel_type}",
                                "filename": "knowledge_graph",
                                "section": "graph_consensus",
                                "doc_id": "graph",
                                "confidence": 1.0,
                                "source_type": "graph",
                            }
                        )
            except Exception as e:
                logger.warning("Graph query failed: %s", e)

        if LLM_AVAILABLE and evidence_chunks:
            client = self._get_llm_client()
            if client:
                evidence_text = "\n\n".join(
                    f"[{i + 1}] From: {e['filename']} (Section: {e['section']}, Confidence: {e['confidence']})\n{e['text']}"
                    for i, e in enumerate(evidence_chunks)
                )
                prompt = LITERATURE_SEARCH_PROMPT.format(
                    evidence=evidence_text,
                    graph_context=graph_context or "No graph data available.",
                    question=question,
                )
                try:
                    response = await client.aio.models.generate_content(
                        model=settings.gemini_model,
                        contents=prompt,
                        config=types.GenerateContentConfig(
                            temperature=0.3,
                            response_mime_type="application/json",
                        ),
                    )
                    result = json.loads(response.text or "{}")
                    answer = result.get(
                        "answer",
                        "I couldn't generate a complete answer based on the available evidence.",
                    )
                    cited_sources = result.get("sources", [])
                    for cs in cited_sources:
                        sources.append(
                            Source(
                                doc_id=cs.get("doc_id", ""),
                                filename=cs.get("filename", ""),
                                section=cs.get("section", ""),
                                text=cs.get("text", "")[:300],
                                confidence=cs.get("confidence"),
                                relation_type=cs.get("relation_type"),
                            )
                        )
                    return answer, sources
                except Exception as e:
                    logger.warning("LLM answer generation failed: %s", e)

        evidence_summary = (
            "\n".join(
                f"- {e['filename']}: {e.get('text', '')[:100]}..." for e in evidence_chunks[:5]
            )  # type: ignore
            if evidence_chunks
            else "No specific evidence found."
        )
        answer = f"""Based on the available research data, here is what I found:

{evidence_summary}

{f"Retrieved from {len(evidence_chunks)} document chunks and graph data." if evidence_chunks else "The knowledge graph and vector database did not return specific results for this query. Try rephrasing your question or uploading more documents."}"""
        return answer, sources

    async def _graph_query(self, question: str, intent: str) -> tuple[str, list[Source]]:
        sources: list[Source] = []
        graph_data: dict[str, Any] = {}
        graph = self._get_graph() if GRAPH_ENGINE_AVAILABLE else None

        if graph is None:
            answer = "The knowledge graph is currently empty or unavailable. Upload and analyze documents first to build the graph."
            return answer, sources

        try:
            if intent == "graph_contradictions":
                contradictions = get_high_confidence_contradictions(graph)
                clusters = find_contradiction_clusters(graph)
                graph_data = {
                    "total_contradictions": len(contradictions),
                    "contradiction_clusters": len(clusters),
                    "contradictions": [
                        {
                            "source": c["source_id"],
                            "target": c["target_id"],
                            "support_score": c.get("support_score"),
                            "contradiction_score": c.get("contradiction_score"),
                            "confidence": c.get("confidence"),
                        }
                        for c in contradictions[:20]
                    ],
                    "clusters": [{"nodes": c} for c in clusters[:10]],
                }
                for c in contradictions[:10]:
                    sources.append(
                        Source(
                            doc_id=c["source_id"],
                            text=f"Contradiction edge: {c['source_id']} <-> {c['target_id']} (confidence: {c.get('confidence', 'N/A')})",
                            confidence=c.get("confidence"),
                            relation_type="CONTRADICT",
                        )
                    )

            elif intent == "graph_consensus":
                consensus = consensus_breakdown(graph)
                consensus_papers = find_consensus_papers(graph)
                graph_data = {
                    "relation_breakdown": consensus,
                    "consensus_papers": consensus_papers[:20],
                    "total_edges": graph.number_of_edges(),
                    "total_nodes": graph.number_of_nodes(),
                }
                for cp in consensus_papers[:5]:
                    sources.append(
                        Source(
                            doc_id=cp["paper_id"],
                            text=f"Paper {cp['paper_id']} has trust score: {cp['trust_score']:.2f}",
                            confidence=cp["trust_score"],
                            relation_type="SUPPORT",
                        )
                    )

            elif intent == "graph_claim_reliability":
                unstable = find_unstable_claims(graph)
                summary = graph_summary(graph)
                graph_data = {
                    "unstable_claims": unstable[:20],
                    "graph_summary": summary,
                }
                for uc in unstable[:5]:
                    sources.append(
                        Source(
                            doc_id=uc["claim_id"],
                            text=f"Claim {uc['claim_id']} reliability: {uc.get('reliability', 'N/A'):.2f}",
                            confidence=uc.get("reliability"),
                            relation_type="MIXED",
                        )
                    )

            elif intent == "graph_summary":
                summary = graph_summary(graph)
                failures = find_verifier_failure_patterns(graph)
                low_conf_regions = find_low_confidence_regions(graph)
                graph_data = {
                    "summary": summary,
                    "verifier_failures": failures,
                    "low_confidence_regions": low_conf_regions,
                }
                sources.append(
                    Source(
                        doc_id="graph",
                        text=f"Graph summary: {summary['total_nodes']} nodes, {summary['total_edges']} edges, {summary['contradiction_count']} contradictions",
                        confidence=summary.get("average_confidence"),
                    )
                )

            elif intent == "graph_explore":
                q = question.lower()
                paper_terms = [w for w in q.split() if len(w) > 3]
                found = False
                for term in paper_terms:
                    neighbors = find_claim_neighbors(graph, term)
                    if neighbors:
                        graph_data["neighbors"] = neighbors[:20]
                        graph_data["searched_term"] = term
                        found = True
                        break
                if not found:
                    review_claims = find_review_required_claims(graph)
                    graph_data = {
                        "message": "No specific claim matches found. Here are review-required claims:",
                        "review_required": review_claims[:20],
                    }
        except Exception as e:
            logger.warning("Graph analytics failed: %s", e)
            graph_data = {"error": str(e)}

        if LLM_AVAILABLE:
            client = self._get_llm_client()
            if client:
                prompt = GRAPH_ANSWER_PROMPT.format(
                    graph_data=json.dumps(graph_data, indent=2, default=str),
                    question=question,
                )
                try:
                    response = await client.aio.models.generate_content(
                        model=settings.gemini_model,
                        contents=prompt,
                        config=types.GenerateContentConfig(
                            temperature=0.3,
                            response_mime_type="application/json",
                        ),
                    )
                    result = json.loads(response.text or "{}")
                    answer = result.get("answer", "Analysis complete. See graph data above.")
                    cited_sources = result.get("sources", [])
                    for cs in cited_sources:
                        sources.append(
                            Source(
                                doc_id=cs.get("doc_id", ""),
                                filename=cs.get("filename", ""),
                                section=cs.get("section", ""),
                                text=cs.get("text", "")[:300],
                                confidence=cs.get("confidence"),
                                relation_type=cs.get("relation_type"),
                            )
                        )
                    return answer, sources
                except Exception as e:
                    logger.warning("LLM graph answer failed: %s", e)

        formatted = json.dumps(graph_data, indent=2, default=str)
        answer = f"""Based on the knowledge graph analysis:

{formatted[:2000]}"""
        return answer, sources

    async def _general_chat(self, question: str) -> tuple[str, list[Source]]:
        sources: list[Source] = []
        graph = self._get_graph() if GRAPH_ENGINE_AVAILABLE else None
        context = ""
        if graph:
            try:
                summary = graph_summary(graph)
                context = f"\nKnowledge graph has {summary['total_nodes']} nodes and {summary['total_edges']} edges."
            except Exception:
                pass

        if LLM_AVAILABLE:
            client = self._get_llm_client()
            if client:
                prompt = GENERAL_CHAT_PROMPT.format(question=question + context)
                try:
                    response = await client.aio.models.generate_content(
                        model=settings.gemini_model,
                        contents=prompt,
                        config=types.GenerateContentConfig(
                            temperature=0.5,
                            response_mime_type="application/json",
                        ),
                    )
                    result = json.loads(response.text or "{}")
                    return result.get(
                        "answer", "I'm here to help with research questions!"
                    ), sources
                except Exception as e:
                    logger.warning("General chat failed: %s", e)

        return (
            f"I can help you explore your research knowledge graph and find evidence.{context}",
            sources,
        )


_rag_agent: RAGAgent | None = None


def get_rag_agent() -> RAGAgent:
    global _rag_agent
    if _rag_agent is None:
        _rag_agent = RAGAgent()
    return _rag_agent


def reset_rag_agent():
    global _rag_agent
    _rag_agent = None
