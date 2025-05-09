import numpy as np
import logging
import sys
from functools import lru_cache # For caching embeddings and tokenizations

# --- Platform Check for NLEmbedding ---
# NLEmbedding is macOS-specific (Darwin)
IS_DARWIN = sys.platform == "darwin"

if IS_DARWIN:
    try:
        from NaturalLanguage import NLEmbedding, NLTokenizer, NLTokenUnitWord
        from Foundation import NSMakeRange # Used by NLTokenizer
    except ImportError as e:
        # This can happen if PyObjC or its NaturalLanguage bindings are not installed
        raise RuntimeError(
            f"Failed to import Apple NaturalLanguage frameworks (PyObjC). "
            f"Ensure 'pyobjc-framework-Cocoa' and potentially other 'pyobjc-framework-*' "
            f"are installed. Original error: {e}"
        )
else:
    # Define stubs or raise errors for non-Darwin platforms if these features are critical
    NLEmbedding = None
    NLTokenizer = None
    NLTokenUnitWord = None
    NSMakeRange = None
    # Optionally, print a warning that NLP features will be limited
    # print("Warning: NLP embedding features are only available on macOS. Text search will be token-based only.")


# --- Logging Configuration ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# --- Embedding Model Initialization (macOS only) ---
apple_embed_model = None
EMBEDDING_DIM = 0  # Default to 0, will be updated if model loads

if IS_DARWIN and NLEmbedding:
    try:
        # Initialize Apple's sentence contextual embedding model for English
        apple_embed_model = NLEmbedding.sentenceEmbeddingForLanguage_("en")
        if apple_embed_model is None:
            # This can happen if the language model isn't available on the system
            raise RuntimeError("NLEmbedding.sentenceEmbeddingForLanguage_('en') returned None. Ensure English language support is available.")
        
        EMBEDDING_DIM = apple_embed_model.dimension()
        logger.info(f"Successfully loaded Apple NLEmbedding model for English. Dimension: {EMBEDDING_DIM}.")

        # Sanity check for the method existence
        if not hasattr(apple_embed_model, 'vectorForString_'):
            # This is a more critical error, indicating an issue with the PyObjC bindings or macOS version
            logger.error("Apple NLEmbedding model loaded but missing `vectorForString_` method. This may indicate an issue with PyObjC or macOS version compatibility.")
            apple_embed_model = None # Disable if critical method is missing
            EMBEDDING_DIM = 0
            # raise RuntimeError("Apple NLEmbedding model loaded but missing `vectorForString_` method.")

    except Exception as e:
        logger.error(f"Failed to initialize Apple NLEmbedding: {e}. Semantic search capabilities will be disabled.")
        apple_embed_model = None # Ensure it's None if initialization fails
        EMBEDDING_DIM = 0
else:
    logger.info("Running on non-macOS platform or NLEmbedding not available. Semantic search disabled; token-based search will be used.")


# --- Embedding Function ---
@lru_cache(maxsize=1024) # Cache results for recently processed texts
def get_embedding(text: str) -> np.ndarray:
    """
    Generates a sentence embedding for the given text using Apple's NLEmbedding.
    If NLEmbedding is unavailable or text is empty, returns a zero vector of EMBEDDING_DIM (if known) or an empty array.
    """
    if not IS_DARWIN or apple_embed_model is None:
        # logger.debug("NLEmbedding model not available. Returning zero/empty vector for embedding.")
        return np.zeros(EMBEDDING_DIM, dtype=np.float32) if EMBEDDING_DIM > 0 else np.array([], dtype=np.float32)

    if not text or text.isspace():
        logger.warning("Input text for embedding is empty or whitespace. Returning zero vector.")
        return np.zeros(EMBEDDING_DIM, dtype=np.float32)

    # Split text into sentences/lines and average their embeddings for a more robust document representation.
    # NLEmbedding.vectorForString_ typically works best on sentence-like units.
    sentences = [line.strip() for line in text.splitlines() if line.strip()]
    if not sentences:
        logger.warning("No non-empty lines found in text for embedding. Returning zero vector.")
        return np.zeros(EMBEDDING_DIM, dtype=np.float32)

    vecs = []
    for s in sentences:
        try:
            ns_vector = apple_embed_model.vectorForString_(s)
            if ns_vector: # ns_vector could be None if the string is problematic
                # Convert Objective-C NSArray of NSNumbers to a Python list of floats, then to NumPy array
                py_vector = [float(x) for x in ns_vector]
                vecs.append(np.array(py_vector, dtype=np.float32))
            else:
                logger.debug(f"NLEmbedding returned None for sentence: '{s[:50]}...'")
        except Exception as e:
            logger.error(f"Error getting vector for sentence '{s[:50]}...': {e}")
            continue # Skip problematic sentences

    if not vecs:
        logger.warning("No valid vectors generated for any sentence in the text. Returning zero vector.")
        return np.zeros(EMBEDDING_DIM, dtype=np.float32)

    # Calculate the mean of the sentence vectors
    mean_vector = np.mean(vecs, axis=0)
    return mean_vector.astype(np.float32)


# --- Cosine Similarity ---
def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    """
    Calculates the cosine similarity between two numpy vectors.

    Args:
        a: The first numpy array.
        b: The second numpy array.

    Returns:
        The cosine similarity score (float between -1 and 1),
        or 0.0 if either vector has zero magnitude or if inputs are incompatible.
    """
    if not isinstance(a, np.ndarray) or not isinstance(b, np.ndarray):
        logger.warning("Cosine similarity called with non-NumPy array inputs.")
        return 0.0
    if a.size == 0 or b.size == 0: # Handle empty embeddings
        # logger.debug("Cosine similarity: one or both vectors are empty.")
        return 0.0
    if a.shape != b.shape:
        logger.warning(f"Cosine similarity: vector shapes mismatch: {a.shape} vs {b.shape}.")
        return 0.0

    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)

    if norm_a == 0 or norm_b == 0:
        # logger.debug("Cosine similarity: one or both vectors have zero magnitude.")
        return 0.0

    similarity = np.dot(a, b) / (norm_a * norm_b)
    # Clip values to handle potential floating-point inaccuracies slightly outside [-1, 1]
    return float(np.clip(similarity, -1.0, 1.0))


# --- Tokenizer Initialization (macOS only) ---
tokenizer = None
if IS_DARWIN and NLTokenizer and NLTokenUnitWord:
    try:
        tokenizer = NLTokenizer.alloc().initWithUnit_(NLTokenUnitWord)
        if tokenizer is None:
             logger.error("Failed to initialize NLTokenizer.")
        else:
            logger.info("NLTokenizer for word tokenization initialized.")
    except Exception as e:
        logger.error(f"Error initializing NLTokenizer: {e}")
        tokenizer = None # Ensure it's None on failure
else:
    logger.info("Running on non-macOS platform or NLTokenizer not available. Using basic split for tokenization.")


# --- Tokenization Function ---
@lru_cache(maxsize=2048) # Cache tokenization results
def tokenize_text(text: str) -> set:
    """
    Tokenizes the text into a set of unique lowercase word tokens.
    Uses Apple's NLTokenizer on macOS, otherwise falls back to a simple split-based method.
    """
    if not text or text.isspace():
        return set()

    text_lower = text.lower() # Normalize to lowercase first

    if IS_DARWIN and tokenizer and NSMakeRange:
        try:
            tokenizer.setString_(text_lower) # Tokenize the lowercased string
            tokens = set()
            # NSMakeRange(0, len(text_lower)) is crucial for tokenizing the entire string
            for token_range in tokenizer.tokensForRange_(NSMakeRange(0, len(text_lower))):
                # The rangeValue() gives the range within the original string (text_lower)
                r = token_range.rangeValue()
                token = text_lower[r.location : r.location + r.length]
                tokens.add(token)
            return tokens
        except Exception as e:
            logger.warning(f"NLTokenizer error during tokenization: {e}. Falling back to basic split.")
            # Fallthrough to basic split if NLTokenizer fails

    # Fallback for non-macOS or if NLTokenizer failed
    # Basic split by whitespace and common punctuation (can be improved)
    import re
    # Split by non-alphanumeric characters, keeping alphanumeric sequences as tokens
    split_tokens = re.findall(r'[a-z0-9]+', text_lower)
    return set(s for s in split_tokens if s) # Filter out any empty strings that might result

# --- Example Usage (for testing if run directly) ---
if __name__ == "__main__":
    logger.info("Running nlp.py directly for testing...")

    test_text_1 = "Hello world! This is a test sentence for Apple's NLEmbedding."
    test_text_2 = "A completely different sentence to check similarity."
    test_text_3 = "Hello world, this is quite similar."
    empty_text = "   "
    
    print(f"\n--- Tokenization Test ---")
    print(f"Text: '{test_text_1}'")
    print(f"Tokens: {tokenize_text(test_text_1)}")
    print(f"Text: 'Another test with numbers 123 and symbols !@#$'")
    print(f"Tokens: {tokenize_text('Another test with numbers 123 and symbols !@#$')}")
    print(f"Text (empty): '{empty_text}'")
    print(f"Tokens: {tokenize_text(empty_text)}")

    if IS_DARWIN and apple_embed_model:
        print(f"\n--- Embedding and Similarity Test (macOS) ---")
        emb1 = get_embedding(test_text_1)
        emb2 = get_embedding(test_text_2)
        emb3 = get_embedding(test_text_3)
        emb_empty = get_embedding(empty_text)

        print(f"Embedding for text 1 (shape {emb1.shape}): {emb1[:5]}...") # Print first 5 dimensions
        print(f"Embedding for empty text (shape {emb_empty.shape}): {emb_empty[:5]}...")

        if emb1.size > 0 and emb2.size > 0 and emb3.size > 0:
            sim_1_2 = cosine_similarity(emb1, emb2)
            sim_1_3 = cosine_similarity(emb1, emb3)
            sim_1_empty = cosine_similarity(emb1, emb_empty)
            print(f"Similarity (Text 1 vs Text 2): {sim_1_2:.4f}")
            print(f"Similarity (Text 1 vs Text 3): {sim_1_3:.4f}") # Expect higher similarity
            print(f"Similarity (Text 1 vs Empty Text): {sim_1_empty:.4f}")
        else:
            print("Embeddings not generated, skipping similarity calculation.")
    else:
        print("\n--- Embedding and Similarity Test (Skipped on non-macOS or if model failed) ---")

    print("\n--- Testing tokenization cache ---")
    tokenize_text("Cache test one.")
    tokenize_text("Cache test one.") # Should be faster
    print("Done with nlp.py tests.")