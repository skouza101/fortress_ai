import json
import logging
import re
from typing import Dict, Any, List, Optional
from app.agents.state import AgentState
from app.services.llm import generate

logger = logging.getLogger(__name__)

# How many chars to send per chunk. ~4000 words, comfortably within most LLM context windows.
# Each chunk gets its own findings pass; results are merged at the end.
CHUNK_SIZE = 8000
CHUNK_OVERLAP = 500  # Overlap so clauses spanning a chunk boundary aren't missed


class LegalRiskAnalyst:
    async def run(self, state: AgentState) -> AgentState:
        logger.info("LegalRiskAnalyst: Starting analysis")

        contract_text = state.get("merged_context", "")
        research = state.get("research_report", "")
        query = state.get("original_query", "")
        parsed_doc = state.get("parsed_document")

        if not contract_text.strip():
            logger.error("LegalRiskAnalyst: No contract text in merged_context")
            return {"risk_analysis": {"error": "No contract text provided", "findings": []}}

        if parsed_doc and hasattr(parsed_doc, "section_map") and parsed_doc.section_map:
            # Structure-aware: analyze the whole doc using section boundaries
            risk_analysis = await self._analyze_with_structure(
                parsed_doc, contract_text, research, query
            )
        else:
            # Flat: chunk the contract and merge findings across chunks
            risk_analysis = await self._analyze_chunked(contract_text, research, query)

        return {"risk_analysis": risk_analysis}

    # ── Chunked analysis (no ParsedDocument) ─────────────────────────────────

    async def _analyze_chunked(
        self, contract_text: str, research: str, query: str
    ) -> Dict:
        """
        Split contract into overlapping chunks and run the analyst prompt on each.
        Merge and deduplicate findings across chunks.

        This ensures the full contract is analyzed regardless of length.
        """
        chunks = self._split_into_chunks(contract_text, CHUNK_SIZE, CHUNK_OVERLAP)
        total_chars = len(contract_text)
        logger.info(
            f"LegalRiskAnalyst: {total_chars} chars → {len(chunks)} chunks "
            f"(chunk_size={CHUNK_SIZE}, overlap={CHUNK_OVERLAP})"
        )

        all_findings: List[Dict] = []
        chunk_summaries: List[str] = []

        for i, (chunk_text, char_start) in enumerate(chunks):
            chunk_label = f"Part {i+1}/{len(chunks)} (chars {char_start}–{char_start+len(chunk_text)})"
            logger.info(f"LegalRiskAnalyst: Analyzing {chunk_label}")

            prompt = self._build_chunk_prompt(
                chunk_text=chunk_text,
                chunk_label=chunk_label,
                total_chunks=len(chunks),
                research=research,
                query=query,
            )

            response = await generate(
                prompt,
                system_prompt=(
                    "You are a Senior Legal Risk Analyst. "
                    "Analyze only the contract text provided. "
                    "Return ONLY valid JSON. No markdown fences. No commentary."
                ),
                temperature=0.1,
                max_tokens=6000,
                json_mode=True,
            )

            parsed = self._parse_chunk_response(response, chunk_label)
            all_findings.extend(parsed.get("findings", []))
            if parsed.get("summary"):
                chunk_summaries.append(f"[{chunk_label}] {parsed['summary']}")

        # Deduplicate findings that appear in overlapping chunks
        deduped = self._deduplicate_findings(all_findings)

        # Sort by priority then risk
        risk_order = {"High": 0, "Critical": 0, "Medium": 1, "Low": 2}
        deduped.sort(
            key=lambda f: (f.get("priority", 99), risk_order.get(f.get("risk", "Medium"), 1))
        )

        # Generate an overall summary from chunk summaries
        overall_summary = await self._synthesize_summary(
            deduped, chunk_summaries, query
        ) if deduped else "No risk findings identified in this contract."

        logger.info(f"LegalRiskAnalyst: {len(all_findings)} raw → {len(deduped)} deduped findings")

        return {
            "findings": deduped,
            "summary": overall_summary,
        }

    def _split_into_chunks(
        self, text: str, chunk_size: int, overlap: int
    ) -> List[tuple]:
        """
        Split text into overlapping chunks. Returns list of (chunk_text, char_start).
        Tries to split at paragraph/section boundaries rather than mid-sentence.
        """
        chunks = []
        start = 0
        text_len = len(text)

        while start < text_len:
            end = min(start + chunk_size, text_len)

            # If not at the end, try to break at a paragraph or newline boundary
            if end < text_len:
                # Look back up to 200 chars for a good break point
                break_search = text[end - 200:end]
                # Prefer double newline (paragraph), then single newline
                for sep in ["\n\n", "\n"]:
                    idx = break_search.rfind(sep)
                    if idx != -1:
                        end = end - 200 + idx + len(sep)
                        break

            chunks.append((text[start:end], start))
            if end >= text_len:
                break
            start = end - overlap  # Overlap so boundary clauses aren't split

        return chunks

    def _build_chunk_prompt(
        self,
        chunk_text: str,
        chunk_label: str,
        total_chunks: int,
        research: str,
        query: str,
    ) -> str:
        research_snippet = research[:2000] if research else "No supplemental research."

        json_schema = json.dumps({
            "findings": [
                {
                    "section": "<section number as it appears in this text, e.g. '4.1' or '10'>",
                    "title": "<short descriptive title of the risk>",
                    "risk": "High | Medium | Low",
                    "justification": "<why this clause is risky — reference legal standards or what protection is missing>",
                    "contract_text": "<exact quoted text from the contract that creates the risk>",
                    "recommendation": "<specific actionable revision or negotiation point>",
                    "priority": "<integer, 1=most urgent>",
                    "clause_type": "payment | indemnification | termination | liability | ip | data | dispute | delay | compliance | completeness | other"
                }
            ],
            "summary": "<2-3 sentence summary of risks found in this section>"
        }, indent=2)

        return f"""You are a Senior Legal Risk Analyst performing a clause-by-clause review.

ANALYSIS OBJECTIVE: {query}

DOCUMENT SECTION: {chunk_label} of {total_chunks} total sections
(This is a portion of a larger contract. Analyze what is present here.)

═══════════════════════════════════════════
CONTRACT TEXT — analyze THIS text:
═══════════════════════════════════════════
{chunk_text}

═══════════════════════════════════════════
CONTRACT STRUCTURE CONTEXT (from pre-analysis):
═══════════════════════════════════════════
{research_snippet}

═══════════════════════════════════════════
INSTRUCTIONS:
═══════════════════════════════════════════
1. Read every clause in the CONTRACT TEXT above carefully.
2. Find ALL risky, one-sided, vague, or missing provisions in this section.
3. For EACH finding:
   - Use the exact section number from the text (e.g. "4.1", "10", "17")
   - Quote the exact contract language causing the risk
   - Explain specifically why it is risky (one-sided terms, missing cap, short deadline, etc.)
   - Give a specific revision suggestion
4. Also flag MISSING clauses that should be present but are not in this section.
5. If this section has no risks, return an empty findings array — do NOT invent findings.

CLAUSE TYPES TO LOOK FOR:
- Payment: blank amounts, short withholding rights, no interest on late payment
- Indemnification: uncapped, one-sided, survives termination
- Termination: asymmetric rights, no notice period, unlimited State discretion
- Liability: unlimited exposure, damage waivers, contractor bears all risk
- IP/Records: broad State ownership, no contractor protections
- Data/Confidentiality: no breach notification, unlimited retention by State
- Dispute resolution: short claim filing windows, must continue performing during disputes
- Delay: contractor waives all delay damages
- Funding: automatic cancellation without compensation
- Compliance: broad regulatory obligations with penalties
- Completeness: blank fields, missing dollar amounts, undefined terms, broken references

OUTPUT — return ONLY this JSON, no markdown:
{json_schema}
"""

    def _parse_chunk_response(self, response: str, chunk_label: str) -> Dict:
        try:
            clean = re.sub(
                r'^```(?:json)?\s*|\s*```$', '', response.strip(), flags=re.MULTILINE
            ).strip()
            data = json.loads(clean)
            data.setdefault("findings", [])
            data.setdefault("summary", "")

            valid = []
            for f in data["findings"]:
                if not f.get("section") or not f.get("title"):
                    logger.warning(f"Skipping finding with missing section/title: {f}")
                    continue
                f.setdefault("risk", "Medium")
                f.setdefault("priority", 99)
                f.setdefault("clause_type", "other")
                f.setdefault("justification", "")
                f.setdefault("contract_text", "")
                f.setdefault("recommendation", "")
                f.setdefault("page", None)
                valid.append(f)

            data["findings"] = valid
            logger.info(f"Chunk [{chunk_label}]: {len(valid)} findings")
            return data

        except (json.JSONDecodeError, ValueError) as e:
            logger.error(f"Chunk [{chunk_label}] JSON parse failed: {e}\n{response[:300]}")
            return {"findings": [], "summary": ""}

    def _deduplicate_findings(self, findings: List[Dict]) -> List[Dict]:
        """
        Remove duplicate findings that appear in overlapping chunks.
        Two findings are duplicates if they share the same section AND
        their titles or contract_text have significant overlap.
        """
        seen: Dict[str, Dict] = {}
        risk_order = {"Critical": 4, "High": 3, "Medium": 2, "Low": 1}
        deduped = []

        for f in findings:
            section = str(f.get("section", "")).strip().lower()
            title = str(f.get("title", "")).strip().lower()
            # Normalise title to first 40 chars for fuzzy dedup
            key = f"{section}::{title[:40]}"

            if key not in seen:
                seen[key] = f
                deduped.append(f)
            else:
                # Keep the higher-risk version
                existing = seen[key]
                if risk_order.get(f.get("risk", ""), 0) > risk_order.get(existing.get("risk", ""), 0):
                    idx = deduped.index(existing)
                    deduped[idx] = f
                    seen[key] = f

        return deduped

    async def _synthesize_summary(
        self, findings: List[Dict], chunk_summaries: List[str], query: str
    ) -> str:
        """Generate a brief overall summary from all findings."""
        high = sum(1 for f in findings if f.get("risk") in ("High", "Critical"))
        med = sum(1 for f in findings if f.get("risk") == "Medium")
        low = sum(1 for f in findings if f.get("risk") == "Low")
        top_findings = [f"{f['section']}: {f['title']} ({f['risk']})" for f in findings[:5]]

        prompt = f"""Summarize the overall legal risk profile of this contract in 3-4 sentences.

Risk counts: {high} High, {med} Medium, {low} Low (total {len(findings)} findings)
Top findings: {', '.join(top_findings)}
Section summaries: {' | '.join(chunk_summaries[:4])}

Write a plain-English executive summary. Be specific about the most serious risks.
"""
        try:
            return await generate(
                prompt,
                system_prompt="You are a legal risk analyst. Write a concise, factual summary.",
                temperature=0.2,
            )
        except Exception as e:
            logger.warning(f"Summary synthesis failed: {e}")
            return f"Analysis complete: {high} high, {med} medium, {low} low risk findings across {len(findings)} total clauses."

    # ── Structure-aware analysis (ParsedDocument available) ──────────────────

    async def _analyze_with_structure(
        self, parsed_doc, contract_text: str, research: str, query: str
    ) -> Dict:
        """
        When ParsedDocument is available, use section boundaries instead of
        character-based chunking for more precise findings.
        Falls back to chunked if sections are too few or too large.
        """
        section_map = getattr(parsed_doc, "section_map", {})
        if not section_map or len(section_map) < 3:
            logger.info("LegalRiskAnalyst: section_map too sparse, falling back to chunked")
            return await self._analyze_chunked(contract_text, research, query)

        # Group sections into batches that fit within CHUNK_SIZE
        batches = []
        current_batch_text = ""
        current_batch_sections = []

        for sec_num in sorted(section_map.keys()):
            sec = section_map[sec_num]
            sec_text = getattr(sec, "text", "") or ""
            if len(current_batch_text) + len(sec_text) > CHUNK_SIZE and current_batch_text:
                batches.append((current_batch_text, current_batch_sections[:]))
                current_batch_text = sec_text
                current_batch_sections = [sec_num]
            else:
                current_batch_text += f"\n\n{sec_text}"
                current_batch_sections.append(sec_num)

        if current_batch_text:
            batches.append((current_batch_text, current_batch_sections))

        if not batches:
            return await self._analyze_chunked(contract_text, research, query)

        logger.info(f"LegalRiskAnalyst: structure-aware, {len(batches)} section batches")

        all_findings: List[Dict] = []
        chunk_summaries: List[str] = []

        for i, (batch_text, section_nums) in enumerate(batches):
            chunk_label = f"Sections {section_nums[0]}–{section_nums[-1]}"
            prompt = self._build_chunk_prompt(
                chunk_text=batch_text,
                chunk_label=chunk_label,
                total_chunks=len(batches),
                research=research,
                query=query,
            )
            response = await generate(
                prompt,
                system_prompt=(
                    "You are a Senior Legal Risk Analyst. "
                    "Analyze only the contract text provided. "
                    "Return ONLY valid JSON. No markdown fences."
                ),
                temperature=0.1,
                max_tokens=6000,
                json_mode=True,
            )
            parsed = self._parse_chunk_response(response, chunk_label)
            all_findings.extend(parsed.get("findings", []))
            if parsed.get("summary"):
                chunk_summaries.append(f"[{chunk_label}] {parsed['summary']}")

        deduped = self._deduplicate_findings(all_findings)
        risk_order = {"High": 0, "Critical": 0, "Medium": 1, "Low": 2}
        deduped.sort(
            key=lambda f: (f.get("priority", 99), risk_order.get(f.get("risk", "Medium"), 1))
        )
        overall_summary = await self._synthesize_summary(deduped, chunk_summaries, query)

        return {"findings": deduped, "summary": overall_summary}

# Made with Bob
