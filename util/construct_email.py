import math
from tqdm import tqdm
from email.header import Header
from email.mime.text import MIMEText
from email.utils import parseaddr, formataddr
import smtplib
from datetime import datetime, timezone
from loguru import logger

framework = """
<!DOCTYPE HTML>
<html>
<head>
  <style>
    .star-wrapper {
      font-size: 1.3em; /* Adjust star size */
      line-height: 1; /* Vertical alignment fix */
      display: inline-flex;
      align-items: center; /* Keep aligned */
    }
    .half-star {
      display: inline-block;
      width: 0.5em; /* Width of half star */
      overflow: hidden;
      white-space: nowrap;
      vertical-align: middle;
    }
    .full-star {
      vertical-align: middle;
    }
  </style>
</head>
<body>

<div>
    __CONTENT__
</div>

<br><br>
<div>
If you wish to unsubscribe, please remove your email from the GitHub Action settings.
</div>

</body>
</html>
"""


def get_empty_html():
    block_template = """
  <table border="0" cellpadding="0" cellspacing="0" width="100%" style="font-family: Arial, sans-serif; border: 1px solid #ddd; border-radius: 8px; padding: 16px; background-color: #f9f9f9;">
  <tr>
    <td style="font-size: 20px; font-weight: bold; color: #333;">
        No Papers Today. Take a Rest!
    </td>
  </tr>
  """
    return block_template


def get_summary_html(content: str) -> str:
    style = """
    <style>
      .summary-wrapper {
        border-radius: 16px;
        padding: 24px 28px;
        background: linear-gradient(135deg, rgba(66,133,244,0.12), rgba(219,68,55,0.08));
        box-shadow: 0 18px 45px rgba(15, 23, 42, 0.12);
        margin-bottom: 32px;
        font-family: 'Helvetica Neue', Arial, sans-serif;
      }
      .summary-section {
        margin-bottom: 24px;
      }
      .summary-section h2 {
        margin: 0 0 12px 0;
        font-size: 22px;
        color: #1f2937;
        border-bottom: 2px solid rgba(59,130,246,0.2);
        padding-bottom: 8px;
      }
      .summary-section p {
        margin: 0;
        line-height: 1.7;
        color: #374151;
        font-size: 15px;
      }
      .summary-list {
        list-style: none;
        padding: 0;
        margin: 0;
        display: grid;
        gap: 16px;
      }
      .summary-item {
        padding: 16px 18px;
        border-radius: 12px;
        background: rgba(255,255,255,0.85);
        border: 1px solid rgba(229, 231, 235, 0.8);
      }
      .summary-item__header {
        display: flex;
        align-items: center;
        gap: 10px;
        flex-wrap: wrap;
      }
      .summary-item__title {
        font-size: 17px;
        font-weight: 600;
        color: #1d4ed8;
        margin: 0;
      }
      .summary-pill {
        display: inline-flex;
        align-items: center;
        padding: 3px 10px;
        border-radius: 999px;
        background: rgba(59, 130, 246, 0.12);
        color: #1d4ed8;
        font-size: 12px;
        font-weight: 600;
        letter-spacing: 0.3px;
      }
      .summary-item p {
        margin: 10px 0 0 0;
        color: #4b5563;
        font-size: 14px;
        line-height: 1.6;
      }
      .summary-item strong {
        color: #111827;
      }
    </style>
    """
    return f"{style}\n<div class=\"summary-wrapper\">\n{content}\n</div>"


def render_summary_sections(summary_data: dict) -> str:
    """Convert structured summary data into an HTML block."""
    trend_summary = summary_data.get("trend_summary", "No current research trend information.")
    additional_observation = summary_data.get("additional_observation", "None")

    recommendations = summary_data.get("recommendations", [])
    recommendations_html = []
    if isinstance(recommendations, list):
        for item in recommendations:
            if not isinstance(item, dict):
                continue
            title = item.get("title")
            if not title:
                continue
            relevance = item.get("relevance_label", "Unknown relevance")
            reason = item.get("recommend_reason", "No recommendation reason provided.")
            contribution = item.get("key_contribution", "No key contribution information provided.")
            recommendations_html.append(
                "  <li class=\"summary-item\">\n"
                "    <div class=\"summary-item__header\">"
                f"<span class=\"summary-item__title\">{title}</span>"
                f"<span class=\"summary-pill\">{relevance}</span></div>\n"
                f"    <p><strong>Reason:</strong> {reason}</p>\n"
                f"    <p><strong>Key Contribution:</strong> {contribution}</p>\n"
                "  </li>"
            )

    sections = [
        "<div class=\"summary-section\">",
        "  <h2>Today's Research Trend</h2>",
        f"  <p>{trend_summary}</p>",
        "</div>",
        "<div class=\"summary-section\">",
        "  <h2>Top Recommendations</h2>",
    ]
    if recommendations_html:
        sections.append("  <ol class=\"summary-list\">")
        sections.extend(recommendations_html)
        sections.append("  </ol>")
    else:
        sections.append("  <p>No recommended papers available.</p>")
    sections.append("</div>")
    sections.extend(
        [
            "<div class=\"summary-section\">",
            "  <h2>Additional Observations</h2>",
            f"  <p>{additional_observation}</p>",
            "</div>",
        ]
    )

    final_html = "\n".join(sections)
    return get_summary_html(final_html)


def get_block_html(title: str, rate: str, arxiv_id: str, abstract: str, pdf_url: str):
    block_template = """
    <table border="0" cellpadding="0" cellspacing="0" width="100%" style="font-family: Arial, sans-serif; border: 1px solid #ddd; border-radius: 8px; padding: 16px; background-color: #f9f9f9;">
    <tr>
        <td style="font-size: 20px; font-weight: bold; color: #333;">
            {title}
        </td>
    </tr>
    <tr>
        <td style="font-size: 14px; color: #333; padding: 8px 0;">
            <strong>Relevance:</strong> {rate}
        </td>
    </tr>
    <tr>
        <td style="font-size: 14px; color: #333; padding: 8px 0;">
            <strong>arXiv ID:</strong> {arxiv_id}
        </td>
    </tr>
    <tr>
        <td style="font-size: 14px; color: #333; padding: 8px 0;">
            <strong>TLDR:</strong> {abstract}
        </td>
    </tr>

    <tr>
        <td style="padding: 8px 0;">
            <a href="{pdf_url}" style="display: inline-block; text-decoration: none; font-size: 14px; font-weight: bold; color: #fff; background-color: #d9534f; padding: 8px 16px; border-radius: 4px;">PDF</a>
        </td>
    </tr>
</table>
"""
    return block_template.format(
        title=title, rate=rate, arxiv_id=arxiv_id, abstract=abstract, pdf_url=pdf_url
    )


def get_stars(score: float):
    full_star = '<span class="full-star">⭐</span>'
    half_star = '<span class="half-star">⭐</span>'
    low = 2
    high = 8
    if score <= low:
        return ""
    elif score >= high:
        return full_star * 5
    else:
        interval = (high - low) / 10
        star_num = math.ceil((score - low) / interval)
        full_star_num = int(star_num / 2)
        half_star_num = star_num - full_star_num * 2
        return (
            '<div class="star-wrapper">'
            + full_star * full_star_num
            + half_star * half_star_num
            + "</div>"
        )


def send_email(
    sender: str,
    receiver: str,
    password: str,
    smtp_server: str,
    smtp_port: int,
    html: str,
):
    def _format_addr(s):
        name, addr = parseaddr(s)
        return formataddr((Header(name, "utf-8").encode(), addr))

    msg = MIMEText(html, "html", "utf-8")
    msg["From"] = _format_addr("Github Action <%s>" % sender)
    msg["To"] = _format_addr("You <%s>" % receiver)
    today = datetime.now(timezone.utc).strftime("%Y/%m/%d")
    msg["Subject"] = Header(f"Daily arXiv {today}", "utf-8").encode()

    try:
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
    except Exception as e:
        logger.warning(f"Failed to use TLS. {e}")
        logger.warning(f"Try to use SSL.")
        server = smtplib.SMTP_SSL(smtp_server, smtp_port)

    server.login(sender, password)
    server.sendmail(sender, [receiver], msg.as_string())
    server.quit()
