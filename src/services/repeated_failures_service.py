"""
Repeated Failures Service Module for MonsterC CSV Analysis Tool.

This module provides repeated failures analysis functionality,
extracted from the legacy monolith following the Strangler Fig pattern.
"""

import html
import subprocess
import json
import os
import asyncio
import time
import threading
import tempfile
import base64
from typing import Any, List, Optional, Tuple, Union, Dict

import gradio as gr
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from src.common.logging_config import capture_exceptions, get_logger
from src.common.mappings import DEVICE_MAP, get_test_from_result_fail, STATION_TO_MACHINE

# Initialize logger
logger = get_logger(__name__)


@capture_exceptions(user_message="Failed to get model code")
def get_model_code(model: str) -> str:
    """
    Helper function to get model code from device map.

    Args:
        model: Device model name

    Returns:
        Model code or 'Unknown' if not found
    """
    code = DEVICE_MAP.get(model, "Unknown")
    if isinstance(code, list):
        return code[0]  # Take first code if multiple exist
    return code


def get_machine_name_from_station(station_id: str) -> tuple[str, str]:
    """
    Get the machine name and location from station ID.
    
    Args:
        station_id: Station ID like 'radi183'
        
    Returns:
        Tuple of (machine_name, location) like ('bertta18', 'B18 Red Secondary')
    """
    # Handle direct bertta station IDs
    station_lower = station_id.lower()
    if station_lower.startswith('bertta'):
        # Extract number from bertta24_station -> bertta24
        if '_' in station_lower:
            machine_name = station_lower.split('_')[0]
        else:
            machine_name = station_lower
        
        # Validate the bert number
        bert_number = machine_name.replace('bertta', '')
        valid_bert_numbers = ['17', '18', '24', '25', '56']
        
        if bert_number in valid_bert_numbers:
            return machine_name, f"Direct {machine_name} station"
        else:
            # Map to a valid bert if possible
            bert_mapping = {
                '103': 'bertta56',
                '37': 'bertta24',
                '58': 'bertta25',
                '22': 'bertta24',
            }
            if bert_number in bert_mapping:
                return bert_mapping[bert_number], f"Mapped from {machine_name}"
    
    # Use the existing STATION_TO_MACHINE mapping
    location = STATION_TO_MACHINE.get(station_lower, "Unknown Machine")
    
    # Extract machine name from comments in the original mapping
    machine_map = {
        "B56 Red Primary": "bertta56",
        "B18 Red Secondary": "bertta18",
        "B25 Green Secondary": "bertta25",
        "B17 Green Primary": "bertta17",
        "B24 Manual Trades": "bertta24",
        "B22 Manual Core": "bertta24",  # Map to bertta24 since bertta22 is not valid in bert_tool.sh
        "B103 NPI": "bertta56",  # Map to bertta56 since bertta103 is not valid
        "B37 Packers": "bertta24",  # Map to bertta24 since bertta37 is not valid
        "B58 Hawks": "bertta25"  # Map to bertta25 since bertta58 is not valid
    }
    
    machine_name = machine_map.get(location, "Unknown")
    return machine_name, location


@capture_exceptions(user_message="Failed to execute remote command")
def execute_remote_command(machine_name: str, command: str, command_type: str) -> Dict[str, Any]:
    """
    Execute a command remotely on the specified machine using bert_tool.sh.
    
    Args:
        machine_name: Machine name like 'bertta18'
        command: The db-export command to execute
        command_type: Type of command ('messages', 'gauge', or 'raw_data')
        
    Returns:
        Dict with status, output, and error information
    """
    logger.info("*" * 80)
    logger.info("EXECUTE_REMOTE_COMMAND CALLED")
    logger.info(f"Machine Name: {machine_name}")
    logger.info(f"Command Type: {command_type}")
    logger.info(f"Full Command: {command}")
    logger.info("*" * 80)
    
    try:
        # Extract bert number from machine name (e.g., 'bertta18' -> '18')
        bert_number = machine_name.replace('bertta', '')
        
        # Validate bert number - bert_tool.sh only accepts specific numbers
        valid_bert_numbers = ['17', '18', '24', '25', '56']  # As per bert_tool.sh validation
        if bert_number not in valid_bert_numbers:
            # Map other machines to valid bert numbers or return error
            bert_mapping = {
                '103': '56',  # Map bertta103 to bertta56
                '37': '24',   # Map bertta37 to bertta24
                '58': '25',   # Map bertta58 to bertta25
                '22': '24',   # Map bertta22 to bertta24 (Manual Core)
            }
            
            if bert_number in bert_mapping:
                logger.warning(f"Mapping bert{bert_number} to bert{bert_mapping[bert_number]} for compatibility")
                bert_number = bert_mapping[bert_number]
            else:
                return {
                    'status': 'error',
                    'error': f'Invalid bert number: {bert_number}. Valid numbers are: {", ".join(valid_bert_numbers)}',
                    'output': ''
                }
        
        # Get password from environment or use default
        password = os.environ.get('FUSIONPW', 'fusionproject')
        
        # Path to bert_tool.sh
        bert_tool_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'bert_tool.sh')
        
        # Ensure bert_tool.sh exists
        if not os.path.exists(bert_tool_path):
            return {
                'status': 'error',
                'error': f'bert_tool.sh not found at {bert_tool_path}',
                'output': ''
            }
        
        # Set up environment to prevent interactive SSH prompts
        env = os.environ.copy()
        env['SSH_ASKPASS'] = '/bin/false'
        env['DISPLAY'] = ''  # Prevent X11 askpass
        
        # STEP 1: Get list of existing files BEFORE running the command
        # This helps us identify which file is newly created
        existing_files = set()
        if command_type == "messages":
            # List existing message export files before command execution
            list_before_cmd = [
                'bash',
                bert_tool_path,
                '--bert', bert_number,
                '--pw', password,
                '--cmd', 'ls -1 /home/fusion/ | grep "messages_export" || true'
            ]
            
            list_before_result = subprocess.run(
                list_before_cmd,
                capture_output=True,
                text=True,
                timeout=30,
                env=env
            )
            
            if list_before_result.returncode == 0 and list_before_result.stdout:
                # Parse existing files
                lines = list_before_result.stdout.strip().split('\n')
                for line in lines:
                    # Skip bert_tool output lines and command echoes
                    if ('▶' in line or '✅' in line or 'running on' in line or 
                        line.strip().startswith('ls ') or '|' in line):
                        continue
                    clean_line = line.strip()
                    # Only add if it looks like a filename
                    if clean_line and 'messages_export' in clean_line and '_export_' in clean_line:
                        existing_files.add(clean_line)
                logger.info(f"Existing message files before command: {existing_files}")
        
        # STEP 2: Execute the actual db-export command
        bert_cmd = [
            'bash',
            bert_tool_path,
            '--bert', bert_number,
            '--pw', password,
            '--cmd', f"cd /home/fusion && {command}"
        ]
        
        logger.info(f"Executing remote command on {machine_name}: {command}")
        logger.debug(f"Full bert command: {' '.join(bert_cmd)}")
        
        # Record command execution time
        import time
        command_start_time = time.time()
        
        # Execute the command
        result = subprocess.run(
            bert_cmd,
            capture_output=True,
            text=True,
            timeout=300,  # 5 minute timeout
            env=env
        )
        
        command_end_time = time.time()
        
        if result.returncode == 0:
            logger.info(f"Command executed successfully on {machine_name}")
            logger.info(f"STDOUT: {result.stdout}")
            
            # STEP 3: Find the newly created file
            # Wait a moment to ensure file creation is complete
            time.sleep(1)
            
            # List files again, but this time look for files created after our command
            list_cmd = [
                'bash',
                bert_tool_path,
                '--bert', bert_number,
                '--pw', password,
                '--cmd', 'ls -1t /home/fusion/ | grep -E "(messages_export|gauge_export|raw_data_export)" | head -10'
            ]
            
            list_result = subprocess.run(
                list_cmd,
                capture_output=True,
                text=True,
                timeout=30,
                env=env
            )
            
            created_file = None
            if list_result.returncode == 0 and list_result.stdout:
                logger.info(f"Raw stdout from ls command: {repr(list_result.stdout)}")
                
                # Parse the listing to find the newest file
                lines = list_result.stdout.strip().split('\n')
                logger.info(f"Number of lines in output: {len(lines)}")
                
                # First, let's see all the lines for debugging
                for i, line in enumerate(lines):
                    logger.debug(f"Line {i}: {repr(line)}")
                
                # Now parse for actual filenames
                parsed_files = []
                for line in lines:
                    # Skip bert_tool output lines
                    if '▶' in line or '✅' in line or 'running on' in line or 'Executing' in line:
                        continue
                    clean_line = line.strip()
                    if not clean_line:
                        continue
                    
                    # Check if this line looks like a filename (not a command or other output)
                    if '_export_' in clean_line and not clean_line.startswith('ls ') and not clean_line.startswith('grep '):
                        parsed_files.append(clean_line)
                        logger.info(f"Parsed filename: {clean_line}")
                
                logger.info(f"Total parsed files: {len(parsed_files)}")
                logger.info(f"Parsed files list: {parsed_files}")
                
                # For messages command, find the new file
                if command_type == "messages":
                    logger.info(f"Existing files before command: {existing_files}")
                    for filename in parsed_files:
                        if 'messages_export' in filename and filename not in existing_files:
                            created_file = filename
                            logger.info(f"Found NEW messages file: {created_file}")
                            break
                    
                    # If we couldn't identify a new file, use the most recent one
                    if not created_file and parsed_files:
                        for filename in parsed_files:
                            if 'messages_export' in filename:
                                created_file = filename
                                logger.warning(f"Could not identify new file, using most recent: {created_file}")
                                break
                
                # For other command types
                elif command_type == "gauge" and parsed_files:
                    for filename in parsed_files:
                        if 'gauge_export' in filename:
                            created_file = filename
                            logger.info(f"Found gauge file: {created_file}")
                            break
                elif command_type == "raw_data" and parsed_files:
                    for filename in parsed_files:
                        if 'raw_data_export' in filename:
                            created_file = filename
                            logger.info(f"Found raw_data file: {created_file}")
                            break
                
                if not created_file:
                    logger.warning(f"No {command_type}_export file found in parsed output")
            
            # STEP 4: For messages command, retrieve the CSV content
            csv_content = None
            if command_type == "messages" and created_file:
                logger.info(f"Attempting to retrieve CSV content for messages file: {created_file}")
                
                # Ensure we have a valid filename, not a command
                if created_file.startswith('ls ') or '|' in created_file:
                    logger.error(f"ERROR: created_file contains a command, not a filename: {created_file}")
                    logger.error("This indicates a parsing error in the file listing logic")
                else:
                    # Use SCP to transfer the file locally to avoid pipe buffer deadlock
                    logger.info("Using SCP method to transfer CSV file...")
                    
                    # Create temporary directory for file transfer
                    temp_dir = tempfile.mkdtemp()
                    local_file = os.path.join(temp_dir, created_file)
                    
                    # Map bert number to port
                    bert_to_port = {
                        '17': '45017',
                        '18': '45018', 
                        '24': '45024',
                        '25': '45025',
                        '56': '45056'
                    }
                    
                    # Build SCP command with ProxyJump
                    scp_cmd = [
                        'sshpass', '-p', password,
                        'scp',
                        '-o', 'StrictHostKeyChecking=no',
                        '-o', 'UserKnownHostsFile=/dev/null',
                        '-o', f'ProxyJump=ubuntu@52.54.110.136',
                        '-P', bert_to_port.get(bert_number, '45024'),
                        f'fusion@127.0.0.1:/home/fusion/{created_file}',
                        local_file
                    ]
                    
                    try:
                        # Execute file transfer
                        logger.info(f"Transferring CSV file via SCP: {created_file}")
                        logger.info(f"SCP command: {' '.join(scp_cmd)}")
                        scp_result = subprocess.run(scp_cmd, capture_output=True, text=True, timeout=30)
                        
                        if scp_result.returncode == 0 and os.path.exists(local_file):
                            # Read the transferred file
                            with open(local_file, 'r', encoding='utf-8') as f:
                                csv_content = f.read()
                            
                            logger.info(f"Successfully retrieved CSV content via SCP: {len(csv_content)} bytes")
                            
                            # Cleanup
                            os.remove(local_file)
                            os.rmdir(temp_dir)
                        else:
                            logger.error(f"SCP transfer failed with return code: {scp_result.returncode}")
                            logger.error(f"SCP stderr: {scp_result.stderr}")
                            
                            # Fallback to base64 encoding method
                            logger.info("Attempting fallback method using base64 encoding...")
                            
                            # Set up environment to prevent interactive SSH prompts
                            env = os.environ.copy()
                            env['SSH_ASKPASS'] = '/bin/false'
                            env['DISPLAY'] = ''  # Prevent X11 askpass
                            
                            base64_cmd = [
                                'bash',
                                bert_tool_path,
                                '--bert', bert_number,
                                '--pw', password,
                                '--cmd', f'base64 /home/fusion/{created_file}'
                            ]
                            
                            base64_result = subprocess.run(base64_cmd, capture_output=True, text=True, timeout=30, env=env)
                            
                            if base64_result.returncode == 0:
                                # Decode base64 content
                                encoded_content = base64_result.stdout
                                # Clean bert_tool output
                                lines = encoded_content.strip().split('\n')
                                clean_content = []
                                for line in lines:
                                    if not any(marker in line for marker in ['▶', '✅', 'running on', 'cd /', 'base64']):
                                        clean_content.append(line)
                                
                                try:
                                    csv_content = base64.b64decode(''.join(clean_content)).decode('utf-8')
                                    logger.info(f"Successfully retrieved CSV content via base64: {len(csv_content)} bytes")
                                except Exception as e:
                                    logger.error(f"Failed to decode base64 content: {str(e)}")
                                    csv_content = None
                            else:
                                logger.error(f"Base64 fallback failed: {base64_result.stderr}")
                                csv_content = None
                            
                            # Cleanup temp directory if it still exists
                            if os.path.exists(temp_dir):
                                if os.path.exists(local_file):
                                    os.remove(local_file)
                                os.rmdir(temp_dir)
                                
                    except subprocess.TimeoutExpired:
                        logger.error("SCP command timed out after 30 seconds")
                        csv_content = None
                        # Cleanup on timeout
                        if os.path.exists(local_file):
                            os.remove(local_file)
                        if os.path.exists(temp_dir):
                            os.rmdir(temp_dir)
                    except Exception as e:
                        logger.error(f"Error transferring CSV file: {str(e)}")
                        csv_content = None
                        # Cleanup on error
                        if os.path.exists(local_file):
                            os.remove(local_file)
                        if os.path.exists(temp_dir):
                            os.rmdir(temp_dir)
            
            return {
                'status': 'success',
                'output': result.stdout,
                'error': '',
                'created_file': created_file,
                'csv_content': csv_content,
                'command_type': command_type
            }
        else:
            logger.error(f"Command failed with return code {result.returncode}")
            logger.error(f"STDERR: {result.stderr}")
            return {
                'status': 'error',
                'output': result.stdout,
                'error': result.stderr
            }
            
    except subprocess.TimeoutExpired:
        logger.error("Command timed out after 5 minutes")
        return {
            'status': 'error',
            'error': 'Command timed out after 5 minutes',
            'output': ''
        }
    except Exception as e:
        logger.error(f"Error executing remote command: {str(e)}")
        return {
            'status': 'error',
            'error': str(e),
            'output': ''
        }


@capture_exceptions(user_message="Failed to create summary")
def create_summary(df: pd.DataFrame) -> str:
    """
    Create beautiful HTML summary of the dataframe with enhanced styling.

    Args:
        df: DataFrame with repeated failures data

    Returns:
        HTML formatted summary with beautiful styling
    """
    # Calculate severity levels based on failure counts
    max_tc_count = df["TC Count"].max() if len(df) > 0 else 0

    # Create HTML with enhanced styling
    html_content = f"""
    <div style="padding: 20px;">
        <!-- Header Section -->
        <div style="background: linear-gradient(135deg, #ff6b6b 0%, #ee5a24 100%); padding: 25px; border-radius: 15px; margin-bottom: 20px; box-shadow: 0 10px 30px rgba(0,0,0,0.1);">
            <h2 style="color: white; margin: 0 0 10px 0; font-size: 24px; text-align: center;">
                🔍 Repeated Failures Analysis
            </h2>
            <p style="color: white; margin: 0; text-align: center; opacity: 0.9; font-size: 16px;">
                Found <span style="font-size: 28px; font-weight: bold;">{len(df)}</span> instances of repeated failures
            </p>
        </div>

        <!-- Command Generation Container - Commands will be injected here dynamically -->
        <div id="command_generation_injection_point"></div>

        <!-- Table Container -->
        <div style="background: white; border-radius: 15px; box-shadow: 0 5px 20px rgba(0,0,0,0.08); overflow: hidden;">
            <table style="width: 100%; border-collapse: collapse; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;">
                <!-- Table Header -->
                <thead>
                    <tr style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);">
                        <th style="padding: 15px; text-align: left; color: white; font-weight: 600; font-size: 21px; border-right: 1px solid rgba(255,255,255,0.1);">
                            <div style="display: flex; align-items: center; gap: 8px;">
                                <span style="opacity: 0.8;">📱</span> Model
                            </div>
                        </th>
                        <th style="padding: 15px; text-align: left; color: white; font-weight: 600; font-size: 21px; border-right: 1px solid rgba(255,255,255,0.1);">
                            <div style="display: flex; align-items: center; gap: 8px;">
                                <span style="opacity: 0.8;">🔤</span> Code
                            </div>
                        </th>
                        <th style="padding: 15px; text-align: left; color: white; font-weight: 600; font-size: 21px; border-right: 1px solid rgba(255,255,255,0.1);">
                            <div style="display: flex; align-items: center; gap: 8px;">
                                <span style="opacity: 0.8;">🏭</span> Station
                            </div>
                        </th>
                        <th style="padding: 15px; text-align: left; color: white; font-weight: 600; font-size: 21px; border-right: 1px solid rgba(255,255,255,0.1);">
                            <div style="display: flex; align-items: center; gap: 8px;">
                                <span style="opacity: 0.8;">👤</span> Operator
                            </div>
                        </th>
                        <th style="padding: 15px; text-align: left; color: white; font-weight: 600; font-size: 21px; border-right: 1px solid rgba(255,255,255,0.1);">
                            <div style="display: flex; align-items: center; gap: 8px;">
                                <span style="opacity: 0.8;">🧪</span> Test Case
                            </div>
                        </th>
                        <th style="padding: 15px; text-align: center; color: white; font-weight: 600; font-size: 21px; border-right: 1px solid rgba(255,255,255,0.1);">
                            <div style="display: flex; align-items: center; justify-content: center; gap: 8px;">
                                <span style="opacity: 0.8;">📊</span> Count
                            </div>
                        </th>
                        <th style="padding: 15px; text-align: center; color: white; font-weight: 600; font-size: 21px;">
                            <div style="display: flex; align-items: center; justify-content: center; gap: 8px;">
                                <span style="opacity: 0.8;">📱</span> IMEIs
                            </div>
                        </th>
                    </tr>
                </thead>
                <!-- Table Body -->
                <tbody>
    """

    # Add table rows with enhanced styling
    for idx, row in df.iterrows():
        # Determine severity color based on TC Count
        tc_count = row["TC Count"]
        if tc_count >= max_tc_count * 0.8:
            severity_color = "#dc3545"  # Critical (Red)
            severity_bg = "rgba(220, 53, 69, 0.1)"
            severity_icon = "🔴"
        elif tc_count >= max_tc_count * 0.5:
            severity_color = "#fd7e14"  # High (Orange)
            severity_bg = "rgba(253, 126, 20, 0.1)"
            severity_icon = "🟠"
        elif tc_count >= max_tc_count * 0.3:
            severity_color = "#ffc107"  # Medium (Yellow)
            severity_bg = "rgba(255, 193, 7, 0.1)"
            severity_icon = "🟡"
        else:
            severity_color = "#28a745"  # Low (Green)
            severity_bg = "rgba(40, 167, 69, 0.1)"
            severity_icon = "🟢"

        # Alternate row background
        row_bg = "#f8f9fa" if idx % 2 == 0 else "#ffffff"

        # Escape HTML special characters
        model_escaped = html.escape(str(row["Model"]))
        model_code_escaped = html.escape(str(row["Model Code"]))
        station_id_escaped = html.escape(str(row["Station ID"]))
        operator_escaped = html.escape(str(row["Operator"]))
        result_fail_escaped = html.escape(str(row["result_FAIL"]))

        # Escape single quotes for JavaScript
        model_js_escaped = model_escaped.replace("'", "\\'")
        station_js_escaped = station_id_escaped.replace("'", "\\'")
        result_fail_js_escaped = result_fail_escaped.replace("'", "\\'")

        html_content += f"""
                    <tr style="background: {row_bg}; transition: all 0.2s ease; cursor: pointer;"
                        onmouseover="this.style.background='linear-gradient(90deg, {severity_bg} 0%, rgba(255,255,255,0) 100%)'; this.style.transform='translateX(5px)';"
                        onmouseout="this.style.background='{row_bg}'; this.style.transform='translateX(0)';"
                        onclick="window.handleFailureRowClick('{model_js_escaped}', '{station_js_escaped}', '{result_fail_js_escaped}', {idx})">
                        <td style="padding: 12px 15px; border-bottom: 1px solid #e9ecef; font-size: 21px; font-weight: 500; color: #333;">
                            {model_escaped}
                        </td>
                        <td style="padding: 12px 15px; border-bottom: 1px solid #e9ecef; font-size: 19.5px; color: #6c757d; font-family: monospace;">
                            {model_code_escaped}
                        </td>
                        <td style="padding: 12px 15px; border-bottom: 1px solid #e9ecef; font-size: 19.5px; color: #495057;">
                            {station_id_escaped}
                        </td>
                        <td style="padding: 12px 15px; border-bottom: 1px solid #e9ecef; font-size: 19.5px; color: #495057;">
                            {operator_escaped}
                        </td>
                        <td style="padding: 12px 15px; border-bottom: 1px solid #e9ecef; font-size: 19.5px; color: #333; max-width: 300px;">
                            <div style="overflow: hidden; text-overflow: ellipsis; white-space: nowrap; color: #333;" title="{result_fail_escaped}">
                                {result_fail_escaped}
                            </div>
                        </td>
                        <td style="padding: 12px 15px; border-bottom: 1px solid #e9ecef; text-align: center;">
                            <div style="display: flex; align-items: center; justify-content: center; gap: 8px;">
                                <span style="font-size: 18px;">{severity_icon}</span>
                                <span style="font-size: 24px; font-weight: bold; color: {severity_color};">
                                    {row['TC Count']}
                                </span>
                            </div>
                        </td>
                        <td style="padding: 12px 15px; border-bottom: 1px solid #e9ecef; text-align: center;">
                            <span style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 6px 16px; border-radius: 20px; font-size: 19.5px; font-weight: 500;">
                                {row['IMEI Count']}
                            </span>
                        </td>
                    </tr>
        """

    html_content += """
                </tbody>
            </table>
        </div>

        <!-- Summary Cards -->
        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; margin-top: 20px;">
    """

    # Calculate summary statistics
    if len(df) > 0:
        total_failures = df["TC Count"].sum()
        total_imeis = df["IMEI Count"].sum()
        unique_models = df["Model"].nunique()
        unique_stations = df["Station ID"].nunique()

        html_content += f"""
            <!-- Total Failures Card -->
            <div style="background: linear-gradient(135deg, #ff6b6b 0%, #ee5a24 100%); padding: 20px; border-radius: 12px; color: white; box-shadow: 0 4px 15px rgba(255, 107, 107, 0.3); transition: transform 0.3s ease;">
                <div style="display: flex; justify-content: space-between; align-items: start;">
                    <div>
                        <p style="margin: 0 0 8px 0; font-size: 14px; opacity: 0.9;">Total Failures</p>
                        <h3 style="margin: 0; font-size: 28px; font-weight: bold;">{total_failures:,}</h3>
                    </div>
                    <div style="font-size: 42px; opacity: 1.0; filter: none; z-index: 10; position: relative;">🚨</div>
                </div>
            </div>

            <!-- Affected IMEIs Card -->
            <div style="background: linear-gradient(135deg, #5f27cd 0%, #341f97 100%); padding: 20px; border-radius: 12px; color: white; box-shadow: 0 4px 15px rgba(95, 39, 205, 0.3); transition: transform 0.3s ease;">
                <div style="display: flex; justify-content: space-between; align-items: start;">
                    <div>
                        <p style="margin: 0 0 8px 0; font-size: 14px; opacity: 0.9;">Affected IMEIs</p>
                        <h3 style="margin: 0; font-size: 28px; font-weight: bold;">{total_imeis:,}</h3>
                    </div>
                    <div style="font-size: 42px; opacity: 1.0; filter: none; z-index: 10; position: relative;">📱</div>
                </div>
            </div>

            <!-- Unique Models Card -->
            <div style="background: linear-gradient(135deg, #00d2d3 0%, #01a3a4 100%); padding: 20px; border-radius: 12px; color: white; box-shadow: 0 4px 15px rgba(0, 210, 211, 0.3); transition: transform 0.3s ease;">
                <div style="display: flex; justify-content: space-between; align-items: start;">
                    <div>
                        <p style="margin: 0 0 8px 0; font-size: 14px; opacity: 0.9;">Unique Models</p>
                        <h3 style="margin: 0; font-size: 28px; font-weight: bold;">{unique_models}</h3>
                    </div>
                    <div style="font-size: 42px; opacity: 1.0; filter: none; z-index: 10; position: relative;">📊</div>
                </div>
            </div>

            <!-- Test Stations Card -->
            <div style="background: linear-gradient(135deg, #feca57 0%, #ff9ff3 100%); padding: 20px; border-radius: 12px; color: white; box-shadow: 0 4px 15px rgba(254, 202, 87, 0.3); transition: transform 0.3s ease;">
                <div style="display: flex; justify-content: space-between; align-items: start;">
                    <div>
                        <p style="margin: 0 0 8px 0; font-size: 14px; opacity: 0.9;">Test Stations</p>
                        <h3 style="margin: 0; font-size: 28px; font-weight: bold;">{unique_stations}</h3>
                    </div>
                    <div style="font-size: 42px; opacity: 1.0; filter: none; z-index: 10; position: relative;">🏭</div>
                </div>
            </div>
        """

    html_content += """
        </div>

        <!-- Legend -->
        <div style="margin-top: 20px; padding: 15px; background: rgba(107, 99, 246, 0.05); border-radius: 10px; border: 1px solid rgba(107, 99, 246, 0.2);">
            <h4 style="margin: 0 0 10px 0; color: #667eea; font-size: 24px;">📊 Severity Legend</h4>
            <div style="display: flex; gap: 20px; flex-wrap: wrap; font-size: 19.5px;">
                <div style="display: flex; align-items: center; gap: 8px;">
                    <span>🔴</span> <span style="color: #dc3545; font-weight: 500;">Critical</span> <span style="color: #6c757d;">(≥80% of max)</span>
                </div>
                <div style="display: flex; align-items: center; gap: 8px;">
                    <span>🟠</span> <span style="color: #fd7e14; font-weight: 500;">High</span> <span style="color: #6c757d;">(≥50% of max)</span>
                </div>
                <div style="display: flex; align-items: center; gap: 8px;">
                    <span>🟡</span> <span style="color: #ffc107; font-weight: 500;">Medium</span> <span style="color: #6c757d;">(≥30% of max)</span>
                </div>
                <div style="display: flex; align-items: center; gap: 8px;">
                    <span>🟢</span> <span style="color: #28a745; font-weight: 500;">Low</span> <span style="color: #6c757d;">(<30% of max)</span>
                </div>
            </div>
        </div>
    </div>

    <style>
        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(20px); }
            to { opacity: 1; transform: translateY(0); }
        }

        /* Apply animation to all cards */
        div[style*="grid-template-columns"] > div {
            animation: fadeIn 0.6s ease-out forwards;
        }

        div[style*="grid-template-columns"] > div:nth-child(2) {
            animation-delay: 0.1s;
        }

        div[style*="grid-template-columns"] > div:nth-child(3) {
            animation-delay: 0.2s;
        }

        div[style*="grid-template-columns"] > div:nth-child(4) {
            animation-delay: 0.3s;
        }

        /* Hover effect for cards */
        div[style*="grid-template-columns"] > div:hover {
            transform: translateY(-3px) !important;
            box-shadow: 0 8px 25px rgba(0,0,0,0.15) !important;
        }

        /* Highlight selected row */
        tr.selected-row {
            background: linear-gradient(90deg, rgba(102, 126, 234, 0.1) 0%, rgba(118, 75, 162, 0.1) 100%) !important;
        }
    </style>

    <script>
        // Global variable to store the current selected row
        window.selectedRowIndex = null;

        // Function to handle row clicks from the HTML table
        window.handleFailureRowClick = function(model, station, testCase, rowIndex) {
            console.log('Row clicked:', model, station, testCase, rowIndex);

            // Remove previous selection highlight
            document.querySelectorAll('tr.selected-row').forEach(row => {
                row.classList.remove('selected-row');
            });

            // Add selection highlight to clicked row
            const clickedRow = document.querySelectorAll('tbody tr')[rowIndex];
            if (clickedRow) {
                clickedRow.classList.add('selected-row');
            }

            // Store selected row index and data
            window.selectedRowIndex = rowIndex;
            window.selectedRowData = { model, station, testCase };

            // Show loading state in injection point
            const injectionPoint = document.getElementById('command_generation_injection_point');
            if (injectionPoint) {
                injectionPoint.innerHTML = '<div style="text-align: center; padding: 20px;"><div style="display: inline-block; width: 40px; height: 40px; border: 3px solid #f3f3f3; border-top: 3px solid #667eea; border-radius: 50%; animation: spin 1s linear infinite;"></div><p style="margin-top: 10px; color: #667eea;">Generating commands...</p></div>';
            }

            // Call the external handler if it exists
            if (window.onFailureRowClick) {
                window.onFailureRowClick(model, station, testCase);
            }
        };

        // Function to inject command UI into the proper location
        window.injectCommandUI = function(commandHtml) {
            const injectionPoint = document.getElementById('command_generation_injection_point');
            if (injectionPoint) {
                injectionPoint.innerHTML = commandHtml;
                // Scroll to the command UI smoothly
                injectionPoint.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
            }
        };
    </script>
    """

    return html_content


@capture_exceptions(user_message="Failed to create plot")
def create_plot(df: pd.DataFrame) -> go.Figure:
    """
    Create bar chart visualization of the data.

    Args:
        df: DataFrame with repeated failures data

    Returns:
        Plotly figure with bar chart
    """
    fig = px.bar(
        df,
        x="Station ID",
        y="TC Count",
        color="Model",
        hover_data=["result_FAIL", "Operator", "IMEI Count"],
        title=f"Filtered Repeated Failures",
        labels={"TC Count": "Number of Test Case Failures"},
        height=600,
    )

    fig.update_layout(
        xaxis_title="Station ID",
        yaxis_title="Number of Test Case Failures",
        xaxis_tickangle=-45,
        legend_title="Model",
        barmode="group",
    )

    return fig


@capture_exceptions(user_message="Failed to analyze repeated failures")
def analyze_repeated_failures(
    df: pd.DataFrame, min_failures: int = 4
) -> Tuple[str, Any, Any, Any, pd.DataFrame]:
    """
    Analyzes repeated failures in test data and returns summary, chart, and interactive components.

    Args:
        df: Input DataFrame with test data
        min_failures: Minimum number of failures to be considered "repeated"

    Returns:
        Tuple of (summary_text, figure, interactive_dataframe, dropdown, original_dataframe)
    """
    try:
        # If df is a file object, load it first
        if hasattr(df, "name"):
            from src.common.io import load_data

            df = load_data(df)

        # Filter for FAILURE in Overall status
        failure_df = df[df["Overall status"] == "FAILURE"]
        logger.info(f"Found {len(failure_df)} failures")

        # Create initial aggregation with both counts and operator info
        agg_df = (
            failure_df.groupby(["Model", "Station ID", "result_FAIL", "Operator"])
            .agg({"IMEI": ["count", "nunique"]})
            .reset_index()
        )

        # Rename columns
        agg_df.columns = [
            "Model",
            "Station ID",
            "result_FAIL",
            "Operator",
            "TC Count",
            "IMEI Count",
        ]

        # Filter for minimum test case failures threshold
        repeated_failures = agg_df[agg_df["TC Count"] >= min_failures].copy()
        logger.info(f"Found {len(repeated_failures)} instances of repeated failures")

        # Add Model Code column
        repeated_failures["Model Code"] = repeated_failures["Model"].apply(
            get_model_code
        )

        # Sort by TC Count in descending order
        repeated_failures = repeated_failures.sort_values("TC Count", ascending=False)

        # Create summary using the beautiful HTML format
        summary = create_summary(repeated_failures)

        # Create bar chart
        fig = px.bar(
            repeated_failures,
            x="Station ID",
            y="TC Count",
            color="Model",
            hover_data=["result_FAIL", "Operator", "IMEI Count"],
            title=f"Repeated Failures (≥{min_failures} times)",
            labels={"TC Count": "Number of Test Case Failures"},
            height=600,
        )

        fig.update_layout(
            xaxis_title="Station ID",
            yaxis_title="Number of Test Case Failures",
            xaxis_tickangle=-45,
            legend_title="Model",
            barmode="group",
        )

        # Get test cases for dropdown
        test_case_counts = repeated_failures.groupby("result_FAIL")["TC Count"].max()
        sorted_test_cases = test_case_counts.sort_values(ascending=False).index.tolist()

        dropdown_choices = ["Select All", "Clear All"] + [
            f"{test_case} ({test_case_counts[test_case]}) max failures"
            for test_case in sorted_test_cases
        ]

        logger.info("Successfully completed repeated failures analysis")
        return (
            summary,
            fig,
            gr.Dropdown(
                choices=dropdown_choices,
                value=dropdown_choices[2:],
                label="Filter by Test Case",
                multiselect=True,
            ),
            df,  # Return the original dataframe for command generation
            repeated_failures,  # Return the repeated failures dataframe for filtering
        )

    except Exception as e:
        logger.error(f"Error in analyze_repeated_failures: {str(e)}")
        error_message = f"""
        <div style="text-align: center; padding: 40px; background: linear-gradient(135deg, #ff6b6b 0%, #ee5a24 100%); border-radius: 15px; color: white;">
            <h3 style="margin: 0; font-size: 24px;">⚠️ Error Occurred</h3>
            <p style="margin: 10px 0 0 0; font-size: 16px; opacity: 0.9;">{html.escape(str(e))}</p>
            <p style="margin: 10px 0 0 0; font-size: 14px; opacity: 0.7;">Please check your input and try again.</p>
        </div>
        """
        return error_message, None, None, None, None


@capture_exceptions(user_message="Failed to update summary chart and data")
def update_summary_chart_and_data(
    repeated_failures_df: pd.DataFrame, sort_by: str, selected_test_cases: List[str]
) -> Tuple[str, go.Figure]:
    """
    Updates the summary chart based on sorting and filtering preferences.

    Args:
        repeated_failures_df: Input dataframe with repeated failures data
        sort_by: Column name to sort by; one of "TC Count", "Model", "Station ID", "Test Case", or "Model Code"
        selected_test_cases: List of selected test cases to filter by

    Returns:
        Tuple of (summary_text, plotly_figure)
    """

    # Check for no data
    if repeated_failures_df is None or len(repeated_failures_df) == 0:
        return "No data available to sort/filter", None

    # Make a copy of the dataframe so we don't modify the original
    df = repeated_failures_df.copy()

    # Handle test case filtering
    if selected_test_cases:
        # If the user chose "Select All", do nothing
        if "Select All" in selected_test_cases:
            pass
        # If the user chose "Clear All", filter out all test cases
        elif "Clear All" in selected_test_cases:
            df = df[df["result_FAIL"] == ""]
        # If the user chose specific test cases, filter for those
        else:
            # Convert the selected test cases to the actual test case names without counts
            selected_actual_cases = [
                test_case.split(" (")[0] for test_case in selected_test_cases
            ]
            # Filter the dataframe for the selected test cases
            df = df[df["result_FAIL"].isin(selected_actual_cases)]

    # Sort the dataframe by the selected column
    sort_column_map = {
        "TC Count": "TC Count",
        "Model": "Model",
        "Station ID": "Station ID",
        "Operator": "Operator",
        "Test Case": "result_FAIL",
        "Model Code": "Model Code",
    }

    df = df.sort_values(sort_column_map[sort_by], ascending=False)

    # Create an updated interactive dataframe with explicit column names
    interactive_df = gr.Dataframe(
        value=df,
        headers=df.columns.tolist(),
        interactive=True,
        wrap=True,
        show_label=True,
        column_widths=None,
        label="Filtered Repeated Failures",
    )

    # Return the updated summary text and plotly figure
    return create_summary(df), create_plot(df)


@capture_exceptions(user_message="Failed to update summary")
def update_summary(
    repeated_failures_df: pd.DataFrame, sort_by: str, selected_test_cases: List[str]
) -> str:
    """
    Updates the summary text based on sorting and filtering preferences.

    Args:
        repeated_failures_df: Input dataframe with repeated failures data
        sort_by: Column name to sort by
        selected_test_cases: List of selected test cases to filter by

    Returns:
        Updated summary text
    """
    try:
        if repeated_failures_df is None or len(repeated_failures_df) == 0:
            return """
            <div style="text-align: center; padding: 40px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); border-radius: 15px; color: white;">
                <h3 style="margin: 0; font-size: 24px;">📊 No Data Available</h3>
                <p style="margin: 10px 0 0 0; font-size: 16px; opacity: 0.9;">No data available to sort/filter</p>
            </div>
            """

        df = repeated_failures_df.copy()

        # Handle Select All/Clear All and apply test case filter
        if selected_test_cases:
            if "Select All" in selected_test_cases:
                # Include all test cases
                pass
            elif "Clear All" in selected_test_cases:
                # Clear all selections
                df = df[df["result_FAIL"] == ""]  # This will create an empty result
            else:
                # Filter for selected test cases
                selected_actual_cases = [
                    test_case.split(" (")[0] for test_case in selected_test_cases
                ]
                df = df[df["result_FAIL"].isin(selected_actual_cases)]

        # Apply sorting
        sort_column_map = {
            "TC Count": "TC Count",
            "Model": "Model",
            "Station ID": "Station ID",
            "Operator": "Operator",
            "Test Case": "result_FAIL",
            "Model Code": "Model Code",
        }
        df = df.sort_values(sort_column_map[sort_by], ascending=False)

        # Use the beautiful create_summary function
        return create_summary(df)
    except Exception as e:
        logger.error(f"Error updating summary: {str(e)}")
        return f"""
        <div style="text-align: center; padding: 40px; background: linear-gradient(135deg, #ff6b6b 0%, #ee5a24 100%); border-radius: 15px; color: white;">
            <h3 style="margin: 0; font-size: 24px;">⚠️ Error Occurred</h3>
            <p style="margin: 10px 0 0 0; font-size: 16px; opacity: 0.9;">Error updating summary: {str(e)}</p>
        </div>
        """


@capture_exceptions(user_message="Failed to handle test case selection")
def handle_test_case_selection(
    evt: gr.SelectData, selected_test_cases: List[str]
) -> List[str]:
    """
    Handles the Select All/Clear All functionality for test case filter.

    Args:
        evt: Gradio SelectData event
        selected_test_cases: Currently selected test cases

    Returns:
        Updated list of selected test cases
    """
    if evt.value == "Select All":
        # This needs to be handled by the UI layer as it needs access to test_case_filter.choices
        # Return a special marker that the UI can recognize
        return ["__SELECT_ALL__"]
    elif evt.value == "Clear All":
        return []
    return selected_test_cases


@capture_exceptions(user_message="Failed to handle remote command execution")
def handle_remote_command_execution(machine: str, command: str, command_type: str) -> Dict[str, Any]:
    """
    Handle the remote command execution request from the UI.
    
    Args:
        machine: Machine name (e.g., 'bertta18')
        command: The db-export command to execute
        command_type: Type of command ('messages', 'gauge', or 'raw_data')
        
    Returns:
        Dict with execution status and results
    """
    logger.info("=" * 80)
    logger.info("REMOTE COMMAND EXECUTION HANDLER CALLED")
    logger.info(f"Machine: {machine}")
    logger.info(f"Command type: {command_type}")
    logger.info(f"Command: {command}")
    logger.info("=" * 80)
    
    try:
        # Execute the command remotely
        result = execute_remote_command(machine, command, command_type)
        
        # Log the result
        if result['status'] == 'success':
            logger.info(f"Command executed successfully on {machine}")
            if result.get('created_file'):
                logger.info(f"Output file created: {result['created_file']}")
        else:
            logger.error(f"Command failed on {machine}: {result['error']}")
        
        # Pass through all the result data including CSV content
        return result
        
    except Exception as e:
        logger.error(f"Error in handle_remote_command_execution: {str(e)}")
        return {
            'status': 'error',
            'error': str(e),
            'output': '',
            'csv_content': None,
            'command_type': command_type
        }


@capture_exceptions(user_message="Failed to generate IMEI commands")
def generate_imei_commands(
    full_df: pd.DataFrame, model: str, station_id: str, test_case: str
) -> str:
    """
    Generate db-export commands for failed IMEIs based on the selected row.

    Args:
        full_df: The original full dataframe with all test data
        model: The model from the clicked row
        station_id: The station ID from the clicked row
        test_case: The test case (result_FAIL) from the clicked row

    Returns:
        HTML string containing the command generation UI with proper db-export commands
    """
    logger.info("=" * 60)
    logger.info("generate_imei_commands called!")
    logger.info(f"Model: {model}")
    logger.info(f"Station ID: {station_id}")
    logger.info(f"Test Case: {test_case}")
    logger.info(f"Full DF shape: {full_df.shape if full_df is not None else 'None'}")
    logger.info("=" * 60)

    try:
        if full_df is None or full_df.empty:
            logger.warning("No data available in full_df")
            return (
                '<div style="color: red;">No data available to generate commands.</div>'
            )

        # Filter the dataframe for matching failures
        filtered_df = full_df[
            (full_df["Model"] == model)
            & (full_df["Station ID"] == station_id)
            & (full_df["result_FAIL"] == test_case)
            & (full_df["Overall status"] == "FAILURE")
        ]

        logger.info(f"Filtered dataframe shape: {filtered_df.shape}")

        if filtered_df.empty:
            logger.warning("No matching failures found")
            return '<div style="color: red;">No matching failures found for the selected criteria.</div>'

        # Check if IMEI column exists
        if "IMEI" not in filtered_df.columns:
            logger.error("IMEI column not found in dataframe")
            logger.info(f"Available columns: {filtered_df.columns.tolist()}")
            return '<div style="color: red;">IMEI column not found in the data. Please ensure your CSV has an IMEI column.</div>'

        # Get unique IMEIs
        imeis = filtered_df["IMEI"].dropna().unique().tolist()
        logger.info(f"Found {len(imeis)} unique IMEIs")

        # Convert IMEIs to strings (handle float IMEIs)
        imeis = [
            str(int(float(imei))) if isinstance(imei, (int, float)) else str(imei)
            for imei in imeis
        ]
        imei_count = len(imeis)
        logger.info(f"Converted IMEIs: {imeis[:5]}...")  # Log first 5

        # Handle case with no IMEIs
        if not imeis:
            logger.warning("No valid IMEIs found after conversion")
            return '<div style="color: red;">No valid IMEIs found for the selected criteria.</div>'

        # Generate the db-export commands
        imei_args = " ".join([f"--dut {imei}" for imei in imeis])

        # Map the failure description to the proper test name
        mapped_test_name = get_test_from_result_fail(test_case)
        logger.debug(f"Mapped test_case '{test_case}' to test name '{mapped_test_name}'")

        # Create the three commands
        messages_cmd = f"db-export messages {imei_args}"
        gauge_cmd = f'db-export gauge --test "{mapped_test_name}" {imei_args}'
        raw_data_cmd = f'db-export raw_data --test "{mapped_test_name}" {imei_args}'

        # Escape for JavaScript - need to escape backslashes first, then backticks and quotes
        messages_cmd_js = (
            messages_cmd.replace("\\", "\\\\").replace("`", "\\`").replace('"', '\\"').replace("'", "\\'")
        )
        gauge_cmd_js = (
            gauge_cmd.replace("\\", "\\\\").replace("`", "\\`").replace('"', '\\"').replace("'", "\\'")
        )
        raw_data_cmd_js = (
            raw_data_cmd.replace("\\", "\\\\").replace("`", "\\`").replace('"', '\\"').replace("'", "\\'")
        )

        # Get machine name and location from station ID
        machine_name, location = get_machine_name_from_station(station_id)
        
        # Create the HTML response with improved design
        html_content = f"""
        <div id="command-ui" style="margin: 15px 0; animation: slideDown 0.4s ease-out;">
            <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); border-radius: 15px; padding: 25px; box-shadow: 0 10px 30px rgba(0,0,0,0.2);">
                <div style="text-align: center; margin-bottom: 20px;">
                    <h3 style="margin: 0 0 15px 0; color: white; font-size: 24px; font-weight: 700; text-shadow: 2px 2px 4px rgba(0,0,0,0.3);">
                        🔧 IMEI Extractor Commands
                    </h3>
                    <div style="background: rgba(255,255,255,0.2); border-radius: 10px; padding: 15px; backdrop-filter: blur(10px);">
                        <p style="margin: 0 0 10px 0; color: white; font-size: 16px; font-weight: 500;">
                            <strong>📱 Model:</strong> {html.escape(model)} &nbsp;&nbsp;|&nbsp;&nbsp; 
                            <strong>📍 Station:</strong> {html.escape(station_id)} &nbsp;&nbsp;|&nbsp;&nbsp; 
                            <strong>🔍 Test:</strong> {html.escape(test_case)}
                        </p>
                        <p style="margin: 0 0 10px 0; color: white; font-size: 16px;">
                            <strong>📊 Found:</strong> <span style="font-size: 20px; font-weight: 700;">{imei_count}</span> failed IMEIs
                        </p>
                        <div style="background: rgba(0,0,0,0.3); border-radius: 8px; padding: 12px; margin-top: 10px;">
                            <p style="margin: 0; color: #ffd700; font-size: 18px; font-weight: 700; text-shadow: 2px 2px 4px rgba(0,0,0,0.5);">
                                🖥️ CONNECT TO: <span style="font-size: 22px; text-transform: uppercase;">{machine_name}</span>
                            </p>
                            <p style="margin: 5px 0 0 0; color: #e0e0e0; font-size: 14px;">
                                Location: {location}
                            </p>
                        </div>
                    </div>
                </div>

                <!-- Messages Command -->
                <div style="background: white; border-radius: 10px; padding: 15px; margin-bottom: 12px; box-shadow: 0 2px 10px rgba(0,0,0,0.1);">
                    <p style="margin: 0 0 8px 0; color: #333; font-size: 15px; font-weight: 600;">📨 Messages Command:</p>
                    <div style="display: flex; align-items: center; gap: 10px;">
                        <code style="flex: 1; background: #1a1a1a; color: #00ff00; padding: 12px 16px; border-radius: 6px; font-family: 'Consolas', 'Monaco', 'Courier New', monospace; font-size: 13px; overflow-x: auto; white-space: nowrap; display: block; border: 1px solid #333;">
                            {html.escape(messages_cmd)}
                        </code>
                        <button onclick='navigator.clipboard.writeText(`{messages_cmd_js}`).then(() => {{ this.innerHTML = "✓"; setTimeout(() => this.innerHTML = "📋", 2000); }})'
                                style="background: #4caf50; color: white; border: none; padding: 10px 15px; border-radius: 6px; cursor: pointer; font-size: 14px; transition: all 0.2s ease; flex-shrink: 0; font-weight: 600;"
                                onmouseover="this.style.background='#45a049'" onmouseout="this.style.background='#4caf50'">
                            📋
                        </button>
                        <button onclick='runRemoteCommand("{machine_name}", `{messages_cmd_js}`, "messages")'
                                class="run-command-button"
                                style="background: #2196F3; color: white; border: none; padding: 10px 15px; border-radius: 6px; cursor: pointer; font-size: 14px; transition: all 0.2s ease; flex-shrink: 0; font-weight: 600;"
                                onmouseover="this.style.background='#1976D2'" onmouseout="this.style.background='#2196F3'"
                                title="Run command on {machine_name}">
                            ▶️
                        </button>
                    </div>
                </div>

                <!-- Gauge Command -->
                <div style="background: white; border-radius: 10px; padding: 15px; margin-bottom: 12px; box-shadow: 0 2px 10px rgba(0,0,0,0.1);">
                    <p style="margin: 0 0 8px 0; color: #333; font-size: 15px; font-weight: 600;">📊 Gauge Command:</p>
                    <div style="display: flex; align-items: center; gap: 10px;">
                        <code style="flex: 1; background: #1a1a1a; color: #00ff00; padding: 12px 16px; border-radius: 6px; font-family: 'Consolas', 'Monaco', 'Courier New', monospace; font-size: 13px; overflow-x: auto; white-space: nowrap; display: block; border: 1px solid #333;">
                            {html.escape(gauge_cmd)}
                        </code>
                        <button onclick='navigator.clipboard.writeText(`{gauge_cmd_js}`).then(() => {{ this.innerHTML = "✓"; setTimeout(() => this.innerHTML = "📋", 2000); }})'
                                style="background: #4caf50; color: white; border: none; padding: 10px 15px; border-radius: 6px; cursor: pointer; font-size: 14px; transition: all 0.2s ease; flex-shrink: 0; font-weight: 600;"
                                onmouseover="this.style.background='#45a049'" onmouseout="this.style.background='#4caf50'">
                            📋
                        </button>
                        <button onclick='runRemoteCommand("{machine_name}", `{gauge_cmd_js}`, "gauge")'
                                class="run-command-button"
                                style="background: #2196F3; color: white; border: none; padding: 10px 15px; border-radius: 6px; cursor: pointer; font-size: 14px; transition: all 0.2s ease; flex-shrink: 0; font-weight: 600;"
                                onmouseover="this.style.background='#1976D2'" onmouseout="this.style.background='#2196F3'"
                                title="Run command on {machine_name}">
                            ▶️
                        </button>
                    </div>
                </div>

                <!-- Raw Data Command -->
                <div style="background: white; border-radius: 10px; padding: 15px; margin-bottom: 12px; box-shadow: 0 2px 10px rgba(0,0,0,0.1);">
                    <p style="margin: 0 0 8px 0; color: #333; font-size: 15px; font-weight: 600;">💾 Raw Data Command:</p>
                    <div style="display: flex; align-items: center; gap: 10px;">
                        <code style="flex: 1; background: #1a1a1a; color: #00ff00; padding: 12px 16px; border-radius: 6px; font-family: 'Consolas', 'Monaco', 'Courier New', monospace; font-size: 13px; overflow-x: auto; white-space: nowrap; display: block; border: 1px solid #333;">
                            {html.escape(raw_data_cmd)}
                        </code>
                        <button onclick='navigator.clipboard.writeText(`{raw_data_cmd_js}`).then(() => {{ this.innerHTML = "✓"; setTimeout(() => this.innerHTML = "📋", 2000); }})'
                                style="background: #4caf50; color: white; border: none; padding: 10px 15px; border-radius: 6px; cursor: pointer; font-size: 14px; transition: all 0.2s ease; flex-shrink: 0; font-weight: 600;"
                                onmouseover="this.style.background='#45a049'" onmouseout="this.style.background='#4caf50'">
                            📋
                        </button>
                        <button onclick='runRemoteCommand("{machine_name}", `{raw_data_cmd_js}`, "raw_data")'
                                class="run-command-button"
                                style="background: #2196F3; color: white; border: none; padding: 10px 15px; border-radius: 6px; cursor: pointer; font-size: 14px; transition: all 0.2s ease; flex-shrink: 0; font-weight: 600;"
                                onmouseover="this.style.background='#1976D2'" onmouseout="this.style.background='#2196F3'"
                                title="Run command on {machine_name}">
                            ▶️
                        </button>
                    </div>
                </div>
            </div>
        </div>

        """

        return html_content

    except Exception as e:
        logger.error(f"Error generating IMEI commands: {str(e)}")
        return f'<div style="color: red;">Error generating commands: {html.escape(str(e))}</div>'
