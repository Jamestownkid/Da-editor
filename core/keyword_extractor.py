"""
Da Editor - Keyword Extractor
==============================
1a. extracts keywords from SRT files
1b. uses NLP to find nouns and key phrases
1c. filters and ranks by importance
"""

import os
import re
from typing import List
from collections import Counter


class KeywordExtractor:
    """
    extract searchable keywords from SRT transcripts
    
    1a. parses SRT format
    1b. extracts nouns and key phrases
    1c. returns ranked list of keywords
    """
    
    # common words we wanna skip - they aint gonna give good images
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
        "okay", "ok", "right", "yes", "no", "maybe", "probably", "definitely"
    }
    
    # words that usually give good image results
    BOOST_WORDS = {
        "mountain", "ocean", "city", "nature", "sunset", "sunrise", "landscape",
        "building", "architecture", "technology", "science", "art", "music",
        "sports", "food", "travel", "adventure", "business", "money", "health",
        "fitness", "fashion", "beauty", "animals", "wildlife", "space", "universe"
    }
    
    def __init__(self):
        self.nlp = None  # lazy load spacy
        print("[Keywords] extractor ready")
    
    def extract_from_srt(self, srt_path: str, max_keywords: int = 30) -> List[str]:
        """
        1a. extract keywords from SRT file
        """
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
        """
        1b. parse SRT format and extract just the text
        """
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
            
            # this is actual text
            text_lines.append(line)
        
        return " ".join(text_lines)
    
    def _extract_keywords(self, text: str) -> List[str]:
        """
        2a. extract candidate keywords using multiple methods
        """
        keywords = []
        
        # method 1: simple word extraction
        words = re.findall(r'\b[a-zA-Z]{3,}\b', text.lower())
        filtered = [w for w in words if w not in self.STOP_WORDS]
        keywords.extend(filtered)
        
        # method 2: try spacy for noun extraction if available
        try:
            keywords.extend(self._extract_nouns_spacy(text))
        except:
            pass
        
        # method 3: look for two-word phrases (bigrams)
        bigrams = self._extract_bigrams(text)
        keywords.extend(bigrams)
        
        return keywords
    
    def _extract_nouns_spacy(self, text: str) -> List[str]:
        """
        2b. use spacy to extract nouns and noun phrases
        """
        try:
            import spacy
            
            if self.nlp is None:
                try:
                    self.nlp = spacy.load("en_core_web_sm")
                except:
                    # try downloading if not present
                    import subprocess
                    subprocess.run(["python", "-m", "spacy", "download", "en_core_web_sm"])
                    self.nlp = spacy.load("en_core_web_sm")
            
            doc = self.nlp(text)
            nouns = []
            
            # get nouns
            for token in doc:
                if token.pos_ in ["NOUN", "PROPN"] and len(token.text) > 2:
                    nouns.append(token.text.lower())
            
            # get noun phrases
            for chunk in doc.noun_chunks:
                if len(chunk.text.split()) <= 3:  # max 3 words
                    phrase = chunk.text.lower()
                    # filter out phrases starting with stop words
                    first_word = phrase.split()[0]
                    if first_word not in self.STOP_WORDS:
                        nouns.append(phrase)
            
            return nouns
            
        except Exception as e:
            print(f"[Keywords] spacy extraction failed: {e}")
            return []
    
    def _extract_bigrams(self, text: str) -> List[str]:
        """
        2c. extract two-word phrases
        """
        words = re.findall(r'\b[a-zA-Z]{3,}\b', text.lower())
        bigrams = []
        
        for i in range(len(words) - 1):
            w1, w2 = words[i], words[i + 1]
            if w1 not in self.STOP_WORDS and w2 not in self.STOP_WORDS:
                bigrams.append(f"{w1} {w2}")
        
        return bigrams
    
    def _rank_keywords(self, keywords: List[str]) -> List[str]:
        """
        3a. rank keywords by frequency and quality
        """
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
            
            scored.append((kw, score))
        
        # sort by score
        scored.sort(key=lambda x: x[1], reverse=True)
        
        # return just the keywords
        return [kw for kw, _ in scored]


def test_extractor():
    """quick test with sample text"""
    extractor = KeywordExtractor()
    
    # create a test SRT
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
    
    # save temp file
    import tempfile
    with tempfile.NamedTemporaryFile(mode="w", suffix=".srt", delete=False) as f:
        f.write(test_srt)
        temp_path = f.name
    
    # extract keywords
    keywords = extractor.extract_from_srt(temp_path)
    print(f"[Test] Keywords: {keywords[:10]}")
    
    # cleanup
    os.unlink(temp_path)


if __name__ == "__main__":
    test_extractor()
