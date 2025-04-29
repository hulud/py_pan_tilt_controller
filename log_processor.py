#!/usr/bin/env python3
"""
Log Processor for Pan-Tilt Control System

This script processes log files and splits them into separate streams based on 
logger name and level as specified in the configuration.

Usage:
    python log_processor.py input_log.log

Output:
    - <logger>.log files for each logger channel
    - summary.json with statistics
"""
import sys
import re
import json
import os
import yaml
from collections import Counter

def load_config():
    """Load configuration from YAML file"""
    config_path = os.path.join('config', 'settings.yaml')
    if not os.path.exists(config_path):
        print(f"Warning: Configuration file {config_path} not found. Using defaults.")
        return {}
    
    with open(config_path, 'r') as f:
        return yaml.safe_load(f)

def process_logs(input_file, loggers=None, level_rules=None, outputs=None):
    """
    Process logs according to the specified rules.
    
    Args:
        input_file: Path to the input log file
        loggers: List of logger names to extract
        level_rules: Dictionary mapping logger patterns to minimum log levels
        outputs: Dictionary specifying output file paths
        
    Returns:
        Dictionary with processing statistics
    """
    # Try to load from YAML config first
    config = load_config()
    log_config = config.get('logging', {})
    
    if loggers is None:
        # Use loggers from config if available
        if 'loggers' in log_config:
            loggers = list(log_config['loggers'].keys())
        else:
            loggers = [
                "run_all", 
                "run_all.server_thread", 
                "run_all.server_thread.serial_tx",
                "run_all.server_thread.serial_rx", 
                "run_all.server_thread.zero_point",
                "run_all.server_thread.parser", 
                "run_all.client_thread", 
                "gui_client.api_client"
            ]
    
    if level_rules is None:
        # Use patterns from config if available
        if 'patterns' in log_config:
            level_rules = log_config['patterns']
        else:
            level_rules = {
                "*.serial_*": "DEBUG",
                "*": "INFO"
            }
    
    if outputs is None:
        outputs = {
            "<logger>.log": "all routed entries",
            "summary.json": "summary report"
        }
    
    # Setup level hierarchy
    level_hierarchy = {
        "DEBUG": 0,
        "INFO": 1,
        "WARNING": 2,
        "ERROR": 3,
        "CRITICAL": 4
    }
    
    # Compile logger pattern matchers
    pattern_matchers = {}
    for pattern, level in level_rules.items():
        if "*" in pattern:
            regex_pattern = pattern.replace(".", "\\.").replace("*", ".*")
            pattern_matchers[re.compile(f"^{regex_pattern}$")] = level
        else:
            pattern_matchers[re.compile(f"^{pattern}$")] = level
    
    # Setup counters and stats
    stats = {
        "total_lines": 0,
        "processed_lines": 0,
        "lines_per_logger": {logger: 0 for logger in loggers},
        "top_warnings": Counter()
    }
    
    # Open output files
    output_files = {}
    for logger in loggers:
        output_path = outputs.get("<logger>.log", "").replace("<logger>", logger)
        if output_path:
            output_files[logger] = open(f"{logger}.log", "w")
    
    # Parse log lines
    log_pattern = re.compile(r'(\d+:\d+:\d+\.\d+) - ([^-]+) - ([^-]+) - (.+)')
    
    with open(input_file, 'r') as f:
        for line in f:
            stats["total_lines"] += 1
            match = log_pattern.match(line.strip())
            
            if not match:
                continue
                
            timestamp, logger_name, level, message = match.groups()
            logger_name = logger_name.strip()
            level = level.strip()
            
            # Skip if not in our target loggers
            if logger_name not in loggers:
                continue
            
            # Determine minimum level for this logger
            min_level = "INFO"  # Default
            for pattern, pattern_level in pattern_matchers.items():
                if pattern.match(logger_name):
                    min_level = pattern_level
                    break
            
            # Skip if below minimum level
            if level_hierarchy.get(level, 0) < level_hierarchy.get(min_level, 0):
                continue
            
            # Process the line
            stats["processed_lines"] += 1
            stats["lines_per_logger"][logger_name] = stats["lines_per_logger"].get(logger_name, 0) + 1
            
            # Store warning messages for parser
            if logger_name == "run_all.server_thread.parser" and level == "WARNING":
                stats["top_warnings"][message] += 1
            
            # Write to output file
            if logger_name in output_files:
                output_files[logger_name].write(line)
    
    # Close output files
    for f in output_files.values():
        f.close()
    
    # Generate summary report
    stats["top_warnings"] = dict(stats["top_warnings"].most_common(5))
    
    summary_path = outputs.get("summary.json", "")
    if summary_path:
        with open(summary_path, "w") as f:
            json.dump(stats, f, indent=2)
    
    return stats

def main():
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} <input_log_file>")
        return 1
    
    input_file = sys.argv[1]
    if not os.path.exists(input_file):
        print(f"Error: Input file '{input_file}' not found")
        return 1
    
    try:
        stats = process_logs(input_file)
        print(f"Processed {stats['processed_lines']} of {stats['total_lines']} lines")
        print("\nLines per logger:")
        for logger, count in stats['lines_per_logger'].items():
            print(f"  {logger}: {count}")
        
        print("\nTop 5 parser warnings:")
        for warning, count in stats['top_warnings'].items():
            print(f"  [{count}] {warning}")
        
        print(f"\nOutput files created: {list(stats['lines_per_logger'].keys())}")
        print("Summary written to: summary.json")
        return 0
    
    except Exception as e:
        print(f"Error processing logs: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
