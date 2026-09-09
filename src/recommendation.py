"""
Generate human-readable business recommendations per customer segment,
based on the aggregated profile produced in notebooks/04_business_analysis.ipynb
(or any DataFrame with a 'segment_name' column).

This module is intentionally rule-based (not ML) — recommendations should
be traceable to a simple, explainable rule, which is easier to defend in
an interview than a black-box output. RULES is also imported directly by
src/export_segments.py so the same recommendation text gets written into
the customer_segments table (single source of truth for Power BI).

Usage:
    from src.recommendation import generate_recommendations
    recs = generate_recommendations(profile_df)
"""

from typing import Dict
import pandas as pd

from src.utils import get_logger

logger = get_logger(__name__)


RULES = {
    "Loyal Customers": (
        "Frequency cao nhất trong 4 segment (đặt lại đơn nhiều lần), dù chi tiêu trung "
        "bình mỗi đơn không phải cao nhất. Ưu tiên VIP Campaign / chương trình loyalty: "
        "giữ chân nhóm đã chứng minh hành vi mua lặp lại thật sự, chi phí giữ chân nhóm "
        "này thường rẻ hơn thu hút khách mới."
    ),
    "High-Value Potential": (
        "Chỉ chiếm phần nhỏ khách hàng nhưng monetary trung bình cao vượt trội (gấp ~4 lần "
        "Loyal Customers) dù hầu như mới mua 1 lần (frequency ~1). Đây là nhóm 'chi mạnh tay "
        "nhưng chưa quay lại' — ưu tiên cross-sell / personalized offer để thúc đẩy mua lần 2, "
        "biến giá trị đơn lẻ cao thành mối quan hệ dài hạn."
    ),
    "Active One-Time Customers": (
        "Chiếm tỷ trọng khách hàng lớn nhất, mới mua gần đây (recency thấp nhất trong 4 nhóm) "
        "nhưng đều là mua lần đầu (frequency=1) — KHÔNG có bằng chứng đây là khách từng loyal "
        "rồi suy giảm, nên đây là nhóm 'cơ hội chuyển đổi' chứ không phải 'rủi ro mất khách'. "
        "Ưu tiên chiến dịch khuyến khích đơn hàng thứ 2 (second-purchase incentive), welcome-back "
        "offer trong khung thời gian ngắn sau đơn đầu tiên."
    ),
    "Dormant Customers": (
        "Recency rất cao (lâu nhất trong 4 nhóm, gấp ~3 lần Active One-Time), frequency/monetary "
        "thấp. Chưa đủ cơ sở khẳng định 'mất hẳn' (dataset chỉ có ~2 năm dữ liệu), nên gọi "
        "'Dormant' thay vì 'Lost'. Cân nhắc chiến dịch win-back chi phí thấp (email reactivation); "
        "nếu không phản hồi sau vài đợt, giảm ưu tiên ngân sách marketing cho nhóm này."
    ),
}

DEFAULT_RULE = (
    "Chưa có rule cụ thể cho segment này — xem lại RFM profile để xác định "
    "chiến lược phù hợp (đối chiếu với 4 nhóm chuẩn: Loyal Customers, "
    "High-Value Potential, Active One-Time Customers, Dormant Customers)."
)


def generate_recommendations(profile_df: pd.DataFrame) -> Dict[str, str]:
    """
    profile_df must have a 'segment_name' column (as produced by
    src/export_segments.py's label_clusters()). Returns a dict mapping
    segment_name -> recommendation text.
    """
    if "segment_name" not in profile_df.columns:
        raise ValueError("profile_df must have a 'segment_name' column.")

    recommendations = {}
    for segment in profile_df["segment_name"].unique():
        recommendations[segment] = RULES.get(segment, DEFAULT_RULE)

    logger.info(f"Generated recommendations for {len(recommendations)} segments.")
    return recommendations


if __name__ == "__main__":
    dummy = pd.DataFrame({"segment_name": ["Loyal Customers", "Dormant Customers"]})
    for seg, text in generate_recommendations(dummy).items():
        print(f"--- {seg} ---")
        print(text, "\n")
