"""
LCD Grading Analysis Service for MonsterC.

This service handles the analysis of LCD Grading 1 data to track display quality grades (N, F, S).
It provides filtering by Source, Operator, OS Name, and Model with percentage calculations.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional, Any
from contextlib import contextmanager

from src.common.logging_config import get_logger, capture_exceptions

logger = get_logger(__name__)


@contextmanager
def log_service_call(operation: str):
    """Log service operations with timing."""
    logger.info(f"LCD Grading Service - Starting {operation}")
    start_time = pd.Timestamp.now()
    try:
        yield
    finally:
        duration = (pd.Timestamp.now() - start_time).total_seconds()
        logger.info(f"LCD Grading Service - Completed {operation} in {duration:.2f}s")


def analyze_lcd_grading(
    df: pd.DataFrame,
    source_filter: Optional[str] = None,
    os_filter: Optional[str] = None,
    model_filter: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    Analyze LCD Grading 1 data with multi-level filtering.
    
    Args:
        df: Input DataFrame with LCD Grading 1 column
        source_filter: Filter by Source (Automated Trade-In or Automated CRTC)
        os_filter: Filter by OS name (Android or iOS)
        model_filter: Filter by specific models
        
    Returns:
        Dictionary containing analysis results and HTML visualization
    """
    try:
        with log_service_call("LCD Grading Analysis"):
            # Validate LCD Grading 1 column exists
            if 'LCD Grading 1' not in df.columns:
                logger.warning("LCD Grading 1 column not found in DataFrame")
                return {
                'html': generate_error_html("LCD Grading 1 column not found in the data"),
                'data': {},
                'total_records': 0
            }
        
        # Apply automation line filtering (4 stations)
        automation_operators = ['STN251_RED', 'STN252_RED', 'STN351_GRN', 'STN352_GRN']
        filtered_df = df[df['Operator'].str.contains('|'.join(automation_operators), na=False)]
        
        # Apply source filtering
        if source_filter and source_filter != 'All':
            if source_filter == 'Automated Trade-In':
                filtered_df = filtered_df[filtered_df['Source'] == 'Automated TRADE-IN']
            elif source_filter == 'Automated CRTC':
                filtered_df = filtered_df[filtered_df['Source'] == 'Automated CRTC']
        
        # Apply OS filtering
        if os_filter and os_filter != 'All':
            filtered_df = filtered_df[filtered_df['OS name'] == os_filter]
        
        # Apply model filtering
        if model_filter and 'All' not in model_filter:
            filtered_df = filtered_df[filtered_df['Model'].isin(model_filter)]
        
        # Clean LCD Grading values
        valid_grades = ['N', 'F', 'S']
        filtered_df = filtered_df[filtered_df['LCD Grading 1'].isin(valid_grades)]
        
        if filtered_df.empty:
            return {
                'html': generate_error_html("No valid LCD Grading data found after filtering"),
                'data': {},
                'total_records': 0
            }
        
        # Calculate overall statistics
        total_records = len(filtered_df)
        grade_counts = filtered_df['LCD Grading 1'].value_counts()
        grade_percentages = (grade_counts / total_records * 100).round(2)
        
        # Calculate OS breakdown
        os_breakdown = {}
        if 'OS name' in filtered_df.columns:
            for os in ['Android', 'iOS']:
                os_df = filtered_df[filtered_df['OS name'] == os]
                if not os_df.empty:
                    os_counts = os_df['LCD Grading 1'].value_counts()
                    os_total = len(os_df)
                    os_percentages = (os_counts / os_total * 100).round(2)
                    os_breakdown[os] = {
                        'total': os_total,
                        'counts': os_counts.to_dict(),
                        'percentages': os_percentages.to_dict()
                    }
        
        # Calculate source breakdown
        source_breakdown = {}
        if 'Source' in filtered_df.columns:
            for source in ['Automated TRADE-IN', 'Automated CRTC']:
                source_df = filtered_df[filtered_df['Source'] == source]
                if not source_df.empty:
                    source_counts = source_df['LCD Grading 1'].value_counts()
                    source_total = len(source_df)
                    source_percentages = (source_counts / source_total * 100).round(2)
                    source_breakdown[source] = {
                        'total': source_total,
                        'counts': source_counts.to_dict(),
                        'percentages': source_percentages.to_dict()
                    }
        
        # Calculate model breakdown if specific models are selected
        model_breakdown = {}
        if model_filter and 'All' not in model_filter:
            for model in model_filter:
                model_df = filtered_df[filtered_df['Model'] == model]
                if not model_df.empty:
                    model_counts = model_df['LCD Grading 1'].value_counts()
                    model_total = len(model_df)
                    model_percentages = (model_counts / model_total * 100).round(2)
                    model_breakdown[model] = {
                        'total': model_total,
                        'counts': model_counts.to_dict(),
                        'percentages': model_percentages.to_dict()
                    }
        
        # Generate HTML visualization
        html = generate_lcd_grading_html(
            total_records,
            grade_counts.to_dict(),
            grade_percentages.to_dict(),
            os_breakdown,
            source_breakdown,
            model_breakdown
        )
        
        return {
            'html': html,
            'data': {
                'total_records': total_records,
                'grade_counts': grade_counts.to_dict(),
                'grade_percentages': grade_percentages.to_dict(),
                'os_breakdown': os_breakdown,
                'source_breakdown': source_breakdown,
                'model_breakdown': model_breakdown
            },
            'total_records': total_records
        }
    except Exception as e:
        logger.error(f"Error in LCD Grading analysis: {str(e)}", exc_info=True)
        return {
            'html': generate_error_html(f"Analysis error: {str(e)}"),
            'data': {},
            'total_records': 0
        }


def generate_lcd_grading_html(
    total_records: int,
    grade_counts: Dict[str, int],
    grade_percentages: Dict[str, float],
    os_breakdown: Dict[str, Any],
    source_breakdown: Dict[str, Any],
    model_breakdown: Dict[str, Any]
) -> str:
    """Generate HTML visualization for LCD Grading analysis."""
    
    # Define colors for grades
    grade_colors = {
        'N': '#2ECC71',  # Green for No defects
        'F': '#F39C12',  # Orange for Faint
        'S': '#E74C3C'   # Red for Severe
    }
    
    # Calculate goal differences
    goals = {'N': 97.5, 'F': 2.0, 'S': 1.0}  # Target percentages
    
    html = f"""
    <div style="padding: 20px; font-family: Arial, sans-serif;">
        <!-- Header -->
        <div style="background: linear-gradient(135deg, #3498db 0%, #2980b9 100%); 
                    padding: 25px; border-radius: 15px; margin-bottom: 25px; 
                    box-shadow: 0 10px 30px rgba(0,0,0,0.1);">
            <h2 style="color: white; margin: 0 0 10px 0; font-size: 28px; text-align: center;">
                📊 LCD Grading Analysis
            </h2>
            <p style="color: white; margin: 0; text-align: center; opacity: 0.9; font-size: 16px;">
                Total Records Analyzed: {total_records:,}
            </p>
        </div>
        
        <!-- Overall Grade Distribution -->
        <div style="background: white; padding: 25px; border-radius: 12px; 
                    box-shadow: 0 8px 20px rgba(0,0,0,0.08); margin-bottom: 25px;">
            <h3 style="margin: 0 0 20px 0; font-size: 22px; color: #2c3e50;">
                Overall Grade Distribution
            </h3>
            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 20px;">
    """
    
    # Add grade cards
    for grade in ['N', 'F', 'S']:
        count = grade_counts.get(grade, 0)
        percentage = grade_percentages.get(grade, 0)
        goal = goals.get(grade, 0)
        diff = percentage - goal
        diff_color = '#2ECC71' if (grade == 'N' and diff >= 0) or (grade in ['F', 'S'] and diff <= 0) else '#E74C3C'
        
        grade_label = {
            'N': 'No Defects',
            'F': 'Faint',
            'S': 'Severe'
        }.get(grade, grade)
        
        html += f"""
            <div style="background: linear-gradient(135deg, {grade_colors[grade]} 0%, {grade_colors[grade]}dd 100%);
                        padding: 20px; border-radius: 12px; color: white; position: relative;">
                <h4 style="margin: 0 0 10px 0; font-size: 18px; opacity: 0.9;">
                    {grade_label} ({grade})
                </h4>
                <div style="font-size: 36px; font-weight: bold; margin: 10px 0;">
                    {percentage:.1f}%
                </div>
                <div style="font-size: 14px; opacity: 0.8;">
                    {count:,} records
                </div>
                <div style="margin-top: 15px; font-size: 13px;">
                    <div>Goal: {goal:.1f}%</div>
                    <div style="color: {diff_color}; font-weight: bold;">
                        {'+' if diff >= 0 else ''}{diff:.1f}% from goal
                    </div>
                </div>
                <!-- Progress bar -->
                <div style="margin-top: 15px; background: rgba(255,255,255,0.3); 
                            height: 8px; border-radius: 4px; overflow: hidden;">
                    <div style="background: rgba(255,255,255,0.8); height: 100%; 
                                width: {min(percentage, 100)}%; transition: width 1s ease;">
                    </div>
                </div>
            </div>
        """
    
    html += """
            </div>
        </div>
    """
    
    # OS Breakdown
    if os_breakdown:
        html += """
        <div style="background: white; padding: 25px; border-radius: 12px; 
                    box-shadow: 0 8px 20px rgba(0,0,0,0.08); margin-bottom: 25px;">
            <h3 style="margin: 0 0 20px 0; font-size: 22px; color: #2c3e50;">
                Operating System Breakdown
            </h3>
            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px;">
        """
        
        for os, data in os_breakdown.items():
            os_color = '#3498db' if os == 'iOS' else '#2ecc71'
            html += f"""
                <div style="border: 2px solid {os_color}; border-radius: 12px; padding: 20px;">
                    <h4 style="margin: 0 0 15px 0; color: {os_color}; font-size: 20px;">
                        {os} ({data['total']:,} records)
                    </h4>
            """
            
            for grade in ['N', 'F', 'S']:
                pct = data['percentages'].get(grade, 0)
                cnt = data['counts'].get(grade, 0)
                html += f"""
                    <div style="display: flex; align-items: center; margin-bottom: 10px;">
                        <div style="width: 30px; font-weight: bold; color: {grade_colors[grade]};">
                            {grade}:
                        </div>
                        <div style="flex: 1; background: #f0f0f0; height: 25px; 
                                    border-radius: 5px; margin: 0 10px; position: relative;">
                            <div style="background: {grade_colors[grade]}; height: 100%; 
                                        width: {pct}%; border-radius: 5px; transition: width 0.5s;">
                            </div>
                            <span style="position: absolute; left: 50%; top: 50%; 
                                         transform: translate(-50%, -50%); font-size: 12px;">
                                {pct:.1f}% ({cnt:,})
                            </span>
                        </div>
                    </div>
                """
            
            html += "</div>"
        
        html += """
            </div>
        </div>
        """
    
    # Source Breakdown
    if source_breakdown:
        html += """
        <div style="background: white; padding: 25px; border-radius: 12px; 
                    box-shadow: 0 8px 20px rgba(0,0,0,0.08); margin-bottom: 25px;">
            <h3 style="margin: 0 0 20px 0; font-size: 22px; color: #2c3e50;">
                Source Profile Breakdown
            </h3>
            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px;">
        """
        
        for source, data in source_breakdown.items():
            source_label = 'Trade-In (Older Devices)' if 'TRADE-IN' in source else 'CRTC (Newer Devices)'
            source_color = '#e74c3c' if 'TRADE-IN' in source else '#9b59b6'
            
            html += f"""
                <div style="border: 2px solid {source_color}; border-radius: 12px; padding: 20px;">
                    <h4 style="margin: 0 0 15px 0; color: {source_color}; font-size: 18px;">
                        {source_label}
                    </h4>
                    <p style="margin: 0 0 15px 0; color: #666; font-size: 14px;">
                        {data['total']:,} records analyzed
                    </p>
            """
            
            for grade in ['N', 'F', 'S']:
                pct = data['percentages'].get(grade, 0)
                cnt = data['counts'].get(grade, 0)
                html += f"""
                    <div style="display: flex; align-items: center; margin-bottom: 10px;">
                        <div style="width: 30px; font-weight: bold; color: {grade_colors[grade]};">
                            {grade}:
                        </div>
                        <div style="flex: 1; background: #f0f0f0; height: 25px; 
                                    border-radius: 5px; margin: 0 10px; position: relative;">
                            <div style="background: {grade_colors[grade]}; height: 100%; 
                                        width: {pct}%; border-radius: 5px; transition: width 0.5s;">
                            </div>
                            <span style="position: absolute; left: 50%; top: 50%; 
                                         transform: translate(-50%, -50%); font-size: 12px;">
                                {pct:.1f}% ({cnt:,})
                            </span>
                        </div>
                    </div>
                """
            
            html += "</div>"
        
        html += """
            </div>
        </div>
        """
    
    # Model Breakdown (if selected)
    if model_breakdown:
        html += """
        <div style="background: white; padding: 25px; border-radius: 12px; 
                    box-shadow: 0 8px 20px rgba(0,0,0,0.08);">
            <h3 style="margin: 0 0 20px 0; font-size: 22px; color: #2c3e50;">
                Model-Specific Analysis
            </h3>
            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px;">
        """
        
        for model, data in model_breakdown.items():
            html += f"""
                <div style="border: 2px solid #34495e; border-radius: 12px; padding: 20px;">
                    <h4 style="margin: 0 0 15px 0; color: #34495e; font-size: 18px;">
                        {model}
                    </h4>
                    <p style="margin: 0 0 15px 0; color: #666; font-size: 14px;">
                        {data['total']:,} tests performed
                    </p>
            """
            
            for grade in ['N', 'F', 'S']:
                pct = data['percentages'].get(grade, 0)
                cnt = data['counts'].get(grade, 0)
                html += f"""
                    <div style="display: flex; align-items: center; margin-bottom: 10px;">
                        <div style="width: 30px; font-weight: bold; color: {grade_colors[grade]};">
                            {grade}:
                        </div>
                        <div style="flex: 1; background: #f0f0f0; height: 25px; 
                                    border-radius: 5px; margin: 0 10px; position: relative;">
                            <div style="background: {grade_colors[grade]}; height: 100%; 
                                        width: {pct}%; border-radius: 5px; transition: width 0.5s;">
                            </div>
                            <span style="position: absolute; left: 50%; top: 50%; 
                                         transform: translate(-50%, -50%); font-size: 12px;">
                                {pct:.1f}% ({cnt:,})
                            </span>
                        </div>
                    </div>
                """
            
            html += "</div>"
        
        html += """
            </div>
        </div>
        """
    
    html += "</div>"
    
    return html


def generate_error_html(message: str) -> str:
    """Generate error HTML message."""
    return f"""
    <div style="text-align: center; padding: 40px; background: linear-gradient(135deg, #e74c3c 0%, #c0392b 100%); 
                border-radius: 15px; color: white;">
        <h2 style="margin: 0; font-size: 24px;">⚠️ Analysis Error</h2>
        <p style="margin: 10px 0 0 0; font-size: 16px; opacity: 0.9;">{message}</p>
    </div>
    """


def get_unique_models(df: pd.DataFrame, operator_filter: bool = True) -> List[str]:
    """Get unique models from the DataFrame, optionally filtered by automation operators."""
    try:
        with log_service_call("Get Unique Models"):
            if operator_filter:
                automation_operators = ['STN251_RED', 'STN252_RED', 'STN351_GRN', 'STN352_GRN']
                filtered_df = df[df['Operator'].str.contains('|'.join(automation_operators), na=False)]
            else:
                filtered_df = df
            
            if 'Model' in filtered_df.columns:
                models = filtered_df['Model'].dropna().unique().tolist()
                return sorted(models)
            return []
    except Exception as e:
        logger.error(f"Error getting unique models: {str(e)}", exc_info=True)
        return []