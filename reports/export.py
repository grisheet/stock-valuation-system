"""reports/export.py – CSV and PDF export for valuation results."""
from __future__ import annotations

import io
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd

logger = logging.getLogger(__name__)


class ReportExporter:
    """Export valuation results to CSV and (optional) PDF via reportlab.

    PDF generation requires ``reportlab`` to be installed.
    If not available, PDF export falls back gracefully with a warning.
    """

    def __init__(self, output_dir: str = ".") -> None:
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------ #
    # CSV Export                                                          #
    # ------------------------------------------------------------------ #

    def to_csv(
        self,
        data: Dict[str, Any],
        ticker: str,
        filename: Optional[str] = None,
    ) -> Path:
        """Export a flat valuation summary dict to CSV.

        Parameters
        ----------
        data : dict  Key-value pairs (str -> scalar).
        ticker : str  Used in the default filename.
        filename : str, optional  Override the output filename.
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        fname = filename or f"{ticker}_valuation_{timestamp}.csv"
        path = self.output_dir / fname

        rows = [{"Metric": k, "Value": v} for k, v in data.items()]
        df = pd.DataFrame(rows)
        df.to_csv(path, index=False)
        logger.info("CSV exported to %s", path)
        return path

    def dataframe_to_csv(
        self,
        df: pd.DataFrame,
        filename: str,
    ) -> Path:
        """Export a DataFrame directly to CSV."""
        path = self.output_dir / filename
        df.to_csv(path)
        logger.info("DataFrame CSV exported to %s", path)
        return path

    def to_csv_bytes(self, data: Dict[str, Any]) -> bytes:
        """Return CSV content as bytes (for Streamlit download_button)."""
        rows = [{"Metric": k, "Value": v} for k, v in data.items()]
        df = pd.DataFrame(rows)
        buf = io.StringIO()
        df.to_csv(buf, index=False)
        return buf.getvalue().encode("utf-8")

    def dataframe_to_csv_bytes(self, df: pd.DataFrame) -> bytes:
        """Return DataFrame as CSV bytes for Streamlit download."""
        buf = io.StringIO()
        df.to_csv(buf)
        return buf.getvalue().encode("utf-8")

    # ------------------------------------------------------------------ #
    # PDF Export                                                          #
    # ------------------------------------------------------------------ #

    def to_pdf(
        self,
        sections: List[Dict[str, Any]],
        ticker: str,
        title: str = "Stock Valuation Report",
        filename: Optional[str] = None,
    ) -> Optional[Path]:
        """Generate a PDF report.

        Parameters
        ----------
        sections : list[dict]
            Each dict must have:
              - "heading": str
              - "data": dict[str, Any] OR pd.DataFrame
        ticker : str
        title : str  Report title.
        filename : str, optional

        Returns None if reportlab is not installed.
        """
        try:
            from reportlab.lib.pagesizes import LETTER
            from reportlab.lib.styles import getSampleStyleSheet
            from reportlab.lib.units import inch
            from reportlab.platypus import (
                Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle,
            )
            from reportlab.lib import colors
        except ImportError:
            logger.warning(
                "reportlab not installed; PDF export unavailable. "
                "Install with: pip install reportlab"
            )
            return None

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        fname = filename or f"{ticker}_report_{timestamp}.pdf"
        path = self.output_dir / fname

        styles = getSampleStyleSheet()
        doc = SimpleDocTemplate(str(path), pagesize=LETTER)
        story = []

        # Title
        story.append(Paragraph(f"{title}: {ticker}", styles["Title"]))
        story.append(Paragraph(
            f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            styles["Normal"],
        ))
        story.append(Spacer(1, 0.3 * inch))

        for section in sections:
            heading = section.get("heading", "")
            raw_data = section.get("data", {})

            story.append(Paragraph(heading, styles["Heading2"]))

            if isinstance(raw_data, pd.DataFrame):
                table_data = [list(raw_data.reset_index().columns)]
                for _, row in raw_data.reset_index().iterrows():
                    table_data.append([str(v) for v in row])
            else:
                table_data = [["Metric", "Value"]] + [
                    [str(k), str(v)] for k, v in raw_data.items()
                ]

            tbl = Table(table_data, hAlign="LEFT")
            tbl.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2c3e50")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1),
                 [colors.HexColor("#ecf0f1"), colors.white]),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
            ]))
            story.append(tbl)
            story.append(Spacer(1, 0.2 * inch))

        doc.build(story)
        logger.info("PDF exported to %s", path)
        return path

    def to_pdf_bytes(
        self,
        sections: List[Dict[str, Any]],
        ticker: str,
        title: str = "Stock Valuation Report",
    ) -> Optional[bytes]:
        """Return PDF content as bytes for Streamlit download (requires reportlab)."""
        path = self.to_pdf(sections, ticker, title, filename="_tmp_report.pdf")
        if path is None or not path.exists():
            return None
        data = path.read_bytes()
        path.unlink(missing_ok=True)
        return data
