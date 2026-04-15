# import google.generativeai as genai
# import time
# from typing import Optional, Dict, Any, List
# import json
# from .config import settings
# from .models import (
#     Signal, Strategy, Personality, CompanyDetails,
#     SelectedOffer, Channel, Intent, Stage
# )

# class LLMService:
#     """Service for interacting with Google Gemini API"""

#     def __init__(self):
#         genai.configure(api_key=settings.GOOGLE_API_KEY)
#         self.model = genai.GenerativeModel(
#             model_name=settings.GEMINI_MODEL,
#             generation_config={
#                 "temperature": settings.GEMINI_TEMPERATURE,
#                 "max_output_tokens": settings.GEMINI_MAX_TOKENS,
#             }
#         )

#     def _call_llm(self, prompt: str, system_instruction: Optional[str] = None) -> str:
#         """Make a call to Gemini and return raw text response"""
#         try:
#             full_prompt = f"{system_instruction}\n\n{prompt}" if system_instruction else prompt
#             response = self.model.generate_content(full_prompt)
#             time.sleep(1)  # Rate limit safety for free tier
#             return response.text
#         except Exception as e:
#             raise Exception(f"LLM call failed: {str(e)}")

#     def _parse_json(self, raw: str) -> dict:
#         """
#         More robust JSON parser that handles common LLM mistakes.
#         - Strips markdown code fences
#         - Replaces escaped newlines inside strings
#         - Tries to fix some common syntax errors
#         """
#         # 1. Strip markdown fences and whitespace
#         cleaned = raw.strip()
#         if cleaned.startswith("```json"):
#             cleaned = cleaned[7:]
#         if cleaned.startswith("```"):
#             cleaned = cleaned[3:]
#         if cleaned.endswith("```"):
#             cleaned = cleaned[:-3]
#         cleaned = cleaned.strip()

#         # 2. Handle simple newline issues by replacing them
#         # Important for multi-line strings that LLMs sometimes generate
#         cleaned = cleaned.replace("\n", "\\n")
        
#         # 3. Attempt to parse
#         try:
#             return json.loads(cleaned)
#         except json.JSONDecodeError as e:
#             # If it still fails, raise a more informative error
#             raise json.JSONDecodeError(
#                 f"Failed to parse LLM JSON response. Error: {e.msg}. Raw response: <<< {raw} >>>",
#                 e.doc,
#                 e.pos
#             )

#     def _build_personality_block(self, personality: Personality, stage: Stage) -> str:
#         """Convert personality config into a plain English instruction block for the LLM"""
#         stage_override = personality.stage_instructions.get(stage.value, "")

#         lines = [
#             f"BASE STYLE: {personality.base_template.value}",
#         ]

#         if personality.custom_template_description:
#             lines.append(f"CUSTOM STYLE DESCRIPTION: {personality.custom_template_description}")

#         if personality.personality_traits:
#             lines.append(f"PERSONALITY TRAITS: {', '.join(personality.personality_traits)}")

#         if personality.always_include_phrases:
#             lines.append(f"MUST INCLUDE THESE PHRASES (use naturally): {', '.join(personality.always_include_phrases)}")

#         if personality.never_use_phrases:
#             lines.append(f"NEVER USE THESE PHRASES: {', '.join(personality.never_use_phrases)}")

#         lines.append(f"TOUCHDOWNS PER MESSAGE: Hit exactly {personality.touchdowns_per_message} distinct value or hook points")

#         if personality.enabled_hook_types:
#             lines.append(f"ALLOWED HOOK TYPES: {', '.join(personality.enabled_hook_types)}")

#         lines.append(f"URGENCY LEVEL: {personality.urgency_level}/10 (1=no urgency, 10=extremely urgent)")
#         lines.append(f"SELF DEPRECATION: {personality.self_deprecation}/10 (1=none, 10=a lot)")
#         lines.append(f"HUMOR/SARCASM: {personality.humor_sarcasm}/10 (1=very serious, 10=very funny)")

#         if stage_override:
#             lines.append(f"STAGE SPECIFIC INSTRUCTION: {stage_override}")

#         return "\n".join(lines)

#     def _build_company_block(self, company: CompanyDetails) -> str:
#         """Convert company details into a plain English block"""
#         lines = [f"SENDER COMPANY: {company.company_name}"]

#         if company.website:
#             lines.append(f"WEBSITE: {company.website}")
#         if company.industry:
#             lines.append(f"INDUSTRY: {company.industry}")
#         if company.elevator_pitch:
#             lines.append(f"ELEVATOR PITCH: {company.elevator_pitch}")
#         if company.value_props:
#             lines.append(f"VALUE PROPS:\n" + "\n".join(f"  - {v}" for v in company.value_props))
#         if company.social_proof:
#             lines.append(f"SOCIAL PROOF:\n" + "\n".join(f"  - {s}" for s in company.social_proof))

#         return "\n".join(lines)

#     def _build_offer_block(self, offer: SelectedOffer) -> str:
#         """Convert selected offer into a plain English block"""
#         lines = [f"OFFER: {offer.offer_name}"]

#         if offer.pain_points:
#             lines.append(f"PAIN POINTS IT SOLVES:\n" + "\n".join(f"  - {p}" for p in offer.pain_points))
#         if offer.solution_summary:
#             lines.append(f"SOLUTION SUMMARY: {offer.solution_summary}")
#         if offer.proof_points:
#             lines.append(f"PROOF POINTS:\n" + "\n".join(f"  - {p}" for p in offer.proof_points))
#         if offer.cta:
#             lines.append(f"CALL TO ACTION TO USE: {offer.cta}")

#         return "\n".join(lines)

#     def _build_channel_instructions(self, channel: Channel, stage: Stage, intent: Intent) -> str:
#         """Build channel and context specific writing rules"""

#         channel_rules = {
#             Channel.LINKEDIN_DM: "Keep it short and conversational. LinkedIn DMs should feel like a casual message from a peer, not a sales pitch. No formal salutations. Get to the point fast.",
#             Channel.LINKEDIN_INMAIL: "Slightly more formal than a DM but still personal. You have a subject line. Use it to spark curiosity not sell.",
#             Channel.EMAIL: "Can be slightly longer. Professional but warm. Subject line is critical. Avoid spam trigger words.",
#             Channel.TWITTER_DM: "Very short. Max 2-3 sentences. Extremely casual. Use their Twitter voice as inspiration.",
#             Channel.SMS: "Ultra short. Max 160 characters. No fluff. Direct and human."
#         }

#         stage_rules = {
#             Stage.FIRST_TOUCH: "This is the first time they're hearing from you. Do NOT pitch hard. Build curiosity. Be a human first.",
#             Stage.SECOND_TOUCH: "They've seen your first message. Reference it lightly. Add a new angle or piece of value.",
#             Stage.THIRD_TOUCH: "Final attempt in this mini-sequence. Be slightly more direct. Show you've done your homework.",
#             Stage.BREAKUP: "Last message ever. Keep it light. Leave the door open. No guilt tripping.",
#             Stage.NURTURE: "No immediate ask. Pure value. Share an insight, article, or relevant observation."
#         }

#         intent_rules = {
#             Intent.DIRECT_OUTREACH: "You're initiating cold. Be respectful of their time.",
#             Intent.FOLLOW_UP: "You're following up on a previous interaction. Reference it.",
#             Intent.REFERRAL: "You were referred or have a mutual connection. Lead with that.",
#             Intent.RE_ENGAGEMENT: "You've spoken before but gone cold. Acknowledge the gap.",
#             Intent.EVENT_BASED: "You're reaching out because of a specific event or trigger."
#         }

#         return "\n".join([
#             f"CHANNEL RULES: {channel_rules.get(channel, '')}",
#             f"STAGE RULES: {stage_rules.get(stage, '')}",
#             f"INTENT RULES: {intent_rules.get(intent, '')}"
#         ])

#     # --- NEW HELPER: Build memory context block ---
#     def _build_memory_block(
#         self,
#         hooks_already_used: List[str],
#         angles_already_tried: List[str],
#         times_contacted_before: int,
#         last_message_sent: Optional[str]
#     ) -> str:
#         """Convert memory data into instructions for the LLM"""
#         lines = []

#         if times_contacted_before > 0:
#             lines.append(f"PREVIOUS CONTACT: This prospect has been contacted {times_contacted_before} time(s) before.")
#         else:
#             lines.append("PREVIOUS CONTACT: This is the first time contacting this prospect.")

#         if hooks_already_used:
#             lines.append(f"HOOKS ALREADY USED (do NOT repeat these):\n" + "\n".join(f"  - {h}" for h in hooks_already_used))

#         if angles_already_tried:
#             lines.append(f"ANGLES ALREADY TRIED (use a DIFFERENT angle):\n" + "\n".join(f"  - {a}" for a in angles_already_tried))

#         if last_message_sent:
#             lines.append(f"LAST MESSAGE SENT TO THEM:\n  \"{last_message_sent}\"")
#             lines.append("IMPORTANT: Your new message must be clearly different from the last one sent.")

#         return "\n".join(lines) if lines else "NO PRIOR CONTACT HISTORY"

#     # ------------------------------------------------------------------
#     # PUBLIC METHODS
#     # ------------------------------------------------------------------

#     def analyze_research_signals(
#         self,
#         signals: List[Signal],
#         prospect_name: str,
#         company: str,
#         personality: Personality,
#         hooks_already_used: List[str] = None  # NEW PARAMETER
#     ) -> Dict[str, Any]:
#         """Use LLM to analyze research signals and pick the best hooks"""

#         if hooks_already_used is None:
#             hooks_already_used = []

#         # Filter to only enabled hook types if specified
#         filtered_signals = signals
#         if personality.enabled_hook_types:
#             filtered_signals = [
#                 s for s in signals
#                 if s.type in personality.enabled_hook_types
#             ]
#             if not filtered_signals:
#                 filtered_signals = signals

#         signals_text = "\n".join([
#             f"- [{s.strength.upper()}] {s.type}: {s.content} (Why relevant: {s.why_relevant})"
#             for s in filtered_signals
#         ])

#         # NEW: Build memory context for hook avoidance
#         memory_context = ""
#         if hooks_already_used:
#             memory_context = "\n\nHOOKS ALREADY USED WITH THIS PROSPECT (do NOT pick these again):\n"
#             memory_context += "\n".join(f"  - {h}" for h in hooks_already_used)
#             memory_context += "\n\nYou MUST choose different hooks than the ones listed above."

#         prompt = f"""You are a sales strategy expert analyzing research signals about {prospect_name} at {company}.

# RESEARCH SIGNALS:
# {signals_text}

# ALLOWED HOOK TYPES: {', '.join(personality.enabled_hook_types) if personality.enabled_hook_types else 'All types allowed'}{memory_context}

# Your task:
# 1. Identify the BEST primary hook (most timely, relevant, and personal)
# 2. Identify a good secondary hook (backup/supporting context)
# 3. Explain your reasoning

# Return JSON:
# {{
#     "primary_hook": "the best hook to use",
#     "secondary_hook": "a supporting hook",
#     "reasoning": "why you chose these hooks",
#     "confidence": "high/medium/low"
# }}"""

#         try:
#             response = self._call_llm(
#                 prompt,
#                 system_instruction="You are an expert sales strategist. Always return valid JSON only. No markdown."
#             )
#             return self._parse_json(response)
#         except Exception as e:
#             return {
#                 "primary_hook": signals[0].content if signals else "General interest in your work",
#                 "secondary_hook": signals[1].content if len(signals) > 1 else "Industry trends",
#                 "reasoning": f"Fallback due to error: {str(e)}",
#                 "confidence": "low"
#             }

#     def create_strategy(
#         self,
#         primary_hook: str,
#         secondary_hook: str,
#         prospect_name: str,
#         company: str,
#         prospect_role: Optional[str],
#         personality: Personality,
#         company_details: CompanyDetails,
#         selected_offer: SelectedOffer,
#         channel: Channel,
#         intent: Intent,
#         stage: Stage,
#         angles_already_tried: List[str] = None  # NEW PARAMETER
#     ) -> Strategy:
#         """Use LLM to create a complete messaging strategy"""

#         if angles_already_tried is None:
#             angles_already_tried = []

#         role_context = f"({prospect_role})" if prospect_role else ""

#         # NEW: Build memory context for angle avoidance
#         memory_context = ""
#         if angles_already_tried:
#             memory_context = f"\n\nANGLES ALREADY TRIED WITH THIS PROSPECT (use a DIFFERENT angle):\n"
#             memory_context += "\n".join(f"  - {a}" for a in angles_already_tried)
#             memory_context += "\n\nYou MUST choose a different angle than the ones listed above."

#         prompt = f"""You are a sales messaging strategist.

# TARGET: {prospect_name} {role_context} at {company}

# PRIMARY HOOK: {primary_hook}
# SECONDARY HOOK: {secondary_hook}

# {self._build_personality_block(personality, stage)}

# {self._build_company_block(company_details)}

# {self._build_offer_block(selected_offer)}

# {self._build_channel_instructions(channel, stage, intent)}{memory_context}

# Create a strategy with:
# 1. A specific ANGLE (how to position the conversation)
# 2. REASONING for why this approach will work for THIS person

# Return JSON:
# {{
#     "angle": "the conversation angle to take",
#     "reasoning": "why this strategy works for this specific person"
# }}"""

#         try:
#             response = self._call_llm(
#                 prompt,
#                 system_instruction="You are a sales strategy expert. Always return valid JSON only. No markdown."
#             )
#             result = self._parse_json(response)

#             return Strategy(
#                 primary_hook=primary_hook,
#                 secondary_hook=secondary_hook,
#                 angle=result.get("angle", "Professional peer-to-peer conversation"),
#                 tone=personality.base_template.value,
#                 cta_style=selected_offer.cta or "soft_question",
#                 reasoning=result.get("reasoning", "")
#             )
#         except Exception as e:
#             return Strategy(
#                 primary_hook=primary_hook,
#                 secondary_hook=secondary_hook,
#                 angle="Professional peer-to-peer conversation",
#                 tone=personality.base_template.value,
#                 cta_style=selected_offer.cta or "soft_question",
#                 reasoning=f"Fallback strategy: {str(e)}"
#             )

#     def write_message(
#         self,
#         strategy: Strategy,
#         prospect_name: str,
#         company: str,
#         prospect_role: Optional[str],
#         personality: Personality,
#         company_details: CompanyDetails,
#         selected_offer: SelectedOffer,
#         channel: Channel,
#         intent: Intent,
#         stage: Stage,
#         times_contacted_before: int = 0,          # NEW PARAMETER
#         last_message_sent: Optional[str] = None   # NEW PARAMETER
#     ) -> Dict[str, Any]:
#         """Use LLM to write the actual outreach message"""

#         channel_limits = {
#             Channel.LINKEDIN_DM: (50, 300),
#             Channel.LINKEDIN_INMAIL: (100, 600),
#             Channel.EMAIL: (100, 800),
#             Channel.TWITTER_DM: (20, 280),
#             Channel.SMS: (20, 160)
#         }
#         min_len, max_len = channel_limits.get(channel, (50, 300))

#         include_subject = channel in [Channel.LINKEDIN_INMAIL, Channel.EMAIL]

#         role_context = f"({prospect_role})" if prospect_role else ""

#         # NEW: Build memory context block
#         memory_block = self._build_memory_block(
#             hooks_already_used=[],  # Already handled in strategist
#             angles_already_tried=[],  # Already handled in strategist
#             times_contacted_before=times_contacted_before,
#             last_message_sent=last_message_sent
#         )

#         prompt = f"""You are writing a personalized outreach message.

# TARGET: {prospect_name} {role_context} at {company}

# STRATEGY:
# - Primary Hook: {strategy.primary_hook}
# - Secondary Hook: {strategy.secondary_hook}
# - Angle: {strategy.angle}
# - Strategic Reasoning: {strategy.reasoning}

# {self._build_personality_block(personality, stage)}

# {self._build_company_block(company_details)}

# {self._build_offer_block(selected_offer)}

# {self._build_channel_instructions(channel, stage, intent)}

# CONTACT HISTORY:
# {memory_block}

# HARD REQUIREMENTS:
# - Length: {min_len} to {max_len} characters
# - Hit exactly {personality.touchdowns_per_message} distinct touchpoints
# - Never use: {', '.join(personality.never_use_phrases) if personality.never_use_phrases else 'nothing banned'}
# - Must include naturally: {', '.join(personality.always_include_phrases) if personality.always_include_phrases else 'no required phrases'}
# {"- Include a subject line" if include_subject else "- No subject line needed"}

# Write the message now.

# Return JSON:
# {{
#     "body": "the message text",
#     "subject": {"\"subject line here\"" if include_subject else "null"},
#     "sentence_breakdown": [
#         {{"text": "sentence text", "purpose": "hook/credibility/value/cta", "driven_by": ["source1", "source2"]}}
#     ]
# }}"""

#         try:
#             response = self._call_llm(
#                 prompt,
#                 system_instruction="You are an expert sales copywriter. Write authentic human messages. Always return valid JSON only. No markdown."
#             )
#             return self._parse_json(response)
#         except Exception as e:
#             fallback = f"Hi {prospect_name}, came across your work at {company} and wanted to connect."
#             return {
#                 "body": fallback,
#                 "subject": None,
#                 "sentence_breakdown": [
#                     {"text": fallback, "purpose": "general", "driven_by": ["fallback"]}
#                 ],
#                 "error": str(e)
#             }

#     def validate_message(
#         self,
#         message: str,
#         prospect_name: str,
#         channel: Channel,
#         personality: Personality
#     ) -> Dict[str, Any]:
#         """Use LLM to validate message quality - NO CHANGES NEEDED"""

#         channel_limits = {
#             Channel.LINKEDIN_DM: (50, 300),
#             Channel.LINKEDIN_INMAIL: (100, 600),
#             Channel.EMAIL: (100, 800),
#             Channel.TWITTER_DM: (20, 280),
#             Channel.SMS: (20, 160)
#         }
#         min_len, max_len = channel_limits.get(channel, (50, 300))

#         banned = ', '.join(personality.never_use_phrases) if personality.never_use_phrases else "none"
#         required = ', '.join(personality.always_include_phrases) if personality.always_include_phrases else "none"

#         prompt = f"""Evaluate this outreach message for quality.

# MESSAGE:
# {message}

# TARGET: {prospect_name}
# CHANNEL: {channel.value}
# CHARACTER COUNT: {len(message)}
# REQUIRED LENGTH: {min_len} to {max_len} characters
# BANNED PHRASES: {banned}
# REQUIRED PHRASES: {required}
# TOUCHDOWNS REQUIRED: {personality.touchdowns_per_message}

# Check for:
# 1. Length compliance
# 2. Banned phrases present
# 3. Required phrases missing
# 4. Generic/templated language
# 5. Overpersonalization (creepy)
# 6. Clarity of CTA
# 7. Authenticity
# 8. Correct number of touchdowns

# Score 0-100. Be strict.

# Return JSON:
# {{
#     "score": 85,
#     "warnings": ["list of specific issues"],
#     "suggested_fixes": "specific actionable recommendations",
#     "valid": true
# }}"""

#         try:
#             response = self._call_llm(
#                 prompt,
#                 system_instruction="You are a message quality expert. Always return valid JSON only. No markdown."
#             )
#             return self._parse_json(response)
#         except Exception as e:
#             warnings = [f"Validation LLM failed: {str(e)}"]
#             score = 100

#             if len(message) > max_len:
#                 warnings.append(f"Too long by {len(message) - max_len} characters")
#                 score -= 15
#             if len(message) < min_len:
#                 warnings.append(f"Too short by {min_len - len(message)} characters")
#                 score -= 15

#             for phrase in personality.never_use_phrases:
#                 if phrase.lower() in message.lower():
#                     warnings.append(f"Banned phrase detected: '{phrase}'")
#                     score -= 10

#             return {
#                 "score": score,
#                 "warnings": warnings,
#                 "suggested_fixes": "Review issues listed in warnings" if warnings else None,
#                 "valid": score >= settings.MIN_QUALITY_SCORE
#             }

# llm_service = LLMService()
import google.generativeai as genai
import time
from typing import Optional, Dict, Any, List
import json
from .config import settings
from .models import (
    Signal, Strategy, Personality, CompanyDetails,
    SelectedOffer, Channel, Intent, Stage
)

class LLMService:
    """Service for interacting with Google Gemini API"""

    def __init__(self):
        genai.configure(api_key=settings.GOOGLE_API_KEY)
        self.model = genai.GenerativeModel(
            model_name=settings.GEMINI_MODEL,
            generation_config={
                "temperature": settings.GEMINI_TEMPERATURE,
                "max_output_tokens": settings.GEMINI_MAX_TOKENS,
            }
        )

    def _call_llm(self, prompt: str, system_instruction: Optional[str] = None) -> str:
        """Make a call to Gemini and return raw text response"""
        try:
            full_prompt = f"{system_instruction}\n\n{prompt}" if system_instruction else prompt
            response = self.model.generate_content(full_prompt)
            time.sleep(1) # Rate limit safety
            return response.text
        except Exception as e:
            raise Exception(f"LLM call failed: {str(e)}")

    def _parse_json(self, raw: str) -> dict:
        """
        Uses json5 to parse potentially sloppy JSON from the LLM.
        json5 is much more tolerant of syntax errors like trailing commas,
        unquoted keys, single quotes, etc.
        """
        import json5  # Import it here

        # 1. Strip markdown fences and whitespace
        cleaned = raw.strip()
        if cleaned.startswith("```json"):
            cleaned = cleaned[7:]
        if cleaned.startswith("```"):
            cleaned = cleaned[3:]
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]
        cleaned = cleaned.strip()
        
        # 2. Attempt to parse with the more lenient json5 library
        try:
            return json5.loads(cleaned)
        except Exception as e:
            # If even json5 fails, we have a major problem.
            raise ValueError(
                f"Failed to parse LLM response even with json5. Error: {str(e)}. Raw response: <<< {raw} >>>"
            )

    def _build_personality_block(self, personality: Personality, stage: Stage) -> str:
        """Convert personality config into a plain English instruction block for the LLM"""
        stage_override = personality.stage_instructions.get(stage.value, "")
        lines = [f"BASE STYLE: {personality.base_template.value}"]
        if personality.custom_template_description: lines.append(f"CUSTOM STYLE DESCRIPTION: {personality.custom_template_description}")
        if personality.personality_traits: lines.append(f"PERSONALITY TRAITS: {', '.join(personality.personality_traits)}")
        if personality.always_include_phrases: lines.append(f"MUST INCLUDE THESE PHRASES (use naturally): {', '.join(personality.always_include_phrases)}")
        if personality.never_use_phrases: lines.append(f"NEVER USE THESE PHRASES: {', '.join(personality.never_use_phrases)}")
        lines.append(f"TOUCHDOWNS PER MESSAGE: Hit exactly {personality.touchdowns_per_message} distinct value or hook points")
        if personality.enabled_hook_types: lines.append(f"ALLOWED HOOK TYPES: {', '.join(personality.enabled_hook_types)}")
        lines.append(f"URGENCY LEVEL: {personality.urgency_level}/10 (1=no urgency, 10=extremely urgent)")
        lines.append(f"SELF DEPRECATION: {personality.self_deprecation}/10 (1=none, 10=a lot)")
        lines.append(f"HUMOR/SARCASM: {personality.humor_sarcasm}/10 (1=very serious, 10=very funny)")
        if stage_override: lines.append(f"STAGE SPECIFIC INSTRUCTION: {stage_override}")
        return "\n".join(lines)

    def _build_company_block(self, company: CompanyDetails) -> str:
        """Convert company details into a plain English block"""
        lines = [f"SENDER COMPANY: {company.company_name}"]
        if company.website: lines.append(f"WEBSITE: {company.website}")
        if company.industry: lines.append(f"INDUSTRY: {company.industry}")
        if company.elevator_pitch: lines.append(f"ELEVATOR PITCH: {company.elevator_pitch}")
        if company.value_props: lines.append(f"VALUE PROPS:\n" + "\n".join(f"  - {v}" for v in company.value_props))
        if company.social_proof: lines.append(f"SOCIAL PROOF:\n" + "\n".join(f"  - {s}" for s in company.social_proof))
        return "\n".join(lines)

    def _build_offer_block(self, offer: SelectedOffer) -> str:
        """Convert selected offer into a plain English block"""
        lines = [f"OFFER: {offer.offer_name}"]
        if offer.pain_points: lines.append(f"PAIN POINTS IT SOLVES:\n" + "\n".join(f"  - {p}" for p in offer.pain_points))
        if offer.solution_summary: lines.append(f"SOLUTION SUMMARY: {offer.solution_summary}")
        if offer.proof_points: lines.append(f"PROOF POINTS:\n" + "\n".join(f"  - {p}" for p in offer.proof_points))
        if offer.cta: lines.append(f"CALL TO ACTION TO USE: {offer.cta}")
        return "\n".join(lines)

    def _build_channel_instructions(self, channel: Channel, stage: Stage, intent: Intent) -> str:
        """Build channel and context specific writing rules"""
        channel_rules = {Channel.LINKEDIN_DM: "Short, conversational, peer-like.", Channel.LINKEDIN_INMAIL: "Semi-formal, subject line matters.", Channel.EMAIL: "Professional but warm, subject is critical.", Channel.TWITTER_DM: "Very short, casual.", Channel.SMS: "Ultra short, direct."}
        stage_rules = {Stage.FIRST_TOUCH: "Build curiosity, be human.", Stage.SECOND_TOUCH: "Reference first message, add new value.", Stage.THIRD_TOUCH: "Be more direct.", Stage.BREAKUP: "Light, leave door open.", Stage.NURTURE: "No ask, pure value."}
        intent_rules = {Intent.DIRECT_OUTREACH: "Respect their time.", Intent.FOLLOW_UP: "Reference past interaction.", Intent.REFERRAL: "Lead with mutual connection.", Intent.RE_ENGAGEMENT: "Acknowledge the gap.", Intent.EVENT_BASED: "Reference the trigger."}
        return "\n".join([f"CHANNEL RULES: {channel_rules.get(channel, '')}", f"STAGE RULES: {stage_rules.get(stage, '')}", f"INTENT RULES: {intent_rules.get(intent, '')}"])

    def _build_memory_block(self, times_contacted_before: int, last_message_sent: Optional[str]) -> str:
        """Convert memory data into instructions for the LLM"""
        lines = []
        if times_contacted_before > 0:
            lines.append(f"PREVIOUS CONTACT: This prospect has been contacted {times_contacted_before} time(s) before.")
        else:
            lines.append("PREVIOUS CONTACT: This is the first time contacting this prospect.")
        if last_message_sent:
            lines.append(f"LAST MESSAGE SENT TO THEM:\n  \"{last_message_sent}\"")
            lines.append("IMPORTANT: Your new message must be clearly different from the last one sent.")
        return "\n".join(lines) if lines else "NO PRIOR CONTACT HISTORY"

    # ------------------------------------------------------------------
    # PUBLIC METHODS
    # ------------------------------------------------------------------

    def analyze_research_signals(
        self,
        signals: List[Signal],
        prospect_name: str,
        company: str,
        personality: Personality,
        hooks_already_used: List[str] = None
    ) -> Dict[str, Any]:
        if hooks_already_used is None: hooks_already_used = []
        filtered_signals = signals
        if personality.enabled_hook_types:
            filtered_signals = [s for s in signals if s.type in personality.enabled_hook_types] or signals
        signals_text = "\n".join([f"- [{s.strength.upper()}] {s.type}: {s.content} (Why relevant: {s.why_relevant})" for s in filtered_signals])
        memory_context = ""
        if hooks_already_used: memory_context = "\n\nHOOKS ALREADY USED (do NOT pick these again):\n" + "\n".join(f"  - {h}" for h in hooks_already_used)
        prompt = f"""You are a sales strategy expert analyzing research signals about {prospect_name} at {company}.
RESEARCH SIGNALS:
{signals_text}
ALLOWED HOOK TYPES: {', '.join(personality.enabled_hook_types) if personality.enabled_hook_types else 'All types allowed'}{memory_context}
Your task:
1. Identify the BEST primary hook (most timely, relevant, personal)
2. Identify a good secondary hook
3. Explain your reasoning
Return JSON: {{"primary_hook": "...", "secondary_hook": "...", "reasoning": "...", "confidence": "..."}}"""
        try:
            response = self._call_llm(prompt, system_instruction="You are an expert sales strategist. Always return valid JSON only. All JSON string values must be properly escaped. No markdown.")
            return self._parse_json(response)
        except Exception as e:
            return {"primary_hook": signals[0].content if signals else "General interest", "secondary_hook": signals[1].content if len(signals) > 1 else "Industry trends", "reasoning": f"Fallback due to error: {str(e)}", "confidence": "low"}

    def create_strategy(
        self,
        primary_hook: str,
        secondary_hook: str,
        prospect_name: str,
        company: str,
        prospect_role: Optional[str],
        personality: Personality,
        company_details: CompanyDetails,
        selected_offer: SelectedOffer,
        channel: Channel,
        intent: Intent,
        stage: Stage,
        angles_already_tried: List[str] = None
    ) -> Strategy:
        if angles_already_tried is None: angles_already_tried = []
        role_context = f"({prospect_role})" if prospect_role else ""
        memory_context = ""
        if angles_already_tried: memory_context = f"\n\nANGLES ALREADY TRIED (use a DIFFERENT angle):\n" + "\n".join(f"  - {a}" for a in angles_already_tried)
        prompt = f"""You are a sales messaging strategist.
TARGET: {prospect_name} {role_context} at {company}
PRIMARY HOOK: {primary_hook}
SECONDARY HOOK: {secondary_hook}
{self._build_personality_block(personality, stage)}
{self._build_company_block(company_details)}
{self._build_offer_block(selected_offer)}
{self._build_channel_instructions(channel, stage, intent)}{memory_context}
Create a strategy with:
1. A specific ANGLE (how to position the conversation)
2. REASONING for why this approach will work for THIS person
Return JSON: {{"angle": "...", "reasoning": "..."}}"""
        try:
            response = self._call_llm(prompt, system_instruction="You are a sales strategy expert. Always return valid JSON only. All JSON string values must be properly escaped. No markdown.")
            result = self._parse_json(response)
            return Strategy(primary_hook=primary_hook, secondary_hook=secondary_hook, angle=result.get("angle", "Peer-to-peer"), tone=personality.base_template.value, cta_style=selected_offer.cta or "soft_question", reasoning=result.get("reasoning", ""))
        except Exception as e:
            return Strategy(primary_hook=primary_hook, secondary_hook=secondary_hook, angle="Peer-to-peer", tone=personality.base_template.value, cta_style=selected_offer.cta or "soft_question", reasoning=f"Fallback strategy: {str(e)}")

    def write_message(
        self,
        strategy: Strategy,
        prospect_name: str,
        company: str,
        prospect_role: Optional[str],
        personality: Personality,
        company_details: CompanyDetails,
        selected_offer: SelectedOffer,
        channel: Channel,
        intent: Intent,
        stage: Stage,
        times_contacted_before: int = 0,
        last_message_sent: Optional[str] = None,
        # --- NEW PARAMETERS FOR REVISION ---
        is_revision: bool = False,
        previous_draft: Optional[str] = None,
        feedback_from_critic: Optional[str] = None
    ) -> Dict[str, Any]:
        channel_limits = {Channel.LINKEDIN_DM: (50, 300), Channel.LINKEDIN_INMAIL: (100, 600), Channel.EMAIL: (100, 800), Channel.TWITTER_DM: (20, 280), Channel.SMS: (20, 160)}
        min_len, max_len = channel_limits.get(channel, (50, 300))
        include_subject = channel in [Channel.LINKEDIN_INMAIL, Channel.EMAIL]
        role_context = f"({prospect_role})" if prospect_role else ""
        memory_block = self._build_memory_block(times_contacted_before, last_message_sent)

        # --- NEW: Build the revision block if applicable ---
        revision_block = ""
        if is_revision and previous_draft and feedback_from_critic:
            revision_block = f"""
REVISION REQUIRED:
Your previous attempt was rejected.
PREVIOUS DRAFT:
"{previous_draft}"

REASON FOR REJECTION / FEEDBACK TO IMPLEMENT:
"{feedback_from_critic}"

You MUST fix the issues mentioned in the feedback. Create a better, revised version that incorporates the suggestions. Do not repeat the same mistakes.
"""
        
        prompt = f"""You are writing a personalized outreach message.
{revision_block}
TARGET: {prospect_name} {role_context} at {company}
STRATEGY:
- Primary Hook: {strategy.primary_hook}
- Secondary Hook: {strategy.secondary_hook}
- Angle: {strategy.angle}
- Strategic Reasoning: {strategy.reasoning}
{self._build_personality_block(personality, stage)}
{self._build_company_block(company_details)}
{self._build_offer_block(selected_offer)}
{self._build_channel_instructions(channel, stage, intent)}
CONTACT HISTORY:
{memory_block}
HARD REQUIREMENTS:
- Length: {min_len} to {max_len} characters
- Hit exactly {personality.touchdowns_per_message} distinct touchpoints
- Never use: {', '.join(personality.never_use_phrases) if personality.never_use_phrases else 'nothing banned'}
- Must include naturally: {', '.join(personality.always_include_phrases) if personality.always_include_phrases else 'no required phrases'}
{"- Include a subject line" if include_subject else "- No subject line needed"}
Write the message now.
Return JSON: {{"body": "...", "subject": {"\"...\"" if include_subject else "null"}, "sentence_breakdown": [{{"text": "...", "purpose": "...", "driven_by": [...]}}]}}"""
        try:
            response = self._call_llm(prompt, system_instruction="You are an expert sales copywriter. Write authentic human messages. Always return valid JSON only. All JSON string values must be properly escaped. No markdown.")
            return self._parse_json(response)
        except Exception as e:
            fallback = f"Hi {prospect_name}, came across your work at {company} and wanted to connect."
            return {"body": fallback, "subject": None, "sentence_breakdown": [{"text": fallback, "purpose": "general", "driven_by": ["fallback"]}], "error": str(e)}

    # --- UNCHANGED validate_message FUNCTION ---
    def validate_message(
        self,
        message: str,
        prospect_name: str,
        channel: Channel,
        personality: Personality
    ) -> Dict[str, Any]:
        # This function is fine, no changes needed for this task
        # Using your exact existing code
        channel_limits = {Channel.LINKEDIN_DM: (50, 300), Channel.LINKEDIN_INMAIL: (100, 600), Channel.EMAIL: (100, 800), Channel.TWITTER_DM: (20, 280), Channel.SMS: (20, 160)}
        min_len, max_len = channel_limits.get(channel, (50, 300))
        banned = ', '.join(personality.never_use_phrases) if personality.never_use_phrases else "none"
        required = ', '.join(personality.always_include_phrases) if personality.always_include_phrases else "none"
        prompt = f"""Evaluate this outreach message for quality.
MESSAGE:
{message}
TARGET: {prospect_name}
CHANNEL: {channel.value}
CHARACTER COUNT: {len(message)}
REQUIRED LENGTH: {min_len} to {max_len} characters
BANNED PHRASES: {banned}
REQUIRED PHRASES: {required}
TOUCHDOWNS REQUIRED: {personality.touchdowns_per_message}
Check for:
1. Length compliance
2. Banned phrases present
3. Required phrases missing
4. Generic/templated language
5. Overpersonalization (creepy)
6. Clarity of CTA
7. Authenticity
8. Correct number of touchdowns
Score 0-100. Be strict.
Return JSON: {{"score": 85, "warnings": [...], "suggested_fixes": "...", "valid": true}}"""
        try:
            response = self._call_llm(prompt, system_instruction="You are a message quality expert. Always return valid JSON only. All JSON string values must be properly escaped. No markdown.")
            return self._parse_json(response)
        except Exception as e:
            warnings = [f"Validation LLM failed: {str(e)}"]
            score = 100
            if len(message) > max_len: warnings.append(f"Too long by {len(message) - max_len} characters"); score -= 15
            if len(message) < min_len: warnings.append(f"Too short by {min_len - len(message)} characters"); score -= 15
            for phrase in personality.never_use_phrases:
                if phrase.lower() in message.lower(): warnings.append(f"Banned phrase detected: '{phrase}'"); score -= 10
            return {"score": score, "warnings": warnings, "suggested_fixes": "Review issues" if warnings else None, "valid": score >= settings.MIN_QUALITY_SCORE}

llm_service = LLMService()