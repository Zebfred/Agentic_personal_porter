"""
Comparative analysis tests for chunking strategies.

This module provides side-by-side comparisons of different chunking strategies
with metrics, statistics, and quality assessments.
"""

import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import pytest
import numpy as np
from data_pipeline.chunking import (
    FixedSizeChunking,
    FastSemanticChunking,
    ScienceDetailSemanticChunking,
    DocumentChunker
)
from sentence_transformers import SentenceTransformer


def load_sample_paper_text():
    """Load sample scientific paper text for testing."""
    return """
    Proximal Policy Optimization Algorithms
    
    Abstract
    
    We propose a new family of policy gradient methods for reinforcement learning, 
    which alternate between sampling data through interaction with the environment, 
    and optimizing a "surrogate" objective function using stochastic gradient ascent. 
    Whereas standard policy gradient methods perform one gradient update per data sample, 
    we propose a novel objective function that enables multiple epochs of minibatch updates. 
    The new methods, which we call proximal policy optimization (PPO), have some of the 
    benefits of trust region policy optimization (TRPO), but they are much simpler to 
    implement, more general, and have better sample complexity (empirically).
    
    1. Introduction
    
    Reinforcement learning (RL) is a subfield of machine learning that focuses on how 
    intelligent agents should take actions in an environment to maximize the notion of 
    cumulative reward. Unlike supervised learning, RL does not require labeled 
    input/output pairs, and unlike unsupervised learning, it does not require finding 
    hidden structure in unlabeled data.
    
    Policy gradient methods are a class of reinforcement learning algorithms that 
    optimize the policy directly. The policy is typically parameterized by a neural 
    network, and the parameters are updated using gradient ascent on the expected return.
    
    2. Background
    
    In policy gradient methods, the objective is to maximize the expected return. 
    The policy gradient theorem provides a way to compute the gradient of the expected 
    return with respect to the policy parameters. This gradient can be estimated using 
    samples from the current policy.
    
    Trust Region Policy Optimization (TRPO) is a policy gradient method that uses a 
    trust region constraint to ensure that policy updates are not too large. However, 
    TRPO is computationally expensive and difficult to implement.
    
    3. Proximal Policy Optimization
    
    Proximal Policy Optimization (PPO) is a simpler alternative to TRPO that achieves 
    similar performance. PPO uses a clipped objective function that prevents the policy 
    from changing too much in a single update. This clipping mechanism acts as a trust 
    region constraint without requiring the expensive computation of the natural policy gradient.
    
    The PPO objective function is designed to be simple to implement and computationally 
    efficient. It can be optimized using standard stochastic gradient ascent methods, 
    making it more practical than TRPO for many applications.
    
    4. Experiments
    
    We tested PPO on a collection of benchmark tasks, including simulated robotic 
    locomotion and Atari game playing. Our experiments show that PPO outperforms other 
    online policy gradient methods, and overall strikes a favorable balance between 
    sample complexity, simplicity, and wall-time.
    
    The results demonstrate that PPO achieves state-of-the-art performance on many 
    benchmark tasks while being significantly simpler to implement than TRPO.
    """


def analyze_chunks(chunks, strategy_name):
    """Analyze and return statistics about chunks."""
    if not chunks:
        return {
            'strategy': strategy_name,
            'chunk_count': 0,
            'avg_chunk_size': 0,
            'min_chunk_size': 0,
            'max_chunk_size': 0,
            'std_chunk_size': 0,
            'total_chars': 0
        }
    
    chunk_sizes = [len(chunk.get('text', '')) for chunk in chunks]
    
    return {
        'strategy': strategy_name,
        'chunk_count': len(chunks),
        'avg_chunk_size': np.mean(chunk_sizes),
        'min_chunk_size': np.min(chunk_sizes),
        'max_chunk_size': np.max(chunk_sizes),
        'std_chunk_size': np.std(chunk_sizes),
        'total_chars': sum(chunk_sizes),
        'median_chunk_size': np.median(chunk_sizes)
    }


def measure_semantic_coherence(chunks, model_name="all-MiniLM-L6-v2"):
    """Measure semantic coherence within chunks."""
    if not chunks:
        return {'avg_coherence': 0, 'min_coherence': 0, 'max_coherence': 0}
    
    model = SentenceTransformer(model_name)
    coherence_scores = []
    
    for chunk in chunks:
        text = chunk.get('text', '')
        # Split into sentences (simple approach)
        sentences = [s.strip() for s in text.split('.') if len(s.strip()) > 10]
        
        if len(sentences) < 2:
            continue
        
        # Get embeddings
        embeddings = model.encode(sentences)
        
        # Calculate pairwise similarities
        similarities = []
        for i in range(len(embeddings) - 1):
            sim = np.dot(embeddings[i], embeddings[i+1]) / (
                np.linalg.norm(embeddings[i]) * np.linalg.norm(embeddings[i+1])
            )
            similarities.append(sim)
        
        if similarities:
            coherence_scores.append(np.mean(similarities))
    
    if not coherence_scores:
        return {'avg_coherence': 0, 'min_coherence': 0, 'max_coherence': 0}
    
    return {
        'avg_coherence': np.mean(coherence_scores),
        'min_coherence': np.min(coherence_scores),
        'max_coherence': np.max(coherence_scores),
        'std_coherence': np.std(coherence_scores)
    }


def test_chunking_strategies_comparison():
    """Compare all chunking strategies on the same text."""
    text = load_sample_paper_text()
    
    # Initialize all strategies
    fixed_chunker = FixedSizeChunking(chunk_size=1000, overlap=200)
    fast_semantic_chunker = FastSemanticChunking(
        chunk_size=1000, 
        similarity_threshold=0.5
    )
    science_semantic_chunker = ScienceDetailSemanticChunking(
        chunk_size=1000,
        similarity_threshold=0.5
    )
    
    # Generate chunks
    print("\n" + "="*80)
    print("CHUNKING STRATEGIES COMPARATIVE ANALYSIS")
    print("="*80)
    
    print("\nGenerating chunks with each strategy...")
    fixed_chunks = fixed_chunker.chunk(text)
    print(f"✓ Fixed-size: {len(fixed_chunks)} chunks")
    
    fast_semantic_chunks = fast_semantic_chunker.chunk(text)
    print(f"✓ Fast Semantic: {len(fast_semantic_chunks)} chunks")
    
    science_semantic_chunks = science_semantic_chunker.chunk(text)
    print(f"✓ Science Detail Semantic: {len(science_semantic_chunks)} chunks")
    
    # Analyze each strategy
    print("\n" + "-"*80)
    print("CHUNK STATISTICS")
    print("-"*80)
    
    fixed_stats = analyze_chunks(fixed_chunks, "Fixed-Size")
    fast_stats = analyze_chunks(fast_semantic_chunks, "Fast Semantic")
    science_stats = analyze_chunks(science_semantic_chunks, "Science Detail Semantic")
    
    all_stats = [fixed_stats, fast_stats, science_stats]
    
    # Print comparison table
    print(f"\n{'Strategy':<25} {'Count':<10} {'Avg Size':<12} {'Min':<10} {'Max':<10} {'Median':<10}")
    print("-" * 80)
    for stats in all_stats:
        print(f"{stats['strategy']:<25} "
              f"{stats['chunk_count']:<10} "
              f"{stats['avg_chunk_size']:<12.0f} "
              f"{stats['min_chunk_size']:<10.0f} "
              f"{stats['max_chunk_size']:<10.0f} "
              f"{stats['median_chunk_size']:<10.0f}")
    
    # Semantic coherence analysis
    print("\n" + "-"*80)
    print("SEMANTIC COHERENCE ANALYSIS")
    print("-"*80)
    print("(Higher scores indicate more semantically coherent chunks)")
    
    fixed_coherence = measure_semantic_coherence(fixed_chunks)
    fast_coherence = measure_semantic_coherence(fast_semantic_chunks)
    science_coherence = measure_semantic_coherence(science_semantic_chunks)
    
    print(f"\n{'Strategy':<25} {'Avg Coherence':<15} {'Min':<10} {'Max':<10}")
    print("-" * 80)
    print(f"{'Fixed-Size':<25} {fixed_coherence['avg_coherence']:<15.4f} "
          f"{fixed_coherence['min_coherence']:<10.4f} {fixed_coherence['max_coherence']:<10.4f}")
    print(f"{'Fast Semantic':<25} {fast_coherence['avg_coherence']:<15.4f} "
          f"{fast_coherence['min_coherence']:<10.4f} {fast_coherence['max_coherence']:<10.4f}")
    print(f"{'Science Detail Semantic':<25} {science_coherence['avg_coherence']:<15.4f} "
          f"{science_coherence['min_coherence']:<10.4f} {science_coherence['max_coherence']:<10.4f}")
    
    # Key findings
    print("\n" + "-"*80)
    print("KEY FINDINGS")
    print("-"*80)
    
    # Chunk count comparison
    counts = {
        'Fixed-Size': fixed_stats['chunk_count'],
        'Fast Semantic': fast_stats['chunk_count'],
        'Science Detail Semantic': science_stats['chunk_count']
    }
    most_chunks = max(counts, key=counts.get)
    fewest_chunks = min(counts, key=counts.get)
    print(f"\n📊 Chunk Count:")
    print(f"   Most chunks: {most_chunks} ({counts[most_chunks]} chunks)")
    print(f"   Fewest chunks: {fewest_chunks} ({counts[fewest_chunks]} chunks)")
    print(f"   Ratio: {counts[most_chunks] / counts[fewest_chunks]:.2f}x difference")
    
    # Size consistency
    size_consistency = {
        'Fixed-Size': fixed_stats['std_chunk_size'],
        'Fast Semantic': fast_stats['std_chunk_size'],
        'Science Detail Semantic': science_stats['std_chunk_size']
    }
    most_consistent = min(size_consistency, key=size_consistency.get)
    print(f"\n📏 Size Consistency (lower std = more consistent):")
    print(f"   Most consistent: {most_consistent} (std: {size_consistency[most_consistent]:.0f})")
    
    # Semantic coherence
    coherence_scores = {
        'Fixed-Size': fixed_coherence['avg_coherence'],
        'Fast Semantic': fast_coherence['avg_coherence'],
        'Science Detail Semantic': science_coherence['avg_coherence']
    }
    most_coherent = max(coherence_scores, key=coherence_scores.get)
    print(f"\n🧠 Semantic Coherence:")
    print(f"   Most coherent: {most_coherent} (score: {coherence_scores[most_coherent]:.4f})")
    
    # Assertions for pytest
    assert len(fixed_chunks) > 0, "Fixed-size chunking should produce chunks"
    assert len(fast_semantic_chunks) > 0, "Fast semantic chunking should produce chunks"
    assert len(science_semantic_chunks) > 0, "Science semantic chunking should produce chunks"
    
    # Return stats for further analysis
    return {
        'fixed': {'stats': fixed_stats, 'coherence': fixed_coherence, 'chunks': fixed_chunks},
        'fast_semantic': {'stats': fast_stats, 'coherence': fast_coherence, 'chunks': fast_semantic_chunks},
        'science_semantic': {'stats': science_stats, 'coherence': science_coherence, 'chunks': science_semantic_chunks}
    }


def test_chunk_boundary_quality():
    """Test how well chunk boundaries align with semantic boundaries."""
    text = load_sample_paper_text()
    
    fixed_chunker = FixedSizeChunking(chunk_size=1000, overlap=200)
    fast_semantic_chunker = FastSemanticChunking(chunk_size=1000, similarity_threshold=0.5)
    science_semantic_chunker = ScienceDetailSemanticChunking(chunk_size=1000, similarity_threshold=0.5)
    
    fixed_chunks = fixed_chunker.chunk(text)
    fast_chunks = fast_semantic_chunker.chunk(text)
    science_chunks = science_semantic_chunker.chunk(text)
    
    print("\n" + "="*80)
    print("CHUNK BOUNDARY QUALITY ANALYSIS")
    print("="*80)
    
    def analyze_boundaries(chunks, strategy_name):
        """Analyze chunk boundaries in detail."""
        breaks = 0
        endings = []
        problematic_chunks = []
        
        for i, chunk in enumerate(chunks):
            chunk_text = chunk.get('text', '').strip()
            if not chunk_text:
                continue
            
            # Get last 50 characters to see how chunk ends
            last_part = chunk_text[-50:] if len(chunk_text) > 50 else chunk_text
            endings.append(last_part)
            
            # Check if chunk ends with sentence-ending punctuation
            # Also check for newlines, whitespace that might hide the issue
            stripped = chunk_text.rstrip()
            if not stripped:
                continue
                
            last_char = stripped[-1]
            
            # Check for mid-sentence break
            # A proper sentence ending should be: . ! ? followed by optional quote/space
            is_sentence_end = (
                last_char in '.!?' or
                (last_char in '"\'' and len(stripped) > 1 and stripped[-2] in '.!?')
            )
            
            if not is_sentence_end:
                breaks += 1
                problematic_chunks.append({
                    'index': i,
                    'ending': last_part,
                    'last_char': repr(last_char)
                })
        
        return {
            'breaks': breaks,
            'total': len(chunks),
            'percentage': (breaks / len(chunks) * 100) if chunks else 0,
            'endings': endings[:3],  # Show first 3 endings as samples
            'problematic': problematic_chunks[:3]  # Show first 3 problematic chunks
        }
    
    fixed_analysis = analyze_boundaries(fixed_chunks, "Fixed-Size")
    fast_analysis = analyze_boundaries(fast_chunks, "Fast Semantic")
    science_analysis = analyze_boundaries(science_chunks, "Science Detail Semantic")
    
    print(f"\nMid-sentence breaks (chunks not ending with . ! ?):")
    print(f"  Fixed-Size: {fixed_analysis['breaks']}/{fixed_analysis['total']} chunks ({fixed_analysis['percentage']:.1f}%)")
    print(f"  Fast Semantic: {fast_analysis['breaks']}/{fast_analysis['total']} chunks ({fast_analysis['percentage']:.1f}%)")
    print(f"  Science Detail Semantic: {science_analysis['breaks']}/{science_analysis['total']} chunks ({science_analysis['percentage']:.1f}%)")
    
    # Show sample chunk endings
    print("\n" + "-"*80)
    print("SAMPLE CHUNK ENDINGS (last 50 chars of each chunk)")
    print("-"*80)
    
    print("\nFixed-Size (first 3 chunks):")
    for i, ending in enumerate(fixed_analysis['endings'], 1):
        print(f"  Chunk {i}: ...{ending[-30:]}")
    
    print("\nFast Semantic (first 3 chunks):")
    for i, ending in enumerate(fast_analysis['endings'], 1):
        print(f"  Chunk {i}: ...{ending[-30:]}")
    
    print("\nScience Detail Semantic (first 3 chunks):")
    for i, ending in enumerate(science_analysis['endings'], 1):
        print(f"  Chunk {i}: ...{ending[-30:]}")
    
    # Show problematic chunks if any
    if fixed_analysis['problematic'] or fast_analysis['problematic'] or science_analysis['problematic']:
        print("\n" + "-"*80)
        print("PROBLEMATIC CHUNKS (ending mid-sentence)")
        print("-"*80)
        
        if fixed_analysis['problematic']:
            print("\nFixed-Size:")
            for prob in fixed_analysis['problematic']:
                print(f"  Chunk {prob['index']}: ends with {prob['last_char']}")
                print(f"    ...{prob['ending'][-40:]}")
        
        if fast_analysis['problematic']:
            print("\nFast Semantic:")
            for prob in fast_analysis['problematic']:
                print(f"  Chunk {prob['index']}: ends with {prob['last_char']}")
                print(f"    ...{prob['ending'][-40:]}")
        
        if science_analysis['problematic']:
            print("\nScience Detail Semantic:")
            for prob in science_analysis['problematic']:
                print(f"  Chunk {prob['index']}: ends with {prob['last_char']}")
                print(f"    ...{prob['ending'][-40:]}")
    else:
        print("\n✓ All chunks appear to end at sentence boundaries!")
    
    # Additional analysis: check for incomplete sentences
    print("\n" + "-"*80)
    print("SENTENCE COMPLETENESS CHECK")
    print("-"*80)
    
    def check_sentence_completeness(chunks):
        """Check if chunks contain complete sentences."""
        incomplete = 0
        for chunk in chunks:
            text = chunk.get('text', '').strip()
            # Count sentences (simple heuristic: periods followed by space or end)
            sentences = [s.strip() for s in text.split('.') if s.strip()]
            # If last "sentence" doesn't end with punctuation, might be incomplete
            if sentences and not any(sentences[-1].endswith(p) for p in ['.', '!', '?', '"', "'"]):
                # Check if it's actually incomplete or just the last sentence
                last_sent = sentences[-1]
                # If it's very short or doesn't look like a complete thought
                if len(last_sent) < 20 and not any(word in last_sent.lower() for word in ['the', 'a', 'an', 'is', 'are']):
                    incomplete += 1
        return incomplete
    
    fixed_incomplete = check_sentence_completeness(fixed_chunks)
    fast_incomplete = check_sentence_completeness(fast_chunks)
    science_incomplete = check_sentence_completeness(science_chunks)
    
    print(f"Potentially incomplete sentences:")
    print(f"  Fixed-Size: {fixed_incomplete}/{len(fixed_chunks)} chunks")
    print(f"  Fast Semantic: {fast_incomplete}/{len(fast_chunks)} chunks")
    print(f"  Science Detail Semantic: {science_incomplete}/{len(science_chunks)} chunks")
    
    # Paragraph break analysis
    print("\n" + "-"*80)
    print("PARAGRAPH BOUNDARY ANALYSIS")
    print("-"*80)
    
    def analyze_paragraph_breaks(chunks, original_text):
        """Analyze if chunks break at paragraph boundaries."""
        # Split original text into paragraphs (double newlines or significant whitespace)
        paragraphs = [p.strip() for p in original_text.split('\n\n') if p.strip()]
        paragraph_starts = [original_text.find(p) for p in paragraphs]
        
        mid_paragraph_breaks = 0
        paragraph_boundary_breaks = 0
        break_details = []
        
        for i in range(len(chunks) - 1):
            current_chunk = chunks[i]
            next_chunk = chunks[i + 1]
            
            current_text = current_chunk.get('text', '')
            next_text = next_chunk.get('text', '')
            
            # Find where current chunk ends in original text
            # This is approximate - we'll use chunk boundaries
            current_end_pos = current_chunk.get('end_char', len(current_text))
            
            # Check if break is at paragraph boundary
            # A paragraph boundary is typically: end of paragraph + whitespace + start of next
            is_paragraph_boundary = False
            
            # Check if the break point aligns with paragraph boundaries
            for para_start in paragraph_starts:
                # Allow some tolerance (within 50 chars)
                if abs(current_end_pos - para_start) < 50:
                    is_paragraph_boundary = True
                    break
            
            # Also check if chunk ends with paragraph-like structure
            # (ends with sentence + whitespace, next starts with capital or number)
            current_ends_clean = current_text.rstrip()
            next_starts_clean = next_text.lstrip()
            
            if current_ends_clean and next_starts_clean:
                # Check for paragraph-like break: ends with punctuation, next starts with capital/number
                ends_with_punct = current_ends_clean[-1] in '.!?'
                starts_with_capital = next_starts_clean[0].isupper() or next_starts_clean[0].isdigit()
                
                if ends_with_punct and starts_with_capital:
                    # Check if there's significant whitespace (paragraph break)
                    # This is heuristic - we'll check if chunks are separated
                    is_paragraph_boundary = True
            
            if is_paragraph_boundary:
                paragraph_boundary_breaks += 1
            else:
                mid_paragraph_breaks += 1
                # Store details for first few problematic breaks
                if len(break_details) < 3:
                    break_details.append({
                        'chunk_index': i,
                        'current_ending': current_ends_clean[-30:] if len(current_ends_clean) > 30 else current_ends_clean,
                        'next_starting': next_starts_clean[:30] if len(next_starts_clean) > 30 else next_starts_clean
                    })
        
        total_breaks = len(chunks) - 1
        return {
            'mid_paragraph': mid_paragraph_breaks,
            'paragraph_boundary': paragraph_boundary_breaks,
            'total_breaks': total_breaks,
            'paragraph_boundary_percentage': (paragraph_boundary_breaks / total_breaks * 100) if total_breaks > 0 else 0,
            'break_details': break_details
        }
    
    fixed_para_analysis = analyze_paragraph_breaks(fixed_chunks, text)
    fast_para_analysis = analyze_paragraph_breaks(fast_chunks, text)
    science_para_analysis = analyze_paragraph_breaks(science_chunks, text)
    
    print(f"\nParagraph boundary breaks (chunks breaking at paragraph boundaries):")
    print(f"  Fixed-Size: {fixed_para_analysis['paragraph_boundary']}/{fixed_para_analysis['total_breaks']} breaks ({fixed_para_analysis['paragraph_boundary_percentage']:.1f}%)")
    print(f"  Fast Semantic: {fast_para_analysis['paragraph_boundary']}/{fast_para_analysis['total_breaks']} breaks ({fast_para_analysis['paragraph_boundary_percentage']:.1f}%)")
    print(f"  Science Detail Semantic: {science_para_analysis['paragraph_boundary']}/{science_para_analysis['total_breaks']} breaks ({science_para_analysis['paragraph_boundary_percentage']:.1f}%)")
    
    if fixed_para_analysis['break_details'] or fast_para_analysis['break_details'] or science_para_analysis['break_details']:
        print("\nMid-paragraph breaks (first 3 examples):")
        if fixed_para_analysis['break_details']:
            print("\n  Fixed-Size:")
            for detail in fixed_para_analysis['break_details']:
                print(f"    Break after chunk {detail['chunk_index']}:")
                print(f"      ...{detail['current_ending']}")
                print(f"      {detail['next_starting']}...")
    
    # Overlap quality analysis
    print("\n" + "-"*80)
    print("OVERLAP QUALITY ANALYSIS")
    print("-"*80)
    print("(Only applies to Fixed-Size chunking with overlap)")
    
    def analyze_overlap_quality(chunks, overlap_size=200):
        """Analyze the quality of overlaps between chunks."""
        if len(chunks) < 2:
            return {
                'total_overlaps': 0,
                'meaningful_overlaps': 0,
                'sentence_boundary_overlaps': 0,
                'avg_overlap_size': 0
            }
        
        meaningful_overlaps = 0
        sentence_boundary_overlaps = 0
        overlap_sizes = []
        
        for i in range(len(chunks) - 1):
            current_chunk = chunks[i]
            next_chunk = chunks[i + 1]
            
            current_text = current_chunk.get('text', '').strip()
            next_text = next_chunk.get('text', '').strip()
            
            # Find overlap by comparing end of current with start of next
            # Simple approach: check last N chars of current vs first N chars of next
            max_check = min(len(current_text), len(next_text), overlap_size * 2)
            
            overlap_found = False
            overlap_length = 0
            
            # Check for overlapping text
            for check_len in range(50, max_check, 10):  # Check in increments
                current_end = current_text[-check_len:]
                next_start = next_text[:check_len]
                
                # Find longest common substring
                if current_end in next_text or next_start in current_text:
                    overlap_length = check_len
                    overlap_found = True
                    break
            
            if overlap_found:
                overlap_sizes.append(overlap_length)
                
                # Check if overlap starts/ends at sentence boundary
                # Get the overlap region
                current_end = current_text[-overlap_length:]
                next_start = next_text[:overlap_length]
                
                # Check if overlap region starts with sentence beginning (capital letter after punctuation)
                # or ends with sentence ending (punctuation)
                starts_at_sentence = (
                    next_start[0].isupper() or
                    (len(next_start) > 1 and next_start[0] in ' \n' and next_start[1].isupper())
                )
                ends_at_sentence = current_end[-1] in '.!?'
                
                if starts_at_sentence or ends_at_sentence:
                    sentence_boundary_overlaps += 1
                
                # Check if overlap is "meaningful" (contains complete words, not mid-word)
                # Simple heuristic: check if overlap contains spaces (suggests complete words)
                if ' ' in current_end or ' ' in next_start:
                    meaningful_overlaps += 1
        
        total_overlaps = len(chunks) - 1
        return {
            'total_overlaps': total_overlaps,
            'meaningful_overlaps': meaningful_overlaps,
            'meaningful_percentage': (meaningful_overlaps / total_overlaps * 100) if total_overlaps > 0 else 0,
            'sentence_boundary_overlaps': sentence_boundary_overlaps,
            'sentence_boundary_percentage': (sentence_boundary_overlaps / total_overlaps * 100) if total_overlaps > 0 else 0,
            'avg_overlap_size': np.mean(overlap_sizes) if overlap_sizes else 0,
            'overlap_sizes': overlap_sizes
        }
    
    # Only Fixed-Size chunking uses overlap
    fixed_overlap_analysis = analyze_overlap_quality(fixed_chunks, overlap_size=200)
    
    print(f"\nFixed-Size Overlap Analysis (target overlap: 200 chars):")
    print(f"  Total overlaps: {fixed_overlap_analysis['total_overlaps']}")
    print(f"  Meaningful overlaps (contain complete words): {fixed_overlap_analysis['meaningful_overlaps']}/{fixed_overlap_analysis['total_overlaps']} ({fixed_overlap_analysis['meaningful_percentage']:.1f}%)")
    print(f"  Sentence boundary overlaps: {fixed_overlap_analysis['sentence_boundary_overlaps']}/{fixed_overlap_analysis['total_overlaps']} ({fixed_overlap_analysis['sentence_boundary_percentage']:.1f}%)")
    print(f"  Average overlap size: {fixed_overlap_analysis['avg_overlap_size']:.0f} characters")
    
    # Overlap quality score
    if fixed_overlap_analysis['total_overlaps'] > 0:
        quality_score = (
            (fixed_overlap_analysis['meaningful_percentage'] / 100) * 0.5 +
            (fixed_overlap_analysis['sentence_boundary_percentage'] / 100) * 0.5
        )
        print(f"  Overall overlap quality score: {quality_score:.2f}/1.0")
        print(f"    (0.5 = meaningful overlaps, 0.5 = sentence boundaries)")
    
    # For semantic chunking, check if there's any natural overlap/continuity
    print(f"\nSemantic Chunking Continuity (no explicit overlap, but check for context preservation):")
    
    def check_semantic_continuity(chunks):
        """Check if semantic chunks maintain context continuity."""
        continuity_scores = []
        
        for i in range(len(chunks) - 1):
            current_chunk = chunks[i]
            next_chunk = chunks[i + 1]
            
            current_text = current_chunk.get('text', '').strip()
            next_text = next_chunk.get('text', '').strip()
            
            # Check if chunks are topically related
            # Simple heuristic: check for common words (excluding very common words)
            current_words = set(word.lower() for word in current_text.split() if len(word) > 4)
            next_words = set(word.lower() for word in next_text.split() if len(word) > 4)
            
            common_words = current_words.intersection(next_words)
            # Exclude very common words
            stop_words = {'that', 'this', 'with', 'from', 'their', 'there', 'these', 'those', 'which', 'would'}
            common_words = common_words - stop_words
            
            if len(current_words) > 0 and len(next_words) > 0:
                continuity = len(common_words) / max(len(current_words), len(next_words))
                continuity_scores.append(continuity)
        
        return {
            'avg_continuity': np.mean(continuity_scores) if continuity_scores else 0,
            'min_continuity': np.min(continuity_scores) if continuity_scores else 0,
            'max_continuity': np.max(continuity_scores) if continuity_scores else 0
        }
    
    fast_continuity = check_semantic_continuity(fast_chunks)
    science_continuity = check_semantic_continuity(science_chunks)
    
    print(f"  Fast Semantic continuity: {fast_continuity['avg_continuity']:.3f} (higher = better context preservation)")
    print(f"  Science Detail Semantic continuity: {science_continuity['avg_continuity']:.3f} (higher = better context preservation)")
    
    assert True  # Test always passes, this is for analysis


if __name__ == "__main__":
    # Run comparative analysis
    print("Running comparative chunking analysis...")
    test_chunking_strategies_comparison()
    test_chunk_boundary_quality()
    print("\n" + "="*80)
    print("Analysis complete!")
    print("="*80)

