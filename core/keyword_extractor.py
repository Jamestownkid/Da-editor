"""
Da Editor - Keyword Extractor (v2)
===================================
FIXED:
- NO auto-download of spaCy models at runtime (causes freezes)
- spaCy is now truly optional - graceful fallback to regex
- Better bigram extraction
"""

import os
import re
from typing import List
from collections import Counter


class KeywordExtractor:
    """
    extract searchable keywords from SRT transcripts
    
    v2 FIXES:
    - spaCy is optional - never downloads at runtime
    - falls back to regex cleanly
    """
    
    # common words to skip
    STOP_WORDS = {
        "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for",
        "of", "with", "by", "from", "as", "is", "was", "are", "were", "been",
        "be", "have", "has", "had", "do", "does", "did", "will", "would", "could",
        "should", "may", "might", "must", "shall", "can", "need", "dare", "ought",
        "used", "it", "its", "this", "that", "these", "those", "i", "me", "my",
        "myself", "we", "our", "ours", "you", "your", "yours", "he", "him", "his",
        "she", "her", "hers", "they", "them", "their", "what", "which", "who",
        "whom", "when", "where", "why", "how", "all", "each", "every", "both",
        "few", "more", "most", "other", "some", "such", "no", "nor", "not", "only",
        "own", "same", "so", "than", "too", "very", "just", "also", "now", "here",
        "there", "then", "once", "if", "because", "about", "into", "through",
        "during", "before", "after", "above", "below", "between", "under", "again",
        "further", "up", "down", "out", "off", "over", "any", "well", "back",
        "um", "uh", "like", "know", "think", "got", "get", "go", "going", "gonna",
        "really", "actually", "basically", "literally", "things", "thing", "stuff",
        "something", "nothing", "everything", "someone", "anyone", "everyone", "yeah",
        "okay", "ok", "right", "yes", "no", "maybe", "probably", "definitely",
        "want", "need", "make", "made", "let", "put", "take", "say", "said", "tell"
    }
    
    # words that give good image results
    BOOST_WORDS = {
        "mountain", "ocean", "city", "nature", "sunset", "sunrise", "landscape",
        "building", "architecture", "technology", "science", "art", "music",
        "sports", "food", "travel", "adventure", "business", "money", "health",
        "fitness", "fashion", "beauty", "animals", "wildlife", "space", "universe",
        "beach", "forest", "desert", "river", "lake", "sky", "clouds", "rain",
        "snow", "winter", "summer", "spring", "autumn", "night", "day", "morning",
        "car", "house", "office", "computer", "phone", "camera", "book", "movie"
    }
    
    def __init__(self):
        self.nlp = None  # lazy load spacy - but NEVER download
        self._spacy_available = None
        print("[Keywords v2] extractor ready (no auto-download)")
    
    def _check_spacy(self) -> bool:
        """Check if spaCy is available WITHOUT downloading anything"""
        if self._spacy_available is not None:
            return self._spacy_available
        
        try:
            import spacy
            # Try to load the model - but NEVER download
            self.nlp = spacy.load("en_core_web_sm")
            self._spacy_available = True
            print("[Keywords] spaCy available")
        except Exception as e:
            # spaCy not available or model not installed - that's fine
            self._spacy_available = False
            print(f"[Keywords] spaCy not available (will use regex): {str(e)[:50]}")
        
        return self._spacy_available
    
    def extract_from_srt(self, srt_path: str, max_keywords: int = 30) -> List[str]:
        """Extract keywords from SRT file"""
        if not os.path.exists(srt_path):
            print(f"[Keywords] file not found: {srt_path}")
            return []
        
        # read and parse SRT
        with open(srt_path, "r", encoding="utf-8") as f:
            content = f.read()
        
        text = self._parse_srt(content)
        
        # extract keywords
        keywords = self._extract_keywords(text)
        
        # rank and return top N
        ranked = self._rank_keywords(keywords)[:max_keywords]
        
        print(f"[Keywords] extracted {len(ranked)} keywords from {os.path.basename(srt_path)}")
        return ranked
    
    def _parse_srt(self, content: str) -> str:
        """Parse SRT format and extract just the text"""
        lines = content.split("\n")
        text_lines = []
        
        for line in lines:
            line = line.strip()
            # skip empty, numbers, timestamps
            if not line:
                continue
            if line.isdigit():
                continue
            if "-->" in line:
                continue
            
            text_lines.append(line)
        
        return " ".join(text_lines)
    
    def _extract_keywords(self, text: str) -> List[str]:
        """Extract candidate keywords using multiple methods"""
        keywords = []
        
        # method 1: simple word extraction (always works)
        words = re.findall(r'\b[a-zA-Z]{3,}\b', text.lower())
        filtered = [w for w in words if w not in self.STOP_WORDS]
        keywords.extend(filtered)
        
        # method 2: try spacy ONLY if already installed (no auto-download)
        if self._check_spacy() and self.nlp:
            try:
                keywords.extend(self._extract_nouns_spacy(text))
            except Exception as e:
                print(f"[Keywords] spaCy extraction failed: {e}")
        
        # method 3: bigrams (two-word phrases)
        bigrams = self._extract_bigrams(text)
        keywords.extend(bigrams)
        
        # method 4: capitalized words (proper nouns)
        proper = self._extract_proper_nouns(text)
        keywords.extend(proper)
        
        return keywords
    
    def _extract_nouns_spacy(self, text: str) -> List[str]:
        """Use spaCy to extract nouns (ONLY if already loaded)"""
        if not self.nlp:
            return []
        
        doc = self.nlp(text)
        nouns = []
        
        # get nouns
        for token in doc:
            if token.pos_ in ["NOUN", "PROPN"] and len(token.text) > 2:
                word = token.text.lower()
                if word not in self.STOP_WORDS:
                    nouns.append(word)
        
        # get noun phrases
        for chunk in doc.noun_chunks:
            if len(chunk.text.split()) <= 3:
                phrase = chunk.text.lower()
                first_word = phrase.split()[0]
                if first_word not in self.STOP_WORDS:
                    nouns.append(phrase)
        
        return nouns
    
    def _extract_bigrams(self, text: str) -> List[str]:
        """Extract two-word phrases"""
        words = re.findall(r'\b[a-zA-Z]{3,}\b', text.lower())
        bigrams = []
        
        for i in range(len(words) - 1):
            w1, w2 = words[i], words[i + 1]
            if w1 not in self.STOP_WORDS and w2 not in self.STOP_WORDS:
                bigrams.append(f"{w1} {w2}")
        
        return bigrams
    
    def _extract_proper_nouns(self, text: str) -> List[str]:
        """Extract capitalized words that might be proper nouns"""
        # Find words that start with capital letter
        proper = re.findall(r'\b[A-Z][a-z]{2,}\b', text)
        return [p.lower() for p in proper if p.lower() not in self.STOP_WORDS]
    
    def _rank_keywords(self, keywords: List[str]) -> List[str]:
        """Rank keywords by frequency and quality"""
        # count occurrences
        counts = Counter(keywords)
        
        # score each keyword
        scored = []
        for kw, count in counts.items():
            score = count
            
            # boost certain words
            for boost_word in self.BOOST_WORDS:
                if boost_word in kw:
                    score *= 2
                    break
            
            # prefer single nouns for image search
            if len(kw.split()) == 1:
                score *= 1.5
            
            # boost longer words (more specific)
            if len(kw) > 6:
                score *= 1.2
            
            scored.append((kw, score))
        
        # sort by score
        scored.sort(key=lambda x: x[1], reverse=True)
        
        return [kw for kw, _ in scored]


def test_extractor():
    """Quick test"""
    extractor = KeywordExtractor()
    
    test_srt = """1
00:00:00,000 --> 00:00:05,000
Today we're going to explore the beautiful mountains of Colorado.

2
00:00:05,000 --> 00:00:10,000
The Rocky Mountains offer amazing hiking trails and stunning landscapes.

3
00:00:10,000 --> 00:00:15,000
We'll see wildlife including bears, deer, and eagles.
"""
    
    import tempfile
    with tempfile.NamedTemporaryFile(mode="w", suffix=".srt", delete=False) as f:
        f.write(test_srt)
        temp_path = f.name
    
    keywords = extractor.extract_from_srt(temp_path)
    print(f"[Test] Keywords: {keywords[:10]}")
    
    os.unlink(temp_path)


if __name__ == "__main__":
    test_extractor()
