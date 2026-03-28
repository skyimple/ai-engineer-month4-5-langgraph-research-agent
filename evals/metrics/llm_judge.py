"""Shared LLM helper and combined evaluation for metrics."""

import os
import re
from typing import List, Dict, Any, Optional

from langchain_openai import ChatOpenAI
from dotenv import load_dotenv

load_dotenv('config.env')

_llm_instance = None


def get_llm() -> ChatOpenAI:
    """Get or create a cached ChatOpenAI instance for evaluation."""
    global _llm_instance
    if _llm_instance is None:
        api_key = os.getenv("DASHSCOPE_API_KEY")
        if not api_key:
            raise ValueError("DASHSCOPE_API_KEY not set")
        _llm_instance = ChatOpenAI(
            model="qwen3.5-plus",
            temperature=0.0,
            max_tokens=300,
            api_key=api_key,
            base_url="https://dashscope.aliyuncs.com/compatible-mode/v1"
        )
    return _llm_instance


def evaluate_all_metrics(
    answer: str,
    sources: List[Dict[str, Any]],
    topic: str,
    golden_answer: str = "",
    key_points: Optional[List[str]] = None
) -> Dict[str, float]:
    """Evaluate all metrics in a single LLM call.

    Args:
        answer: The generated report
        sources: List of source dicts with 'title', 'url', 'body'
        topic: The research topic
        golden_answer: Optional golden standard answer
        key_points: Optional list of key evaluation points

    Returns:
        Dict with faithfulness, relevance, source_accuracy, coverage scores
    """
    # Faithfulness and source_accuracy are 0 if no sources
    if not sources:
        # Only relevance can be evaluated without sources
        relevance = _evaluate_relevance_only(answer, topic, golden_answer, key_points)
        return {
            "faithfulness": 0.0,
            "relevance": relevance,
            "source_accuracy": 0.0,
            "coverage": 0.0
        }

    api_key = os.getenv("DASHSCOPE_API_KEY")
    if not api_key:
        return {
            "faithfulness": 0.5,
            "relevance": 0.5,
            "source_accuracy": 0.5,
            "coverage": 0.5
        }

    llm = get_llm()

    # Build source context
    source_context = "\n".join([
        f"- {s.get('title', 'Unknown')}: {s.get('url', 'N/A')}\n  {s.get('snippet', s.get('body', ''))[:200]}"
        for s in sources[:10]
    ])

    # Build key points text
    key_points_text = ""
    if key_points:
        key_points_text = "\n关键评估点:\n" + "\n".join(f"- {kp}" for kp in key_points)

    # Build golden answer text
    golden_text = ""
    if golden_answer:
        golden_text = f"\n标准答案:\n{golden_answer[:1000]}\n"

    prompt = f"""你是一个评估专家。请对以下研究报告进行多维度评估。

研究主题: {topic}
{key_points_text}{golden_text}
报告内容:
{answer[:2000]}

参考资料:
{source_context}

请从以下4个维度分别给出0-1之间的分数：

1. 忠实度(faithfulness)：报告是否基于参考资料中的信息，而非凭空编造
2. 相关性(relevance)：报告是否紧扣主题，覆盖了核心方面
3. 来源准确性(source_accuracy)：来源是否与主题相关，来自可信网站
4. 覆盖率(coverage)：报告覆盖了多少关键评估点

输出格式（每行一个分数）：
faithfulness: 0.XX
relevance: 0.XX
source_accuracy: 0.XX
coverage: 0.XX
"""

    try:
        response = llm.invoke(prompt)
        content = response.content.strip()
        print(f"    LLM judge response:\n{content}")

        def extract_score(name):
            # Try multiple patterns to handle various LLM output formats
            patterns = [
                rf'{name}\s*[：:]\s*(\d+\.?\d*)',  # faithfulness: 0.85 or faithfulness：0.85
                rf'{name}[^0-9]*?(\d+\.?\d*)',      # faithfulness)... 0.85
            ]
            for pattern in patterns:
                match = re.search(pattern, content, re.IGNORECASE)
                if match:
                    score = float(match.group(1))
                    return min(score, 1.0)
            print(f"    WARNING: Could not extract score for '{name}' from response")
            return 0.5

        result = {
            "faithfulness": extract_score("faithfulness"),
            "relevance": extract_score("relevance"),
            "source_accuracy": extract_score("source_accuracy"),
            "coverage": extract_score("coverage")
        }
        print(f"    Extracted scores: {result}")
        return result
    except Exception as e:
        print(f"Combined evaluation error: {e}")
        return {
            "faithfulness": 0.5,
            "relevance": 0.5,
            "source_accuracy": 0.5,
            "coverage": 0.5
        }


def _evaluate_relevance_only(
    answer: str,
    topic: str,
    golden_answer: str = "",
    key_points: Optional[List[str]] = None
) -> float:
    """Evaluate relevance only (used when no sources available)."""
    api_key = os.getenv("DASHSCOPE_API_KEY")
    if not api_key:
        return 0.5

    try:
        llm = get_llm()
        prompt = f"""你是一个评估专家。请评估以下答案与研究主题的相关程度。

研究主题: {topic}

答案:
{answer[:2000]}

请给出0-1之间的分数，0表示完全不相关，1表示完全相关。
只需输出一个数字，保留2位小数，例如：0.85
"""
        response = llm.invoke(prompt)
        match = re.search(r'0?\.\d+', response.content.strip())
        return float(match.group()) if match else 0.5
    except Exception:
        return 0.5


def evaluate_citation_quality(answer: str, sources: List[Dict[str, Any]]) -> float:
    """Evaluate whether the answer properly cites sources (pure string matching)."""
    if not sources:
        return 0.0

    source_domains = set()
    for s in sources:
        url = s.get('href', s.get('url', ''))
        if url:
            match = re.search(r'https?://([^/]+)', url)
            if match:
                source_domains.add(match.group(1))

    mentioned = sum(
        1 for domain in source_domains
        if domain.replace('www.', '') in answer.lower().replace('www.', '')
    )

    return min(mentioned / len(source_domains), 1.0) if source_domains else 0.5
