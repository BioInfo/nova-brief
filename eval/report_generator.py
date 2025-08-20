"""
PDF Report Generator for Nova Brief Evaluation Results.

This module creates professional PDF reports summarizing evaluation metrics
from the LLM-as-Judge harness for executive consumption.
"""

import os
from datetime import datetime
from typing import Dict, Any, List, Optional
from fpdf import FPDF


class EvaluationReportPDF(FPDF):
    """Custom PDF class for Nova Brief evaluation reports."""
    
    def __init__(self):
        super().__init__()
        self.set_auto_page_break(auto=True, margin=15)
        
    def header(self):
        """Add header to each page."""
        self.set_font('Arial', 'B', 15)
        self.cell(0, 10, 'Nova Brief Evaluation Report', 0, 1, 'C')
        self.ln(10)
        
    def footer(self):
        """Add footer to each page."""
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.cell(0, 10, f'Page {self.page_no()}', 0, 0, 'C')
        
    def add_title_page(self, timestamp: str):
        """Add title page with report metadata."""
        self.add_page()
        
        # Main title
        self.set_font('Arial', 'B', 24)
        self.ln(40)
        self.cell(0, 15, 'Nova Brief', 0, 1, 'C')
        self.cell(0, 15, 'Evaluation Report', 0, 1, 'C')
        
        # Subtitle
        self.ln(20)
        self.set_font('Arial', '', 16)
        self.cell(0, 10, 'LLM-as-Judge Quality Assessment', 0, 1, 'C')
        
        # Timestamp
        self.ln(30)
        self.set_font('Arial', '', 12)
        self.cell(0, 10, f'Generated: {timestamp}', 0, 1, 'C')
        
        # Description
        self.ln(40)
        self.set_font('Arial', '', 11)
        description = [
            "This report presents a comprehensive evaluation of Nova Brief's",
            "research agent performance using semantic quality scoring.",
            "",
            "The evaluation employs a unified quality rubric assessing:",
            "- Comprehensiveness - Coverage of research questions",
            "- Synthesis & Depth - Integration of facts into coherent narrative",
            "- Clarity & Coherence - Structure and readability",
            "",
            "All scores range from 0.0 to 1.0, with higher scores indicating",
            "better performance."
        ]
        
        for line in description:
            self.cell(0, 6, line, 0, 1, 'C')
            
    def add_executive_summary(self, eval_results: Dict[str, Any]):
        """Add executive summary section."""
        self.add_page()
        self.set_font('Arial', 'B', 16)
        self.cell(0, 10, 'Executive Summary', 0, 1, 'L')
        self.ln(5)
        
        # Extract key metrics
        results = eval_results.get("results", [])
        successful_results = [r for r in results if r.get("success", False)]
        
        if not successful_results:
            self.set_font('Arial', '', 12)
            self.cell(0, 8, 'No successful evaluations to report.', 0, 1, 'L')
            return
            
        # Calculate averages
        avg_overall = sum(r.get("overall_quality_score", 0) for r in successful_results) / len(successful_results)
        avg_comprehensiveness = sum(r.get("comprehensiveness_score", 0) for r in successful_results) / len(successful_results)
        avg_synthesis = sum(r.get("synthesis_score", 0) for r in successful_results) / len(successful_results)
        avg_clarity = sum(r.get("clarity_score", 0) for r in successful_results) / len(successful_results)
        
        # Find best performing model/topic
        best_result = max(successful_results, key=lambda x: x.get("overall_quality_score", 0))
        best_score = best_result.get("overall_quality_score", 0)
        
        self.set_font('Arial', '', 12)
        
        summary_lines = [
            f"Evaluation completed on {len(results)} topics with {len(successful_results)} successful runs.",
            "",
            "Key Findings:",
            f"- Average Overall Quality Score: {avg_overall:.3f}",
            f"- Average Comprehensiveness: {avg_comprehensiveness:.3f}",
            f"- Average Synthesis & Depth: {avg_synthesis:.3f}",
            f"- Average Clarity & Coherence: {avg_clarity:.3f}",
            "",
            f"Best Performance: {best_score:.3f} overall quality score",
            "",
            "Performance Assessment:",
            self._get_performance_assessment(avg_overall),
        ]
        
        for line in summary_lines:
            if line.startswith("-"):
                self.set_font('Arial', '', 11)
            else:
                self.set_font('Arial', '', 12)
            self.cell(0, 6, line, 0, 1, 'L')
            
    def add_comparison_table(self, eval_results: Dict[str, Any]):
        """Add detailed comparison table."""
        self.add_page()
        self.set_font('Arial', 'B', 16)
        self.cell(0, 10, 'Detailed Results', 0, 1, 'L')
        self.ln(5)
        
        results = eval_results.get("results", [])
        successful_results = [r for r in results if r.get("success", False)]
        
        if not successful_results:
            self.set_font('Arial', '', 12)
            self.cell(0, 8, 'No successful results to display.', 0, 1, 'L')
            return
            
        # Table headers
        self.set_font('Arial', 'B', 10)
        col_widths = [60, 25, 25, 25, 25, 30]
        headers = ['Topic', 'Overall', 'Comp.', 'Synth.', 'Clarity', 'Duration']
        
        for i, header in enumerate(headers):
            self.cell(col_widths[i], 8, header, 1, 0, 'C')
        self.ln()
        
        # Table rows
        self.set_font('Arial', '', 9)
        for result in successful_results[:10]:  # Limit to first 10 results
            topic = result.get("topic", "Unknown")[:25] + "..." if len(result.get("topic", "")) > 25 else result.get("topic", "Unknown")
            overall = f"{result.get('overall_quality_score', 0):.3f}"
            comp = f"{result.get('comprehensiveness_score', 0):.3f}"
            synth = f"{result.get('synthesis_score', 0):.3f}"
            clarity = f"{result.get('clarity_score', 0):.3f}"
            duration = f"{result.get('duration_s', 0):.1f}s"
            
            row_data = [topic, overall, comp, synth, clarity, duration]
            
            for i, data in enumerate(row_data):
                self.cell(col_widths[i], 6, str(data), 1, 0, 'C' if i > 0 else 'L')
            self.ln()
            
        if len(successful_results) > 10:
            self.ln(5)
            self.set_font('Arial', 'I', 10)
            self.cell(0, 6, f"... and {len(successful_results) - 10} more results", 0, 1, 'L')
            
    def add_model_breakdown(self, eval_results: Dict[str, Any]):
        """Add per-model performance breakdown."""
        self.add_page()
        self.set_font('Arial', 'B', 16)
        self.cell(0, 10, 'Performance Analysis', 0, 1, 'L')
        self.ln(5)
        
        results = eval_results.get("results", [])
        successful_results = [r for r in results if r.get("success", False)]
        
        if not successful_results:
            return
            
        # Group by model if available
        model_groups = {}
        for result in successful_results:
            model = result.get("model_used", "default")
            if model not in model_groups:
                model_groups[model] = []
            model_groups[model].append(result)
            
        self.set_font('Arial', 'B', 14)
        self.cell(0, 8, 'Score Distribution:', 0, 1, 'L')
        self.ln(3)
        
        # Calculate score ranges
        all_scores = [r.get("overall_quality_score", 0) for r in successful_results]
        excellent = len([s for s in all_scores if s >= 0.8])
        good = len([s for s in all_scores if 0.6 <= s < 0.8])
        needs_improvement = len([s for s in all_scores if s < 0.6])
        
        self.set_font('Arial', '', 12)
        distribution_lines = [
            f"Excellent (>=0.8): {excellent} topics ({excellent/len(all_scores)*100:.1f}%)",
            f"Good (0.6-0.8): {good} topics ({good/len(all_scores)*100:.1f}%)",
            f"Needs Improvement (<0.6): {needs_improvement} topics ({needs_improvement/len(all_scores)*100:.1f}%)",
        ]
        
        for line in distribution_lines:
            self.cell(0, 6, line, 0, 1, 'L')
            
        self.ln(10)
        
        # Quality insights
        self.set_font('Arial', 'B', 14)
        self.cell(0, 8, 'Quality Insights:', 0, 1, 'L')
        self.ln(3)
        
        avg_overall = sum(all_scores) / len(all_scores)
        insights = self._generate_quality_insights(eval_results, avg_overall)
        
        self.set_font('Arial', '', 12)
        for insight in insights:
            self.cell(0, 6, f"- {insight}", 0, 1, 'L')
            
    def _get_performance_assessment(self, avg_score: float) -> str:
        """Get performance assessment based on average score."""
        if avg_score >= 0.8:
            return "Excellent - Consistently high-quality outputs"
        elif avg_score >= 0.7:
            return "Good - Solid performance with room for optimization"
        elif avg_score >= 0.6:
            return "Satisfactory - Meets basic quality standards"
        else:
            return "Needs Improvement - Below quality thresholds"
            
    def _generate_quality_insights(self, eval_results: Dict[str, Any], avg_overall: float) -> List[str]:
        """Generate quality insights from evaluation results."""
        insights = []
        
        results = eval_results.get("results", [])
        successful_results = [r for r in results if r.get("success", False)]
        
        if not successful_results:
            return ["No successful results available for analysis."]
            
        # Calculate dimension averages
        avg_comp = sum(r.get("comprehensiveness_score", 0) for r in successful_results) / len(successful_results)
        avg_synth = sum(r.get("synthesis_score", 0) for r in successful_results) / len(successful_results)
        avg_clarity = sum(r.get("clarity_score", 0) for r in successful_results) / len(successful_results)
        
        # Identify strengths and weaknesses
        dimensions = [
            ("Comprehensiveness", avg_comp),
            ("Synthesis & Depth", avg_synth),
            ("Clarity & Coherence", avg_clarity)
        ]
        
        best_dim = max(dimensions, key=lambda x: x[1])
        worst_dim = min(dimensions, key=lambda x: x[1])
        
        insights.append(f"Strongest area: {best_dim[0]} ({best_dim[1]:.3f})")
        insights.append(f"Area for improvement: {worst_dim[0]} ({worst_dim[1]:.3f})")
        
        # Performance consistency
        scores = [r.get("overall_quality_score", 0) for r in successful_results]
        if len(scores) > 1:
            std_dev = (sum((x - avg_overall) ** 2 for x in scores) / (len(scores) - 1)) ** 0.5
            if std_dev < 0.1:
                insights.append("Performance is highly consistent across topics")
            elif std_dev > 0.2:
                insights.append("Performance varies significantly across topics")
                
        return insights


def create_pdf_report(eval_results: Dict[str, Any], output_filename: str) -> None:
    """
    Create a professional PDF evaluation report.
    
    Args:
        eval_results: Dictionary containing evaluation results from harness
        output_filename: Path where PDF should be saved
    
    Raises:
        Exception: If PDF generation fails
    """
    try:
        # Create PDF instance
        pdf = EvaluationReportPDF()
        
        # Generate timestamp
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Add sections
        pdf.add_title_page(timestamp)
        pdf.add_executive_summary(eval_results)
        pdf.add_comparison_table(eval_results)
        pdf.add_model_breakdown(eval_results)
        
        # Ensure output directory exists
        os.makedirs(os.path.dirname(output_filename), exist_ok=True)
        
        # Save PDF
        pdf.output(output_filename)
        
        print(f"📄 PDF report generated: {output_filename}")
        
    except Exception as e:
        print(f"⚠️  PDF generation failed: {e}")
        raise


def validate_eval_results(eval_results: Dict[str, Any]) -> bool:
    """
    Validate that evaluation results contain required fields for PDF generation.
    
    Args:
        eval_results: Evaluation results dictionary
        
    Returns:
        True if valid, False otherwise
    """
    required_fields = ["results", "success"]
    
    for field in required_fields:
        if field not in eval_results:
            return False
            
    if not eval_results.get("success", False):
        return False
        
    results = eval_results.get("results", [])
    if not isinstance(results, list) or len(results) == 0:
        return False
        
    return True