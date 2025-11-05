# services/ai-gateway/core/file_system_controller.py
import os
import glob
import asyncio
from typing import List, Dict, Any, Optional
from pathlib import Path
import logging
from datetime import datetime, timedelta

class FileSystemController:
    def __init__(self):
        self.recent_files = []
        self.is_initialized = False

    async def initialize(self):
        """Initialize the file system controller"""
        try:
            await self._load_recent_files()
            self.is_initialized = True
            logging.info("File System Controller initialized successfully")
        except Exception as e:
            logging.error(f"File System Controller initialization failed: {e}")
            raise

    async def search_files(self, query: str, directory: Optional[str] = None, 
                         file_types: List[str] = None, content_search: bool = False,
                         use_semantic: bool = True) -> List[Dict[str, Any]]:
        """Search for files with various criteria"""
        try:
            search_dir = directory or os.path.expanduser("~")
            file_types = file_types or []
            
            if use_semantic and content_search:
                results = await self._semantic_search(query, search_dir, file_types)
            elif content_search:
                results = await self._content_search(query, search_dir, file_types)
            else:
                results = await self._filename_search(query, search_dir, file_types)
            
            # Sort by relevance and return
            sorted_results = sorted(results, key=lambda x: x.get('relevance', 0), reverse=True)
            return sorted_results[:50]  # Limit results
            
        except Exception as e:
            logging.error(f"File search failed: {e}")
            raise

    async def organize_files(self, directory: str, strategy: str = "type") -> Dict[str, Any]:
        """Organize files in a directory using specified strategy"""
        try:
            target_dir = Path(directory)
            if not target_dir.exists():
                raise ValueError(f"Directory {directory} does not exist")
            
            organized_count = 0
            categories = {}
            
            for file_path in target_dir.iterdir():
                if file_path.is_file():
                    category = await self._categorize_file(file_path, strategy)
                    
                    if category not in categories:
                        categories[category] = []
                    
                    # Create category directory if it doesn't exist
                    category_dir = target_dir / category
                    category_dir.mkdir(exist_ok=True)
                    
                    # Move file to category directory
                    new_path = category_dir / file_path.name
                    file_path.rename(new_path)
                    categories[category].append(str(new_path))
                    organized_count += 1
            
            return {
                'strategy': strategy,
                'directory': directory,
                'files_organized': organized_count,
                'categories': categories
            }
            
        except Exception as e:
            logging.error(f"File organization failed: {e}")
            raise

    async def get_recent_files(self, limit: int = 20, file_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get recently accessed files"""
        try:
            recent_files = await self._get_recent_files_system()
            
            if file_type:
                recent_files = [f for f in recent_files if f.get('type') == file_type]
            
            return recent_files[:limit]
            
        except Exception as e:
            logging.error(f"Failed to get recent files: {e}")
            return []

    async def health_check(self) -> bool:
        """Health check for file system controller"""
        return self.is_initialized

    # Private helper methods
    async def _semantic_search(self, query: str, directory: str, file_types: List[str]) -> List[Dict[str, Any]]:
        """Semantic file search using AI/ML"""
        # This would integrate with your AI models for semantic understanding
        # For now, fall back to enhanced keyword search
        return await self._enhanced_keyword_search(query, directory, file_types)

    async def _content_search(self, query: str, directory: str, file_types: List[str]) -> List[Dict[str, Any]]:
        """Search file contents for the query"""
        results = []
        
        try:
            # Use platform-specific tools for content search
            if os.name == 'posix':  # Linux/Mac
                # Use grep for content search
                file_pattern = f"*.{{{','.join(file_types)}}}" if file_types else "*"
                cmd = f"grep -rl '{query}' {directory} --include='{file_pattern}'"
                process = await asyncio.create_subprocess_shell(
                    cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                stdout, stderr = await process.communicate()
                
                if stdout:
                    file_paths = stdout.decode().splitlines()
                    for file_path in file_paths:
                        if os.path.isfile(file_path):
                            stat = os.stat(file_path)
                            results.append({
                                'path': file_path,
                                'name': os.path.basename(file_path),
                                'size': stat.st_size,
                                'modified': datetime.fromtimestamp(stat.st_mtime),
                                'type': os.path.splitext(file_path)[1],
                                'relevance': 0.8  # Content matches are highly relevant
                            })
            
        except Exception as e:
            logging.warning(f"Content search failed, falling back to filename search: {e}")
            results = await self._filename_search(query, directory, file_types)
        
        return results

    async def _filename_search(self, query: str, directory: str, file_types: List[str]) -> List[Dict[str, Any]]:
        """Search files by filename"""
        results = []
        search_dir = Path(directory)
        
        try:
            # Build search pattern
            if file_types:
                patterns = [f"*{query}*.{ext}" for ext in file_types]
            else:
                patterns = [f"*{query}*"]
            
            # Search for files matching patterns
            for pattern in patterns:
                for file_path in search_dir.rglob(pattern):
                    if file_path.is_file():
                        try:
                            stat = file_path.stat()
                            relevance = self._calculate_relevance(file_path.name, query)
                            
                            results.append({
                                'path': str(file_path),
                                'name': file_path.name,
                                'size': stat.st_size,
                                'modified': datetime.fromtimestamp(stat.st_mtime),
                                'type': file_path.suffix,
                                'relevance': relevance
                            })
                        except (OSError, PermissionError):
                            continue  # Skip files we can't access
            
        except Exception as e:
            logging.error(f"Filename search failed: {e}")
        
        return results

    async def _enhanced_keyword_search(self, query: str, directory: str, file_types: List[str]) -> List[Dict[str, Any]]:
        """Enhanced keyword search with relevance scoring"""
        filename_results = await self._filename_search(query, directory, file_types)
        
        # Enhance with additional metadata and relevance scoring
        for result in filename_results:
            # Add additional relevance factors
            path_relevance = self._calculate_path_relevance(result['path'], query)
            result['relevance'] = max(result['relevance'], path_relevance)
            
            # Add file category
            result['category'] = await self._get_file_category(result['path'])
        
        return filename_results

    async def _categorize_file(self, file_path: Path, strategy: str) -> str:
        """Categorize a file based on the specified strategy"""
        if strategy == "type":
            return self._get_file_category(str(file_path))
        elif strategy == "date":
            stat = file_path.stat()
            file_date = datetime.fromtimestamp(stat.st_mtime)
            return file_date.strftime("%Y-%m")
        elif strategy == "size":
            stat = file_path.stat()
            size_mb = stat.st_size / (1024 * 1024)
            if size_mb < 1:
                return "small"
            elif size_mb < 10:
                return "medium"
            else:
                return "large"
        else:
            return "other"

    def _get_file_category(self, file_path: str) -> str:
        """Get file category based on extension"""
        extension = Path(file_path).suffix.lower()
        
        categories = {
            '.pdf': 'documents',
            '.doc': 'documents', '.docx': 'documents',
            '.txt': 'documents', '.rtf': 'documents',
            '.jpg': 'images', '.jpeg': 'images', '.png': 'images',
            '.gif': 'images', '.bmp': 'images', '.svg': 'images',
            '.mp4': 'videos', '.avi': 'videos', '.mov': 'videos',
            '.mkv': 'videos', '.mpg': 'videos',
            '.mp3': 'audio', '.wav': 'audio', '.flac': 'audio',
            '.aac': 'audio', '.ogg': 'audio',
            '.zip': 'archives', '.rar': 'archives', '.7z': 'archives',
            '.tar': 'archives', '.gz': 'archives',
            '.exe': 'executables', '.msi': 'executables',
            '.py': 'code', '.js': 'code', '.html': 'code',
            '.css': 'code', '.json': 'code', '.xml': 'code'
        }
        
        return categories.get(extension, 'other')

    def _calculate_relevance(self, filename: str, query: str) -> float:
        """Calculate relevance score for a filename match"""
        filename_lower = filename.lower()
        query_lower = query.lower()
        
        relevance = 0.0
        
        # Exact match
        if filename_lower == query_lower:
            relevance += 1.0
        # Starts with query
        elif filename_lower.startswith(query_lower):
            relevance += 0.8
        # Contains query
        elif query_lower in filename_lower:
            relevance += 0.6
        # Partial match (words)
        else:
            query_words = query_lower.split()
            filename_words = filename_lower.replace('_', ' ').replace('-', ' ').split()
            matching_words = sum(1 for word in query_words if any(f_word.startswith(word) for f_word in filename_words))
            relevance += matching_words * 0.2
        
        return min(relevance, 1.0)

    def _calculate_path_relevance(self, file_path: str, query: str) -> float:
        """Calculate relevance based on file path"""
        path_lower = file_path.lower()
        query_lower = query.lower()
        
        if query_lower in path_lower:
            # Higher relevance if query appears in directory names
            path_parts = path_lower.split(os.sep)
            if any(query_lower in part for part in path_parts[:-1]):  # Exclude filename
                return 0.7
            return 0.4
        return 0.0

    async def _get_recent_files_system(self) -> List[Dict[str, Any]]:
        """Get recently accessed files from system"""
        # This would use platform-specific methods to get recent files
        # For now, return a mock implementation
        return [
            {
                'path': '/Users/test/documents/report.pdf',
                'name': 'report.pdf',
                'type': '.pdf',
                'last_accessed': datetime.now() - timedelta(hours=1),
                'size': 1024000
            }
        ]

    async def _load_recent_files(self):
        """Load recent files from cache"""
        # In production, this would load from a persistent cache
        self.recent_files = []
