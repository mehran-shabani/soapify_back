# search/services.py
"""
Search services for SOAPify (MySQL FULLTEXT + Embeddings rerank).
"""
from __future__ import annotations

import time
import math
import logging
from typing import List, Dict, Any, Optional, Tuple
from functools import reduce
from operator import or_ as OR

from django.db import models
from django.db.models.expressions import RawSQL
from django.db.models import Q
from django.contrib.auth import get_user_model

from .models import SearchableContent, SearchQuery as SearchQueryModel, SearchResult
from embeddings.models import TextEmbedding, EMBED_DIM

logger = logging.getLogger(__name__)
User = get_user_model()


class SearchService:
    """Thin wrapper delegating to HybridSearchService (backward-compat for tests)."""
    def __init__(self):
        self._hybrid = HybridSearchService()

    def search(self, *args, **kwargs):
        # Return only the results list for compatibility with tests
        return [r for r in self._hybrid.search(*args, **kwargs).get("results", [])]


class HybridSearchService:
    """Hybrid search service combining FULLTEXT (MySQL) and semantic rerank."""

    def __init__(self):
        # وزن‌دهی نهایی (کازاین کوچک‌تر بهتر؛ تبدیل به similarity می‌کنیم)
        self.fts_weight = 0.6
        self.semantic_weight = 0.4

    # ---------- Public API ----------
    def search(
        self,
        query_text: str,
        user: Optional[User] = None,
        filters: Optional[Dict[str, Any]] = None,
        limit: int = 20,
        boolean_mode: bool = True,
        candidate_limit: int = 300,
    ) -> Dict[str, Any]:
        """
        1) FULLTEXT روی SearchableContent (کاندیدا)
        2) ریرنک کاندیدا با امبدینگ‌ها (cosine)
        3) ترکیب امتیازها
        """
        start_time = time.time()
        if not query_text or not query_text.strip():
            return {"results": [], "total_count": 0, "execution_time_ms": 0, "query": query_text}

        filters = filters or {}

        # 1) FULLTEXT candidates
        fts_candidates = self._full_text_candidates(query_text, filters, candidate_limit, boolean_mode)

        # اگر هیچ کاندیدایی نیست، خالی برگرد
        if not fts_candidates:
            exec_ms = int((time.time() - start_time) * 1000)
            sq = SearchQueryModel.objects.create(
                query_text=query_text, filters=filters, user=user, results_count=0, execution_time_ms=exec_ms
            )
            return {
                "results": [],
                "total_count": 0,
                "execution_time_ms": exec_ms,
                "query": query_text,
                "filters": filters,
                "search_id": sq.id,
            }

        # 2) semantic rerank روی همین کاندیداها
        semantic_scored = self._semantic_rerank(query_text, fts_candidates)

        # 3) ترکیب امتیازها
        combined_results = self._combine_results(fts_candidates, semantic_scored, limit)

        # زمان اجرا
        execution_time_ms = int((time.time() - start_time) * 1000)

        # ذخیرهٔ کوئری برای آنالیتیکس
        search_query_obj = SearchQueryModel.objects.create(
            query_text=query_text,
            filters=filters,
            user=user,
            results_count=len(combined_results),
            execution_time_ms=execution_time_ms,
        )

        # کش نتایج
        self._cache_search_results(search_query_obj, combined_results)

        return {
            "results": combined_results,
            "total_count": len(combined_results),
            "execution_time_ms": execution_time_ms,
            "query": query_text,
            "filters": filters,
            "search_id": search_query_obj.id,
        }

    # ---------- Internal: FULLTEXT ----------
    def _full_text_candidates(
        self,
        query_text: str,
        filters: Dict[str, Any],
        candidate_limit: int,
        boolean_mode: bool,
    ) -> List[Dict[str, Any]]:
        """کوئری FULLTEXT با MATCH ... AGAINST روی ستون generated: fulltext_all"""
        try:
            qs = SearchableContent.objects.all()

            # فیلترها
            if filters.get("encounter_id"):
                qs = qs.filter(encounter_id=filters["encounter_id"])
            if filters.get("content_type"):
                cts = filters["content_type"]
                if isinstance(cts, str):
                    cts = [cts]
                qs = qs.filter(content_type__in=cts)
            if filters.get("date_from"):
                qs = qs.filter(created_at__gte=filters["date_from"])
            if filters.get("date_to"):
                qs = qs.filter(created_at__lte=filters["date_to"])

            mode_sql = "IN BOOLEAN MODE" if boolean_mode else "IN NATURAL LANGUAGE MODE"
            raw = RawSQL(f"MATCH(fulltext_all) AGAINST (%s {mode_sql})", (query_text,))

            results = (
                qs.annotate(relevance=raw)
                  .filter(relevance__gt=0)
                  .only("id", "encounter_id", "content_type", "content_id", "title", "content", "metadata")
                  .order_by("-relevance", "-created_at")[:candidate_limit]
                  .values("id", "encounter_id", "content_type", "content_id", "title", "content", "metadata", "relevance")
            )

            # شکل استاندارد خروجی کاندیدا برای مرحلهٔ semantic
            formatted = []
            for r in results:
                formatted.append({
                    "id": r["id"],  # id جدول SearchableContent
                    "encounter_id": r["encounter_id"],
                    "content_type": r["content_type"],
                    "content_id": r["content_id"],
                    "title": r["title"],
                    "content": r["content"],
                    "metadata": r["metadata"],
                    "keyword_relevance": float(r["relevance"]),
                })
            return formatted

        except Exception as e:
            logger.error(f"FULLTEXT search failed: {e}")
            return []

    # ---------- Internal: Semantic rerank ----------
    def _semantic_rerank(self, query_text: str, candidates: List[Dict[str, Any]]) -> Dict[Tuple[int, str, int], float]:
        """
        بر اساس امبدینگ: distance (کوچک‌تر بهتر). خروجی: map از key=(encounter_id, content_type, content_id) به distance
        """
        # 1) ساخت امبدینگ کوئری (اینجا فرض می‌کنیم در جای دیگری ساخته می‌شود)
        # اگر سرویسی دارید که امبدینگ می‌سازد، اینجا فراخوانی کنید و بردار را بگیرید.
        # برای مستقل بودن این فایل، یک نمونهٔ ساده/جعلی می‌گذاریم که حتماً جایگزین کنید:
        query_vec = self._make_query_embedding(query_text)

        # 2) خواندن امبدینگ کاندیداها
        keys = [(c["encounter_id"], c["content_type"], c["content_id"]) for c in candidates]
        if not keys:
            return {}

        q_or = reduce(OR, (Q(encounter_id=e, content_type=ct, content_id=cid) for e, ct, cid in keys))
        embedding_rows = TextEmbedding.objects.filter(q_or).only(
            "encounter_id", "content_type", "content_id", "embedding_vector"
        )

        emb_map: Dict[Tuple[int, str, int], List[float]] = {}
        for row in embedding_rows:
            emb_map[(row.encounter_id, row.content_type, row.content_id)] = row.embedding_vector

        # 3) محاسبهٔ فاصله کازاین
        distances: Dict[Tuple[int, str, int], float] = {}
        for key in keys:
            emb = emb_map.get(key)
            if not emb:
                continue
            distances[key] = _cosine_distance(emb, query_vec)
        return distances

    # ---------- Internal: Combine ----------
    def _combine_results(
        self,
        fts_candidates: List[Dict[str, Any]],
        semantic_dist: Dict[Tuple[int, str, int], float],
        limit: int,
    ) -> List[Dict[str, Any]]:
        """
        ترکیب: similarity_sem = 1 - distance (clamped to [0,1])، سپس
        combined = w_ft * norm(keyword_relevance) + w_sem * similarity_sem
        """
        # نرمال‌سازی سادهٔ امتیاز FULLTEXT بین 0..1
        if fts_candidates:
            max_kw = max(c["keyword_relevance"] for c in fts_candidates) or 1.0
        else:
            max_kw = 1.0

        results = []
        for c in fts_candidates:
            key = (c["encounter_id"], c["content_type"], c["content_id"])
            dist = semantic_dist.get(key)
            if dist is None:
                # اگر امبدینگی نیافتیم، فقط FULLTEXT را لحاظ می‌کنیم
                sem_sim = 0.0
            else:
                sem_sim = max(0.0, min(1.0, 1.0 - float(dist)))  # 1 - distance

            kw_norm = float(c["keyword_relevance"]) / max_kw
            combined = kw_norm * self.fts_weight + sem_sim * self.semantic_weight

            results.append({
                "id": c["id"],
                "encounter_id": c["encounter_id"],
                "content_type": c["content_type"],
                "content_id": c["content_id"],
                "title": c["title"],
                "content": c["content"],
                "snippet": self._generate_snippet(c["content"], ""),  # می‌تونی query_text پاس بدی برای هایلایت
                "score": float(kw_norm),                # امتیاز raw کیورد
                "semantic_similarity": float(sem_sim),  # شباهت 0..1
                "combined_score": float(combined),
                "search_type": "hybrid" if dist is not None else "full_text",
                "metadata": c.get("metadata") or {},
                "created_at": None,  # اختیاری
            })

        results.sort(key=lambda x: x["combined_score"], reverse=True)
        return results[:limit]

    # ---------- Helpers ----------
    def _generate_snippet(self, content: str, query_text: str, max_length: int = 200) -> str:
        if not content:
            return ""
        # ساده: ابتدای متن را برمی‌گردانیم؛ می‌توانی مثل قبل sliding-window با هایلایت کلمات بسازی
        snippet = content[:max_length]
        if len(content) > max_length:
            snippet += "..."
        return snippet

    def _cache_search_results(self, search_query_obj: SearchQueryModel, results: List[Dict[str, Any]]):
        try:
            SearchResult.objects.filter(query=search_query_obj).delete()
            bulk = []
            for rank, r in enumerate(results, 1):
                try:
                    sc = SearchableContent.objects.get(id=r["id"])
                except SearchableContent.DoesNotExist:
                    continue
                bulk.append(SearchResult(
                    query=search_query_obj,
                    content=sc,
                    relevance_score=r["combined_score"],
                    rank=rank,
                    snippet=r["snippet"],
                ))
            if bulk:
                SearchResult.objects.bulk_create(bulk)
        except Exception as e:
            logger.error(f"Failed to cache search results: {e}")

    # ---- Fake/simple embedding for query (جایگزین با سرویس واقعی) ----
    def _make_query_embedding(self, text: str) -> List[float]:
        """
        TODO: این تابع را با سرویس واقعی ساخت امبدینگ (OpenAI/HF) جایگزین کنید.
        فعلاً بردار واحد با hashing ساده تولید می‌کند تا روند کامل باشد.
        """
        import random
        random.seed(hash(text) & 0xFFFFFFFF)
        vec = [random.random() for _ in range(EMBED_DIM)]
        # unit normalize
        s = math.sqrt(sum(x*x for x in vec)) or 1.0
        return [x / s for x in vec]


def _cosine_distance(a: List[float], b: List[float]) -> float:
    dot = 0.0
    na = 0.0
    nb = 0.0
    for x, y in zip(a, b):
        fx = float(x); fy = float(y)
        dot += fx * fy
        na += fx * fx
        nb += fy * fy
    na = math.sqrt(na) or 1.0
    nb = math.sqrt(nb) or 1.0
    return 1.0 - (dot / (na * nb))