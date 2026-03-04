#!/usr/bin/env python3
"""
File Naming Conventions & Auto-cleanup
Standardizes file naming across projects and cleans up temporary files
"""

import os
import re
import sys
import glob
import logging
from datetime import datetime, timedelta
from pathlib import Path

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)

class FileNamingManager:
    
    # Standard prefixes for different file types
    PREFIXES = {
        'prod': 'Production files (deployed)',
        'test': 'Test files (temporary)',
        'temp': 'Temporary files (auto-cleanup)',
        'debug': 'Debug files (auto-cleanup)',
        'backup': 'Backup files (preserve)',
        'draft': 'Draft files (review periodically)',
        'archive': 'Archive files (long-term storage)'
    }
    
    # File patterns to auto-cleanup (older than specified days)
    CLEANUP_PATTERNS = {
        'temp_*.py': 1,      # Temp Python files after 1 day
        'debug_*.py': 3,     # Debug files after 3 days
        'test_*.py': 7,      # Test files after 7 days (unless in tests/)
        'temp_*.json': 1,    # Temp JSON files after 1 day
        'debug_*.log': 7,    # Debug logs after 7 days
        'temp_*.db': 1,      # Temp databases after 1 day
        '*_temp.py': 1,      # Files ending with _temp
        '*_debug.py': 3,     # Files ending with _debug
        '*.tmp': 1,          # Generic temp files
    }
    
    def __init__(self, base_dir: str = None):
        """Initialize with base directory (default: current working directory)"""
        self.base_dir = Path(base_dir or os.getcwd())
        
    def suggest_name(self, current_name: str, file_type: str = None) -> str:
        """Suggest a standardized name for a file"""
        # Remove path, get just filename
        filename = os.path.basename(current_name)
        base, ext = os.path.splitext(filename)
        
        # If already has a standard prefix, return as-is
        for prefix in self.PREFIXES.keys():
            if base.startswith(f"{prefix}_"):
                return current_name
        
        # Auto-detect file type if not specified
        if not file_type:
            file_type = self._detect_file_type(filename, base)
        
        # Generate standardized name
        if file_type:
            new_base = f"{file_type}_{base}"
        else:
            new_base = base
        
        # Clean up the base name
        new_base = self._clean_name(new_base)
        
        return new_base + ext
    
    def _detect_file_type(self, filename: str, base: str) -> str:
        """Auto-detect appropriate file type prefix"""
        
        # Production indicators
        if any(word in base.lower() for word in ['production', 'prod', 'final', 'release']):
            return 'prod'
        
        # Test indicators  
        if any(word in base.lower() for word in ['test', 'testing', 'spec']):
            return 'test'
        
        # Debug indicators
        if any(word in base.lower() for word in ['debug', 'troubleshoot', 'investigate']):
            return 'debug'
        
        # Temporary indicators
        if any(word in base.lower() for word in ['temp', 'temporary', 'tmp', 'scratch']):
            return 'temp'
        
        # Backup indicators
        if any(word in base.lower() for word in ['backup', 'bak', 'copy']):
            return 'backup'
        
        # Draft indicators
        if any(word in base.lower() for word in ['draft', 'wip', 'work_in_progress']):
            return 'draft'
        
        return None
    
    def _clean_name(self, name: str) -> str:
        """Clean up filename to follow conventions"""
        # Convert to lowercase
        name = name.lower()
        
        # Replace spaces and special chars with underscores
        name = re.sub(r'[^\w\-_.]', '_', name)
        
        # Remove multiple underscores
        name = re.sub(r'_+', '_', name)
        
        # Remove leading/trailing underscores
        name = name.strip('_')
        
        return name
    
    def organize_directory(self, directory: str = None, dry_run: bool = True) -> dict:
        """Organize files in directory according to naming conventions"""
        target_dir = Path(directory or self.base_dir)
        results = {
            'renamed': [],
            'suggestions': [],
            'cleanup_candidates': [],
            'organized': []
        }
        
        logger.info(f"Organizing directory: {target_dir}")
        
        # Find files that could be better named
        for file_path in target_dir.glob("*.py"):
            if file_path.is_file():
                current_name = file_path.name
                suggested_name = self.suggest_name(current_name)
                
                if suggested_name != current_name:
                    results['suggestions'].append({
                        'current': str(file_path),
                        'suggested': str(file_path.parent / suggested_name),
                        'reason': f"Standardize with prefix"
                    })
        
        # Find cleanup candidates
        for pattern, max_age_days in self.CLEANUP_PATTERNS.items():
            for file_path in target_dir.glob(pattern):
                if file_path.is_file():
                    file_age = datetime.now() - datetime.fromtimestamp(file_path.stat().st_mtime)
                    if file_age.days > max_age_days:
                        results['cleanup_candidates'].append({
                            'file': str(file_path),
                            'age_days': file_age.days,
                            'max_age': max_age_days,
                            'pattern': pattern
                        })
        
        # Execute changes if not dry run
        if not dry_run:
            self._execute_organization(results, target_dir)
        
        return results
    
    def _execute_organization(self, results: dict, target_dir: Path):
        """Execute the organization changes"""
        
        # Apply renames
        for suggestion in results['suggestions']:
            old_path = Path(suggestion['current'])
            new_path = Path(suggestion['suggested'])
            
            if not new_path.exists():
                try:
                    old_path.rename(new_path)
                    results['renamed'].append(suggestion)
                    logger.info(f"Renamed: {old_path.name} → {new_path.name}")
                except Exception as e:
                    logger.error(f"Failed to rename {old_path}: {e}")
        
        # Clean up old files (move to archive)
        archive_dir = target_dir / "archive" / datetime.now().strftime("%Y-%m-%d")
        archive_dir.mkdir(parents=True, exist_ok=True)
        
        for candidate in results['cleanup_candidates']:
            file_path = Path(candidate['file'])
            archive_path = archive_dir / file_path.name
            
            try:
                file_path.rename(archive_path)
                results['organized'].append({
                    'file': str(file_path),
                    'archived_to': str(archive_path)
                })
                logger.info(f"Archived: {file_path.name}")
            except Exception as e:
                logger.error(f"Failed to archive {file_path}: {e}")
    
    def create_file_with_standard_name(self, base_name: str, file_type: str, 
                                     extension: str = '.py') -> str:
        """Create a new file with standardized naming"""
        
        if file_type not in self.PREFIXES:
            raise ValueError(f"Unknown file type: {file_type}. Valid types: {list(self.PREFIXES.keys())}")
        
        # Clean the base name
        clean_base = self._clean_name(base_name)
        
        # Add timestamp for temp/debug files
        if file_type in ['temp', 'debug']:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{file_type}_{clean_base}_{timestamp}{extension}"
        else:
            filename = f"{file_type}_{clean_base}{extension}"
        
        filepath = self.base_dir / filename
        
        # Create the file with a header comment
        if extension == '.py':
            header = f'''#!/usr/bin/env python3
"""
{self.PREFIXES[file_type]} - {base_name}
Created: {datetime.now().isoformat()}
Type: {file_type}
"""

# Your code here
'''
        else:
            header = f"# {self.PREFIXES[file_type]} - {base_name}\n# Created: {datetime.now().isoformat()}\n\n"
        
        with open(filepath, 'w') as f:
            f.write(header)
        
        logger.info(f"Created: {filename}")
        return str(filepath)
    
    def report_status(self, directory: str = None) -> dict:
        """Generate a status report of file organization"""
        target_dir = Path(directory or self.base_dir)
        
        stats = {
            'total_files': 0,
            'by_prefix': {},
            'cleanup_needed': 0,
            'well_organized': 0
        }
        
        # Count files by prefix
        for file_path in target_dir.glob("*.*"):
            if file_path.is_file():
                stats['total_files'] += 1
                
                # Check prefix
                basename = file_path.stem
                found_prefix = None
                for prefix in self.PREFIXES.keys():
                    if basename.startswith(f"{prefix}_"):
                        found_prefix = prefix
                        break
                
                if found_prefix:
                    stats['by_prefix'][found_prefix] = stats['by_prefix'].get(found_prefix, 0) + 1
                    stats['well_organized'] += 1
                else:
                    stats['by_prefix']['no_prefix'] = stats['by_prefix'].get('no_prefix', 0) + 1
        
        # Check cleanup candidates
        for pattern, max_age_days in self.CLEANUP_PATTERNS.items():
            for file_path in target_dir.glob(pattern):
                if file_path.is_file():
                    file_age = datetime.now() - datetime.fromtimestamp(file_path.stat().st_mtime)
                    if file_age.days > max_age_days:
                        stats['cleanup_needed'] += 1
        
        return stats


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 file-naming-conventions.py <command> [args]")
        print("Commands:")
        print("  status [directory]              - Show file organization status")
        print("  suggest <filename>              - Suggest standardized name")
        print("  organize [directory] [--apply]  - Organize directory (dry-run by default)")
        print("  create <name> <type> [ext]      - Create file with standard name")
        print("  types                           - Show available file types")
        sys.exit(1)
    
    command = sys.argv[1]
    manager = FileNamingManager()
    
    if command == "types":
        print("📋 Available File Types:")
        for prefix, description in manager.PREFIXES.items():
            print(f"   {prefix}: {description}")
    
    elif command == "status":
        directory = sys.argv[2] if len(sys.argv) > 2 else None
        stats = manager.report_status(directory)
        
        print("📊 File Organization Status")
        print(f"   Total files: {stats['total_files']}")
        print(f"   Well organized: {stats['well_organized']} ({stats['well_organized']/stats['total_files']*100:.1f}%)" if stats['total_files'] > 0 else "   No files found")
        print(f"   Cleanup needed: {stats['cleanup_needed']}")
        
        if stats['by_prefix']:
            print("\n📂 Files by type:")
            for prefix, count in sorted(stats['by_prefix'].items()):
                print(f"   {prefix}: {count}")
    
    elif command == "suggest" and len(sys.argv) >= 3:
        filename = sys.argv[2]
        suggested = manager.suggest_name(filename)
        print(f"Current:   {filename}")
        print(f"Suggested: {suggested}")
    
    elif command == "organize":
        directory = None
        apply = False
        
        for arg in sys.argv[2:]:
            if arg == "--apply":
                apply = True
            else:
                directory = arg
        
        results = manager.organize_directory(directory, dry_run=not apply)
        
        print(f"🗂️  Organization Results ({'APPLIED' if apply else 'DRY RUN'})")
        print(f"   Rename suggestions: {len(results['suggestions'])}")
        print(f"   Cleanup candidates: {len(results['cleanup_candidates'])}")
        
        if results['suggestions']:
            print("\n📝 Rename Suggestions:")
            for suggestion in results['suggestions'][:5]:  # Show first 5
                print(f"   {os.path.basename(suggestion['current'])} → {os.path.basename(suggestion['suggested'])}")
            if len(results['suggestions']) > 5:
                print(f"   ... and {len(results['suggestions']) - 5} more")
        
        if results['cleanup_candidates']:
            print("\n🧹 Cleanup Candidates:")
            for candidate in results['cleanup_candidates'][:5]:  # Show first 5
                print(f"   {os.path.basename(candidate['file'])} ({candidate['age_days']} days old)")
            if len(results['cleanup_candidates']) > 5:
                print(f"   ... and {len(results['cleanup_candidates']) - 5} more")
        
        if not apply:
            print(f"\n💡 Run with --apply to execute changes")
    
    elif command == "create" and len(sys.argv) >= 4:
        name = sys.argv[2]
        file_type = sys.argv[3]
        extension = sys.argv[4] if len(sys.argv) > 4 else '.py'
        
        try:
            filepath = manager.create_file_with_standard_name(name, file_type, extension)
            print(f"Created: {filepath}")
        except ValueError as e:
            print(f"Error: {e}")
    
    else:
        print("Invalid command or missing arguments")
        sys.exit(1)


if __name__ == "__main__":
    main()