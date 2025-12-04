"""Named Entity Recognition processor using spaCy."""
import re
from typing import List, Dict, Any, Optional
import spacy
from spacy.language import Language

from app.config import settings


class NERProcessor:
    """Process text for Named Entity Recognition."""
    
    _instance: Optional["NERProcessor"] = None
    _nlp: Optional[Language] = None
    
    def __new__(cls):
        """Singleton pattern for NER processor."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        """Initialize the NER processor."""
        if self._nlp is None:
            self._load_model()
    
    def _load_model(self):
        """Load the spaCy model."""
        try:
            self._nlp = spacy.load(settings.spacy_model)
        except OSError:
            # Model not found, download it
            print(f"Downloading spaCy model: {settings.spacy_model}")
            spacy.cli.download(settings.spacy_model)
            self._nlp = spacy.load(settings.spacy_model)
    
    def extract_entities(self, text: str) -> List[Dict[str, Any]]:
        """
        Extract named entities from text.
        
        Args:
            text: The text to process
            
        Returns:
            List of entity dictionaries with text, type, positions, and sentence
        """
        if not text or not text.strip():
            return []
        
        # Clean text
        text = self._clean_text(text)
        
        # Process with spaCy
        doc = self._nlp(text)
        
        entities = []
        for ent in doc.ents:
            # Get the sentence containing the entity
            sentence = ent.sent.text if ent.sent else None
            
            entity = {
                "text": ent.text,
                "type": ent.label_,
                "start_pos": ent.start_char,
                "end_pos": ent.end_char,
                "sentence": sentence
            }
            entities.append(entity)
        
        # Extract additional entities (email addresses, phone numbers)
        entities.extend(self._extract_email_addresses(text))
        entities.extend(self._extract_phone_numbers(text))
        
        return entities
    
    def _clean_text(self, text: str) -> str:
        """Clean and normalize text."""
        # Remove excessive whitespace
        text = re.sub(r'\s+', ' ', text)
        # Remove null bytes
        text = text.replace('\x00', '')
        return text.strip()
    
    def _extract_email_addresses(self, text: str) -> List[Dict[str, Any]]:
        """Extract email addresses from text."""
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        entities = []
        
        for match in re.finditer(email_pattern, text):
            entities.append({
                "text": match.group(),
                "type": "EMAIL",
                "start_pos": match.start(),
                "end_pos": match.end(),
                "sentence": None
            })
        
        return entities
    
    def _extract_phone_numbers(self, text: str) -> List[Dict[str, Any]]:
        """Extract phone numbers from text."""
        # Simple phone pattern (US format)
        phone_pattern = r'\b(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b'
        entities = []
        
        for match in re.finditer(phone_pattern, text):
            entities.append({
                "text": match.group(),
                "type": "PHONE",
                "start_pos": match.start(),
                "end_pos": match.end(),
                "sentence": None
            })
        
        return entities
    
    def get_entity_types(self) -> List[str]:
        """Get list of supported entity types."""
        return [
            "PERSON",      # People, including fictional
            "ORG",         # Organizations
            "GPE",         # Geopolitical entities (countries, cities)
            "LOC",         # Locations (non-GPE)
            "DATE",        # Dates
            "TIME",        # Times
            "MONEY",       # Money amounts
            "PERCENT",     # Percentages
            "CARDINAL",    # Numerals not falling into other types
            "ORDINAL",     # Ordinals (first, second, etc.)
            "EMAIL",       # Email addresses (custom)
            "PHONE",       # Phone numbers (custom)
            "NOUN_PHRASE", # Noun phrases/chunks
            "VERB_PHRASE", # Verb phrases
            "ACTION",      # Action verbs
        ]
    
    def extract_phrases(self, text: str) -> Dict[str, List[Dict[str, Any]]]:
        """
        Extract noun phrases, verb phrases, and key actions from text.
        
        Args:
            text: The text to process
            
        Returns:
            Dictionary with noun_phrases, verb_phrases, and actions
        """
        if not text or not text.strip():
            return {"noun_phrases": [], "verb_phrases": [], "actions": []}
        
        # Clean text
        text = self._clean_text(text)
        
        # Process with spaCy
        doc = self._nlp(text)
        
        result = {
            "noun_phrases": self._extract_noun_phrases(doc),
            "verb_phrases": self._extract_verb_phrases(doc),
            "actions": self._extract_actions(doc)
        }
        
        return result
    
    def _extract_noun_phrases(self, doc) -> List[Dict[str, Any]]:
        """Extract noun phrases/chunks from spaCy doc."""
        noun_phrases = []
        seen = set()  # Deduplicate
        
        for chunk in doc.noun_chunks:
            # Skip very short or common phrases
            chunk_text = chunk.text.strip()
            if len(chunk_text) < 3 or chunk_text.lower() in seen:
                continue
            
            # Skip if it's just a pronoun or determiner
            if chunk.root.pos_ in ["PRON", "DET"]:
                continue
            
            seen.add(chunk_text.lower())
            noun_phrases.append({
                "text": chunk_text,
                "type": "NOUN_PHRASE",
                "root": chunk.root.text,
                "root_pos": chunk.root.pos_,
                "start_pos": chunk.start_char,
                "end_pos": chunk.end_char,
                "sentence": chunk.sent.text if chunk.sent else None
            })
        
        return noun_phrases
    
    def _extract_verb_phrases(self, doc) -> List[Dict[str, Any]]:
        """Extract verb phrases from spaCy doc using dependency parsing."""
        verb_phrases = []
        seen = set()
        
        for token in doc:
            # Find main verbs
            if token.pos_ == "VERB":
                # Build the verb phrase by collecting related tokens
                phrase_tokens = [token]
                
                # Get auxiliary verbs (will, have, be, etc.)
                for child in token.children:
                    if child.dep_ in ["aux", "auxpass", "neg"]:
                        phrase_tokens.append(child)
                
                # Get particles (phrasal verbs like "look up", "give in")
                for child in token.children:
                    if child.dep_ == "prt":
                        phrase_tokens.append(child)
                
                # Get adverbs modifying the verb
                for child in token.children:
                    if child.dep_ == "advmod" and child.pos_ == "ADV":
                        phrase_tokens.append(child)
                
                # Sort by position and create phrase
                phrase_tokens.sort(key=lambda t: t.i)
                phrase_text = " ".join(t.text for t in phrase_tokens)
                
                # Skip very short phrases or duplicates
                if len(phrase_text) < 3 or phrase_text.lower() in seen:
                    continue
                
                seen.add(phrase_text.lower())
                
                # Get the direct object if exists (for context)
                direct_obj = None
                for child in token.children:
                    if child.dep_ in ["dobj", "pobj"]:
                        direct_obj = child.text
                        break
                
                verb_phrases.append({
                    "text": phrase_text,
                    "type": "VERB_PHRASE",
                    "lemma": token.lemma_,
                    "tense": self._get_verb_tense(token),
                    "direct_object": direct_obj,
                    "start_pos": min(t.idx for t in phrase_tokens),
                    "end_pos": max(t.idx + len(t.text) for t in phrase_tokens),
                    "sentence": token.sent.text if token.sent else None
                })
        
        return verb_phrases
    
    def _extract_actions(self, doc) -> List[Dict[str, Any]]:
        """Extract action verbs with their subjects and objects."""
        actions = []
        seen = set()
        
        for token in doc:
            # Find main action verbs (not auxiliary)
            if token.pos_ == "VERB" and token.dep_ not in ["aux", "auxpass"]:
                # Get subject
                subject = None
                for child in token.children:
                    if child.dep_ in ["nsubj", "nsubjpass"]:
                        subject = child.text
                        # Try to get compound subject
                        for subchild in child.children:
                            if subchild.dep_ == "compound":
                                subject = subchild.text + " " + subject
                        break
                
                # Get object
                obj = None
                for child in token.children:
                    if child.dep_ in ["dobj", "pobj", "attr"]:
                        obj = child.text
                        # Try to get compound object
                        for subchild in child.children:
                            if subchild.dep_ == "compound":
                                obj = subchild.text + " " + obj
                        break
                
                # Build action string
                action_parts = []
                if subject:
                    action_parts.append(subject)
                action_parts.append(token.lemma_)
                if obj:
                    action_parts.append(obj)
                
                action_text = " ".join(action_parts)
                
                # Skip duplicates or very short actions
                if len(action_text) < 4 or action_text.lower() in seen:
                    continue
                
                seen.add(action_text.lower())
                
                actions.append({
                    "text": action_text,
                    "type": "ACTION",
                    "verb": token.text,
                    "verb_lemma": token.lemma_,
                    "subject": subject,
                    "object": obj,
                    "sentence": token.sent.text if token.sent else None
                })
        
        return actions
    
    def _get_verb_tense(self, token) -> str:
        """Determine the tense of a verb token."""
        # Check morphological features
        morph = token.morph
        
        if "Tense=Past" in str(morph):
            return "past"
        elif "Tense=Pres" in str(morph):
            return "present"
        elif "VerbForm=Inf" in str(morph):
            return "infinitive"
        elif "VerbForm=Ger" in str(morph):
            return "gerund"
        else:
            return "unknown"
    
    def extract_all(self, text: str) -> Dict[str, Any]:
        """
        Extract all NER entities AND phrases from text.
        
        Args:
            text: The text to process
            
        Returns:
            Dictionary with entities, noun_phrases, verb_phrases, and actions
        """
        entities = self.extract_entities(text)
        phrases = self.extract_phrases(text)
        
        return {
            "entities": entities,
            "noun_phrases": phrases["noun_phrases"],
            "verb_phrases": phrases["verb_phrases"],
            "actions": phrases["actions"]
        }
    
    def highlight_entities_html(self, text: str, entities: List[Dict[str, Any]]) -> str:
        """
        Generate HTML with highlighted entities.
        
        Args:
            text: Original text
            entities: List of entity dictionaries (supports both 'start'/'end' and 'start_pos'/'end_pos' keys)
            
        Returns:
            HTML string with marked entities
        """
        if not entities:
            return text
        
        # Helper functions to support both key naming conventions
        def get_start(e):
            return e.get("start_pos", e.get("start", 0))
        
        def get_end(e):
            return e.get("end_pos", e.get("end", 0))
        
        # Sort entities by start position (reverse to process from end)
        sorted_entities = sorted(entities, key=get_start, reverse=True)
        
        result = text
        for entity in sorted_entities:
            start = get_start(entity)
            end = get_end(entity)
            entity_type = entity["type"]
            entity_text = entity["text"]
            
            # Create highlighted span
            highlighted = f'<mark data-entity="{entity_type}" class="entity-{entity_type.lower()}">{entity_text}</mark>'
            result = result[:start] + highlighted + result[end:]
        
        return result


# Global instance
ner_processor = NERProcessor()

